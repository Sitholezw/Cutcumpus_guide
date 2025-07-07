from flask import Blueprint, request, jsonify, current_app, render_template_string
import numpy as np
import json
from sentence_transformers import SentenceTransformer
import datetime
import pdfplumber
from werkzeug.utils import secure_filename
import re
import os

# Create a Blueprint for the app
main = Blueprint('main', __name__)
bp = Blueprint('routes', __name__)

# Load the model once at startup
model = SentenceTransformer('all-MiniLM-L6-v2')
model_ready = [True]

# Load the FAQ data from faqs.json
with open('faqs.json', encoding='utf-8') as f:
    FAQS_DATA = json.load(f)

# Precompute embeddings
question_embeddings_cache = model.encode([item["question"] for item in FAQS_DATA])

def search_answer(question, faqs_data, embeddings_cache, top_k=1):
    question_embedding = model.encode([question])
    similarities = np.dot(embeddings_cache, question_embedding[0])
    top_indices = np.argsort(similarities)[::-1][:top_k]
    results = []
    for idx in top_indices:
        results.append((faqs_data[idx], similarities[idx]))
    return results

@bp.route('/model_status')
def model_status():
    return jsonify({'ready': model_ready[0]})

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>CUT | FAQ Chatbot </title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" type="image/png" href="{{ url_for('static', filename='assets/images/favicon.png') }}">
  <style>
    :root {
      --bg: url('{{ url_for('static', filename='assets/images/background.jpg') }}') center/cover no-repeat fixed, linear-gradient(135deg, #e0e7ff 0%, #f4f7fa 100%);
      --bubble-bot: #f1f5fb;
      --bubble-user: #2563eb;
      --bubble-shadow: 0 2px 8px rgba(0,0,0,0.07);
      --text: #222;
      --bot-avatar-bg: #2563eb;
      --bot-avatar-color: #fff;
    }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: background 0.3s;
    }
    h1 {
      margin-top: 40px;
      color: #222;
      font-weight: 700;
      letter-spacing: 1px;
      text-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    #headman {
      /* Default color, will be overridden in dark mode */
      color: #222;
    }
    #chatbox {
      width: 100%;
      max-width: 420px;
      background: rgba(255, 255, 255, 0.55); /* semi-transparent white */
      border-radius: 18px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.10);
      padding: 28px 18px 18px 18px;
      margin: 30px 0 0 0;
      min-height: 340px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      overflow-y: auto;
      transition: box-shadow 0.2s;
      backdrop-filter: blur(12px); /* glass effect */
      -webkit-backdrop-filter: blur(12px); /* Safari support */
    }
    .bubble {
      max-width: 80%;
      padding: 14px 20px;
      border-radius: 22px;
      margin-bottom: 6px;
      font-size: 1rem;
      line-height: 1.6;
      word-break: break-word;
      display: flex;
      align-items: flex-end;
      box-shadow: var(--bubble-shadow);
      position: relative;
      opacity: 0;
      animation: fadeIn 0.4s forwards;
    }
    @keyframes fadeIn {
      to { opacity: 1; }
    }
    .user {
      align-self: flex-end;
      background: var(--bubble-user);
      color: #fff;
      border-bottom-right-radius: 8px;
      justify-content: flex-end;
    }
    .bot {
      align-self: flex-start;
      background: var(--bubble-bot);
      color: var(--text);
      border-bottom-left-radius: 8px;
      justify-content: flex-start;
    }
    .bot-avatar {
      width: 32px;
      height: 32px;
      background: var(--bot-avatar-bg);
      color: var(--bot-avatar-color);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.3em;
      margin-right: 10px;
      flex-shrink: 0;
      box-shadow: 0 1px 4px rgba(37,99,235,0.10);
    }
    .bubble-content {
      flex: 1;
    }
    .copy-btn {
      background: none;
      border: none;
      color: #2563eb;
      font-size: 0.9em;
      cursor: pointer;
      margin-left: 8px;
      padding: 0;
      transition: color 0.2s;
    }
    .copy-btn:hover {
      color: #1e40af;
    }
    .timestamp {
      font-size: 0.75em;
      color: #888;
      margin-top: 4px;
      margin-left: 2px;
    }
    #inputArea {
      width: 100%;
      max-width: 420px;
      display: flex;
      gap: 8px;
      margin-top: 18px;
      align-items: center;
    }
    #questionInput {
      flex: 1;
      padding: 13px;
      border-radius: 10px;
      border: 1.5px solid #c7d2fe;
      font-size: 1rem;
      outline: none;
      transition: border 0.2s;
      background: #f8fafc;
    }
    #questionInput:focus {
      border: 1.5px solid #2563eb;
      background: #fff;
    }
    #sendBtn {
      background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 0 22px;
      font-size: 1rem;
      cursor: pointer;
      transition: background 0.2s;
      height: 44px;
    }
    #sendBtn:disabled {
      background: #a5b4fc;
      cursor: not-allowed;
    }
    #sendBtn:hover:not(:disabled) {
      background: #1e40af;
    }
    #faqSuggestions {
      margin-top: 18px;
      font-size: 0.98rem;
      color: #555;
      width: 100%;
      max-width: 420px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    #faqSuggestions button {
      background: #e0e7ff;
      color: #2563eb;
      border: 1px solid #c7d2fe;
      border-radius: 8px;
      padding: 8px 12px;
      cursor: pointer;
      transition: background 0.2s, color 0.2s;
      font-size: 0.98em;
    }
    #faqSuggestions button:hover {
      background: #c7d2fe;
      color: #1e40af;
    }
    #themeToggle {
      position: absolute;
      top: 18px;
      right: 18px;
      background: #fff;
      border: none;
      border-radius: 50%;
      width: 38px;
      height: 38px;
      font-size: 1.3em;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      cursor: pointer;
      transition: background 0.2s;
    }
    #themeToggle:hover {
      background: #e0e7ff;
    }
    @media (max-width: 500px) {
      #chatbox, #inputArea, #faqSuggestions {
        max-width: 98vw;
        padding: 0 2vw;
      }
      h1 {
        font-size: 1.2em;
      }
    }
    body.dark {
      --bg: url('{{ url_for('static', filename='assets/images/background.jpg') }}') center/cover no-repeat fixed, linear-gradient(135deg, #23272a 0%, #181a1b 100%);
      --bubble-bot: #23272a;
      --bubble-user: #1e40af;
      --text: #f4f7fa;
      --bot-avatar-bg: #1e40af;
      --bot-avatar-color: #fff;
    }
    body.dark #chatbox {
      background: rgba(24, 26, 27, 0.55); /* semi-transparent dark */
      box-shadow: 0 4px 24px rgba(0,0,0,0.25);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }
    body.dark #questionInput {
      background: #23272a;
      color: #f4f7fa;
      border: 1.5px solid #374151;
    }
    body.dark #questionInput:focus {
      background: #181a1b;
      border: 1.5px solid #2563eb;
    }
    body.dark #sendBtn {
      background: #1e40af;
    }
    body.dark #sendBtn:hover:not(:disabled) {
      background: #2563eb;
    }
    body.dark #faqSuggestions button {
      background: #23272a;
      color: #a5b4fc;
      border: 1px solid #374151;
    }
    body.dark #faqSuggestions button:hover {
      background: #1e293b;
      color: #fff;
    }
    body.dark #themeToggle {
      background: #23272a;
      color: #a5b4fc;
    }
    body.dark #themeToggle:hover {
      background: #1e293b;
    }
    body.dark #headman {
      color: #222;
    }

    /* Responsive styles for mobile */
    @media (max-width: 600px) {
      #chatbox,
      #inputArea,
      #faqSuggestions {
        max-width: 98vw;
        width: 98vw;
        padding-left: 2vw;
        padding-right: 2vw;
        min-width: 0;
      }
      h1 {
        font-size: 1.1em;
        margin-top: 18px;
      }
      #chatbox {
        padding: 18px 6px 12px 6px;
        min-height: 220px;
      }
      #inputArea {
        gap: 4px;
      }
      #faqSuggestions {
        font-size: 0.95em;
        gap: 4px;
      }
      .bubble {
        font-size: 0.98em;
        padding: 10px 12px;
      }
      .bot-avatar {
        width: 26px;
        height: 26px;
        font-size: 1em;
        margin-right: 6px;
      }
    }
    body.dark form textarea,
body.dark form input,
body.dark form select {
  background: #23272a;
  color: var(--text);
  border: 1.5px solid #374151;
}
body.dark form textarea:focus,
body.dark form input:focus,
body.dark form select:focus {
  background: #181a1b;
  border: 1.5px solid var(--primary-dark);
}
  </style>
</head>
<body>
  <h1 id="headman">CUT CHATBOT</h1>
  <button id="themeToggle" title="Toggle theme">🌙</button>
  <div id="chatbox"></div>
  <div id="inputArea">
    <input id="questionInput" placeholder="Type your question..." onkeydown="if(event.key==='Enter'){sendQuestion();}" aria-label="Type your question" autocomplete="off" />
    <button id="sendBtn" onclick="sendQuestion()">Send</button>
  </div>
  <div id="faqSuggestions">
    <strong style="margin-right:8px;">Popular:</strong>
    <button onclick="quickAsk('How do I retrieve my reg number?')">How do I retrieve my reg number?</button>
    <button onclick="quickAsk('How do I accept my offer?')">How do I accept my offer?</button>
    <button onclick="quickAsk('How do I create a strong recommended password ?')">Strong password?</button>
    <button onclick="quickAsk('I cannot log in into the system?')">Cannot log in?</button>
  </div>
  <div id="loadingOverlay" style="position:fixed;top:0;left:0;width:100vw;height:100vh;display:flex;align-items:center;justify-content:center;background:#fff;z-index:9999;">
  <h2 style="text-align:center;">Loading AI model, please wait...</h2>
</div>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script>
    const chatbox = document.getElementById('chatbox');
    const input = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    function addBubble(text, sender) {
      const bubble = document.createElement('div');
      bubble.className = 'bubble ' + sender;
      if (sender === 'bot') {
        // Bot avatar
        const avatar = document.createElement('div');
        avatar.className = 'bot-avatar';
        avatar.innerText = '🤖';
        bubble.appendChild(avatar);

        // Bubble content
        const content = document.createElement('div');
        content.className = 'bubble-content';
        content.innerHTML = marked.parse(text);

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.innerText = 'Copy';
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(content.innerText);
          copyBtn.innerText = 'Copied!';
          setTimeout(() => copyBtn.innerText = 'Copy', 1000);
        };
        content.appendChild(copyBtn);

        // Timestamp
        const time = document.createElement('div');
        time.className = 'timestamp';
        time.innerText = new Date().toLocaleTimeString();
        content.appendChild(time);

        bubble.appendChild(content);
      } else {
        bubble.innerText = text;
        const time = document.createElement('div');
        time.className = 'timestamp';
        time.innerText = new Date().toLocaleTimeString();
        bubble.appendChild(time);
      }
      chatbox.appendChild(bubble);
      chatbox.scrollTop = chatbox.scrollHeight;
    }

    function showTyping() {
      const typing = document.createElement('div');
      typing.id = 'typing-indicator';
      typing.className = 'bubble bot';
      typing.innerHTML = '<div class="bot-avatar">🤖</div><div class="bubble-content">Bot is typing...</div>';
      chatbox.appendChild(typing);
      chatbox.scrollTop = chatbox.scrollHeight;
    }
    function hideTyping() {
      const typing = document.getElementById('typing-indicator');
      if (typing) typing.remove();
    }

    async function sendQuestion() {
      const question = input.value.trim();
      if (!question) return;
      addBubble(question, 'user');
      input.value = '';
      showTyping();
      sendBtn.disabled = true;
      try {
        const res = await fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question })
        });
        let data;
        try {
          data = await res.json();
        } catch (e) {
          data = { answer: "Sorry, something went wrong. Please try again later." };
        }
        hideTyping();
        addBubble(data.answer, 'bot');
      } catch (e) {
        hideTyping();
        addBubble("Sorry, something went wrong. Please try again later.", 'bot');
      }
      sendBtn.disabled = false;
      input.focus();
    }

    function quickAsk(question) {
      input.value = question;
      sendQuestion();
    }

    // Enable send button only if input is not empty
    input.addEventListener('input', () => {
      sendBtn.disabled = input.value.trim().length === 0;
    });

    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    let darkMode = false;
    themeToggle.onclick = () => {
      darkMode = !darkMode;
      if (darkMode) {
        document.body.classList.add('dark');
        themeToggle.innerHTML = '☀️';
        localStorage.setItem('darkMode', 'true');
      } else {
        document.body.classList.remove('dark');
        themeToggle.innerHTML = '🌙';
        localStorage.setItem('darkMode', 'false');
      }
    };
    // Load dark mode preference
    window.onload = () => {
      const darkModePreference = localStorage.getItem('darkMode');
      if (darkModePreference === 'true') {
        darkMode = true;
        document.body.classList.add('dark');
        themeToggle.innerHTML = '☀️';
      } else {
        darkMode = false;
        document.body.classList.remove('dark');
        themeToggle.innerHTML = '🌙';
      }
      if (!chatbox.innerHTML) {
        addBubble("Hi! I'm your CUT FAQ assistant. Ask me anything about the application process.", 'bot');
      }
      input.focus();
    };

    async function waitForModel() {
      let ready = false;
      const overlay = document.getElementById('loadingOverlay');
      while (!ready) {
        const res = await fetch('/model_status');
        const data = await res.json();
        ready = data.ready;
        if (!ready) {
          overlay.style.display = 'flex';
          await new Promise(r => setTimeout(r, 1500));
        }
      }
      overlay.style.display = 'none';
    }

    waitForModel();
  </script>
</body>
</html> """  # Keep all your existing HTML as is

@bp.route('/')
def index():
    return render_template_string(HTML_PAGE)

@bp.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').strip()
    # Log the question
    with open('question_log.txt', 'a', encoding='utf-8') as logf:
        logf.write(f"{datetime.datetime.now().isoformat()} - {question}\n")
    threshold = 0.50  # You can adjust this value
    results = search_answer(question, FAQS_DATA, question_embeddings_cache, top_k=1)
    if results and results[0][1] >= threshold:
        return jsonify({'answer': results[0][0]['answer']})
    return jsonify({'answer': "Sorry, I couldn't find an answer to your question kindly get in touch with the helpdesk at +263672127433."}), 404

@bp.route('/health')
def health():
    return jsonify({'status': 'ok'})

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Test@12345")  # Set a strong password!

@bp.route('/admin', methods=['GET'])
def admin_page():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return "Unauthorized", 401
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <title>CUT | FAQ Admin Panel</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" type="image/png" href="{{ url_for('static', filename='assets/images/favicon.png') }}">
  <style>
    :root {
      --bg: url('{{ url_for('static', filename='assets/images/background.jpg') }}') center/cover no-repeat fixed, linear-gradient(135deg, #e0e7ff 0%, #f4f7fa 100%);
      --glass: rgba(255,255,255,0.55);
      --text: #222;
      --primary: #2563eb;
      --primary-dark: #1e40af;
    }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', Arial, sans-serif;
      margin: 0;
      padding: 0;
      min-height: 100vh;
      transition: background 0.3s;
    }
    .container {
      max-width: 700px;
      margin: 40px auto;
      background: var(--glass);
      border-radius: 18px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.13);
      padding: 36px 28px 28px 28px;
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      position: relative;
    }
    h2 {
      margin-top: 0;
      font-size: 2em;
      letter-spacing: 1px;
      color: var(--primary);
      text-align: center;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }
    h2 img {
      width: 38px;
      height: 38px;
      vertical-align: middle;
    }
    .theme-toggle {
      position: absolute;
      top: 18px;
      right: 18px;
      background: #fff;
      border: none;
      border-radius: 50%;
      width: 38px;
      height: 38px;
      font-size: 1.3em;
      box-shadow: 0 2px 8px rgba(0,0,0,0.07);
      cursor: pointer;
      transition: background 0.2s;
      z-index: 10;
    }
    .theme-toggle:hover {
      background: #e0e7ff;
    }
    .download-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #e0e7ff;
      color: #2563eb;
      border: 1px solid #c7d2fe;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.2s, color 0.2s;
      text-decoration: none;
      margin-bottom: 10px;
    }
    .download-btn:hover {
      background: #2563eb;
      color: #fff;
    }
    .pdf-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #f1f5fb;
      color: #2563eb;
      border: 1px solid #c7d2fe;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.2s, color 0.2s;
      margin-bottom: 18px;
      margin-top: 8px;
    }
    .pdf-btn:hover {
      background: #2563eb;
      color: #fff;
    }
    form {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 18px;
      align-items: flex-end;
    }
    form input, form select {
      padding: 10px;
      border-radius: 8px;
      border: 1.5px solid #c7d2fe;
      font-size: 1em;
      flex: 1 1 180px;
      background: #f8fafc;
      transition: border 0.2s;
    }
    form input:focus, form select:focus {
      border: 1.5px solid var(--primary);
      background: #fff;
      outline: none;
    }
    form button {
      background: var(--primary);
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 10px 22px;
      font-size: 1em;
      cursor: pointer;
      transition: background 0.2s;
    }
    form button:hover {
      background: var(--primary-dark);
    }
    #faqSearch {
      width: 100%;
      margin-bottom: 18px;
      padding: 10px;
      border-radius: 8px;
      border: 1.5px solid #c7d2fe;
      font-size: 1em;
      background: #f8fafc;
      transition: border 0.2s;
    }
    #faqSearch:focus {
      border: 1.5px solid var(--primary);
      background: #fff;
      outline: none;
    }
    .faq-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .faq-item {
      background: rgba(241,245,251,0.85);
      border-radius: 12px;
      margin-bottom: 12px;
      padding: 16px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.04);
      position: relative;
      transition: background 0.2s;
    }
    .faq-actions {
      margin-top: 6px;
      display: flex;
      gap: 10px;
    }
    .faq-actions button {
      background: #fff;
      color: var(--primary);
      border: 1px solid #c7d2fe;
      border-radius: 6px;
      padding: 5px 14px;
      font-size: 0.98em;
      cursor: pointer;
      transition: background 0.2s, color 0.2s;
    }
    .faq-actions button:hover {
      background: var(--primary);
      color: #fff;
    }
    @media (max-width: 700px) {
      .container { padding: 12px 2vw; }
      form { flex-direction: column; gap: 8px; }
      .download-btn { float: none; display: block; width: 100%; margin: 0 0 18px 0; }
    }
    /* DARK MODE */
    body.dark {
      --bg: url('{{ url_for('static', filename='assets/images/background.jpg') }}') center/cover no-repeat fixed, linear-gradient(135deg, #23272a 0%, #181a1b 100%);
      --glass: rgba(24,26,27,0.55);
      --text: #f4f7fa;
      --primary: #a5b4fc;
      --primary-dark: #2563eb;
    }
    body.dark {
      color: var(--text);
    }
    body.dark .container {
      background: var(--glass);
      box-shadow: 0 4px 24px rgba(0,0,0,0.25);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }
    body.dark h2 {
      color: var(--primary);
    }
    body.dark form input, body.dark form select, body.dark #faqSearch {
      background: #23272a;
      color: var(--text);
      border: 1.5px solid #374151;
    }
    body.dark form input:focus, body.dark form select:focus, body.dark #faqSearch:focus {
      background: #181a1b;
      border: 1.5px solid var(--primary-dark);
    }
    body.dark form button, body.dark .faq-actions button {
      background: var(--primary-dark);
      color: #fff;
    }
    body.dark form button:hover, body.dark .faq-actions button:hover {
      background: var(--primary);
      color: #23272a;
    }
    body.dark .faq-item {
      background: rgba(35,39,42,0.85);
      color: var(--text);
    }
    body.dark .download-btn, body.dark .pdf-btn {
      background: #23272a;
      color: var(--primary);
      border: 1px solid #374151;
    }
    body.dark .download-btn:hover, body.dark .pdf-btn:hover {
      background: var(--primary-dark);
      color: #fff;
    }
    body.dark .theme-toggle {
      background: #23272a;
      color: var(--primary);
    }
    body.dark .theme-toggle:hover {
      background: #1e293b;
    }
  </style>
</head>
<body>
  <button class="theme-toggle" id="themeToggle" title="Toggle theme">🌙</button>
  <div class="container">
    <h2>
      <img src="{{ url_for('static', filename='assets/images/favicon.png') }}" alt="icon">
      FAQ Admin Panel
    </h2>
    <div style="margin-bottom:18px;">
  <a href="/admin?pw={{request.args.get('pw')}}">FAQ Admin</a> |
  <a href="/admin/feedback?pw={{request.args.get('pw')}}">Feedback Review</a> 
  
</div>
    <div style="margin: 0 auto 18px auto; display: flex; justify-content: center;">
      <a href="/admin/export?pw={{request.args.get('pw')}}" class="download-btn" download>
        <span>⬇️ Download FAQs (JSON)</span>
      </a>
    </div>
    <form id="pdfForm" enctype="multipart/form-data" style="margin-bottom:18px;">
      <label style="font-weight:600;">Import FAQs from PDF:</label>
      <input type="file" name="pdf" accept="application/pdf" required>
      <button type="submit" class="pdf-btn">Upload PDF</button>
    </form>
    <form id="faqForm">
  <input name="question" placeholder="Question" required>
  <textarea name="answer" placeholder="Answer" required rows="3" style="resize:vertical;width:100%;"></textarea>
  <input name="category" placeholder="Category (optional)">
  <button type="submit">Add FAQ</button>
  <button type="button" id="cancelEditBtn" style="display:none;margin-left:8px;">Cancel Edit</button>
</form>
    <input id="faqSearch" placeholder="Search FAQs...">
    <ul id="faqList" class="faq-list">
      {% for faq in faqs %}
        <li class="faq-item">
          <div><b>Q:</b> {{ faq.question }}</div>
          <div><b>A:</b> {{ faq.answer }}</div>
          {% if faq.category %}
            <div><b>Category:</b> {{ faq.category }}</div>
          {% endif %}
          <div class="faq-actions">
            <button type="button" onclick="editFAQ({{ loop.index0 }})">Edit</button>
            <button type="button" onclick="deleteFAQ({{ loop.index0 }})">Delete</button>
          </div>
        </li>
      {% endfor %}
    </ul>
  </div>
  <script>
    // Theme toggle logic
    const themeToggle = document.getElementById('themeToggle');
    let darkMode = false;
    themeToggle.onclick = () => {
      darkMode = !darkMode;
      if (darkMode) {
        document.body.classList.add('dark');
        themeToggle.innerHTML = '☀️';
        localStorage.setItem('adminDarkMode', 'true');
      } else {
        document.body.classList.remove('dark');
        themeToggle.innerHTML = '🌙';
        localStorage.setItem('adminDarkMode', 'false');
      }
    };
    window.onload = () => {
      const darkModePreference = localStorage.getItem('adminDarkMode');
      if (darkModePreference === 'true') {
        darkMode = true;
        document.body.classList.add('dark');
        themeToggle.innerHTML = '☀️';
      } else {
        darkMode = false;
        document.body.classList.remove('dark');
        themeToggle.innerHTML = '🌙';
      }
    };

    // FAQ logic
    const faqs = {{ faqs|tojson }};

    // Edit FAQ logic
        function editFAQ(index) {
      const faq = faqs[index];
      const form = document.getElementById('faqForm');
      form.question.value = faq.question;
      form.answer.value = faq.answer;
      form.category.value = faq.category || '';
      form.dataset.editing = index;
      form.querySelector('button[type="submit"]').textContent = "Update FAQ";
      // Scroll to the Add/Edit FAQ form
      form.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Optionally, focus the first input
      form.question.focus();
    }

    // Add/Edit form handler
    document.getElementById('faqForm').onsubmit = async function(e) {
      e.preventDefault();
      const form = e.target;
      const editing = form.dataset.editing;
      const url = editing !== undefined && editing !== ""
        ? `/admin/edit?pw={{ request.args.get('pw') }}`
        : `/admin/add?pw={{ request.args.get('pw') }}`;
      const payload = {
        question: form.question.value,
        answer: form.answer.value,
        category: form.category.value || ''
      };
      if (editing !== undefined && editing !== "") payload.index = parseInt(editing);

      const res = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        form.reset();
        form.dataset.editing = "";
        form.querySelector('button[type="submit"]').textContent = "Add FAQ";
        document.getElementById('faqSearch').value = '';
        location.reload();
      } else {
        alert('Failed to ' + (editing !== undefined && editing !== "" ? 'edit' : 'add') + ' FAQ');
      }
    };

    // Delete FAQ
    async function deleteFAQ(index) {
      if (!confirm("Are you sure you want to delete this FAQ?")) return;
      const res = await fetch(`/admin/delete?pw={{ request.args.get('pw') }}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ index })
      });
      if (res.ok) {
        location.reload();
      } else {
        alert('Failed to delete FAQ');
      }
    }

    // PDF upload handler (clear file input after upload)
    document.getElementById('pdfForm').onsubmit = async function(e) {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);
      const res = await fetch('/admin/upload_pdf?pw={{request.args.get("pw")}}', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      form.reset(); // Clear PDF file input after upload
      if (data.status === 'ok') {
        alert('Imported ' + data.added + ' FAQs from PDF!');
        location.reload();
      } else {
        alert('Error: ' + (data.message || 'Could not import PDF'));
      }
    };

    // FAQ search (optional: clear on add/edit)
    document.getElementById('faqSearch').addEventListener('input', function() {
      const val = this.value.toLowerCase();
      document.querySelectorAll('#faqList .faq-item').forEach(li => {
        li.style.display = li.textContent.toLowerCase().includes(val) ? '' : 'none';
      });
    });

  </script>
</body>
</html>
    """, faqs=FAQS_DATA)

@bp.route('/admin/feedback')
def admin_feedback():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return "Unauthorized", 401
    feedbacks = []
    try:
        with open('feedback_log.txt', encoding='utf-8') as f:
            for line in f:
                feedbacks.append(json.loads(line))
    except FileNotFoundError:
        pass
    return render_template_string("""
    <html>
    <head>
      <title>Feedback Review</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f8fafc; color: #222; }
        .container { max-width: 800px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 12px #0001; padding: 32px; }
        h2 { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 24px; }
        th, td { border: 1px solid #e5e7eb; padding: 8px 12px; }
        th { background: #e0e7ff; }
        tr:nth-child(even) { background: #f1f5fb; }
      </style>
    </head>
    <body>
      <div class="container">
        <h2>Feedback Log</h2>
        <table>
          <tr>
            <th>Timestamp</th>
            <th>Question</th>
            <th>Answer</th>
            <th>Feedback</th>
          </tr>
          {% for fb in feedbacks %}
          <tr>
            <td>{{fb.timestamp}}</td>
            <td>{{fb.question}}</td>
            <td>{{fb.answer}}</td>
            <td>{{fb.feedback}}</td>
          </tr>
          {% endfor %}
        </table>
      </div>
    </body>
    </html>
    """, feedbacks=feedbacks)

@bp.route('/admin/add', methods=['POST'])
def admin_add():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return jsonify({'status': 'unauthorized'}), 401
    data = request.get_json()
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    category = data.get('category', '').strip()
    if not question or not answer:
        return jsonify({'status': 'error', 'message': 'Question and answer required'}), 400
    if any(faq['question'].lower() == question.lower() for faq in FAQS_DATA):
        return jsonify({'status': 'error', 'message': 'Duplicate question'}), 400
    FAQS_DATA.append({'question': question, 'answer': answer, 'category': category})
    global question_embeddings_cache
    question_embeddings_cache = model.encode([item["question"] for item in FAQS_DATA])
    with open('faqs.json', 'w', encoding='utf-8') as f:
        json.dump(FAQS_DATA, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'ok'})

@bp.route('/admin/edit', methods=['POST'])
def admin_edit():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return jsonify({'status': 'unauthorized'}), 401
    data = request.get_json()
    idx = int(data['index'])
    FAQS_DATA[idx]['question'] = data['question']
    FAQS_DATA[idx]['answer'] = data['answer']
    FAQS_DATA[idx]['category'] = data.get('category', '')
    with open('faqs.json', 'w', encoding='utf-8') as f:
        json.dump(FAQS_DATA, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'ok'})

@bp.route('/admin/delete', methods=['POST'])
def admin_delete():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return jsonify({'status': 'unauthorized'}), 401
    idx = int(request.get_json()['index'])
    FAQS_DATA.pop(idx)
    with open('faqs.json', 'w', encoding='utf-8') as f:
        json.dump(FAQS_DATA, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'ok'})

@bp.route('/admin/export')
def admin_export():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return "Unauthorized", 401
    return current_app.response_class(
        json.dumps(FAQS_DATA, ensure_ascii=False, indent=2),
        mimetype='application/json',
        headers={"Content-Disposition": "attachment;filename=faqs.json"}
    )

@bp.route('/feedback', methods=['POST'])
def feedback():
    data = request.get_json()
    with open('feedback_log.txt', 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            "question": data.get("question"),
            "answer": data.get("answer"),
            "feedback": data.get("feedback"),
            "timestamp": datetime.datetime.now().isoformat()
        }) + "\n")
    return jsonify({'status': 'ok'})

@bp.route('/admin/upload_pdf', methods=['POST'])
def admin_upload_pdf():
    if request.args.get("pw") != ADMIN_PASSWORD:
        return jsonify({'status': 'unauthorized'}), 401
    if 'pdf' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    file = request.files['pdf']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'status': 'error', 'message': 'Not a PDF file'}), 400

    # Extract text from PDF
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Improved extraction: collect answer lines until next question or end
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    new_faqs = []
    i = 0
    while i < len(lines):
        q_match = re.match(r'^(Q(?:uestion)?[:.\s-]*)\s*(.*)', lines[i], re.I)
        if q_match:
            question = q_match.group(2).strip();
            answer_lines = [];
            i += 1;
            # Collect answer lines until next question or end
            while i < len(lines):
                # Stop if next line is a question
                if re.match(r'^(Q(?:uestion)?[:.\s-]*)\s*', lines[i], re.I):
                    break;
                # If line starts with A: or Answer:, remove that
                a_match = re.match(r'^(A(?:nswer)?[:.\s-]*)\s*(.*)', lines[i], re.I)
                if a_match:
                    answer_lines.append(a_match.group(2).strip())
                else:
                    answer_lines.append(lines[i]);
                i += 1
            answer = " ".join(answer_lines).strip()
            if question and answer:
                new_faqs.append({'question': question, 'answer': answer, 'category': ''})
        else:
            i += 1

    # Add to FAQS_DATA and save
    FAQS_DATA.extend(new_faqs)
    global question_embeddings_cache
    question_embeddings_cache = model.encode([item["question"] for item in FAQS_DATA])
    with open('faqs.json', 'w', encoding='utf-8') as f:
        json.dump(FAQS_DATA, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'ok', 'added': len(new_faqs)})


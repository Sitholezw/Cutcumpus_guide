from flask import Blueprint, request, jsonify, current_app, render_template_string
import numpy as np
import json
from sentence_transformers import SentenceTransformer

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
      background: #181a1b;
      box-shadow: 0 4px 24px rgba(0,0,0,0.25);
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
      color: #fff;
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
        if (!res.ok) throw new Error('Server error');
        const data = await res.json();
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

    matches = search_answer(question, FAQS_DATA, question_embeddings_cache, top_k=1)
    if matches:
        return jsonify({'answer': matches[0]['answer']})
    return jsonify({'answer': "Sorry, I couldn't find an answer to your question."}), 404

@bp.route('/health')
def health():
    return jsonify({'status': 'ok'})

@bp.route('/admin', methods=['GET'])
def admin_page():
    return render_template_string("""
    <h2>FAQ Admin Panel</h2>
    <form id="faqForm">
      <input name="question" placeholder="Question" style="width:300px" required>
      <input name="answer" placeholder="Answer" style="width:300px" required>
      <button type="submit">Add FAQ</button>
    </form>
    <ul id="faqList">
      {% for faq in faqs %}
        <li><b>{{faq.question}}</b>: {{faq.answer}}</li>
      {% endfor %}
    </ul>
    <script>
      document.getElementById('faqForm').onsubmit = async function(e) {
        e.preventDefault();
        const form = e.target;
        const res = await fetch('/admin/add', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ question: form.question.value, answer: form.answer.value })
        });
        if (res.ok) location.reload();
        else alert('Failed to add FAQ');
      }
    </script>
    """, faqs=FAQS_DATA)

@bp.route('/admin/add', methods=['POST'])
def admin_add():
    data = request.get_json()
    FAQS_DATA.append({'question': data['question'], 'answer': data['answer']})
    global question_embeddings_cache
    question_embeddings_cache = model.encode([item["question"] for item in FAQS_DATA])
    # Save back to file
    with open('faqs.json', 'w', encoding='utf-8') as f:
        json.dump(FAQS_DATA, f, ensure_ascii=False, indent=2)
    return jsonify({'status': 'ok'})

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search_answer(user_question, qa_data, question_embeddings, top_k=1):
    user_embedding = model.encode([user_question])[0];
    scores = [cosine_sim(user_embedding, q_emb) for q_emb in question_embeddings];
    top_indices = np.argsort(scores)[::-1][:top_k];
    return [qa_data[i] for i in top_indices]

# Register blueprint in your app.py or main file
# app.register_blueprint(bp)

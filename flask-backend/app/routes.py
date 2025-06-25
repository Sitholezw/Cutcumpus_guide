from flask import Blueprint, request, jsonify, current_app, render_template_string
import difflib

# Create a Blueprint for the app
main = Blueprint('main', __name__)

bp = Blueprint('routes', __name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>FAQ Chatbot</title>
  <style>
    :root {
      --bg: #f4f7fa;
      --bubble-bot: #e9ecef;
      --bubble-user: #0078d7;
      --text: #222;
    }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', Arial, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      margin: 0;
      min-height: 100vh;
    }
    h1 {
      margin-top: 40px;
      color: #333;
    }
    #chatbox {
      width: 100%;
      max-width: 420px;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      padding: 24px 18px 18px 18px;
      margin: 30px 0 0 0;
      min-height: 320px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .bubble {
      max-width: 80%;
      padding: 12px 18px;
      border-radius: 18px;
      margin-bottom: 6px;
      font-size: 1rem;
      line-height: 1.5;
      word-break: break-word;
      display: inline-block;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .user {
      align-self: flex-end;
      background: var(--bubble-user);
      color: #fff;
      border-bottom-right-radius: 6px;
    }
    .bot {
      align-self: flex-start;
      background: var(--bubble-bot);
      color: var(--text);
      border-bottom-left-radius: 6px;
    }
    #inputArea {
      width: 100%;
      max-width: 420px;
      display: flex;
      gap: 8px;
      margin-top: 18px;
    }
    #questionInput {
      flex: 1;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid #ccc;
      font-size: 1rem;
      outline: none;
      transition: border 0.2s;
    }
    #questionInput:focus {
      border: 1.5px solid #0078d7;
    }
    #sendBtn {
      background: #0078d7;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0 22px;
      font-size: 1rem;
      cursor: pointer;
      transition: background 0.2s;
    }
    #sendBtn:hover {
      background: #005fa3;
    }
    #faqSuggestions {
      margin-top: 10px;
      font-size: 0.9rem;
      color: #555;
    }
    #faqSuggestions button {
      background: #e1f5fe;
      color: #01579b;
      border: 1px solid #b3e5fc;
      border-radius: 8px;
      padding: 8px 12px;
      margin-right: 8px;
      cursor: pointer;
      transition: background 0.2s;
    }
    #faqSuggestions button:hover {
      background: #b3e5fc;
    }
    @media (max-width: 500px) {
      #chatbox, #inputArea {
        max-width: 98vw;
        padding: 0 2vw;
      }
    }
  </style>
</head>
<body>
  <h1>Ask us anything</h1>
  <div id="chatbox"></div>
  <div id="inputArea">
    <input id="questionInput" placeholder="Type your question..." onkeydown="if(event.key==='Enter'){sendQuestion();}" aria-label="Type your question" />
    <button id="sendBtn" onclick="sendQuestion()">Send</button>
    <input type="file" id="fileInput" style="display:none" onchange="sendFile()" />
    <button onclick="document.getElementById('fileInput').click()">📎</button>
  </div>
  <div id="faqSuggestions">
    <strong>Popular questions:</strong>
    <button onclick="quickAsk('How do I retrieve my reg number?')">How do I retrieve my reg number?</button>
    <button onclick="quickAsk('How do I accept my offer?')">How do I accept my offer?</button>
    <!-- Add more as needed -->
  </div>
  <button id="themeToggle" style="position:absolute;top:10px;right:10px;">🌙</button>

  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script>
    const chatbox = document.getElementById('chatbox');
    const input = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;

    function saveHistory() {
      localStorage.setItem('chatHistory', chatbox.innerHTML);
    }

    function loadHistory() {
      const history = localStorage.getItem('chatHistory');
      if (history) chatbox.innerHTML = history;
    }

    function addBubble(text, sender) {
      const bubble = document.createElement('div');
      bubble.className = 'bubble ' + sender;
      if (sender === 'bot') {
        bubble.innerHTML = marked.parse(text);
      } else {
        bubble.innerText = text;
      }
      const time = document.createElement('div');
      time.style.fontSize = '0.75em';
      time.style.color = '#888';
      time.style.marginTop = '2px';
      time.innerText = new Date().toLocaleTimeString();
      bubble.appendChild(time);
      chatbox.appendChild(bubble);
      chatbox.scrollTop = chatbox.scrollHeight;
      saveHistory();
    }

    function showTyping() {
      const typing = document.createElement('div');
      typing.id = 'typing-indicator';
      typing.className = 'bubble bot';
      typing.innerText = 'Bot is typing...';
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

    function sendFile() {
      const fileInput = document.getElementById('fileInput');
      const file = fileInput.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (e) => {
        const content = e.target.result;
        addBubble("File received: " + file.name, 'user');
        showTyping();
        try {
          const res = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: content })
          });
          if (!res.ok) throw new Error('Server error');
          const data = await res.json();
          hideTyping();
          addBubble(data.answer, 'bot');
        } catch (e) {
          hideTyping();
          addBubble("Sorry, something went wrong with the file. Please try again later.", 'bot');
        }
      };
      reader.readAsText(file);
    }

    function quickAsk(question) {
      addBubble(question, 'user');
      input.value = '';
      showTyping();
      sendBtn.disabled = true;
      fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      })
      .then(res => {
        if (!res.ok) throw new Error('Server error');
        return res.json();
      })
      .then(data => {
        hideTyping();
        addBubble(data.answer, 'bot');
      })
      .catch(e => {
        hideTyping();
        addBubble("Sorry, something went wrong. Please try again later.", 'bot');
      })
      .finally(() => {
        sendBtn.disabled = false;
        input.focus();
      });
    }

    window.onload = () => {
      loadHistory();
      if (!chatbox.innerHTML) {
        addBubble("Hi! I'm your CUT FAQ assistant. Ask me anything about the application process.", 'bot');
      }
      input.focus();
    };

    // Theme toggle script
    const themeToggle = document.getElementById('themeToggle');
    let darkMode = false;

    themeToggle.onclick = () => {
      darkMode = !darkMode;
      if (darkMode) {
        document.body.classList.add('dark');
        themeToggle.innerHTML = '🌙';
        localStorage.setItem('darkMode', 'true');
      } else {
        document.body.classList.remove('dark');
        themeToggle.innerHTML = '☀️';
        localStorage.setItem('darkMode', 'false');
      }
    };

    // Load dark mode preference
    window.onload = () => {
      loadHistory();
      const darkModePreference = localStorage.getItem('darkMode');
      if (darkModePreference === 'true') {
        darkMode = true;
        document.body.classList.add('dark');
        themeToggle.innerHTML = '🌙';
      } else {
        darkMode = false;
        document.body.classList.remove('dark');
        themeToggle.innerHTML = '☀️';
      }
      input.focus();
    };
  </script>
</body>
</html>
"""

@bp.route('/')
def index():
    return render_template_string(HTML_PAGE)

@bp.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').strip()
    faqs = current_app.config['FAQS_DATA']

    # Extract all FAQ questions
    faq_questions = [faq['question'] for faq in faqs]

    # Use difflib to find the closest match
    matches = difflib.get_close_matches(question, faq_questions, n=1, cutoff=0.5)
    if matches:
        # Find the answer for the best match
        for faq in faqs:
            if faq['question'] == matches[0]:
                return jsonify({'answer': faq['answer']})
    return jsonify({'answer': "Sorry, I couldn't find an answer to your question."}), 404
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
    body {
      background: #f4f7fa;
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
      background: #0078d7;
      color: #fff;
      border-bottom-right-radius: 6px;
    }
    .bot {
      align-self: flex-start;
      background: #e9ecef;
      color: #222;
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
  </div>

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
      bubble.innerHTML = text;
      if (sender === 'bot') {
        const copyBtn = document.createElement('button');
        copyBtn.innerText = 'Copy';
        copyBtn.style.marginLeft = '10px';
        copyBtn.style.fontSize = '0.8em';
        copyBtn.onclick = () => {
          navigator.clipboard.writeText(text.replace(/<br\s*\/?>/gi, '\n'));
          copyBtn.innerText = 'Copied!';
          setTimeout(() => copyBtn.innerText = 'Copy', 1000);
        };
        bubble.appendChild(copyBtn);
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

    window.onload = () => {
      loadHistory();
      if (!chatbox.innerHTML) {
        addBubble("Hi! I'm your CUT FAQ assistant. Ask me anything about the application process.", 'bot');
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
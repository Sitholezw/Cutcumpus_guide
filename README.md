# CUT FAQ Chatbot

A web-based AI-powered FAQ chatbot for the CUT application process. Users can ask questions and get instant, smart answers from a curated knowledge base using semantic search (Sentence Transformers). The chatbot features a modern, responsive UI with dark mode, glassy chat bubbles, and admin tools for FAQ management.

---

## Features

- **Semantic Search:** Uses [Sentence Transformers](https://www.sbert.net/) for accurate question matching.
- **Modern UI:** Responsive design, glassmorphism chatbox, dark mode toggle.
- **Instant Answers:** Precomputed FAQ embeddings for fast responses.
- **Admin Panel:** Easily add/edit FAQs (in-memory, can be extended for persistence).
- **Model Loading Feedback:** Shows a loading overlay until the AI model is ready.
- **Popular Questions:** Quick-access buttons for common queries.

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/cut-faq-chatbot.git
cd cut-faq-chatbot/flask-backend
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Main requirements:**
- Flask
- sentence-transformers
- numpy

### 3. Add FAQ Data

Edit or replace `faqs.json` in the backend folder with your Q&A pairs.

### 4. Add Assets

Place your images in:
```
app/static/assets/images/background.jpg
app/static/assets/images/favicon.png
```

### 5. Run the App

```bash
flask run
```

Visit [http://localhost:5000](http://localhost:5000) in your browser.

---

## Project Structure

```
flask-backend/
│
├── app/
│   ├── routes.py         # Main Flask app and HTML
│   └── static/
│       └── assets/
│           └── images/
│               ├── background.jpg
│               └── favicon.png
├── faqs.json             # FAQ knowledge base
├── requirements.txt
```

---

## Admin/Editor Panel

Visit [http://localhost:5000/admin](http://localhost:5000/admin) to add new FAQs (in-memory only by default).

---

## Customization

- **Add more FAQs:** Edit `faqs.json`.
- **Change look:** Edit CSS in `routes.py` (`HTML_PAGE` string).
- **Persist admin changes:** Extend `/admin/add` route to write to `faqs.json`.

---

## License

MIT License

---

## Credits

-

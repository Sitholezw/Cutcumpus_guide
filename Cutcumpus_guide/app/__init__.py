import json
from flask import Flask

def create_app():
    app = Flask(__name__)

    # Load faqs.json into memory at startup
    with open('faqs.json', 'r', encoding='utf-8') as f:
        app.config['FAQS_DATA'] = json.load(f)

    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app

from app import routes, models
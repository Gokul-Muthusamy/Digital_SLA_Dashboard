import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

try:
    from .core import TEMPLATE_DIR, STATIC_DIR, ensure_schema
    from .routes import auth_bp, dashboard_bp, ticket_bp, chat_bp, admin_bp
except ImportError:
    from core import TEMPLATE_DIR, STATIC_DIR, ensure_schema
    from routes import auth_bp, dashboard_bp, ticket_bp, chat_bp, admin_bp


app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "secretkey")

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(ticket_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(admin_bp)

ensure_schema()

if __name__ == "__main__":
    app.run(debug=True)

# main.py
import os
from flask import render_template
from app import create_app, db
from app.models import models # This is important for migrations

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.route('/')
def index():
    return render_template('index.html')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Lesson=models.Lesson, Unit=models.Unit, Note=models.Note, Embedding=models.Embedding, Setting=models.Setting)

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"[Notes Backend] Serving on http://{host}:{port} (LAN & Tailscale accessible)")
    app.run(host=host, port=port)

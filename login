from flask import Flask, request, redirect, url_for, flash, render_template_string, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "replace-with-a-long-random-secret-before-deployment"
DB_PATH = Path(__file__).with_name("blood_bank.db")

HTML = '''
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blood Bank System Login</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f4f7fb;font-family:Arial,sans-serif;color:#202938}
.card{width:min(420px,calc(100% - 32px));padding:28px;background:white;border-radius:14px;box-shadow:0 8px 28px #182b4a15}
h1{color:#8b1e2d;margin-top:0}label{display:block;margin:16px 0 7px;font-weight:600}
input{width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:7px;font-size:15px}
button{width:100%;margin-top:20px;padding:12px;border:0;border-radius:7px;background:#8b1e2d;color:white;font-size:15px;font-weight:bold;cursor:pointer}
.message{padding:11px;margin:12px 0;border-radius:7px;background:#fef2f2;color:#991b1b}.success{background:#ecfdf5;color:#065f46}
.hint{color:#64748b;font-size:13px;line-height:1.5;margin-top:16px}
</style></head><body><main class="card">
{% if logged_in %}
<h1>Welcome!</h1><p>You have successfully logged in as <strong>{{ username }}</strong>.</p>
<p>You can now access your account.</p><form method="post" action="{{ url_for('logout') }}"><button type="submit">Log out</button></form>
{% else %}
<h1>Blood Bank System</h1><p>Enter your credentials to access your account.</p>
{% with messages = get_flashed_messages(with_categories=true) %}{% for category,message in messages %}
<div class="message {{ 'success' if category == 'success' else '' }}">{{ message }}</div>{% endfor %}{% endwith %}
<form method="post" action="{{ url_for('login') }}">
<label for="username">Username</label><input id="username" name="username" required autocomplete="username">
<label for="password">Password</label><input id="password" name="password" type="password" required autocomplete="current-password">
<button type="submit">Log in</button></form>
<p class="hint">Demo account: <strong>staff</strong> / <strong>BloodBank@123</strong></p>
{% endif %}</main></body></html>
'''

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user')''')
        if not conn.execute("SELECT user_id FROM users WHERE username=?", ("staff",)).fetchone():
            conn.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                         ("staff", generate_password_hash("BloodBank@123"), "staff"))

@app.get("/")
def home():
    if session.get("user_id"):
        return render_template_string(HTML, logged_in=True, username=session.get("username"))
    return render_template_string(HTML, logged_in=False)

@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with get_db() as conn:
        user = conn.execute("SELECT user_id,username,password_hash,role FROM users WHERE username=?",
                            (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Invalid username or password. Please try again.", "error")
        return redirect(url_for("home"))
    session.clear()
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    return redirect(url_for("home"))

@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)  # Local development only; disable debug mode for deployment.

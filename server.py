#server.py

from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3, datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app, cors_allowed_origins="*")
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)

# --- SQLite DB setup ---
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
            )""")
c.execute("""CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            receiver TEXT,
            message TEXT,
            timestamp TEXT
            )""")
conn.commit()

# --- Flask-Login User class ---
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    c.execute("SELECT id, email FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        return User(row[0], row[1])
    return None

# --- Routes ---
@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("login_page"))

@app.route("/signup", methods=["GET","POST"])
def signup_page():
    if request.method=="POST":
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode('utf-8')
        try:
            c.execute("INSERT INTO users(email, password) VALUES(?, ?)", (email, password))
            conn.commit()
            return redirect(url_for("login_page"))
        except:
            return "User already exists!"
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login_page():
    if request.method=="POST":
        email = request.form["email"]
        password = request.form["password"]
        c.execute("SELECT id, password FROM users WHERE email=?", (email,))
        row = c.fetchone()
        if row and bcrypt.check_password_hash(row[1], password):
            user = User(row[0], email)
            login_user(user)
            return redirect(url_for("chat"))
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", username=current_user.email)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))

# --- WebSocket --- 
users = {}  # {sid: username}

@socketio.on("register")
def register(username):
    users[request.sid] = username
    # Send full user list to everyone
    emit("user_list", list(users.values()), broadcast=True)

@socketio.on("private_message")
def private_message(data):
    """data = {to: 'username', message: 'ciphertext'}"""
    sender = users.get(request.sid, "Unknown")
    recipient_sid = None
    for sid, uname in users.items():
        if uname == data["to"]:
            recipient_sid = sid
            break
    if recipient_sid:
        # Save message in DB (ciphertext)
        c.execute("INSERT INTO messages(sender, receiver, message, timestamp) VALUES(?,?,?,?)",
                  (sender, data["to"], data["message"], str(datetime.datetime.now())))
        conn.commit()
        # Send to recipient
        emit("private_message", {"from": sender, "message": data["message"]}, room=recipient_sid)
        # Send to sender as confirmation
        emit("private_message", {"from": f"You → {data['to']}", "message": data["message"]}, room=request.sid)

@socketio.on("disconnect")
def disconnect():
    username = users.pop(request.sid, None)
    if username:
        emit("user_list", list(users.values()), broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)

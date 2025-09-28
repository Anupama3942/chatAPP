from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from flask_bcrypt import Bcrypt
import sqlite3
import uuid
import datetime
import json
import logging

app = Flask(__name__)
app.secret_key = "supersecretkey-windows-2024"
socketio = SocketIO(app, cors_allowed_origins="*")
bcrypt = Bcrypt(app)

# Import database config
from database_config import get_db_connection, init_db

# Initialize database - FIXED for newer Flask versions
@app.before_request
def initialize_database():
    # Check if database is initialized by trying to access users table
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cur.fetchone():
            init_db()
            print("✅ Database initialized successfully!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

# Routes
@app.route("/")
def home():
    return redirect(url_for("login_page"))

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        public_key = request.form.get("public_key", "")
        
        try:
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Check if user already exists
            cur.execute("SELECT email FROM users WHERE email = ?", (email,))
            if cur.fetchone():
                return "User already exists!"
            
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            user_id = str(uuid.uuid4())
            
            cur.execute(
                "INSERT INTO users (user_id, email, password_hash, public_key) VALUES (?, ?, ?, ?)",
                (user_id, email, password_hash, public_key)
            )
            
            conn.commit()
            cur.close()
            conn.close()
            
            session['user_id'] = user_id
            session['email'] = email
            return redirect(url_for("chat"))
            
        except Exception as e:
            return f"Registration failed: {str(e)}"
    
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        try:
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("SELECT user_id, password_hash, public_key FROM users WHERE email = ?", (email,))
            row = cur.fetchone()
            
            if row and bcrypt.check_password_hash(row['password_hash'], password):
                session['user_id'] = row['user_id']
                session['email'] = email
                session['public_key'] = row['public_key'] if row['public_key'] else ""
                return redirect(url_for("chat"))
            
            return "Invalid credentials"
            
        except Exception as e:
            return f"Login failed: {str(e)}"
        finally:
            try:
                cur.close()
                conn.close()
            except:
                pass
    
    return render_template("login.html")

@app.route("/chat")
def chat():
    if 'user_id' not in session:
        return redirect(url_for("login_page"))
    return render_template("chat.html", 
                         username=session['email'], 
                         user_id=session['user_id'])

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# WebSocket handlers
online_users = {}

@socketio.on("register")
def handle_register(user_data):
    online_users[request.sid] = user_data
    print(f"✅ User registered: {user_data['email']} (SID: {request.sid})")
    
    user_list = [{
        'user_id': data['user_id'],
        'email': data['email'],
        'public_key': data['public_key']
    } for data in online_users.values()]
    
    print(f"📢 Broadcasting user list with {len(user_list)} users")
    emit("user_list", user_list, broadcast=True)

@socketio.on("private_message")
def handle_private_message(data):
    sender_data = online_users.get(request.sid)
    if not sender_data:
        print("❌ Message from unknown user")
        return
    
    recipient_sid = None
    recipient_email = None
    for sid, user_data in online_users.items():
        if user_data['user_id'] == data['to_user_id']:
            recipient_sid = sid
            recipient_email = user_data['email']
            break
    
    if recipient_sid:
        print(f"📨 Message from {sender_data['email']} to {recipient_email}")
        
        # Forward to recipient
        emit("private_message", {
            'from_user_id': sender_data['user_id'],
            'from_email': sender_data['email'],
            'ciphertext': data['ciphertext'],
            'iv': data['iv']
        }, room=recipient_sid)
    else:
        print(f"❌ Recipient not found for message from {sender_data['email']}")

@socketio.on("connect")
def handle_connect():
    print(f"🔗 Client connected: {request.sid}")

@socketio.on("disconnect")
def handle_disconnect():
    if request.sid in online_users:
        user_email = online_users[request.sid]['email']
        del online_users[request.sid]
        print(f"🔌 User disconnected: {user_email}")
        
        user_list = [{
            'user_id': data['user_id'],
            'email': data['email'],
            'public_key': data['public_key']
        } for data in online_users.values()]
        
        emit("user_list", user_list, broadcast=True)

if __name__ == "__main__":
    print("🚀 Starting CrypTalk Server...")
    print("📊 Initializing database...")
    try:
        # Initialize database on startup
        init_db()
        print("✅ Database ready!")
    except Exception as e:
        print(f"⚠️  Database warning: {e}")
    
    print("🌐 Server starting on http://127.0.0.1:5000")
    socketio.run(app, host="127.0.0.1", port=5000, debug=False)
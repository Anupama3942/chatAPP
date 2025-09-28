from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*")

# Store users: { sid: username }
users = {}

@app.route("/")
def index():
    return render_template("chat.html")

@socketio.on("register")
def register(username):
    users[request.sid] = username
    print(f"[REGISTER] {username} connected.")
    emit("user_list", list(users.values()), broadcast=True)

@socketio.on("private_message")
def private_message(data):
    """data = {to: 'username', message: 'text'}"""
    sender = users.get(request.sid, "Unknown")
    recipient_sid = None
    for sid, uname in users.items():
        if uname == data["to"]:
            recipient_sid = sid
            break
    if recipient_sid:
        emit("private_message", {"from": sender, "message": data["message"]}, room=recipient_sid)
        emit("private_message", {"from": f"You → {data['to']}", "message": data["message"]}, room=request.sid)

@socketio.on("disconnect")
def disconnect():
    username = users.pop(request.sid, "Unknown")
    print(f"[DISCONNECT] {username}")
    emit("user_list", list(users.values()), broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000, debug=True)

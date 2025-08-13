from flask import Flask, render_template, request, redirect, url_for, session
import hashlib
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session storage

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as file:
        return json.load(file)

def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(users, file)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route("/")
def home():
    if "username" in session:
        users = load_users()
        name = users[session["username"]]["name"]
        return f"<h1>Welcome, {name}!</h1><a href='/logout'>Logout</a>"
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        users = load_users()
        if username in users and users[username]["password"] == hash_password(password):
            session["username"] = username
            return redirect(url_for("home"))
        else:
            return "Invalid username or password"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        full_name = request.form["name"]
        password = request.form["password"]
        users = load_users()
        if username in users:
            return "Username already taken"
        users[username] = {"name": full_name, "password": hash_password(password)}
        save_users(users)
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)

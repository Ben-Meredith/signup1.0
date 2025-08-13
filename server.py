from flask import Flask, render_template, request, redirect, url_for, session
import hashlib
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

USERS_FILE = "users.json"
RES_FILE = "reservations.json"

# ---------- Helpers ----------
def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_reservations():
    if not os.path.exists(RES_FILE):
        return []
    with open(RES_FILE, "r") as f:
        return json.load(f)

def save_reservations(res_list):
    with open(RES_FILE, "w") as f:
        json.dump(res_list, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def parse_dt(date_str, time_str):
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

# ---------- Routes ----------
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    users = load_users()
    username = session["username"]
    if username == "admin":
        return redirect(url_for("admin_home"))

    # Regular user schedule
    all_res = load_reservations()
    now = datetime.now()
    mine = [r for r in all_res if r["username"] == username and parse_dt(r["date"], r["time"]) >= now]
    mine.sort(key=lambda r: parse_dt(r["date"], r["time"]))
    return render_template("schedule.html", upcoming=mine, form_values=None, error=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        users = load_users()
        if username in users and users[username]["password"] == hash_password(password):
            session["username"] = username
            return redirect(url_for("home"))
        return "Invalid username or password"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        full_name = request.form["name"].strip()
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

# ---------- User Reservations ----------
@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    if username == "admin":
        return redirect(url_for("admin_home"))

    users = load_users()
    name = users[username]["name"]
    error = None
    form_values = None

    if request.method == "POST":
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        party_size_str = request.form.get("party_size", "").strip()
        notes = request.form.get("notes", "").strip()
        form_values = {"date": date_str, "time": time_str, "party_size": party_size_str, "notes": notes}

        # Validate party size
        try:
            party_size = int(party_size_str)
            if party_size < 1 or party_size > 3:
                error = "Party size must be between 1 and 3."
        except ValueError:
            error = "Party size must be a number."

        # Validate datetime
        if not error:
            try:
                dt = parse_dt(date_str, time_str)
                if dt < datetime.now():
                    error = "Please select a future date and time."
            except Exception:
                error = "Invalid date or time."

        # Check max 3 reservations per slot
        if not error:
            all_res = load_reservations()
            slot_count = sum(1 for r in all_res if r["date"] == date_str and r["time"] == time_str)
            if slot_count >= 3:
                error = "Sorry, this slot is full. Only 3 reservations allowed per time."

        if not error:
            res_list = load_reservations()
            res_list.append({
                "id": str(uuid.uuid4()),
                "username": username,
                "name": name,
                "date": date_str,
                "time": time_str,
                "party_size": party_size,
                "notes": notes,
                "created_at": datetime.utcnow().isoformat() + "Z"
            })
            save_reservations(res_list)
            return redirect(url_for("schedule"))

    # GET -> show upcoming reservations
    all_res = load_reservations()
    upcoming = [r for r in all_res if r["username"] == username and parse_dt(r["date"], r["time"]) >= datetime.now()]
    upcoming.sort(key=lambda r: parse_dt(r["date"], r["time"]))
    return render_template("schedule.html", upcoming=upcoming, form_values=form_values, error=error)

# ---------- Admin ----------
@app.route("/admin")
def admin_home():
    if "username" not in session or session["username"] != "admin":
        return redirect(url_for("login"))

    reservations = load_reservations()
    reservations.sort(key=lambda r: parse_dt(r["date"], r["time"]))
    return render_template("admin.html", reservations=reservations)

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

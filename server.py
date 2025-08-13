from flask import Flask, render_template, request, redirect, url_for, session
import hashlib
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session storage

USERS_FILE = "users.json"
RES_FILE = "reservations.json"

# ---------- Storage helpers ----------
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
    try:
        with open(RES_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "reservations" in data:
                return data["reservations"]
    except Exception:
        pass
    return []

def save_reservations(res_list):
    with open(RES_FILE, "w") as f:
        json.dump(res_list, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def parse_dt(date_str, time_str):
    # "YYYY-MM-DD" + "HH:MM" -> datetime
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")


# ---------- Routes ----------
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    users = load_users()
    name = users[session["username"]]["name"]

    # Upcoming reservations for this user
    all_res = load_reservations()
    now = datetime.now()
    mine = []
    for r in all_res:
        if r.get("username") == session["username"]:
            try:
                dt = parse_dt(r["date"], r["time"])
                r["_dt"] = dt
                if dt >= now:
                    mine.append(r)
            except Exception:
                continue

    mine.sort(key=lambda r: r["_dt"])
    # strip helper field
    for r in mine:
        r.pop("_dt", None)

    return render_template("home.html", name=name, upcoming=mine)

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

# ---------- Reservations ----------
@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if "username" not in session:
        return redirect(url_for("login"))

    users = load_users()
    name = users[session["username"]]["name"]

    if request.method == "POST":
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        party_size_str = request.form.get("party_size", "").strip()
        notes = request.form.get("notes", "").strip()

        # Basic validation
        error = None
        try:
            party_size = int(party_size_str)
            if party_size < 1 or party_size > 10:
                error = "Party size must be between 1 and 10."
        except ValueError:
            error = "Party size must be a number."

        if not error:
            try:
                dt = parse_dt(date_str, time_str)
                if dt < datetime.now():
                    error = "Please pick a future date/time."
            except Exception:
                error = "Invalid date/time."

        if error:
            return render_template(
                "reservations.html",
                name=name,
                error=error,
                form_values={"date": date_str, "time": time_str, "party_size": party_size_str, "notes": notes},
            )

        # Save reservation
        res_list = load_reservations()
        rid = str(uuid.uuid4())
        res = {
            "id": rid,
            "username": session["username"],
            "name": name,
            "date": date_str,
            "time": time_str,
            "party_size": int(party_size_str),
            "notes": notes,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        res_list.append(res)
        save_reservations(res_list)
        return redirect(url_for("reservation_success", rid=rid))

    # GET -> show form
    return render_template("reservations.html", name=name, error=None, form_values=None)

@app.route("/reservations/success")
def reservation_success():
    if "username" not in session:
        return redirect(url_for("login"))

    rid = request.args.get("rid")
    res_list = load_reservations()
    res = next((r for r in res_list if r["id"] == rid and r["username"] == session["username"]), None)

    users = load_users()
    name = users[session["username"]]["name"]

    return render_template("reservation_success.html", name=name, reservation=res)


# ---------- App entry ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use Render's port or default 5000 locally
    app.run(host="0.0.0.0", port=port, debug=True)  # debug=True is fine for dev

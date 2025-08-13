from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# --- Database setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), db.ForeignKey('user.username'), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Routes ---
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.clear()
        return redirect(url_for("login"))

    if user.is_admin:
        return redirect(url_for("admin_home"))

    upcoming = Reservation.query.filter_by(username=user.username).all()
    now = datetime.now()
    upcoming = [r for r in upcoming if datetime.strptime(f"{r.date} {r.time}", "%Y-%m-%d %H:%M") >= now]
    upcoming.sort(key=lambda r: f"{r.date} {r.time}")

    return render_template("home.html", name=user.name, upcoming=upcoming)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session["username"] = user.username
            session["is_admin"] = user.is_admin
            return redirect(url_for("home"))
        flash("Invalid username or password")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username").strip()
        name = request.form.get("name").strip()
        password = request.form.get("password").strip()
        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return render_template("signup.html")
        new_user = User(username=username, name=name, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- User schedule ---
@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")
        party_size = int(request.form.get("party_size"))
        notes = request.form.get("notes")

        # Limit: max 3 active reservations per datetime
        existing_count = Reservation.query.filter_by(date=date, time=time).count()
        if existing_count >= 3:
            flash("Sorry, maximum 3 reservations per time slot.")
            return render_template("schedule.html", name=user.name)

        new_res = Reservation(username=user.username, date=date, time=time, party_size=party_size, notes=notes)
        db.session.add(new_res)
        db.session.commit()
        flash("Reservation booked!")
        return redirect(url_for("schedule"))

    upcoming = Reservation.query.filter_by(username=user.username).all()
    now = datetime.now()
    upcoming = [r for r in upcoming if datetime.strptime(f"{r.date} {r.time}", "%Y-%m-%d %H:%M") >= now]
    upcoming.sort(key=lambda r: f"{r.date} {r.time}")
    return render_template("schedule.html", name=user.name, upcoming=upcoming)

# --- Admin ---
@app.route("/admin")
def admin_home():
    if "username" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    reservations = Reservation.query.all()
    return render_template("admin.html", reservations=reservations)

# --- App entry ---
if __name__ == "__main__":
    db.create_all()  # Make sure database tables exist
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

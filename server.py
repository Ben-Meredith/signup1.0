from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- Routes ----------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login"))

    if user.is_admin:
        return redirect(url_for("admin_home"))

    # Regular user home
    reservations = Reservation.query.filter_by(user_id=user.id).order_by(Reservation.date, Reservation.time).all()
    return render_template("home.html", name=user.name, upcoming=reservations)

@app.route("/admin")
def admin_home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user or not user.is_admin:
        flash("Access denied")
        return redirect(url_for("login"))

    reservations = Reservation.query.order_by(Reservation.date, Reservation.time).all()
    return render_template("admin.html", reservations=reservations)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            if user.is_admin:
                return redirect(url_for("admin_home"))
            return redirect(url_for("home"))

        flash("Invalid username or password")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        name = request.form["name"].strip()
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already taken")
            return redirect(url_for("signup"))

        new_user = User(
            username=username,
            name=name,
            password_hash=generate_password_hash(password),
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if not user or user.is_admin:
        return redirect(url_for("login"))

    if request.method == "POST":
        date = request.form["date"].strip()
        time = request.form["time"].strip()
        party_size = int(request.form["party_size"])
        notes = request.form.get("notes", "").strip()

        # Check max 3 reservations per slot
        slot_count = Reservation.query.filter_by(date=date, time=time).count()
        if slot_count >= 3:
            flash("This slot is full. Please choose another time.")
            return redirect(url_for("schedule"))

        reservation = Reservation(user_id=user.id, date=date, time=time, party_size=party_size, notes=notes)
        db.session.add(reservation)
        db.session.commit()
        flash("Reservation booked successfully!")
        return redirect(url_for("home"))

    return render_template("schedule.html", name=user.name)

# ---------- Admin initial setup ----------
@app.before_first_request
def create_admin():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin = User(
            username="admin",
            name="Administrator",
            password_hash=generate_password_hash("admin123"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

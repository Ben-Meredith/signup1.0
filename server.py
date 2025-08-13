from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import os

# ---------- App setup ----------
app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey("user.username"), nullable=False)
    date = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)    # HH:MM
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- DB init ----------
with app.app_context():
    db.create_all()
    # Ensure admin account exists
    admin = User.query.filter_by(username="admin123").first()
    if not admin:
        admin = User(
            username="admin123",
            name="Administrator",
            password=hashlib.sha256("admin123".encode()).hexdigest(),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# ---------- Helper functions ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def current_user():
    if "username" in session:
        return User.query.filter_by(username=session["username"]).first()
    return None

# ---------- Routes ----------
@app.route("/")
def home():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if user.is_admin:
        return redirect(url_for("admin_home"))

    upcoming = Reservation.query.filter_by(username=user.username).all()
    upcoming = sorted(upcoming, key=lambda r: datetime.strptime(f"{r.date} {r.time}", "%Y-%m-%d %H:%M"))
    return render_template("home.html", name=user.name, upcoming=upcoming)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.password == hash_password(password):
            session["username"] = username
            return redirect(url_for("home"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "error")
            return render_template("signup.html")
        user = User(username=username, name=name, password=hash_password(password))
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

# ---------- Reservations ----------
@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    if user.is_admin:
        return redirect(url_for("admin_home"))

    if request.method == "POST":
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        party_size = int(request.form.get("party_size", 1))
        notes = request.form.get("notes", "").strip()

        # Validate max 3 reservations per slot
        count = Reservation.query.filter_by(date=date_str, time=time_str).count()
        if count >= 3:
            flash("This time slot is full. Please choose another time.", "error")
            return render_template("schedule.html", form_values=request.form)

        new_res = Reservation(
            username=user.username,
            date=date_str,
            time=time_str,
            party_size=party_size,
            notes=notes
        )
        db.session.add(new_res)
        db.session.commit()
        flash("Reservation booked successfully!", "success")
        return redirect(url_for("schedule"))

    return render_template("schedule.html", form_values=None)

# ---------- Admin ----------
@app.route("/admin")
def admin_home():
    user = current_user()
    if not user or not user.is_admin:
        flash("Access denied.", "error")
        return redirect(url_for("login"))

    reservations = Reservation.query.order_by(Reservation.date, Reservation.time).all()
    return render_template("admin.html", reservations=reservations)

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

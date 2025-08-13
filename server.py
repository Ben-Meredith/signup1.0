from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import os

# --- Flask app ---
app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- Database setup ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Helper functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def current_user():
    if "user_id" in session:
        return User.query.get(session["user_id"])
    return None

# --- Initialize DB and create default admin ---
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin_user = User(
            username="admin",
            name="Administrator",
            password=hash_password("admin123"),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

# --- Routes ---
@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if user.is_admin:
        return redirect(url_for("admin_home"))
    # Show user home
    upcoming = Reservation.query.filter_by(user_id=user.id).order_by(Reservation.date, Reservation.time).all()
    return render_template("home.html", name=user.name, upcoming=upcoming)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.password == hash_password(password):
            session["user_id"] = user.id
            return redirect(url_for("index"))
        flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        name = request.form["name"].strip()
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            flash("Username already taken", "danger")
            return render_template("signup.html")
        user = User(username=username, name=name, password=hash_password(password))
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# --- User reservations ---
@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    user = current_user()
    if not user or user.is_admin:
        return redirect(url_for("login"))
    if request.method == "POST":
        date = request.form["date"].strip()
        time = request.form["time"].strip()
        party_size = int(request.form["party_size"])
        notes = request.form["notes"].strip()

        # Limit to 3 reservations per date/time
        count = Reservation.query.filter_by(date=date, time=time).count()
        if count >= 3:
            flash("Maximum of 3 reservations at this time. Choose another time.", "danger")
            return render_template("reservations.html", name=user.name, form_values=request.form)

        res = Reservation(user_id=user.id, date=date, time=time, party_size=party_size, notes=notes)
        db.session.add(res)
        db.session.commit()
        return redirect(url_for("reservation_success", res_id=res.id))
    return render_template("reservations.html", name=user.name, form_values=None)

@app.route("/reservations/success")
def reservation_success():
    user = current_user()
    if not user or user.is_admin:
        return redirect(url_for("login"))
    res_id = request.args.get("res_id")
    res = Reservation.query.get(res_id)
    return render_template("reservation_success.html", name=user.name, reservation=res)

# --- Admin routes ---
@app.route("/admin/home")
def admin_home():
    user = current_user()
    if not user or not user.is_admin:
        return redirect(url_for("index"))
    # All reservations
    reservations = Reservation.query.order_by(Reservation.date, Reservation.time).all()
    return render_template("admin_home.html", name=user.name, reservations=reservations)

# --- App entry ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

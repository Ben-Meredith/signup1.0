from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import hashlib
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change for production

# ---------- Database setup ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------- Helpers ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_max_reservations(date, time):
    count = Reservation.query.filter_by(date=date, time=time).count()
    return count < 3

# ---------- Routes ----------
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    if session.get("is_admin"):
        return redirect(url_for("admin_home"))

    user = User.query.filter_by(username=session["username"]).first()
    upcoming = Reservation.query.filter_by(username=user.username).all()
    upcoming = [r for r in upcoming if datetime.strptime(f"{r.date} {r.time}", "%Y-%m-%d %H:%M") >= datetime.now()]
    upcoming.sort(key=lambda r: f"{r.date} {r.time}")

    return render_template("home.html", name=user.name, upcoming=upcoming)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.password == hash_password(password):
            session["username"] = username
            session["is_admin"] = user.is_admin
            if user.is_admin:
                return redirect(url_for("admin_home"))
            return redirect(url_for("home"))
        return "Invalid username or password"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        name = request.form["name"].strip()
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            return "Username already taken"
        new_user = User(username=username, name=name, password=hash_password(password), is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("is_admin", None)
    return redirect(url_for("login"))

# ---------- Reservations ----------
@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    error = None

    if request.method == "POST":
        date = request.form.get("date").strip()
        time = request.form.get("time").strip()
        party_size = int(request.form.get("party_size"))
        notes = request.form.get("notes").strip()

        if not check_max_reservations(date, time):
            error = "Sorry, only 3 reservations allowed per time slot."
        elif datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M") < datetime.now():
            error = "Please choose a future date/time."

        if not error:
            res = Reservation(username=user.username, name=user.name, date=date, time=time, party_size=party_size, notes=notes)
            db.session.add(res)
            db.session.commit()
            return redirect(url_for("reservation_success", rid=res.id))

    return render_template("reservations.html", name=user.name, error=error)

@app.route("/reservations/success")
def reservation_success():
    if "username" not in session:
        return redirect(url_for("login"))

    rid = request.args.get("rid")
    res = Reservation.query.filter_by(id=rid, username=session["username"]).first()
    return render_template("reservation_success.html", name=session["username"], reservation=res)

# ---------- Admin ----------
@app.route("/admin")
def admin_home():
    if "username" not in session or not session.get("is_admin"):
        return redirect(url_for("login"))

    reservations = Reservation.query.all()
    return render_template("admin.html", reservations=reservations)

# ---------- Initialize ----------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin_user = User(username="admin", name="Administrator", password=hash_password("admin123"), is_admin=True)
        db.session.add(admin_user)
        db.session.commit()

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(64), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date = db.Column(db.String(10), nullable=False)   # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)    # HH:MM
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")

# ---------- Helpers ----------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def max_reservations_reached(date, time):
    count = Reservation.query.filter_by(date=date, time=time).count()
    return count >= 3

# ---------- Routes ----------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if user.is_admin:
        return redirect(url_for("admin_home"))

    reservations = Reservation.query.filter_by(user_id=user.id).order_by(Reservation.date, Reservation.time).all()
    return render_template("home.html", name=user.name, upcoming=reservations)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.password == hash_password(password):
            session["user_id"] = user.id
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
        new_user = User(
            username=username,
            name=name,
            password=hash_password(password),
            is_admin=False
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("login"))

# ---------- Schedule ----------
@app.route("/schedule", methods=["GET", "POST"])
def schedule():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])
    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")
        party_size = int(request.form.get("party_size"))
        notes = request.form.get("notes")

        if max_reservations_reached(date, time):
            error = "Sorry, only 3 reservations are allowed at this time slot."
            return render_template("schedule.html", name=user.name, error=error, form_values=request.form)

        new_res = Reservation(
            user_id=user.id,
            date=date,
            time=time,
            party_size=party_size,
            notes=notes
        )
        db.session.add(new_res)
        db.session.commit()
        return redirect(url_for("schedule_success", res_id=new_res.id))

    return render_template("schedule.html", name=user.name, error=None, form_values=None)

@app.route("/schedule/success")
def schedule_success():
    if "user_id" not in session:
        return redirect(url_for("login"))

    res_id = request.args.get("res_id")
    res = Reservation.query.get(res_id)
    user = User.query.get(session["user_id"])
    return render_template("schedule_success.html", name=user.name, reservation=res)

# ---------- Admin ----------
@app.route("/admin")
def admin_home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.query.get(session["user_id"])
    if not user.is_admin:
        return "Access denied"

    reservations = Reservation.query.order_by(Reservation.date, Reservation.time).all()
    return render_template("admin.html", reservations=reservations)

# ---------- Initialize DB ----------
@app.before_first_request
def create_tables():
    db.create_all()
    # Create default admin if not exists
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", name="Admin", password=hash_password("admin123"), is_admin=True)
        db.session.add(admin)
        db.session.commit()

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

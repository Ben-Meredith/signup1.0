from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey123"  # change this for security
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --------- Models ---------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200))

# --------- Routes ---------
@app.before_first_request
def create_tables():
    db.create_all()
    # create default admin if not exists
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", password=generate_password_hash("admin123"), is_admin=True)
        db.session.add(admin)
        db.session.commit()

@app.route("/")
def index():
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        if user.is_admin:
            return redirect(url_for("admin_home"))
        else:
            return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["username"] = user.username
            if user.is_admin:
                return redirect(url_for("admin_home"))
            return redirect(url_for("home"))
        else:
            flash("❌ Invalid username or password")
            return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        full_name = request.form.get("full_name")

        if User.query.filter_by(username=username).first():
            flash("❌ Username already exists")
            return redirect(url_for("signup"))

        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        flash("✅ Account created successfully")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    upcoming = Reservation.query.filter_by(username=user.username).all()
    return render_template("schedule.html", upcoming=upcoming, name=user.username)

@app.route("/reserve", methods=["GET", "POST"])
def reserve():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        date = request.form.get("date")
        time = request.form.get("time")
        party_size = int(request.form.get("party_size"))
        notes = request.form.get("notes")
        username = session["username"]

        # Limit 3 concurrent reservations
        total_for_time = Reservation.query.filter_by(date=date, time=time).count()
        if total_for_time >= 3:
            flash("❌ Maximum reservations reached for that slot")
            return redirect(url_for("reserve"))

        new_res = Reservation(username=username, date=datetime.strptime(date, "%Y-%m-%d").date(),
                              time=time, party_size=party_size, notes=notes)
        db.session.add(new_res)
        db.session.commit()
        flash("✅ Reservation booked!")
        return redirect(url_for("home"))

    return render_template("reserve.html")

@app.route("/admin")
def admin_home():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user.is_admin:
        return redirect(url_for("home"))

    reservations = Reservation.query.all()
    return render_template("admin.html", reservations=reservations)

if __name__ == "__main__":
    app.run(debug=True)

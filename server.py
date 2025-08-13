from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import hashlib
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"  # replace for production

# ---------- Database config ----------
# Render sets DATABASE_URL. SQLAlchemy prefers "postgresql://" not "postgres://"
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///local.db"  # falls back to local dev db
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# ---------- Models ----------
class User(db.Model):
    __tablename__ = "users"
    username = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.String(36), primary_key=True)  # uuid string
    username = db.Column(db.String(80), db.ForeignKey("users.username"), nullable=False, index=True)
    date = db.Column(db.String(10), nullable=False)   # "YYYY-MM-DD"
    time = db.Column(db.String(5), nullable=False)    # "HH:MM"
    party_size = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Optional convenience property: combined datetime for sorting/filtering
    @property
    def start_at(self) -> datetime:
        return datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")


# ---------- Helpers ----------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ---------- Routes ----------
@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["username"])
    if not user:
        session.pop("username", None)
        return redirect(url_for("login"))

    # Upcoming reservations
    now = datetime.now()
    upcoming = (
        Reservation.query
        .filter(Reservation.username == user.username)
        .all()
    )
    upcoming = [r for r in upcoming if r.start_at >= now]
    upcoming.sort(key=lambda r: r.start_at)

    return render_template("home.html", name=user.name, upcoming=upcoming)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        user = db.session.get(User, username)
        if user and user.password_hash == hash_password(password):
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

        if db.session.get(User, username):
            return "Username already taken"

        user = User(
            username=username,
            name=full_name,
            password_hash=hash_password(password),
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if "username" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["username"])
    if not user:
        session.pop("username", None)
        return redirect(url_for("login"))

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
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                if dt < datetime.now():
                    error = "Please pick a future date/time."
            except Exception:
                error = "Invalid date/time."

        if error:
            return render_template(
                "reservations.html",
                name=user.name,
                error=error,
                form_values={"date": date_str, "time": time_str, "party_size": party_size_str, "notes": notes},
            )

        # Save reservation
        res = Reservation(
            id=str(uuid.uuid4()),
            username=user.username,
            date=date_str,
            time=time_str,
            party_size=int(party_size_str),
            notes=notes,
        )
        db.session.add(res)
        db.session.commit()
        return redirect(url_for("reservation_success", rid=res.id))

    # GET
    return render_template("reservations.html", name=user.name, error=None, form_values=None)


@app.route("/reservations/success")
def reservation_success():
    if "username" not in session:
        return redirect(url_for("login"))

    rid = request.args.get("rid")
    res = Reservation.query.filter_by(id=rid, username=session["username"]).first()

    user = db.session.get(User, session["username"])
    name = user.name if user else "User"

    return render_template("reservation_success.html", name=name, reservation=res)


# ---------- App entry ----------
if __name__ == "__main__":
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    port = int(os.environ.get("PORT", 5000))  # Render will set PORT
    app.run(host="0.0.0.0", port=port, debug=True)  # debug=True ok for dev

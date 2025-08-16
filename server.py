from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reservations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db = SQLAlchemy(app)

# =======================
# Database Models
# =======================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), db.ForeignKey('user.username'))
    title = db.Column(db.String(100))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

# =======================
# Init Database + Admin
# =======================
def initialize():
    with app.app_context():
        db.create_all()
        # Make sure admin always exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

initialize()

# =======================
# Routes
# =======================
@app.route('/')
def index():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user.is_admin:
            return redirect(url_for('admin_home'))
        return redirect(url_for('schedule'))
    return redirect(url_for('login'))

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            if user.is_admin:
                return redirect(url_for('admin_home'))
            return redirect(url_for('schedule'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

# ---------- SIGNUP ----------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash("Username already exists!", "danger")
            return redirect(url_for('signup'))
        new_user = User(username=username, password=password, is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# ---------- USER SCHEDULE ----------
@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    reservations = Reservation.query.filter_by(username=user.username).all()

    if request.method == 'POST':
        # Limit: only 3 reservations allowed TOTAL
        if len(Reservation.query.all()) >= 3:
            flash('Maximum of 3 reservations reached. Cannot book more.', 'danger')
        else:
            title = request.form['title']
            start_time = datetime.fromisoformat(request.form['start_time'])
            end_time = datetime.fromisoformat(request.form['end_time'])
            new_reservation = Reservation(
                username=user.username,
                title=title,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(new_reservation)
            db.session.commit()
            flash('Reservation booked!', 'success')
        return redirect(url_for('schedule'))

    return render_template('schedule.html', reservations=reservations, username=user.username)

# ---------- ADMIN DASHBOARD ----------
@app.route('/admin')
def admin_home():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user or not user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('schedule'))

    reservations = Reservation.query.all()
    return render_template('admin.html', reservations=reservations)

# =======================
# Run App
# =======================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render gives you a PORT
    app.run(host="0.0.0.0", port=port, debug=False)

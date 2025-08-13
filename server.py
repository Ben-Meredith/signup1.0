from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reservations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db = SQLAlchemy(app)

# Models
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

# Initialize database and create admin
def initialize():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

initialize()

# Routes
@app.route('/')
def index():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user.is_admin:
            return redirect(url_for('admin_home'))
        return redirect(url_for('schedule'))
    return redirect(url_for('login'))

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

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    reservations = Reservation.query.filter_by(username=user.username).all()

    if request.method == 'POST':
        if len(Reservation.query.all()) >= 3:
            flash('Maximum of 3 reservations reached.', 'danger')
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

@app.route('/admin', methods=['GET'])
def admin_home():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if not user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('schedule'))

    reservations = Reservation.query.all()
    return render_template('admin.html', reservations=reservations)

if __name__ == '__main__':
    app.run(debug=True)

import os
from datetime import datetime
import pytz

from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from quiz_flow import generate_quiz_from_pinecone

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:7384625@localhost/Users'   #use your database_username, Password and database_name according to your database. Format = username:Password@localhost/database_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Models
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    quizzes = db.relationship('QuizHistory', backref='user', lazy=True)

class QuizHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    date_taken = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Session variable to store quiz data
quiz_data = None

@app.before_request
def check_user_status():
    if 'user' in session:
        user_email = session['user']
        user_exists = Users.query.filter_by(email=user_email).first()
        if not user_exists:
            session.pop('user', None)
            return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session['user']
    user = Users.query.filter_by(email=user_email).first()
    quiz_history = QuizHistory.query.filter_by(user_id=user.id).order_by(QuizHistory.date_taken.desc()).all()
    return render_template('dashboard.html', quiz_history=quiz_history, user_email=user_email)

@app.route('/input')
def input_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('input.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email.endswith('@gmail.com'):
            return render_template('signup.html', error="Email must end with @gmail.com")

        existing_user = Users.query.filter_by(email=email).first()

        if existing_user:
            return render_template('signup.html', error="Email already registered!")

        hashed_password = generate_password_hash(password)
        new_user = Users(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = Users.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user'] = user.email
            return redirect(url_for('home'))
        else:
            error = "Invalid credentials. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.template_filter('timezone')
def timezone_filter(timezone_str):
    return pytz.timezone(timezone_str)

@app.route('/quiz')
def quiz_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/api/quiz')
def quiz_api():
    global quiz_data
    if quiz_data is None:
        return jsonify({"error": "No quiz data available"})
    return jsonify(quiz_data)

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    global quiz_data
    if 'user' not in session:
        return redirect(url_for('login'))
    
    topic = request.form.get('topic')
    num_questions = int(request.form.get('num_questions'))
    namespaces = ["computer_organization", "operating_system"]
    
    try:
        quiz_data = generate_quiz_from_pinecone(topic, namespaces, top_k=10, num_questions=num_questions)
        if quiz_data.get("error"):
            return render_template('input.html', error=quiz_data["error"])
        return redirect(url_for('quiz_page'))
    except Exception as e:
        return render_template('input.html', error=str(e))

@app.route('/save_quiz_result', methods=['POST'])
def save_quiz_result():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    data = request.get_json()
    user_email = session['user']
    user = Users.query.filter_by(email=user_email).first()
    
    quiz_history = QuizHistory(
        user_id=user.id,
        topic=data['topic'],
        score=data['score'],
        total_questions=data['total_questions']
    )
    
    db.session.add(quiz_history)
    db.session.commit()
    
    return jsonify({"message": "Quiz result saved successfully"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

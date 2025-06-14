import os
import time
from datetime import datetime
import pytz
import pandas as pd
from functools import wraps
from flask import Flask, jsonify, render_template, request, redirect, url_for, session,flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from datetime import datetime, timezone, timedelta
from quiz_flow import generate_quiz_from_pinecone
from ml_model import train_model, load_model

from transformers import BertTokenizer
# Initialize the tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-cased')
import tensorflow as tf

# Load the question classification model
questionclassification_model = tf.keras.models.load_model("C:/Users/ik/Downloads/questionclassification_model/questionclassification_model")

tokenizer = BertTokenizer.from_pretrained('bert-base-cased')

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from supabase import create_client, Client
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from gotrue.errors import AuthApiError
from sqlalchemy import create_engine
import bcrypt  # For password hashing
import re
import jwt
from flask import jsonify
from langchain_groq import ChatGroq
from transformers import BertTokenizer
import tensorflow as tf

# Initialize the ChatGroq LLM
llm = ChatGroq(
    temperature=0,
    groq_api_key="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",
    model_name="llama-3.3-70b-versatile"
)

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure database
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set up the database configuration
DATABASE_URL = os.getenv("DATABASE_URL")  # Fetch from system variables
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Add these models after the existing QuizHistory model
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(500), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    quizzes = db.relationship('QuizHistory', backref='user', lazy=True)
    created_quizzes = db.relationship('Quiz', backref='creator', lazy=True)
    assigned_quizzes_teacher = db.relationship('AssignedQuiz',
                                             foreign_keys='AssignedQuiz.teacher_id',
                                             backref='teacher', lazy=True)
    assigned_quizzes_student = db.relationship('AssignedQuiz',
                                             foreign_keys='AssignedQuiz.student_id',
                                             backref='student', lazy=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    questions = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    quiz_history = db.relationship('QuizHistory', backref='quiz', lazy=True)
    assignments = db.relationship('AssignedQuiz', backref='quiz', lazy=True)

class AssignedQuiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')
    assigned_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_date = db.Column(db.DateTime)
    score = db.Column(db.Float)

class QuizHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'))  # Make this optional for self-generated quizzes
    assigned_quiz_id = db.Column(db.Integer, db.ForeignKey('assigned_quiz.id'))
    topic = db.Column(db.String(200), nullable=False)  # Add this line
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    date_taken = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    difficulty = db.Column(db.String(50))  # Add this line

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_history_id = db.Column(db.Integer, db.ForeignKey('quiz_history.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)  # Add this line to store the topic
    questions = db.Column(JSONB, nullable=False)  # Store all questions as JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# Session variable to store quiz data
quiz_data = None

# # Email configuration
# SMTP_SERVER = "smtp.gmail.com"
# SMTP_PORT = 465
# # Fetch email credentials from environment variables
# EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
# EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# # Function to send email
# def send_email(to_email, subject, body):
#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = EMAIL_ADDRESS
#     msg["To"] = to_email

#     try:
#         # Use SMTP_SSL instead of SMTP when using port 465
#         server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
#         server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
#         server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
#         server.quit()
#         print("Email sent successfully!")
#     except Exception as e:
#         print(f"Email sending failed: {str(e)}")
# send_email("izohaib714@gmail.com", "Test Email", "This is a test email from Python.")

@app.before_request
def check_user_status():
    """Check if user session is valid"""
    if 'user' in session and 'access_token' in session:
        try:
            user = supabase.auth.get_user(session['access_token'])  # ✅ Use access token
            if not user:
                session.clear()  # Clear all session data
                return redirect(url_for('login'))
        except Exception as e:
            print("Error checking user status:", str(e))
            session.clear()
            return redirect(url_for('login'))


# Update the dashboard route
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    user = Users.query.filter_by(email=user_email).first()
    print("\n=== Dashboard Debug ===")
    print("1. User:", user.email, user.id, user.role)
    
    if user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        # Get current time in UTC
        current_time = datetime.now(timezone.utc)
        
        # Get both quiz history and assigned quizzes
        assigned_quizzes = AssignedQuiz.query.filter_by(
            student_id=user.id,
            status='pending'
        ).order_by(AssignedQuiz.due_date.asc()).all()
        
        print("2. Found assigned quizzes:", len(assigned_quizzes))
        for aq in assigned_quizzes:
            # Ensure due_date is timezone aware
            if aq.due_date.tzinfo is None:
                aq.due_date = aq.due_date.replace(tzinfo=timezone.utc)
            print(f"   Quiz: {aq.quiz.title}, Due: {aq.due_date}, Status: {aq.status}")
        
        quiz_history = QuizHistory.query.filter_by(user_id=user.id).order_by(QuizHistory.date_taken.desc()).all()
        print("3. Quiz history entries:", len(quiz_history))
        
        return render_template('dashboard.html', 
                             quiz_history=quiz_history, 
                             assigned_quizzes=assigned_quizzes,
                             user_email=user_email,
                             now=current_time) # Add this line
    
@app.route('/input')
def input_page():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('input.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        # **1️⃣ Validate password before sending it to Supabase**
        password_regex = re.compile(r'^(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{6,}$')
        if not password_regex.match(password):
            return render_template('signup.html', error="Password must have at least 6 characters, one uppercase letter, one number, and one special character.", email=email, role=role)

        try:
             # Hash the password
            hashed_password = generate_password_hash(password)

            # Create a new user in the database
            new_user = Users(email=email, password=hashed_password, role=role)
            db.session.add(new_user)
            db.session.commit()

            # Sign up user in Supabase
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })

            # **Check for errors in response**
            if response.user is None and response.error is not None:
                return render_template('signup.html', error=response.error.message, email=email, role=role)

            return render_template('signup.html', message="Check your email to confirm your account.")

        except AuthApiError as e:
            return render_template('signup.html', error=f"Error: {e}")
        except Exception as e:
            db.session.rollback()
            return render_template('signup.html', error=f"Unexpected error: {str(e)}")

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Authenticate with Supabase
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})

            if not response or not response.session:
                return render_template('login.html', error="Invalid login credentials.")

            session_data = response.session
            user_data = session_data.user  # ✅ Correct way to access user data

            # ✅ Store Supabase Access Token in Flask Session
            session['user'] = user_data.email
            user = Users.query.filter_by(email=email).first()
            if user:
                session['role'] = user.role
            else:
                return render_template('login.html', error="User not found.")
            session['access_token'] = session_data.access_token  # Store token
            session.modified = True  # Ensure session is updated

            # Redirect based on role
            if 'role' in session and session['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        except Exception as e:
            return render_template('login.html', error=f"An unexpected error occurred: {str(e)}")

    return render_template('login.html')

# Route for forgot password
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        response = supabase.from_('users').select('id').eq('email', email).execute()
        if response.data:
            token = jwt.encode({
                'email': email,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            }, app.secret_key, algorithm='HS256')
            reset_link = url_for('reset_password', token=token, _external=True)
            send_email(email, 'Password Reset', f'Click the link to reset your password: {reset_link}')
            flash('Check your email for reset instructions.', 'success')
        else:
            flash('Email not found. Please enter a registered email.', 'error')
    return render_template('forgot_password.html')

# Route for reset password
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token')
    if not token:
        flash('Invalid or expired token.', 'error')
        return redirect(url_for('forgot_password'))

    try:
        decoded_token = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        email = decoded_token['email']
    except jwt.ExpiredSignatureError:
        flash('Token has expired.', 'error')
        return redirect(url_for('forgot_password'))
    except jwt.InvalidTokenError:
        flash('Invalid token.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        response = supabase.auth.update_user({"email": email, "password": new_password})
        if response:
            flash('Password changed successfully! Please go back to login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error updating password. Try again.', 'error')

    return render_template('reset_password.html')

# Update the teacher_required decorator if you haven't already
def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        
        user = Users.query.filter_by(email=session['user']).first()
        if not user or user.role != 'teacher':
            return jsonify({"error": "Access denied. Teachers only."}), 403
            
        return f(*args, **kwargs)
    return decorated_function
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.template_filter('timezone')
def timezone_filter(date):
    if isinstance(date, datetime):
        # Ensure the date is timezone aware
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.strftime('%Y-%m-%d %H:%M:%S %Z')
    return date

def send_quiz_notification(student_email, quiz_title, due_date):
    try:
        # Email credentials
        QUIZMENTOR_EMAIL = "quizmentor1@gmail.com"
        QUIZMENTOR_PASS = "kpbncqfacetxlhkp"
        
        # Create message
        msg = MIMEMultipart()
        msg["From"] = QUIZMENTOR_EMAIL
        msg["To"] = student_email
        msg["Subject"] = f"New Quiz Assigned: {quiz_title}"
        
        # Email body
        body = f"""
        Hello,

        A new quiz has been assigned to you:

        Quiz Title: {quiz_title}
        Due Date: {due_date.strftime('%Y-%m-%d %H:%M:%S')}

        Please log in to your QuizMentor account to attempt the quiz before the due date.

        Best regards,
        QuizMentor Team
        """
        
        msg.attach(MIMEText(body, "plain"))

        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(QUIZMENTOR_EMAIL, QUIZMENTOR_PASS)
        server.sendmail(QUIZMENTOR_EMAIL, student_email, msg.as_string())
        server.quit()
        
        print(f"✅ Email notification sent to {student_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email notification: {str(e)}")
        return False
    
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    user = Users.query.filter_by(email=user_email).first()
    current_time = datetime.now(timezone.utc)  # Ensure `now` is timezone-aware
    
    assigned_quizzes = AssignedQuiz.query.filter_by(
        student_id=user.id,
        status='pending'
    ).order_by(AssignedQuiz.due_date.asc()).all()
    
    # Make `due_date` timezone-aware
    for assignment in assigned_quizzes:
        if assignment.due_date.tzinfo is None:
            assignment.due_date = assignment.due_date.replace(tzinfo=timezone.utc)
    
    quiz_history = QuizHistory.query.filter_by(user_id=user.id).order_by(QuizHistory.date_taken.desc()).all()

    return render_template('dashboard.html', 
                           quiz_history=quiz_history, 
                           assigned_quizzes=assigned_quizzes,
                           user_email=user_email,
                           user_id=user.id,  # Pass user_id for feedback
                           now=current_time)

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user']
    user = Users.query.filter_by(email=user_email).first()
    if user.role != 'teacher':
        return redirect(url_for('dashboard'))
    return render_template('teacher_dashboard.html', user_email=user_email)

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

def prepare_data(input_text):
    token = tokenizer.batch_encode_plus(
        input_text,
        max_length=256,
        truncation=True,
        padding='max_length',
        add_special_tokens=True,
        return_tensors='tf'
    )
    return {
        'input_ids': tf.cast(token['input_ids'], tf.float64),
        'attention_mask': tf.cast(token['attention_mask'], tf.float64)
    }

from collections import Counter
from bert import classify_questions

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    global quiz_data
    if 'user' not in session:
        return redirect(url_for('login'))
    
    topic = request.form.get('topic')
    num_questions = int(request.form.get('num_questions'))
    namespaces = ["computer_organization", "operating_system"]
    
    try:
        # Generate quiz questions
        quiz_data = generate_quiz_from_pinecone(topic, namespaces, top_k=10, num_questions=num_questions)
        if quiz_data.get("error"):
            return render_template('input.html', error=quiz_data["error"])
        
        # Classify the difficulty of each question
        quiz_data['questions'] = classify_questions(quiz_data['questions'])
        
        # Calculate overall difficulty (most common difficulty level)
        difficulty_counts = Counter([q['difficulty'] for q in quiz_data['questions']])
        overall_difficulty = max(difficulty_counts, key=difficulty_counts.get)  # Most common difficulty
        
        # Add overall difficulty to quiz_data for frontend display
        quiz_data['overall_difficulty'] = overall_difficulty
        quiz_data['topic'] = topic
        
        return redirect(url_for('quiz_page'))
    except Exception as e:
        return render_template('input.html', error=str(e))

@app.route('/save_quiz_result', methods=['POST'])
def save_quiz_result():
    if 'user' not in session:
        return jsonify({"error": "User not logged in"}), 401
    
    try:
        data = request.get_json()
        user_email = session['user']
        user = Users.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Save a single entry in QuizHistory
        quiz_history = QuizHistory(
            user_id=user.id,
            topic=data.get('topic', 'Unknown'),
            score=float(data.get('score', 0)),
            total_questions=int(data.get('total_questions', 0)),
            date_taken=datetime.now(timezone.utc),
            difficulty=data.get('overall_difficulty', 'Unknown')  # Save overall difficulty
        )
        db.session.add(quiz_history)
        db.session.flush()  # Get the ID of the newly created quiz history

        # Process questions to include status (correct/incorrect)
        processed_questions = []
        for question in quiz_data['questions']:
            selected_answer = question.get('selected_answer', None)
            is_correct = selected_answer == question.get('correct_answer', None)
            processed_questions.append({
                'question_text': question['question_text'],
                'options': question['options'],
                'difficulty': question['difficulty'],
                'selected_answer': selected_answer,
                'correct_answer': question['correct_answer'],
                'status': 'correct' if is_correct else 'incorrect'
            })

        # Save detailed question data in the History table
        history = History(
            quiz_history_id=quiz_history.id,
            topic=data.get('topic', 'Unknown'),  # Save the topic in the History table
            questions=processed_questions  # Save all questions with status as JSON
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({"message": "Quiz result saved successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to save quiz result"}), 500

# Add these new routes to your existing Flask app
@app.route('/api/teacher/info')
def teacher_info():
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    return jsonify({
        "email": session['user']
    })

@app.route('/api/teacher/stats')
@teacher_required
def teacher_stats():
    teacher = Users.query.filter_by(email=session['user']).first()
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    teacher = Users.query.filter_by(email=session['user']).first()
    if teacher.role != 'teacher':
        return jsonify({"error": "Unauthorized"}), 403

    total_students = Users.query.filter_by(role='student').count()
    active_quizzes = AssignedQuiz.query.filter_by(
        teacher_id=teacher.id,
        status='pending'
    ).count()
    
    # Calculate average class score
    avg_score = db.session.query(func.avg(QuizHistory.score)).scalar() or 0
    
    return jsonify({
        "totalStudents": total_students,
        "activeQuizzes": active_quizzes,
        "averageScore": round(avg_score, 2)
    })
# Add these new routes after your existing routes

@app.route('/api/teacher/assignments')
@teacher_required
def get_teacher_assignments():
    filter_type = request.args.get('filter', 'all')
    teacher = Users.query.filter_by(email=session['user']).first()
    
    query = AssignedQuiz.query.filter_by(teacher_id=teacher.id)
    
    if filter_type == 'active':
        query = query.filter_by(status='pending')
    elif filter_type == 'completed':
        query = query.filter_by(status='completed')
    
    assignments = query.order_by(AssignedQuiz.assigned_date.desc()).limit(10).all()
    
    return jsonify([{
        'id': a.id,
        'quiz_title': a.quiz.title,
        'student_email': a.student.email,
        'due_date': a.due_date.isoformat(),
        'status': a.status
    } for a in assignments])

@app.route('/api/teacher/student-performance')
@teacher_required
def get_student_performance():
    topic = request.args.get('topic')
    order = request.args.get('order', 'desc')
    
    query = db.session.query(
        Users.email.label('student_email'),
        Quiz.topic,
        func.avg(QuizHistory.score).label('average_score')
    ).join(QuizHistory, Users.id == QuizHistory.user_id
    ).join(Quiz, QuizHistory.quiz_id == Quiz.id
    ).filter(Users.role == 'student'
    ).group_by(Users.email, Quiz.topic)
    
    if topic:
        query = query.filter(Quiz.topic == topic)
    
    if order == 'desc':
        query = query.order_by(func.avg(QuizHistory.score).desc())
    else:
        query = query.order_by(func.avg(QuizHistory.score).asc())
    
    results = query.all()
    
    topics = db.session.query(Quiz.topic).distinct().all()
    
    return jsonify({
        'topics': [t[0] for t in topics],
        'performance': [{
            'student_email': r.student_email,
            'topic': r.topic,
            'average_score': round(r.average_score, 2)
        } for r in results]
    })

@app.route('/teacher/assignment/<int:assignment_id>')
@teacher_required
def view_assignment(assignment_id):
    assignment = AssignedQuiz.query.get_or_404(assignment_id)
    return render_template('assignment_details.html', assignment=assignment)
@app.route('/api/teacher/student-performance')
def student_performance():
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    students = Users.query.filter_by(role='student').all()
    performance_data = []
    
    for student in students:
        quizzes = QuizHistory.query.filter_by(user_id=student.id).all()
        avg_score = sum(q.score for q in quizzes) / len(quizzes) if quizzes else 0
        
        performance_data.append({
            "id": student.id,
            "email": student.email,
            "quizzesTaken": len(quizzes),
            "averageScore": round(avg_score, 2)
        })
    
    return jsonify(performance_data)

# Add these routes after your existing routes

@app.route('/create-quiz')
@teacher_required
def create_quiz_page():
    return render_template('create_quiz.html')

@app.route('/api/teacher/students')
@teacher_required
def get_students():
    students = Users.query.filter_by(role='student').all()
    return jsonify([{
        'id': student.id,
        'email': student.email
    } for student in students])

@app.route('/api/generate-quiz', methods=['POST'])
@teacher_required
def generate_quiz_api():
    try:
        query = request.form.get('topic')  # We'll use the topic as the query
        num_questions = int(request.form.get('num_questions', 5))
        
        # Generate questions using existing function with correct parameters
        quiz_data = generate_quiz_from_pinecone(
            query=query,  # Pass as query parameter
            namespaces=["computer_organization", "operating_system"],
            top_k=10,
            num_questions=num_questions
        )
        
        if quiz_data.get("error"):
            return jsonify({"error": quiz_data["error"]}), 400
            
        return jsonify({
            "success": True,
            "questions": quiz_data["questions"],
            "topic": query  # Include the topic in response
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/teacher/assign-quiz', methods=['POST'])
@teacher_required
def assign_quiz_api():
    try:
        data = request.get_json()
        print("\n=== Quiz Assignment Debug ===")
        print("1. Received data:", data)
        
        # Verify all required data is present
        required_fields = ['title', 'topic', 'questions', 'students', 'due_date']
        for field in required_fields:
            if field not in data:
                print(f"Missing field: {field}")
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        teacher = Users.query.filter_by(email=session['user']).first()
        print("2. Teacher:", teacher.email, teacher.id)

        # Create the quiz first
        try:
            quiz = Quiz(
                title=data['title'],
                topic=data['topic'],
                creator_id=teacher.id,
                questions=data['questions']
            )
            db.session.add(quiz)
            db.session.flush()
            print("3. Created quiz:", quiz.id, quiz.title)

            # Now create the assignments and send emails
            due_date = datetime.fromisoformat(data['due_date'].replace('Z', '+00:00'))
            print("4. Due date:", due_date)
            print("5. Students to assign:", data['students'])
            
            for student_id in data['students']:
                # Get student email
                student = Users.query.get(int(student_id))
                if not student:
                    continue
                
                # Create assignment
                assignment = AssignedQuiz(
                    quiz_id=quiz.id,
                    teacher_id=teacher.id,
                    student_id=int(student_id),
                    due_date=due_date,
                    status='pending'
                )
                db.session.add(assignment)
                print(f"6. Created assignment for student {student_id}")
                
                # Send email notification
                send_quiz_notification(student.email, quiz.title, due_date)

            db.session.commit()
            print("7. Successfully committed to database")
            
            return jsonify({"success": True, "quiz_id": quiz.id})
            
        except Exception as e:
            print("Error:", str(e))
            raise

    except Exception as e:
        db.session.rollback()
        print("Fatal error:", str(e))
        return jsonify({"error": str(e)}), 500
    
@app.route('/take-quiz/<int:assignment_id>')
def take_assigned_quiz(assignment_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    assignment = AssignedQuiz.query.get_or_404(assignment_id)
    
    # Verify this quiz is assigned to the current user
    user = Users.query.filter_by(email=session['user']).first()
    if assignment.student_id != user.id:
        return "Unauthorized", 403
        
    if assignment.status != 'pending':
        return "Quiz already completed", 400
    
    # Get quiz data
    quiz = assignment.quiz
    quiz.assignment_id = assignment_id
    
    # No need to modify explanations as they already exist in the questions
    return render_template('take_quiz.html', quiz=quiz)

@app.route('/api/submit-assigned-quiz', methods=['POST'])
def submit_assigned_quiz():
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        assignment_id = data.get('assignment_id')
        if not assignment_id:
            return jsonify({"error": "No assignment ID provided"}), 400
            
        score = data.get('score')
        answers = data.get('answers')
        
        # Get the assignment
        assignment = AssignedQuiz.query.get_or_404(assignment_id)
        
        # Verify the current user is the assigned student
        user = Users.query.filter_by(email=session['user']).first()
        if assignment.student_id != user.id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Update assignment status and score
        assignment.status = 'completed'
        assignment.completed_date = datetime.now(timezone.utc)
        assignment.score = score
        
        # Create quiz history entry
        quiz_history = QuizHistory(
            user_id=user.id,
            quiz_id=assignment.quiz_id,
            assigned_quiz_id=assignment_id,
            topic=assignment.quiz.topic,
            score=score,
            total_questions=len(assignment.quiz.questions),
            date_taken=datetime.now(timezone.utc)
        )
        
        # Save changes
        db.session.add(quiz_history)
        db.session.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting quiz: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/quiz-result/<int:assignment_id>')
def quiz_result(assignment_id):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    assignment = AssignedQuiz.query.get_or_404(assignment_id)
    quiz_history = QuizHistory.query.filter_by(assigned_quiz_id=assignment_id).first_or_404()
    
    # Prepare questions with user answers
    questions_with_answers = []
    for q in assignment.quiz.questions:
        is_correct = q['correct_answer'] == q.get('user_answer')
        questions_with_answers.append({
            'question_text': q['question_text'],
            'options': q['options'],
            'user_answer': q.get('user_answer'),
            'correct_answer': q['correct_answer'],
            'is_correct': is_correct
        })
    
    return render_template('quiz_result.html',
                         score=quiz_history.score,
                         correct_answers=int((quiz_history.score/100) * quiz_history.total_questions),
                         total_questions=quiz_history.total_questions,
                         questions=questions_with_answers)
@app.route('/quiz/details/<int:quiz_id>')
def quiz_details(quiz_id):
    print(f"Fetching details for quiz ID: {quiz_id}")
    quiz = Quiz.query.get_or_404(quiz_id)
    print(f"Quiz found: {quiz.title}")
    return render_template('see_details.html', quiz=quiz)

@app.route('/generate-feedback/<int:user_id>', methods=['GET'])
def generate_feedback(user_id):
    # Fetch the user's quiz history
    quiz_history = QuizHistory.query.filter_by(user_id=user_id).all()
    
    if not quiz_history:
        return jsonify({"error": "No quiz history found for this user."}), 404

    # Prepare performance data
    performance_data = []
    for quiz in quiz_history:
        performance_data.append(f"{quiz.topic}: {quiz.score}%")

    # Create the prompt for the LLM
    groq_prompt = f"Given the following quiz performance: {', '.join(performance_data)}, provide personalized study advice and content links (like here is the link of course or article you can learn ).) ."

    # Call the ChatGroq API
    try:
        response = llm.invoke(groq_prompt)
        feedback = response.content.strip()  # Extract the feedback from the response
    except Exception as e:
        print(f"Error generating feedback: {str(e)}")
        return jsonify({"error": "Failed to generate feedback."}), 500

    return jsonify({"feedback": feedback})

@app.route('/api/train-weak-topic-model', methods=['POST'])
def train_weak_topic_model():
    """Train the weak topic prediction model."""
    try:
        # Fetch user performance data
        quiz_history = QuizHistory.query.all()
        data = []
        for entry in quiz_history:
            data.append({
                "user_id": entry.user_id,
                "topic": entry.topic,
                "score": entry.score
            })

        # Convert data to DataFrame
        df = pd.DataFrame(data)
        if df.empty:
            return jsonify({"error": "No data available to train the model."}), 400

        # Train the model
        train_model(df)
        return jsonify({"message": "Model trained and saved successfully!"})
    except Exception as e:
        print(f"Error training model: {str(e)}")
        return jsonify({"error": "Failed to train the model."}), 500

@app.route('/api/predict-weak-topics', methods=['GET'])
@teacher_required
def predict_weak_topics():
    """Predict weak topics for the class using the trained model."""
    try:
        # Load the trained model and label encoder
        model, label_encoder = load_model()

        # Fetch user performance data
        quiz_history = QuizHistory.query.all()
        data = []
        for entry in quiz_history:
            data.append({
                "user_id": entry.user_id,
                "topic": entry.topic,
                "score": entry.score
            })

        # Convert data to DataFrame
        df = pd.DataFrame(data)
        if df.empty:
            return jsonify({"error": "No data available for prediction."}), 400

        # Preprocess data
        df['topic_encoded'] = label_encoder.transform(df['topic'])

        # Predict weak topics
        predictions = model.predict(df[['topic_encoded', 'score']])
        df['is_weak'] = predictions

        # Aggregate weak topics
        weak_topics = df[df['is_weak'] == 1]['topic'].unique().tolist()

        return jsonify({"weak_topics": weak_topics})
    except FileNotFoundError:
        return jsonify({"error": "Model not found. Train the model first."}), 500
    except Exception as e:
        print(f"Error predicting weak topics: {str(e)}")
        return jsonify({"error": "Failed to predict weak topics."}), 500
    

if __name__ == '__main__':
    with app.app_context():
        # Ensure all database tables are created
        db.create_all()

        # Automatically train the weak topic model on startup
        try:
            # Fetch user performance data
            quiz_history = QuizHistory.query.all()
            data = []
            for entry in quiz_history:
                data.append({
                    "user_id": entry.user_id,
                    "topic": entry.topic,
                    "score": entry.score
                })

            # Convert data to DataFrame
            df = pd.DataFrame(data)
            if not df.empty:
                print("🔍 Training weak topic model on startup...")
                train_model(df)
                print("✅ Weak topic model trained successfully!")
            else:
                print("❌ No data available to train the weak topic model on startup.")
        except Exception as e:
            print(f"❌ Error training weak topic model on startup: {str(e)}")

    # Start the Flask application
    app.run(host='0.0.0.0', port=5000, debug=True)

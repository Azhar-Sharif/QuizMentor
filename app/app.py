import os
from datetime import datetime
import pytz
from functools import wraps
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from quiz_flow import generate_quiz_from_pinecone

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:123@localhost/mentor'   #use your database_username, Password and database_name according to your database. Format = username:Password@localhost/database_name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
# Add these imports at the top with other imports
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
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
        return render_template('teacher_dashboard.html', user_email=user_email)
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
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if not email.endswith('@gmail.com'):
            return render_template('signup.html', error="Email must end with @gmail.com")

        existing_user = Users.query.filter_by(email=email).first()
        if existing_user:
            return render_template('signup.html', error="Email already registered!")

        hashed_password = generate_password_hash(password)
        new_user = Users(email=email, password=hashed_password, role=role)
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
            session['role'] = user.role  # Store role in session
            return redirect(url_for('home'))
        else:
            error = "Invalid credentials. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

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
    
    try:
        data = request.get_json()
        user_email = session['user']
        user = Users.query.filter_by(email=user_email).first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Create quiz history with error handling
        try:
            quiz_history = QuizHistory(
                user_id=user.id,
                topic=data.get('topic', 'Unknown'),  # Default topic if not provided
                score=float(data.get('score', 0)),  # Convert to float
                total_questions=int(data.get('total_questions', 0)),  # Convert to int
                date_taken=datetime.now(timezone.utc)
            )
            
            db.session.add(quiz_history)
            db.session.commit()
            
            print(f"Quiz saved successfully for user {user_email}")  # Debug log
            return jsonify({"message": "Quiz result saved successfully"})
            
        except (ValueError, KeyError) as e:
            print(f"Error processing quiz data: {str(e)}")  # Debug log
            return jsonify({"error": "Invalid quiz data"}), 400
            
    except Exception as e:
        db.session.rollback()
        print(f"Error saving quiz result: {str(e)}")  # Debug log
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
        
    assignment = AssignedQuiz.query.filter_by(id=assignment_id).first_or_404()
    
    # Verify this quiz is assigned to the current user
    user = Users.query.filter_by(email=session['user']).first()
    if assignment.student_id != user.id:
        return "Unauthorized", 403
        
    if assignment.status != 'pending':
        return "Quiz already completed", 400
        
    # Store quiz data in session
    session['current_quiz'] = {
        'assignment_id': assignment_id,
        'questions': assignment.quiz.questions,
        'title': assignment.quiz.title,
        'topic': assignment.quiz.topic
    }
    
    return render_template('take_quiz.html', quiz=assignment.quiz)

@app.route('/api/submit-assigned-quiz', methods=['POST'])
def submit_assigned_quiz():
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
        
    try:
        data = request.get_json()
        assignment_id = data['assignment_id']
        score = data['score']
        answers = data['answers']
        
        # Get the assignment
        assignment = AssignedQuiz.query.get_or_404(assignment_id)
        
        # Update questions with user answers
        questions = assignment.quiz.questions
        for i, question in enumerate(questions):
            question['user_answer'] = answers.get(str(i))
        
        # Update assignment
        assignment.status = 'completed'
        assignment.completed_date = datetime.now(timezone.utc)
        assignment.score = score
        assignment.quiz.questions = questions  # Save updated questions with user answers
        
        # Create quiz history entry
        quiz_history = QuizHistory(
            user_id=assignment.student_id,
            quiz_id=assignment.quiz_id,
            assigned_quiz_id=assignment_id,
            topic=assignment.quiz.topic,
            score=score,
            total_questions=len(questions),
            date_taken=datetime.now(timezone.utc)
        )
        
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, jsonify, render_template, request, redirect, url_for, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone
import json
import os

# Initialize Flask app
app = Flask(__name__)

# Use environment variable for secret_key
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Configure database (PostgreSQL)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:7384625@localhost/Users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Users model for storing credentials
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

@app.before_request
def check_user_status():
    """Middleware to validate the session user against the database."""
    if 'user' in session:  # Check if a user is logged in
        user_email = session['user']  # Get the logged-in user's email from the session
        
        # Query the database to check if the user exists
        user_exists = Users.query.filter_by(email=user_email).first()
        
        if not user_exists:  # If the user doesn't exist in the database
            session.pop('user', None)  # Clear the session
            return redirect(url_for('login'))  # Redirect to login page


# Routes
@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('input.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup route to create new user accounts"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        existing_user = Users.query.filter_by(email=email).first()

        if existing_user:
            return render_template('signup.html', error="Email already registered!")

        # Hash the password before saving
        hashed_password = generate_password_hash(password)
        new_user = Users(email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))  # Redirect to login after signup

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')  # Assuming `username` is the email
        password = request.form.get('password')

        # Fetch the user from the database
        user = Users.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user'] = user.email  # Store user email in session
            return redirect(url_for('home'))
        else:
            error = "Invalid credentials. Please try again."
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/input')
def input_page():
    """Route to display the input page after login"""
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Ensure user is logged in
    return render_template('input.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

def clean_response(response_content):
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[3:-3]
    response_content = response_content.strip()
    try:
        parsed_response = json.loads(response_content)
        for question in parsed_response.get('questions', []):
            if 'options' in question:
                question['options'] = [option.replace("'", '"') for option in question['options']]
        return parsed_response
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Original Response Content:", response_content)
        return None

def search_mcqs_by_query(index, query, namespaces, top_k=50):
    model = SentenceTransformer('all-mpnet-base-v2')
    query_embedding = model.encode(query)
    all_results = []

    for namespace in namespaces:
        try:
            response = index.query(vector=query_embedding.tolist(), namespace=namespace, top_k=top_k, include_metadata=True)
            for match in response["matches"]:
                all_results.append({
                    "id": match["id"],
                    "metadata": match["metadata"],
                    "score": match["score"],
                    "namespace": namespace
                })
        except Exception as e:
            print(f"Error searching namespace '{namespace}': {e}")

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:top_k]

def generate_quiz_with_groq(llm, retrieved_data, query, num_questions):
    formatted_mcqs = ""
    for i, mcq in enumerate(retrieved_data['mcqs']):
        question_img_link = mcq.get('question_img_link', 'No image available')
        formatted_mcqs += f"""
        {{
            "question_text": "{mcq['question_text']}",
            "question_img_link": "{question_img_link}",
            "options": {json.dumps(mcq['options'])},
            "correct_option": "{mcq['correct_option']}"
        }}"""

    groq_prompt = f"""
Create a quiz with exactly {num_questions} multiple-choice questions aligned with the query: "{query}".
Use the following MCQs as much as possible, and generate new ones (using context) only if required. Rewrite or enhance questions if needed to ensure clarity, conciseness, and relevance.

MCQs:
{formatted_mcqs}

Return the quiz in this exact JSON format (starting directly with a valid JSON object):
{{
    "questions": [
        {{
            "question_text": "The question here",
            "question_img_link": "img_link here",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "Correct option text",
            "Explanation_of_correct_answer":"Some text"
        }}
    ]
}}
"""
    response = llm.invoke(groq_prompt)
    return clean_response(response.content)

def generate_quiz_from_pinecone(query, namespaces, top_k=10, num_questions=10):
    pc = Pinecone(api_key="pcsk_3CYnJi_TZbGr8CeCcVxAsz4Li7J5n5hNBRqM7PA7k6xGKx7ftNXUYMYUJLJcb3PZrTneH4", environment="us-west1-gcp")
    index_name = "mcq-index"
    index = pc.Index(index_name)

    mcq_results = search_mcqs_by_query(index, query, namespaces, top_k)
    if not mcq_results:
        return {"error": "No MCQs found for the given query."}

    retrieved_mcqs = []
    for match in mcq_results:
        metadata = match["metadata"]
        retrieved_mcqs.append({
            "topic": metadata.get("topic"),
            "question_no": metadata.get("question_no"),
            "question_text": metadata.get("question_text"),
            "question_img_link": metadata.get("question_img_link"),
            "options": metadata.get("options"),
            "correct_option": metadata.get("correct_option")
        })

    retrieved_data = {
        "query": query,
        "mcqs": retrieved_mcqs
    }

    llm = ChatGroq(
        temperature=0,
        groq_api_key="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",
        model_name="llama-3.3-70b-versatile"
    )

    return generate_quiz_with_groq(llm, retrieved_data, query, num_questions)

@app.route('/quiz')
def quiz_page():
    """Route to serve the quiz page"""
    return render_template('index.html')

@app.route('/api/quiz')
def quiz_api():
    """API endpoint to get quiz data"""
    global quiz_data
    if quiz_data is None:
        return jsonify({"error": "No quiz data available"})
    return jsonify(quiz_data)

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    """Handle quiz generation from form submission"""
    global quiz_data
    
    topic = request.form.get('topic')
    num_questions = int(request.form.get('num_questions'))
    namespaces = ["computer_organization", "operating_system"]  # Add your namespaces
    
    try:
        quiz_data = generate_quiz_from_pinecone(topic, namespaces, top_k=10, num_questions=num_questions)
        if quiz_data.get("error"):
            return render_template('input.html', error=quiz_data["error"])
        return redirect(url_for('quiz_page'))
    except Exception as e:
        return render_template('input.html', error=str(e))

if __name__ == '__main__':
    app.run(debug=True)

# Session variable to store quiz data
quiz_data = None

@app.route('/')
def home():
    """Route to serve the input page"""
    return render_template('input.html')

if __name__ == '__main__':
    app.run(debug=True)


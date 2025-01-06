from flask import Flask, jsonify, render_template, request, redirect, url_for
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone
import json
from llm_integrate.py import *

app = Flask(_name_)
# Session variable to store quiz data
quiz_data = None

@app.route('/')
def home():
    """Route to serve the input page"""
    return render_template('input.html')

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

if _name_ == '_main_':
    app.run(debug=True)

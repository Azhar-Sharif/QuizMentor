from flask import Flask, render_template, request, redirect, url_for
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Initialize Pinecone and the model
pc = Pinecone(api_key="pcsk_3CYnJi_TZbGr8CeCcVxAsz4Li7J5n5hNBRqM7PA7k6xGKx7ftNXUYMYUJLJcb3PZrTneH4", environment="us-west1-gcp")
index_name = "mcq-index"
index = pc.Index(index_name)
app = Flask(__name__)
# Define the function to retrieve MCQs from Pinecone
def retrieve_mcqs(query, namespaces, top_k=10):
    model = SentenceTransformer('all-mpnet-base-v2')
    query_embedding = model.encode(query)
    all_results = []

    for namespace in namespaces:
        response = index.query(vector=query_embedding.tolist(), namespace=namespace, top_k=top_k, include_metadata=True)
        for match in response["matches"]:
            all_results.append({
                "text": match["id"],
                "metadata": match["metadata"],
                "score": match["score"],
                "namespace": namespace
            })

    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:top_k]  # Return top_k best matches

@app.route('/', methods=['GET', 'POST'])
def home():
    # If it's a POST request (form submission)
    if request.method == 'POST':
        answers = request.form.getlist('answers')  # Get the list of selected answers
        correct_answers = request.form.getlist('correct_answers')  # Get the correct answers
        questions = request.form.getlist('questions')  # Get the questions

        score = 0
        feedback = []

        # Check answers and prepare feedback
        for i in range(len(answers)):
            is_correct = answers[i] == correct_answers[i]
            feedback.append({
                'question': questions[i],
                'selected_answer': answers[i],
                'correct_answer': correct_answers[i],
                'is_correct': is_correct
            })
            if is_correct:
                score += 1

        return render_template('index.html', feedback=feedback, score=score, total=len(answers), questions=questions, answers=answers)

    # If it's a GET request (first time loading the page)
    search_query = request.args.get('query', '')
    namespaces = ["computer_organization", "operating_system"]

    if not search_query:
        return render_template('index.html', error="Please provide a search query.", answers=[])

    mcq_results = retrieve_mcqs(search_query, namespaces)

    # Prepare formatted response
    formatted_results = []
    if mcq_results:
        for result in mcq_results:
            metadata = result["metadata"]
            formatted_results.append({
                "question": f"Question {metadata.get('question_no', 'Unknown')}: {metadata.get('question_text', 'No question text available')}",
                "options": metadata.get("options", []),
                "correct_answer": metadata.get("correct_option", "Unknown"),
                "namespace": result["namespace"],
                "score": result["score"]
            })
    else:
        formatted_results = [{"message": "No MCQs found for the given query."}]
    
    return render_template('index.html', questions=formatted_results, answers=[], error=None)

if __name__ == '__main__':
    app.run(debug=True)

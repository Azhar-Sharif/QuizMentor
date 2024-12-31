from flask import Flask, render_template, request, jsonify
from pinecone import Pinecone
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from flask_cors  import CORS
# Initialize Flask app
app = Flask(__name__)
CORS(app)
# Initialize the embedding model
embedding_model = SentenceTransformer("multi-qa-mpnet-base-dot-v1")
# Initialize Pinecone
def initialize_pinecone(api_key, environment):
    return Pinecone(api_key=api_key, environment=environment)

# Initialize Pinecone Index
pinecone_api_key = "pcsk_3CYnJi_TZbGr8CeCcVxAsz4Li7J5n5hNBRqM7PA7k6xGKx7ftNXUYMYUJLJcb3PZrTneH4"
pinecone_environment = "us-west1-gcp"
pc = initialize_pinecone(api_key=pinecone_api_key, environment=pinecone_environment)
# Example list of topics from metadata (extracted topics for both namespaces)
extracted_topics_computer_organization = ['Microprocessor', 'Computer Organization Architecture', 'Digital Logic Number Representation',
                                          'Number Representation', 'Dead Lock', 'Cpu Scheduling']
extracted_topics_operating_system = ['Unix', 'Process Management', 'Memory Management', 'Input Output Systems']

# Function to extract the most relevant topic based on semantic similarity
def extract_topic_from_query(query, topics, model):
    query_embedding = model.encode([query])[0]
    topic_embeddings = model.encode(topics)
    similarities = cosine_similarity([query_embedding], topic_embeddings)[0]
    most_similar_index = np.argmax(similarities)
    return topics[most_similar_index]

# Function to retrieve MCQs based on the topic and question range from Pinecone metadata
def get_mcqs_by_topic(index, topic, namespaces, top_k=10):
    try:
        query_embedding = embedding_model.encode([topic])[0]  # Use topic embedding as the query vector
        query_response = index.query(
            vector=query_embedding,  # Pass the query vector
            filter={"topic": topic},
            top_k=top_k,
            namespace=namespaces,
            include_metadata=True
        )
        
        mcqs = []
        for match in query_response['matches']:
            mcqs.append(match['metadata'])
        
        return mcqs
    
    except Exception as e:
        print(f"Error retrieving MCQs for topic '{topic}': {e}")
        return []

# Function to handle queries and get MCQs
def handle_query(query, topics_computer_organization, topics_operating_system, index, namespaces, model, top_k=10):
    topics = topics_computer_organization + topics_operating_system
    topic = extract_topic_from_query(query, topics, model)
    
    if topic:
        mcqs_for_topic = get_mcqs_by_topic(index, topic, namespaces, top_k)
        return topic, mcqs_for_topic
    return None, []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']
    top_k = int(request.form['top_k'])
    namespaces = ["computer_organization", "operating_system"]

    topic, mcqs_for_topic = handle_query(query, extracted_topics_computer_organization, extracted_topics_operating_system, index, namespaces, embedding_model, top_k)
    
    return jsonify({
        'topic': topic,
        'mcqs': mcqs_for_topic
    })

if __name__ == '__main__':
    app.run(debug=True)

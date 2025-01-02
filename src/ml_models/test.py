from pinecone import Pinecone
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, request, jsonify, render_template
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Initialize Pinecone
# Replace these with your actual Pinecone API key and environment
pc = Pinecone(api_key="pcsk_3CYnJi_TZbGr8CeCcVxAsz4Li7J5n5hNBRqM7PA7k6xGKx7ftNXUYMYUJLJcb3PZrTneH4", environment="us-west1-gcp") 
index_name = "mcq-index"
index = pc.Index(index_name)

# Initialize the embedding model
embedding_model = SentenceTransformer("multi-qa-mpnet-base-dot-v1")

# ... (Your existing functions: retrieve_topics_from_namespaces, 
# extract_topic_from_query, search_pinecone_by_topic) ...

def retrieve_topics_from_namespaces(index, namespaces):
    """
    Retrieve topics from multiple namespaces and store them in separate lists.
    """
    topics_by_namespace = {}

    for namespace in namespaces:
        topics = set()  # Using set to avoid duplicate topics
        try:
            response = index.query(vector=[0] * 768, namespace=namespace, top_k=1000, include_metadata=True)
            for match in response["matches"]:
                metadata = match.get("metadata", {})
                if "topic" in metadata:
                    topics.add(metadata["topic"])
        except Exception as e:
            print(f"Error retrieving metadata from namespace '{namespace}': {e}")

        topics_by_namespace[namespace] = list(topics)  # Convert set to list

    return topics_by_namespace

def extract_topic_from_query(query, topics, model):
    """
    Extract the most relevant topic based on the query.
    
    (Placeholder - Replace with your actual topic extraction logic)
    """
    # ... (Your implementation to extract the topic) ...
    if topics:
        return topics[0]  # Returning the first topic as a placeholder
    else:
        return None

def search_pinecone_by_topic(query, namespaces, top_k=10):
    """
    Searches Pinecone index for vectors similar to the given query within specified namespaces.
    """
    try:
        model = SentenceTransformer('all-mpnet-base-v2')
        query_embedding = model.encode(query)
        
        # Get all topics from specified namespaces
        topics_by_namespace = retrieve_topics_from_namespaces(index, namespaces)
        all_topics = [topic for topics in topics_by_namespace.values() for topic in topics]
        
        # Extract relevant topic based on the query
        extracted_topic = extract_topic_from_query(query, all_topics, embedding_model)

        # Search across specified namespaces
        mcqs = []  
        for namespace in namespaces:
            results = index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True,
                filter={"topic": {"$eq": extracted_topic}},  # Filter by topic
                namespace=namespace 
            )
        
            # Process results and filter for valid metadata
            for match in results.matches:
                metadata = match.metadata
                if metadata and metadata.get("question_text"):  # Check for valid metadata
                    mcqs.append(metadata)
        
        return json.dumps(mcqs, indent=2)

    except Exception as e:
        print(f"Error during Pinecone search: {e}")
        return json.dumps({"error": str(e)})
    
app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index1.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query')
    namespaces = data.get('namespaces', ["computer_organization", "operating_system"])
    top_k = data.get('top_k', 10)

    search_results_json = search_pinecone_by_topic(query, namespaces, top_k)

    return jsonify(json.loads(search_results_json))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
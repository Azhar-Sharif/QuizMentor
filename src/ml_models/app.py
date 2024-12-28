from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS
from pinecone import Pinecone, ServerlessSpec
from langchain_groq import ChatGroq

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow all origins

# Initialize Pinecone
pc = Pinecone(api_key="pcsk_3CYnJi_TZbGr8CeCcVxAsz4Li7J5n5hNBRqM7PA7k6xGKx7ftNXUYMYUJLJcb3PZrTneH4", environment="us-west1-gcp")
index_name = "quiz-index"
index = pc.Index(index_name)

# Initialize ChatGroq
llm = ChatGroq(
    temperature=0,
    groq_api_key="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",
    model_name="llama-3.1-70b-versatile"
)

@app.route("/")
def home():
    return jsonify({"message": "Welcome to QuizMentor Backend!"})

@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    # Get the query from the request body
    data = request.get_json()
    query = data.get("query")
    if not query:
        return jsonify({"error": "Query not provided"}), 400

    try:
        # Generate query embedding
        query_embedding = pc.inference.embed(
            model="multilingual-e5-large",
            inputs=[query],
            parameters={"input_type": "query"}
        )

        # Retrieve relevant context
        results = index.query(
            namespace="example-namespace",
            vector=query_embedding[0].values,
            top_k=3,
            include_metadata=True
        )
        if not results["matches"]:
            return jsonify({"error": "No relevant context found"}), 404

        retrieved_context = "\n".join([match["metadata"]["text"] for match in results["matches"]])

        # Generate quiz with ChatGroq
        groq_prompt = f"""
        Based on the following context, create a quiz with 10 multiple-choice questions:
        {retrieved_context}
        """
        response = llm.invoke(groq_prompt)
        return jsonify({"quiz": response.content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

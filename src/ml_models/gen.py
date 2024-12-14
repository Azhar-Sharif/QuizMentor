# Optimized Quiz Generation Code with LLaMA-3.1-70B-Versatile Model and Pinecone Integration

## Import Required Libraries
from transformers import LlamaForCausalLM, LlamaTokenizer
import pinecone
import numpy as np

# Load the LLaMA-3.1-70B-Versatile Model and Tokenizer
model_name = "llama-3.1-70b-versatile"
tokenizer = LlamaTokenizer.from_pretrained(model_name)
model = LlamaForCausalLM.from_pretrained(model_name, device_map="auto")

# Initialize Pinecone API
pinecone.init(api_key="your-pinecone-api-key", environment="your-pinecone-environment")
index = pinecone.Index("quiz-index")

## Function to Generate Quiz Questions

def generate_quiz(prompt, num_questions=5):
    """Generate quiz questions using the LLaMA-3.1-70B-Versatile model."""
    try:
        input_text = f"Generate {num_questions} quiz questions based on: {prompt}"
        inputs = tokenizer(input_text, return_tensors="np")  # Replacing PyTorch tensors with NumPy
        outputs = model.generate(**inputs, max_length=512, temperature=0.7)
        questions = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return questions
    except Exception as e:
        return f"Error generating quiz: {e}"

## Function to Add Quiz to Pinecone Index

def add_to_pinecone(quiz_text, topic):
    """Add generated quiz to Pinecone index with topic as metadata."""
    try:
        # Use pre-trained model embeddings (placeholder for actual embedding logic)
        embedding_vector = np.zeros(1536).tolist()  # Replace with real embeddings if available

        # Upsert into Pinecone
        index.upsert([
            {
                "id": topic,
                "values": embedding_vector,
                "metadata": {"quiz": quiz_text, "topic": topic}
            }
        ])
        return f"Quiz added to Pinecone under topic: {topic}"
    except Exception as e:
        return f"Error adding to Pinecone: {e}"

## Function to Retrieve Quiz from Pinecone

def retrieve_quiz(topic):
    """Retrieve the most relevant quiz for a topic from Pinecone."""
    try:
        # Placeholder for actual query vector
        query_vector = np.zeros(1536).tolist()

        # Query Pinecone
        query_response = index.query(
            vector=query_vector,
            top_k=1,
            include_metadata=True
        )
        if query_response['matches']:
            return query_response['matches'][0]['metadata']['quiz']
        return f"No quiz found for topic: {topic}"
    except Exception as e:
        return f"Error retrieving quiz: {e}"

## Main Execution
if __name__ == "__main__":
    user_prompt = input("Enter the topic or material for quiz generation: ")
    generated_quiz = generate_quiz(user_prompt)
    print("\nGenerated Quiz:\n", generated_quiz)

    save_quiz = input("Do you want to save this quiz to Pinecone? (yes/no): ").lower()
    if save_quiz == "yes":
        topic = input("Enter a topic keyword for this quiz: ")
        result = add_to_pinecone(generated_quiz, topic)
        print(result)

    retrieve_option = input("Do you want to retrieve a quiz from Pinecone? (yes/no): ").lower()
    if retrieve_option == "yes":
        topic_to_retrieve = input("Enter the topic keyword to retrieve: ")
        retrieved_quiz = retrieve_quiz(topic_to_retrieve)
        print("\nRetrieved Quiz:\n", retrieved_quiz)

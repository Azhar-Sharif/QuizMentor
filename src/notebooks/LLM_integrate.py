from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone
import json
def clean_response(response_content):
    """
    Cleans and parses JSON response content in two phases:
    1. Initial parsing after escaping special characters and extracting JSON content.
    2. If the first attempt fails, performs additional cleaning (like removing backticks, fixing quotes, etc.) and retries.
    """
    # Phase 1: Direct Parsing
    try:
        # Escape special characters
        response_content = response_content.replace('%', '%%')  # Escape '%'

        # Extract JSON content if it's within text
        start_index = response_content.find("[")
        end_index = response_content.rfind("]") + 1  # Include the closing brace
        if start_index != -1 and end_index != -1:
            response_content = response_content[start_index:end_index]

        # Attempt to parse directly
        return json.loads(response_content)

    except json.JSONDecodeError:
        print("Initial parsing failed. Proceeding to additional cleaning.")

    # Phase 2: Additional Cleaning and Parsing
    # Remove triple backticks
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[3:-3]  # Remove first and last three characters

    # Trim whitespace
    response_content = response_content.strip()

    try:
        # Parse the JSON content
        parsed_response = json.loads(response_content)

        # Loop through each question and modify the 'options' list
        for question in parsed_response.get('questions', []):
            if 'options' in question:
                # Replace single quotes with double quotes in each option
                question['options'] = [option.replace("'", '"') for option in question['options']]

        return parsed_response

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON after additional cleaning: {e}")
        print("Final Response Content:", response_content)
        return None




# Function to search MCQs based on user query across multiple namespaces
def search_mcqs_by_query(index, query, namespaces, top_k=50):
    """
    Searches for MCQs across multiple namespaces and returns the best matches.
    """
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

    # Sort all results by score in descending order
    all_results.sort(key=lambda x: x["score"], reverse=True)


    return all_results[:top_k]  # Return top_k best matches across all namespaces


# Function to generate a quiz using ChatGroq (LLaMA model)
def generate_quiz_with_groq(llm, retrieved_data, query, num_questions):
    """
    Generates a quiz using the LLM, allowing augmentation beyond the retrieved data.
    """
    # Format the retrieved data into a usable string format
    formatted_mcqs = ""
    for i, mcq in enumerate(retrieved_data['mcqs']):
        # Handle missing image link
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
Use the following MCQs as much as possible, and generate new ones only if required.Rewrite or enhance questions if needed to ensure clarity, conciseness, and relevance.
AND gnerate in provided json format and add explaination of correct answer also, i repeat IN json foramt.
MCQs:
{formatted_mcqs}
"""

    # Get the response from the LLaMA model
    response = llm.invoke(groq_prompt)

    # Try to parse the response content as JSON
    return clean_response(response.content)



# Function to integrate Pinecone query with quiz generation
def generate_quiz_from_pinecone(query, namespaces, top_k=50, num_questions=10):
    """
    Generates a quiz using data retrieved from Pinecone, aligned with the query and user constraints.
    """
    # Initialize Pinecone
    pc = Pinecone(api_key="pcsk_3CYnJi_TZbGr8CeCcVxAsz4Li7J5n5hNBRqM7PA7k6xGKx7ftNXUYMYUJLJcb3PZrTneH4", environment="us-west1-gcp")
    index_name = "mcq-index"
    index = pc.Index(index_name)

    # Retrieve the MCQs based on the user query
    mcq_results = search_mcqs_by_query(index, query, namespaces, top_k)
    if not mcq_results:
        return "No MCQs found for the given query."

    # Convert retrieved MCQ data into a structured JSON format
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

    # Convert retrieved data into a JSON-like string for LLM
    retrieved_data = {
        "query": query,
        "mcqs": retrieved_mcqs
    }

    # Initialize ChatGroq LLM
    llm = ChatGroq(
        temperature=0,
        groq_api_key="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",  # Replace with your actual API key
        model_name="llama-3.3-70b-versatile"
    )

    # Generate quiz using ChatGroq
    return generate_quiz_with_groq(llm, retrieved_data, query, num_questions)


def main():
    # Example usage
    query = input("Enter your search query: ")
    namespaces = ["computer_organization", "operating_system"]  # Add or modify namespaces as needed
    top_k = 10  # Default value for maximum results to retrieve
    num_questions = int(input("Enter the number of MCQs you want in the quiz: "))

    # Generate quiz based on user query
    quiz = generate_quiz_from_pinecone(query, namespaces, top_k, num_questions)
    print(quiz)

if __name__ == "__main__":
    main()
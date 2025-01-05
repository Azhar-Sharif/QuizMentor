from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
import pinecone
from pinecone import Pinecone
import json

import json

def clean_response(response_content):
    """
    Cleans the response by removing the triple backticks (if present), 
    replacing single quotes with double quotes in the 'options' list, 
    and parsing the cleaned JSON.
    """
    # Remove the starting and ending triple backticks if present
    if response_content.startswith("```") and response_content.endswith("```"):
        response_content = response_content[3:-3]  # Remove the first and last three characters

    # Trim whitespace
    response_content = response_content.strip()

    try:
        # Parse the JSON content
        parsed_response = json.loads(response_content)

        # Loop through each question and modify the options
        for question in parsed_response.get('questions', []):
            if 'options' in question:
                # Replace single quotes with double quotes in each option
                question['options'] = [option.replace("'", '"') for option in question['options']]

        return parsed_response
    
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Original Response Content:", response_content)
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
    return quiz
if __name__ == "__main__":
    main()
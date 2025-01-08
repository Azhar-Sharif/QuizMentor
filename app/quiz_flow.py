import os
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from langchain_groq import ChatGroq
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
Create a quiz with exactly {num_questions} multiple-choice questions aligned with the user query: "{query}".
Use the following MCQs as much as possible, and generate new ones only if required.Rewrite or enhance questions if needed to ensure clarity, conciseness, and relevance in all data.
AND gnerate in provided json format and add Explanation_of_correct_answer also, i repeat IN json foramt.
MCQs:
{formatted_mcqs}
"""
    response = llm.invoke(groq_prompt)
    return {
        "questions" : clean_response(response.content),
        "topic" : query
        }

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

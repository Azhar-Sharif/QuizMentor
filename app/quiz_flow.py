import os
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone
from langchain_groq import ChatGroq
import json

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
    return {
        "questions" : clean_response(response.content)['questions'],
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

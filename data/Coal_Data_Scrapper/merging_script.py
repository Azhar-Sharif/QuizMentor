import json

# File paths for the input files and output file
questions_file = 'Computer_Organization_Architecture.json'  # File with questions, options, and images
answers_file = 'Computer_Organization_Architecture_correct_answers.json'    # File with question numbers and correct options
output_file = 'Computer_Organization_Architecture_mcqs.json'
import json

# Load the answer file
with open(answers_file, "r", encoding="utf-8") as answer_file:
    answers_data = json.load(answer_file)

# Load the question file
with open(questions_file, "r", encoding="utf-8") as question_file:
    questions_data = json.load(question_file)

# Convert the answers into a dictionary for faster lookup
answers_dict = {item["question_number"]: item["correct_answer"] for item in answers_data}

# Append the correct answer to each question
for question in questions_data:
    # Extract the question number from the "question" field (e.g., "Question1" -> 1)
    question_number = int(question["question"].replace("Question", ""))

    # Find the correct answer using the question number
    correct_answer = answers_dict.get(question_number, None)

    # Append the correct answer to the question data
    question["correct_answer"] = correct_answer

# Save the updated questions file
with open(output_file, "w", encoding="utf-8") as updated_file:
    json.dump(questions_data, updated_file, indent=4, ensure_ascii=False)

print(f"File saved as {output_file}")

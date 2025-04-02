import json
import os

# File paths
questions_file = r"D:\QuizMentor\data\DBMS_data_scrapper\Transactions_and_concurrency_control.json"
answers_file = r"D:\QuizMentor\data\DBMS_data_scrapper\Transactions_and_concurrency_control_correct_answers.json"

# Create the output directory
output_directory = r"D:\QuizMentor\data\DBMS_data_scrapper\DBMS_MCQS"
os.makedirs(output_directory, exist_ok=True)

# Generate the output file path based on the questions file name
output_file_name = os.path.basename(questions_file)  # Extract the file name (e.g., "sql.json")
output_file = os.path.join(output_directory, output_file_name)  # Save in the new directory

# Load data from files
with open(questions_file, 'r', encoding='utf-8') as q_file:
    questions_data = json.load(q_file)

with open(answers_file, 'r', encoding='utf-8') as a_file:
    answers_data = json.load(a_file)

# Create a dictionary for quick lookup of correct answers
answers_dict = {answer["question_number"]: answer["correct_answer"] for answer in answers_data}

# Merge the data
merged_data = []
for i, question in enumerate(questions_data, start=1):
    question_number = i
    correct_answer = answers_dict.get(question_number, None)
    merged_question = {
        "question": question["question"],
        "question_paragraph": question["question_paragraph"],
        "options": question["options"],
        "image_link": question["image_link"],
        "correct_answer": correct_answer
    }
    merged_data.append(merged_question)

# Write the merged data to the new file in the DBMS_MCQS directory
with open(output_file, 'w', encoding='utf-8') as out_file:
    json.dump(merged_data, out_file, indent=4)

print(f"Merged data has been written to {output_file}")
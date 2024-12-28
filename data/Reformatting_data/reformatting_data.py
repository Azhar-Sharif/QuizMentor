import json
import os

def update_scraped_data(input_dir, output_dir):
    
    os.makedirs(output_dir, exist_ok=True)

    # Iterate through all JSON files in the input directory
    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_path = os.path.join(input_dir, filename)
            topic_name = filename.replace(".json", "").replace("_", " ").title()  
            print(f"Processing topic: {topic_name}")
            
            with open(input_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            updated_data = []
            # Update each question
            for question in data:
                updated_question = {
                    "topic": topic_name,
                    "question_no": question.pop("question", None),  # Rename question to question_no
                    "question_text": question.pop("question_paragraph", None),  # Rename question_paragraph to question_text
                    "question_img_link": question.pop("image_link", None),  # Rename image_link to question_img_link
                    "options": question.get("options", []),  # Ensure options field exists
                    "correct_option": question.get("correct_answer", "")  # Ensure correct_option field exists
                }
                updated_data.append(updated_question)

            # Save the updated file to the output directory
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as outfile:
                json.dump(updated_data, outfile, indent=4, ensure_ascii=False)

            print(f"Updated {filename} for topic: {topic_name}")

# Directories for input and output files
input_directory = "Coal_mcqs_data" 
output_directory = "Final_Coal_mcqs_data" 


update_scraped_data(input_directory, output_directory)

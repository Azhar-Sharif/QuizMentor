import json

def process_correct_answers(file_path):
    """
    Processes the JSON file to remove the 'question' field and modify the 'correct_answer' field.

    Args:
        file_path (str): Path to the JSON file.
    """
    try:
        # Load the JSON data
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Process each question
        for item in data:
            # Remove the 'question' field
            if 'question' in item:
                del item['question']

            # Extract the string after the first '\n' in 'correct_answer'
            if 'correct_answer' in item and '\n' in item['correct_answer']:
                item['correct_answer'] = item['correct_answer'].split('\n', 1)[1].strip()

        # Save the modified JSON data back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print(f"Processed data saved to {file_path}")

    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {file_path}.")
    except Exception as e:
        print(f"An error occurred: {e}")


# Example usage
if __name__ == "__main__":
    file_path = r"D:\QuizMentor\data\DBMS_data_scrapper\Transactions_and_concurrency_control_correct_answers.json"
    process_correct_answers(file_path)
import json
import os

def correct_question_numbering(file_path):
    """
    Corrects the numbering of questions in a JSON file.

    Args:
        file_path (str): Path to the JSON file containing questions.
    """
    try:
        # Load the JSON data
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Correct the numbering
        for index, question in enumerate(data, start=1):
            question['question'] = f"Question{index}"

        # Save the corrected JSON data back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print(f"Question numbering corrected in {file_path}")

    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {file_path}.")
    except Exception as e:
        print(f"An error occurred: {e}")


def correct_all_json_files_in_directory(directory_path):
    """
    Corrects the numbering of questions in all JSON files in a directory.

    Args:
        directory_path (str): Path to the directory containing JSON files.
    """
    try:
        # Iterate through all files in the directory
        for file_name in os.listdir(directory_path):
            if file_name.endswith('.json'):
                file_path = os.path.join(directory_path, file_name)
                correct_question_numbering(file_path)
    except Exception as e:
        print(f"An error occurred while processing the directory: {e}")


# Example usage
if __name__ == "__main__":
    directory_path = r"d:\QuizMentor\data\DBMS_data_scrapper"
    correct_all_json_files_in_directory(directory_path)
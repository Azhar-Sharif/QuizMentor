from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

# Set up the WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# URL for the topic
topic_url = "https://www.geeksforgeeks.org/quizzes/process-synchronization-gq/"

# List to hold the questions and correct answers
questions_data = []

# Initialize a global question number counter
question_number = 1

# Loop through the first few pages for the topic
for page in range(1, 12):  
    # Construct the page URL
    url = f"{topic_url}?page={page}"
    
    # Navigate to the page
    driver.get(url)
    
    # Wait for the questions to load dynamically
    WebDriverWait(driver, 5).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "QuizQuestionCard_quizCard__9T_0J"))
    )
    
    # Find all the question containers
    question_containers = driver.find_elements(By.CLASS_NAME, "QuizQuestionCard_quizCard__9T_0J")
        
    for container in question_containers:  # Process each question
        try:
            # Extract options and click the first one to trigger the correct answer class
            options_elements = container.find_elements(By.TAG_NAME, "li")
            correct_answer = None  # Initialize correct answer as None
            
            if not options_elements:
                # Skip the question if no options are found
                questions_data.append({
                    "question_number": question_number,
                    "correct_answer": "null"
                })
                question_number += 1
                continue
            
            # Click the first option to potentially load the correct answer
            options_elements[0].click()
            
            # Wait for the correct answer class to appear
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "QuizQuestionCard_selectedRow__b_SAP"))
            )
            
            # Identify the correct option
            for opt in options_elements:
                if "QuizQuestionCard_selectedRow__b_SAP" in opt.get_attribute("class"):
                    correct_answer = opt.text.strip()  # Set the correct answer if found
                    break  # Found the correct answer, move to the next question
            
            # If no correct option is found, leave it as None
            if correct_answer is None:
                correct_answer = "null"
            
            # Append the question number and correct answer to the list
            questions_data.append({
                "question_number": question_number,
                "correct_answer": correct_answer
            })
            
            
        
        except Exception as e:
            print(f"Error processing question {question_number}: {e}")
            # If an error occurs, append null as the answer for that question
            questions_data.append({
                "question_number": question_number,
                "correct_answer": "null"
            })
        question_number += 1

# Quit the WebDriver
driver.quit()

# Save the questions data (including question numbers and correct answers) to a JSON file
file_name = 'process_management_correct_answers.json'
with open(file_name, 'w') as json_file:
    json.dump(questions_data, json_file, indent=4)

print(f"Correct answers saved to {file_name}")

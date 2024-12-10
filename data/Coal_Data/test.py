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
topic_url = "https://www.geeksforgeeks.org/quizzes/computer-organization-and-architecture-gq/"

# List to hold correct answers
correct_answers = []

# Loop through the first few pages for the topic
for page in range(1, 2):  # Modify range for more pages if needed
    # Construct the page URL
    url = f"{topic_url}?page={page}"
    
    # Navigate to the page
    driver.get(url)
    
    # Wait for the page to load
    time.sleep(3)  # Adjust the delay if needed based on the network speed
    
    # Find all the question containers
    question_containers = driver.find_elements(By.CLASS_NAME, "QuizQuestionCard_quizCard__9T_0J")
    
    for container in question_containers:
        try:
            # Extract options and click any one of them to trigger the class loading
            options_elements = container.find_elements(By.TAG_NAME, "li")
            
            for opt in options_elements:
                # Click the option to trigger the class
                opt.click()
                
                # Wait for the class to be applied
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "QuizQuestionCard_selectedRow__b_SAP"))
                )
                
                # Check if the class "QuizQuestionCard_selectedRow__b_SAP" is present in the clicked option
                if "QuizQuestionCard_selectedRow__b_SAP" in opt.get_attribute("class"):
                    correct_answers.append(opt.text.strip())  # Store the correct answer
                    break  # Once the correct answer is found, no need to check further options
        
        except Exception as e:
            print(f"Error processing a question: {e}")

# Quit the WebDriver
driver.quit()

# Save the correct answers to a JSON file
file_name = 'correct_answers.json'
with open(file_name, 'w') as json_file:
    json.dump(correct_answers, json_file, indent=4)

print(f"Correct answers saved to {file_name}")

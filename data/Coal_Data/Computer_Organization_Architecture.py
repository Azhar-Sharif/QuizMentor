import requests
from bs4 import BeautifulSoup
import json

# URL for the Computer Organization and Architecture topic
topic_url = "https://www.geeksforgeeks.org/quizzes/computer-organization-and-architecture-gq/"

# List to hold questions for the current topic
topic_questions_data = []

# Loop through the first 2 pages for the topic
for i in range(1, 26): 
    # Construct the page URL
    url = f"{topic_url}?page={i}"

    # Send a GET request to fetch the raw HTML content
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all the main containers for each quiz question
        question_containers = soup.find_all(class_="QuizQuestionCard_quizCard__9T_0J")

        for container in question_containers:
            # Initialize variables for question text, paragraph text, and optional image link
            question_text = "No question text found"
            question_paragraph_text = "No question paragraph found"
            correct_answer = None
            image_link = None
            
            # Locate the inner div that contains the main question text
            main_question_div = container.find('div')
            
            if main_question_div:
                question_paragraph = main_question_div.find('p')
                if question_paragraph:
                    question_text = question_paragraph.get_text(strip=True)

                # Locate the following sibling div for additional paragraph text
                next_div = main_question_div.find_next_sibling('div')
                if next_div:
                    paragraph_element = next_div.find('p')
                    if paragraph_element:
                        question_paragraph_text = paragraph_element.get_text(strip=True)
                    else:
                        question_paragraph_text = next_div.get_text(strip=True)
                    
                    # Check if there is an image following the paragraph
                    image = next_div.find('img')
                    if image and 'src' in image.attrs:
                        image_link = image['src']
            
            # Extract options and identify the correct answer
            options_container = container.find_all('li')
            options = []
            for opt in (options_container):
                option_text = opt.get_text(strip=True)
                options.append(option_text)

            # Append the question data to the list
            topic_questions_data.append({
                "question": question_text,
                "question_paragraph": question_paragraph_text,
                "options": options,
                "image_link": image_link  # Add image link if present
            })
    else:
        print(f"Failed to retrieve page {i} for Computer Organization and Architecture. Status code:", response.status_code)

# Save the questions data for the topic to a JSON file
file_name = 'Computer_Organization_Architecture.json'
with open(file_name, 'w') as json_file:
    json.dump(topic_questions_data, json_file, indent=4)

print(f"Data saved to {file_name}")

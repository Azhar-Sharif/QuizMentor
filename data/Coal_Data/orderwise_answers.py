import json

# File name of the JSON data
file_name = 'Computer_Organization_Architecture_correct_answers.json'

# Load the JSON data
with open(file_name, 'r') as json_file:
    data = json.load(json_file)

# Fix the question numbering
for index, entry in enumerate(data):
    entry['question_number'] = index + 1

# Save the updated data back to the file
with open(file_name, 'w') as json_file:
    json.dump(data, json_file, indent=4)

print(f"Question numbers updated and saved to {file_name}")

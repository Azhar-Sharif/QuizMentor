import json
from chromadb import Client
from chromadb.config import Settings

# Function to map data into ChromaDB
def map_to_chromadb(data, collection):
    for item in data:
        question_id = item.get("question")
        question_paragraph = item.get("question_paragraph")
        
        if question_id and question_paragraph:
            # Insert data into the collection
            collection.add(
                ids=[question_id],
                documents=[question_paragraph]
            )
            print(f"Mapped to ChromaDB: {question_id} - {question_paragraph}")

# Function to create a separate dictionary for options and links
def create_options_links_structure(data):
    options_links = {}
    for item in data:
        question_id = item.get("question")
        if question_id:
            options_links[question_id] = {
                "options": item.get("options", []),
                "image_link": item.get("image_link")
            }
    return options_links

# Main function to handle the process
def main(json_file_path):
    # Initialize ChromaDB client with updated settings
    chroma_client = Client(Settings(
        persist_directory="./chromadb_data",  # Directory to persist data
        chroma_api_impl="chromadb.api.local.LocalAPI"  # Default API implementation
    ))
    
    # Create or get a collection in ChromaDB
    collection_name = "questions"
    collection = chroma_client.get_or_create_collection(collection_name)
    
    # Load data from JSON file
    try:
        with open(json_file_path, "r") as file:
            questions_data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File not found: {json_file_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON: {e}")
        return
    
    # Map questions to ChromaDB
    map_to_chromadb(questions_data, collection)
    
    # Create options and links structure
    options_links_structure = create_options_links_structure(questions_data)
    
    # Print the resulting structure
    print("Options and Links Structure:")
    print(json.dumps(options_links_structure, indent=4))

# Replace with the full path to your JSON file
json_file_path = "c:/Users/M.KHAN/OneDrive/Desktop/FYP/QuizMentor/data/Coal_Data/Computer_Organization_Architecture.json"
main(json_file_path)

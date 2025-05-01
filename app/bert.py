from transformers import BertTokenizer
import tensorflow as tf

# Load the question classification model
questionclassification_model = tf.keras.models.load_model("C:/Users/ik/Downloads/questionclassification_model/questionclassification_model")
tokenizer = BertTokenizer.from_pretrained('bert-base-cased')

def prepare_data(input_text):
    token = tokenizer.batch_encode_plus(
        input_text,
        max_length=256,
        truncation=True,
        padding='max_length',
        add_special_tokens=True,
        return_tensors='tf'
    )
    return {
        'input_ids': tf.cast(token['input_ids'], tf.float64),
        'attention_mask': tf.cast(token['attention_mask'], tf.float64)
    }

def classify_questions(questions, classes=['Easy', 'Medium', 'Hard']):
    """
    Classify the difficulty of a list of questions.
    Each question should be a dictionary with a 'question_text' key.
    """
    input_texts = [q['question_text'] for q in questions]
    processed_data = prepare_data(input_texts)
    probs = questionclassification_model.predict(processed_data)
    predictions = probs.argmax(axis=1)
    for i, question in enumerate(questions):
        question['difficulty'] = classes[predictions[i]]
    return questions

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle

MODEL_PATH = 'weak_topic_model.pkl'
ENCODER_PATH = 'label_encoder.pkl'

def train_model(data):
    """
    Train the weak topic prediction model and save it to disk.
    :param data: DataFrame containing user performance data.
    """
    # Preprocess data
    data['weak_topic'] = data['score'].apply(lambda x: 1 if x < 50 else 0)  # Weak if score < 50
    label_encoder = LabelEncoder()
    data['topic_encoded'] = label_encoder.fit_transform(data['topic'])

    # Train-test split
    X = data[['topic_encoded', 'score']]
    y = data['weak_topic']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train model
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    # Save model and label encoder
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    with open(ENCODER_PATH, 'wb') as f:
        pickle.dump(label_encoder, f)

    print("✅ Model trained and saved successfully!")


def load_model():
    """
    Load the trained model and label encoder from disk.
    :return: Tuple (model, label_encoder)
    """
    try:
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(ENCODER_PATH, 'rb') as f:
            label_encoder = pickle.load(f)
        return model, label_encoder
    except FileNotFoundError:
        raise FileNotFoundError("Model or label encoder not found. Train the model first.")

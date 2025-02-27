import os
import sys

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_connection import SessionLocal

# Load data from database to create a prediction model
def load_match_data():
    query = text("SELECT home_team_id, away_team_id, score_home, score_away FROM matches")
    try:
        with SessionLocal() as session:
            result = session.execute(query).fetchall()
            df = pd.DataFrame(result, columns=['home_team_id', 'away_team_id', 'score_home', 'score_away'])
            return df
    except SQLAlchemyError as e:
        print(f"Error loading match data: {e}")
        return None

# Prepare data for prediction
def prepare_data(df):
    """
    Prepares the data for training and testing.
    - Creates a target variable: 1 if the home team wins, 0 otherwise.
    """
    # Create target variable
    df['target'] = (df['score_home'] > df['score_away']).astype(int)
    X = df[['home_team_id', 'away_team_id']]  # Features
    y = df['target']  # Target variable
    return train_test_split(X, y, test_size=0.2, random_state=42)

# Train and evaluate a simple prediction model
def train_and_evaluate_model(X_train, X_test, y_train, y_test):
    """
    Trains a logistic regression model and evaluates its accuracy.
    """
    model = LogisticRegression()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy}")

if __name__ == "__main__":
    df = load_match_data()
    if df is not None and not df.empty:
        X_train, X_test, y_train, y_test = prepare_data(df)
        train_and_evaluate_model(X_train, X_test, y_train, y_test)

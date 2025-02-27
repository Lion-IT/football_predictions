import sys
import os
import json

from dotenv import load_dotenv

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_error, log_warning
from utils.notification_utils import send_batch_notifications
from utils.predictions_utils import fetch_predictions_for_match

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Set up logging
logger = setup_logger("etl_prediction_match")

def run():
    # Step 1: Fetch and process predictions
    try:
        match_ID = int(input("Enter the Match ID: "))
        fetch_predictions_for_match(match_ID)
    except Exception as e:
        log_error(logger, f"Error during fetch_and_insert_future_matches_hset: {e}")
        raise

    # Step 2: Send email notifications
    try:
        send_batch_notifications()
    except Exception as e:
        log_error(logger, f"Error while sending notifications: {e}")

if __name__ == "__main__":
    run()
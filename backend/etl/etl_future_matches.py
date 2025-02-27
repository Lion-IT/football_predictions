import sys
import os
import json

from dotenv import load_dotenv

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_info, log_error, log_warning
from utils.notification_utils import send_batch_notifications
from utils.progress_utils import create_progress_bar
from utils.predictions_utils import fetch_predictions_for_match
from utils.future_utils import fetch_and_insert_future_matches_hset

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Set up logging
logger = setup_logger("etl_future_matches")

def run():
    """
    Main entry point for the script.
    Combines all required steps in a single function for integration with the ETL pipeline.
    """
    # Step 1: Load json leagues ids from config
    try:
        # Load and validate predefined leagues
        leagues_json = os.getenv("LEAGUES", "{}")
        predefined_leagues = json.loads(leagues_json)
        if not predefined_leagues:
            log_error(logger, "LEAGUES is empty or invalid.")
            raise ValueError("LEAGUES environment variable is empty or contains invalid JSON.")
    except json.JSONDecodeError as e:
        log_error(logger, f"Failed to parse LEAGUES from environment variable: {e}")
        raise ValueError(f"Invalid JSON in LEAGUES: {e}")

    # Log loaded league IDs
    league_ids = list(predefined_leagues.values())
    if not league_ids:
        log_error(logger, "No league IDs found in LEAGUES. Exiting.")
        return  # Exit the script if no leagues are defined

    # Step 2: Fetch and process future matches
    try:
        unique_matches = fetch_and_insert_future_matches_hset(league_ids)
        progress_bar_matches = create_progress_bar(total=len(unique_matches), desc="Sprawdzanie predykcji...", unit="match")
        for match in unique_matches:
            try:
                fetch_predictions_for_match(match['match_id'], progress_bar_matches)
            except Exception as e:
                log_error(logger, f"Error fetching predictions for match ID {match['match_id']}: {e}")

		# Close progress bar
        progress_bar_matches.close()

    except Exception as e:
        log_error(logger, f"Error during fetch_and_insert_future_matches_hset: {e}")
        raise

    # Step 3: Send email notifications
    try:
        send_batch_notifications()
    except Exception as e:
        log_error(logger, f"Error while sending notifications: {e}")

if __name__ == "__main__":
    run()
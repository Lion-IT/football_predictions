import sys
import os
import json

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timezone
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from config.db_connection import SessionLocal, get_redis_connection
from utils.logging_utils import setup_logger, log_error, log_info
from utils.validation_utils import parse_date_to_local

# Initialize redis
redis_client = get_redis_connection()

# Setup logger
logger = setup_logger("clear_future_match")

def is_match_outdated_or_in_progress(match_date: str, match_status: str) -> bool:
    """
    Check if a match is outdated or in progress based on date and status.
    Args:
        match_date (str): Date of the match.
        match_status (str): Status of the match.
    Returns:
        bool: True if the match is outdated or in progress, False otherwise.
    """
    try:
        match_date_obj = parse_date_to_local(match_date)
        if match_date_obj < datetime.now(timezone.utc) or match_status.upper() in ["FT", "1H", "2H"]:
            return True
    except Exception as e:
        log_error(logger, f"Error parsing match date {match_date}: {e}")
        return False

def clear_redis_keys(key_pattern: str, date_field: str):
    """
    Clears outdated keys from Redis based on the key pattern and date field.
    Args:
        key_pattern (str): The Redis key pattern to match (e.g., "future_match:*").
        date_field (str): The JSON field containing the match date (e.g., "fixture.date").
    """
    try:
        keys = redis_client.keys(key_pattern)
        total_keys = len(keys)
        deleted_keys = 0

        for key in keys:
            match_data_str = redis_client.get(key)
            if match_data_str:
                try:
                    match_data = json.loads(match_data_str)
                    fields = date_field.split('.')
                    match_date = match_data
                    for field in fields:
                        if isinstance(match_date, dict):
                            match_date = match_date.get(field, None)
                        else:
                            log_error(logger, f"Unexpected data structure for key {key}: {match_data}")
                            match_date = None
                            break

                    match_status = match_data.get("fixture", {}).get("status", {}).get("short", "")

                    if match_date and is_match_outdated_or_in_progress(match_date, match_status):
                        redis_client.delete(key)
                        deleted_keys += 1
                        log_info(logger, f"Deleted outdated or in-progress match key: {key}")
                except (ValueError, json.JSONDecodeError) as e:
                    log_error(logger, f"Invalid JSON or date format for key {key}: {e}")

        log_info(logger, f"Checked {total_keys} keys. Deleted {deleted_keys} outdated or in-progress match keys.")
    except Exception as e:
        log_error(logger, f"Error clearing keys with pattern {key_pattern}: {e}")

def clear_unmatched_predictions_h2h():
    """Usuwa klucze predictions_h2h:* z Redis, które nie mają odpowiadającego klucza w predictions:*."""

    try:
        h2h_keys = redis_client.keys("predictions_h2h:*")
        total_keys = len(h2h_keys)
        deleted_keys = 0
        for key in h2h_keys:
            match_id = key.split(":")[1]  # Pobieramy ID meczu
            predictions_key = f"predictions:{match_id}"

            if not redis_client.exists(predictions_key):
                redis_client.delete(key)
                deleted_keys += 1
                log_info(logger, f"Deleted unmatched predictions_h2h key: {key}")

        log_info(logger, f"Checked {total_keys} predictions_h2h keys. Deleted {deleted_keys} unmatched keys.")
    except Exception as e:
        log_error(logger, f"Error clearing unmatched predictions_h2h keys: {e}")

def clear_future_matches():
    """Clears outdated `future_matches` data from Redis and the database."""
    # Clear outdated matches in Redis
    clear_redis_keys("future_match:*", "fixture.date")
    clear_redis_keys("future_match_db:*", "match_date")
    clear_redis_keys("predictions:*", "match_date")

    # Clear outdated matches in the database
    del_future_matches = text("DELETE FROM future_matches WHERE match_date < NOW() OR status IN ('1H', '2H', 'FT', 'PST', 'PEW');")
    del_predictions = text("DELETE FROM predictions WHERE NOT EXISTS (SELECT 1 FROM future_matches WHERE future_matches.match_id = predictions.fixture_id);")
    try:
        with SessionLocal() as session:
            delete1 = session.execute(del_future_matches)
            delete2 = session.execute(del_predictions)
            session.commit()
             # Log results
            log_info(logger, f"Successfully cleared {delete1.rowcount} outdated and in-progress matches from `future_matches` table.")
            log_info(logger, f"Successfully cleared {delete2.rowcount} predictions without matching future matches.")
    except SQLAlchemyError as e:
        log_error(logger, f"Error clearing table `future_matches`: {e}")

def run():
    """
    Entry point function for the script.
    This function is used to integrate with the main ETL pipeline.
    """
    clear_future_matches()
    clear_unmatched_predictions_h2h()

if __name__ == "__main__":
    run()

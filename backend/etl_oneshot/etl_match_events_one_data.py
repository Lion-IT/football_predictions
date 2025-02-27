import sys
import os

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_error
from utils.match_events_utils import run_all_proccess_event_match_with_progress_bar

# Set up logger for match events ETL
logger = setup_logger("etl_match_events_one")

def run():
    try:
        match_id = int(input("Enter the Match ID: "))
        run_all_proccess_event_match_with_progress_bar(match_id)
    except ValueError:
        log_error(logger, "Invalid input. Please provide a numeric value for Match ID.")

if __name__ == "__main__":
    run()

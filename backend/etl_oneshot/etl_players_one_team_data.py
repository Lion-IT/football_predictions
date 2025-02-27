import sys
import os

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_error
from utils.players_utils import fetch_and_insert_players

# Set up logger for player ETL
logger = setup_logger("etl_players_data")

def run():
    try:
        team_id = int(input("Enter the Team ID: "))
        season = int(input("Enter the season (e.g., 2024): "))
        fetch_and_insert_players(team_id, season)
    except ValueError:
        log_error(logger, "Invalid input. Please provide numeric values for Team ID and Season.")

if __name__ == "__main__":
    run()
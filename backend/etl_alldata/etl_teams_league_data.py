import sys
import os

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_error
from utils.teams_utils import fetch_and_insert_teams
from utils.players_utils import fetch_and_insert_players

# Set up the logger
logger = setup_logger("etl_teams_data")

def run():
    try:
        league_id = int(input("Enter the league ID: "))
        season = int(input("Enter the season (e.g., 2024): "))
        teams = fetch_and_insert_teams(league_id, season)
        # Przetwarzaj zawodników dla każdej drużyny
        for team in teams:
            fetch_and_insert_players(team, season)

    except ValueError:
        log_error(logger, "Invalid input. Please provide numeric values for league ID and season.")
    except Exception as e:
        log_error(logger, f"Nieoczekiwany błąd w run: {e}")

if __name__ == "__main__":
    run()
import sys
import os

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_error
from utils.teams_standing import fetch_team_standing, insert_team_standing_to_db
from maintenance.clear_teams_standing_redis import clear_team_standing_from_redis

# Set up the logger
logger = setup_logger("etl_teams_one_data_standing")

def run():
    try:
        team_id = int(input("Enter the Team ID: "))
        season = int(input("Enter the season (e.g., 2024): "))
        clear_team_standing_from_redis(team_id, season)
        team = fetch_team_standing(team_id, season)
        insert_team_standing_to_db(team)
        print(f"Dodano do bazy statsy drużyny {team_id} za sezon {season}")
    except ValueError:
        log_error(logger, "Invalid input. Please provide numeric values for league ID and season.")
    except Exception as e:
        log_error(logger, f"Nieoczekiwany błąd w run: {e}")

if __name__ == "__main__":
    run()
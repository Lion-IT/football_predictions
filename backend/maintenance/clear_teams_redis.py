import sys
import os

# Add the project root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_connection import get_redis_connection
from utils.logging_utils import setup_logger, log_error, log_info

# Initialize redis
redis_client = get_redis_connection()

# Setup logger
logger = setup_logger("clear_teams_redis")

def clear_team_from_redis(team_id, season):
    """ Usuwa klucze team_full_data:{team_id}:{season} z Redis przed aktualizacją. """
    try:
        team_key = redis_client.keys(f"team_full_data:{team_id}:{season}")  # Pobieramy pasujące klucze
        if team_key:  # Jeśli są jakieś klucze do usunięcia
            redis_client.delete(*team_key)  # Usuwamy wszystkie znalezione klucze
            log_info(logger, f"Deleted team data from Redis: {team_key}")
        else:
            log_info(logger, f"No keys found for team {team_id} in season {season}")
    except Exception as e:
        log_error(logger, f"Error clearing team data from Redis: {e}")

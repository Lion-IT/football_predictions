import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_info, log_warning
from utils.teams_utils import fetch_and_insert_teams
from utils.players_utils import fetch_and_insert_players
from utils.special_football_functions import get_current_season

# Set up the logger
logger = setup_logger("etl_teams_all_data")

def run():
    leagues = json.loads(os.getenv("LEAGUES", "{}"))  # Pobierz ligę jako słownik z pliku .env
	# Iteracja przez każdą ligę w słowniku LEAGUES
    for league_name, league_id in leagues.items():
        season = get_current_season(league_id)
        teams = fetch_and_insert_teams(league_id=int(league_id), season=season)
        if not teams:
            season_down = season - 1
            log_warning(logger, f"Nie znaleziono druzyn dla ligi: {league_name} (ID: {league_id}) i sezonu {season}")
            log_warning(logger, f"Szukam danych dla : {league_name} (ID: {league_id}) i sezonu {season_down}")
            teams_research = fetch_and_insert_teams(league_id=int(league_id), season=season_down)
            if not teams_research:
                log_warning(logger, f"Nie znaleziono druzyn dla ligi: {league_name} (ID: {league_id}) i sezonu {season_down}")
                log_warning(logger, f"Skipping for this team")
            continue

        # Pobieranie zawodnikow dla wszystkich druzyn podanych w parametrze
        for team in teams:
            players = fetch_and_insert_players(team, season)
            if not players:
                season_down = season - 1
                fetch_and_insert_players(team, season_down)

if __name__ == "__main__":
    run()
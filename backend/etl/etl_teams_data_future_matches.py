import sys
import os
import concurrent.futures
import threading

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_error
from utils.teams_utils import fetch_and_insert_team, get_latest_team_season
from utils.players_utils import fetch_and_insert_players
from utils.future_utils import fetch_future_away_team, fetch_future_home_team
from maintenance.clear_teams_redis import clear_team_from_redis

# Set up the logger
logger = setup_logger("etl_teams_data_future_matches")

# Globalny lock do aktualizacji paska postępu
progress_lock = threading.Lock()


def process_team(team_id, progress_bar):
    """Pobiera i zapisuje dane dla jednej drużyny."""
    try:
        season = get_latest_team_season(team_id)
        clear_team_from_redis(team_id, season)
        fetch_and_insert_team(team_id, season)
        fetch_and_insert_players(team_id, season)
    except Exception as e:
        log_error(logger, f"Błąd podczas przetwarzania team_id={team_id}: {e}")
    finally:
        with progress_lock:
            progress_bar.update(1)

def run():
    try:
        home_teams = fetch_future_home_team()
        away_teams = fetch_future_away_team()
        all_teams = home_teams + away_teams

        # Przetwarzaj zawodników dla każdej drużyny
        progress_bar = create_progress_bar(len(all_teams), desc="Odświeżanie danych drużyn...", unit=" teams")
        num_teams = len(all_teams)
        max_workers = min(10, num_teams // 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for team_id in all_teams:
                try:
                    future = executor.submit(process_team, team_id, progress_bar)
                    futures.append(future)
                except Exception as e:
                    log_error(logger, f"Błąd przy tworzeniu wątku dla Team ID {team_id}: {e}")
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()  # Sprawdza czy nie było błędu w wątku
                except Exception as e:
                    log_error(logger, f"Błąd w jednym z wątków: {e}")

    except Exception as e:
        log_error(logger, f"❌ Nieoczekiwany błąd w run(): {e}")
    finally:
        progress_bar.close()

if __name__ == "__main__":
    run()
import sys
import os
import concurrent.futures
import threading

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_error, log_warning
from utils.teams_standing import fetch_team_standing, insert_team_standing_to_db
from utils.teams_utils import get_all_teams_from_db, get_latest_team_season

# Set up the logger
logger = setup_logger("etl_teams_all_standing")

# Globalny lock do aktualizacji paska postępu
progress_lock = threading.Lock()

def process_team(team_id, progress_bar):
    """Pobiera i zapisuje dane dla jednej drużyny."""
    try:
        season = get_latest_team_season(team_id)
        data_standing = fetch_team_standing(team_id, season)
        if data_standing:
            insert_team_standing_to_db(data_standing)
        else:
            log_warning(logger, f"Brak danych dla Team ID {team_id}, sezon {season}")
    except Exception as e:
        log_error(logger, f"Błąd podczas przetwarzania team_id={team_id}: {e}")
    finally:
        with progress_lock:
            progress_bar.update(1)

def run():
    try:
        all_teams = get_all_teams_from_db()
        progress_bar = create_progress_bar(len(all_teams), desc="Processing Teams", unit=" teams")

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

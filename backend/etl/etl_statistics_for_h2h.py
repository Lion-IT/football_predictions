import sys
import os
import threading

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_warning, log_info, log_error
from utils.match_statistics_utils import fetch_match_statistics, parse_match_statistics, insert_match_statistics_to_db
from utils.match_utils import insert_matches_to_db, match_id_exists, fetch_match_from_id, get_unique_fixture_ids_for_future_matches
from utils.future_utils import fetch_future_home_team, fetch_future_away_team

# Ustawienie logowania
logger = setup_logger("etl_statistics_for_h2h")

# Blokada dla synchronizacji wielowątkowej aktualizacji paska postępu
lock = threading.Lock()

# Funkcja do pobrania brakujących meczów z API
def fetch_and_insert_missing_matches(missing_fixture_ids):
    """Pobiera i zapisuje brakujące mecze z API"""
    if not missing_fixture_ids:
        return

    with create_progress_bar(len(missing_fixture_ids), "Fetching Missing Matches", "matches") as pbar:
        missing_matches = fetch_match_from_id(missing_fixture_ids)
        if missing_matches:
            insert_matches_to_db(missing_matches)
        pbar.update(len(missing_fixture_ids))

# Funkcja przetwarzająca statystyki meczu
def process_fixture_statistics(fixture_id):
    """Przetwarza statystyki dla meczu"""
    if not match_id_exists(fixture_id):
        log_warning(logger, f"Match ID {fixture_id} does not exist in matches table. Skipping.")
    else:
        statistics = fetch_match_statistics(fixture_id)
        if statistics:
            parsed_statistics = parse_match_statistics(fixture_id, statistics)
            insert_match_statistics_to_db(parsed_statistics)

# Funkcja do przetwarzania meczu i aktualizacji paska postępu
def process_and_update(fixture_id, pbar):
    """Procesuje statystyki meczu i aktualizuje pasek postępu w sposób bezpieczny dla wątków."""
    try:
        process_fixture_statistics(fixture_id)
    except Exception as e:
        log_error(logger, f"Error processing match {fixture_id}: {e}")
    finally:
        with lock:  # Aktualizacja paska postępu w sposób bezpieczny dla wątków
            pbar.update(1)

# Główna funkcja ETL
def run():
    while True:
        home_teams = fetch_future_home_team()
        away_teams = fetch_future_away_team()
        fixture_ids = []

        for i in range(len(home_teams)):  # Iterujemy przez listę przyszłych meczów
            home_id = home_teams[i]
            away_id = away_teams[i]

            if not home_teams or not away_teams:
                log_error(logger, "Home or Away teams list is empty. Skipping.")
                return

            # Pobranie unikalnych fixture_ids tylko dla tych drużyn
            fixture_ids.extend(get_unique_fixture_ids_for_future_matches(home_id, away_id))
        missing_fixture_ids = []

        total_fixtures = len(fixture_ids)
        if total_fixtures == 0:
            log_info(logger, "No matches to process.")
            break

        with create_progress_bar(total_fixtures, "Procesowanie statystyk dla H2H...", " matches") as pbar:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(process_and_update, fixture_id, pbar): fixture_id for fixture_id in fixture_ids}

                for future in as_completed(futures):
                    fixture_id = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        log_error(logger, f"Error processing match {fixture_id}: {e}")

        if not missing_fixture_ids:
            log_info(logger, "Wszystkie statystyki przeprocesowane.")
            break
        else:
            log_info(logger, f"Found {len(missing_fixture_ids)} missing matches. Fetching and inserting them into the database.")
            fetch_and_insert_missing_matches(missing_fixture_ids)
            log_info(logger, "Retrying to process all matches...")

# Uruchomienie programu
if __name__ == "__main__":
    run()

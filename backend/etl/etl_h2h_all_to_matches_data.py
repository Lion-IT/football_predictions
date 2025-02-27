import os
import sys

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_info, log_warning
from utils.notification_utils import send_batch_notifications
from utils.match_utils import get_unique_fixture_ids, fetch_match_from_id, insert_matches_to_db
from utils.h2h_utils import filter_new_matches

# Initialize logger
logger = setup_logger("etl_h2h_to_matches")

def run():
    # Pobierz wszystkie dostępne mecze z H2H
    h2h_matches = get_unique_fixture_ids()
    if not h2h_matches:
        log_warning(logger, "Brak dostępnych meczów w tabeli H2H Matches")
        print("Brak dostępnych meczów w tabeli H2H Matches, system is down!")
        return

    # Używamy wielowątkowego sprawdzania meczów
    new_matches = filter_new_matches(h2h_matches, max_workers=8)

    if not new_matches:
        log_info(logger, "Wszystkie mecze z tabeli H2H są już w bazie. Brak nowych meczów do przetworzenia.")
        print("Wszystkie mecze z tabeli H2H są już w bazie, kończę przetwarzanie.")
        return

    fetched_matches = fetch_match_from_id(new_matches)
    insert_matches_to_db(fetched_matches)

    # Send email notifications
    send_batch_notifications()

if __name__ == "__main__":
    run()
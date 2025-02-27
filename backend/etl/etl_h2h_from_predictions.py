import sys
import os
import json

from dotenv import load_dotenv

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_error, log_warning, log_info
from utils.notification_utils import send_batch_notifications
from utils.h2h_utils import store_h2h_matches
from utils.predictions_utils import fetch_predictions_matches, fetch_h2h_from_predictions

# Set up logging
logger = setup_logger("etl_h2h_from_predictions")

def run():
    # Step 1: Pobierz wszystkie dostępne mecze z tabeli predictions
    predictions_matches = fetch_predictions_matches()
    if not predictions_matches:
        log_warning(logger, "Brak dostępnych meczów. Spróbuj pobrać nowe mecze na dany dzień! [etl_future_matches]")
        return

    fetch_h2h = fetch_h2h_from_predictions(predictions_matches)
    if not fetch_h2h:
        log_warning(logger, "Brak danych o h2h")
        return

    # Step 2: Przetwarzanie danych H2H
    try:
        store_h2h_matches(fetch_h2h)
        log_info(logger, "✅ Dane H2H zostały zapisane do bazy.")
    except Exception as e:
        log_error(logger, f"❌ Błąd podczas zapisu danych H2H: {e}")

    # Step 3: Send email notifications
    try:
        send_batch_notifications()
    except Exception as e:
        log_error(logger, f"Error while sending notifications: {e}")

if __name__ == "__main__":
    run()
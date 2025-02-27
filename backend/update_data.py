import sys
import os
import time
import importlib

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_info, log_error
from utils.progress_utils import create_progress_bar

# Set up logging
logger = setup_logger("main")

# Lista skryptów do uruchomienia
etl_scripts = [
    "maintenance.clear_future_matches",
    "maintenance.reset_api_request_counter",
    "etl.etl_future_matches",
    "etl_alldata.etl_matches_all_data",
    "etl.etl_h2h_from_predictions",
    "etl.etl_h2h_all_to_matches_data",
    "etl.etl_statistics_for_h2h",
    "etl.etl_statistics_for_matches",
    "etl.etl_teams_data_future_matches",
    "etl.etl_teams_standing_future_matches"
]

def run_etl_with_delay(script_list, delay=5):
    """
    Run a list of ETL scripts with a delay between each and show a progress bar.
    """
    # Tworzenie paska postępu
    progress_bar = create_progress_bar(total=len(script_list), desc="Running ETL scripts", unit="script")

    for script_name in script_list:
        try:
            log_info(logger, f"Uruchamianie skryptu: {script_name}")
            module = importlib.import_module(script_name)
            module.run()  # Funkcja 'run()' w każdym skrypcie musi być zaimplementowana
            log_info(logger, f"Zakończono: {script_name}")
        except Exception as e:
            log_error(logger, f"Błąd podczas uruchamiania {script_name}: {e}")
        time.sleep(delay)
        progress_bar.update(1)  # Zaktualizowanie paska postępu

    progress_bar.close()  # Zamknięcie paska postępu po zakończeniu

if __name__ == "__main__":
    log_info(logger, "Rozpoczynanie procesu pobierania danych!")
    run_etl_with_delay(etl_scripts, delay=5)
    log_info(logger, "Proces zakończony")

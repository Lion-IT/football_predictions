import sys
import os
import time
import importlib

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_info, log_error
from utils.progress_utils import create_progress_bar

# Set up logging
logger = setup_logger("deploy_html")

# Lista skryptów do uruchomienia
scripts = [
    "generators.all_html_generate",
    "deploy.deploy_all_ftp"
]

def run_scripts_with_progress(script_list, delay=5):
    """ Run a list of ETL scripts, each with its own progress bar. """

    for script_name in script_list:
        progress_bar = create_progress_bar(total=100, desc=f"🔄 Uruchamianie {script_name}", unit="%")
        try:
            log_info(logger, f"Uruchamianie skryptu: {script_name}")
            module = importlib.import_module(script_name)
            for i in range(10):
                time.sleep(delay / 10)
                progress_bar.update(10)
            module.run()
            log_info(logger, f"✅ Zakończono: {script_name}")
        except Exception as e:
            log_error(logger, f"❌ Błąd podczas uruchamiania {script_name}: {e}")
        finally:
            progress_bar.close()

if __name__ == "__main__":
    print("🚀 Rozpoczynanie procesu generowania HTML i DEPLOY na serwer!\n")
    run_scripts_with_progress(scripts, delay=5)
    print("🏁 Proces zakończony")

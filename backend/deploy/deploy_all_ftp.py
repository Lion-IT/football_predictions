import os
import sys

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from utils.logging_utils import setup_logger, log_error, log_info
from utils.ftp_utils import open_ftp_connection, upload_directory, clean_ftp_folder, close_ftp_connection

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Set up logging
logger = setup_logger("deploy_all_ftp")

# FTP connection details
ftp_host = os.getenv("FTP_HOST", "localhost")
ftp_user = os.getenv("FTP_USER", '')
ftp_pass = os.getenv("FTP_PASSWORD", '')
remote_base_path = os.getenv("REMOTE_PATH", '')
local_base_path = os.path.abspath(os.path.join('Football/frontend/public'))

def run():
    try:
        ftp = open_ftp_connection(ftp_host, ftp_user, ftp_pass)
        if ftp:
            # clean_ftp_folder(ftp, remote_base_path)
            upload_directory(ftp, local_base_path, remote_base_path)
            close_ftp_connection(ftp)
        else:
            print("Nie udało się nawiązać połączenia z FTP.")
    except ValueError:
        log_error(logger, "BŁĄD. Sprawdź pliki logów.")

# if __name__ == "__main__":
#     if "deploy.deploy_all_ftp" not in sys.modules:
#         run()
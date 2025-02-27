from ftplib import FTP
import sys
import os

from dotenv import load_dotenv

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add the necessary directories to the Python path
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# FTP connection details
ftp_host=os.getenv("FTP_HOST", "localhost")
ftp_port=int(os.getenv("FTP_PORT", 21))
ftp_user=os.getenv("FTP_USER", '')
ftp_password=os.getenv("FTP_PASSWORD", '')
remote_path=f"{os.getenv('REMOTE_PATH', 'public_html')}/match_predictions.html"
# Ścieżka do pliku
local_file_path = os.path.abspath(os.path.join('frontend/public/match_predictions.html'))

# Upload the file via FTP
def run():
    ftp = FTP()
    ftp.connect(ftp_host, ftp_port)
    ftp.login(ftp_user, ftp_password)
    with open(local_file_path, 'rb') as file:
        ftp.storbinary(f"STOR {remote_path}", file)
    ftp.quit()
    print("File uploaded successfully.")

if __name__ == "__main__":
    run()
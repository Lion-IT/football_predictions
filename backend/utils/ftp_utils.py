import os
import sys
import ftplib

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ftplib import FTP, error_perm
from utils.logging_utils import setup_logger, log_info, log_error

# Set up logging
logger = setup_logger("ftp_utils")

def open_ftp_connection(ftp_host, ftp_user, ftp_pass):
    """
    Nawiązuje połączenie z serwerem FTP i zwraca obiekt FTP.
    """
    try:
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_pass)
        return ftp
    except Exception as e:
        print(f"Błąd podczas łączenia z serwerem FTP: {e}")
        return None

def clean_ftp_folder(ftp, folder_path):
    """
    Usuwa wszystkie pliki i podfoldery z danego folderu na serwerze FTP, ale nie usuwa samego folderu.
    """
    try:
        ftp.cwd(folder_path)
        items = ftp.nlst()
        for item in items:
            if item in [".", ".."]:
                continue
            try:
                ftp.delete(item)
            except Exception as e:
                try:
                    ftp.rmd(item)
                except Exception as inner_e:
                    print(f"Błąd podczas usuwania folderu: {inner_e}")
        ftp.cwd("..")
    except Exception as e:
        print(f"Błąd podczas czyszczenia folderu {folder_path}: {e}")

def ensure_remote_directory(ftp, remote_path):
    """ Tworzy katalogi na serwerze FTP, jeśli ich nie ma """

    path_parts = remote_path.strip("/").split("/")
    current_path = ""
    for part in path_parts:
        if part:
            current_path = f"{current_path}/{part}".replace("//", "/")
            try:
                ftp.cwd(current_path)
            except ftplib.error_perm:
                print(f"⚠️ Katalog nie istnieje. Tworzę: {current_path}")
                ftp.mkd(current_path)
                ftp.cwd(current_path)

def upload_directory(ftp, local_dir, remote_dir):
    """ Przesyłanie katalogów i ich zawartości na serwer FTP. """

    ensure_remote_directory(ftp, remote_dir)  # Najpierw upewniamy się, że katalog docelowy istnieje
    for root, dirs, files in os.walk(local_dir):
        relative_path = os.path.relpath(root, local_dir).replace("\\", "/")
        remote_path = relative_path if remote_dir == "." else f"{remote_dir}/{relative_path}"
        remote_path = remote_path.replace("//", "/").replace("./", "")
        ensure_remote_directory(ftp, remote_path)  # Tworzymy katalog na serwerze, jeśli nie istnieje
        for file in files:
            local_file_path = os.path.join(root, file)
            remote_file_path = f"{remote_path}/{file}".replace("//", "/").replace("./", "")
            with open(local_file_path, "rb") as file_obj:
                ftp.storbinary(f"STOR {remote_file_path}", file_obj)

def upload_files_to_ftp(ftp, local_folder, remote_folder):
    """
    Upload all files from a local folder to a remote FTP folder.
    """
    try:
        for root, _, files in os.walk(local_folder):
            for file_name in files:
                local_file_path = os.path.join(root, file_name)
                remote_file_path = f"{remote_folder}/{file_name}"
                with open(local_file_path, 'rb') as file:
                    ftp.storbinary(f"STOR {remote_file_path}", file)

        print("All files uploaded successfully.")
    except Exception as e:
        log_error(logger, f"During FTP upload: {e}")

def close_ftp_connection(ftp):
    """
    Zamyka połączenie z serwerem FTP, jeśli jest aktywne.
    :param ftp: Obiekt połączenia FTP.
    """
    try:
        if ftp:
            try:
                ftp.voidcmd("NOOP")
                ftp.quit()
            except Exception:
                print("Połączenie z serwerem FTP już nie jest aktywne.")
        else:
            print("Obiekt FTP jest pusty, połączenie nie zostało nawiązane.")
    except Exception as e:
        print(f"Błąd podczas zamykania połączenia z FTP: {e}")
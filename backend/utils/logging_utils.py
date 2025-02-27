import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from logging.handlers import MemoryHandler

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Pobranie poziomu logowania z ENV (domyślnie WARNING)
log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
log_level_numeric = getattr(logging, log_level, logging.INFO)

# Ensure the logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

class DelayedFileHandler(logging.Handler):
    """
    Niestandardowy handler, który tworzy plik logów dopiero przy pierwszym zapisie.
    """
    def __init__(self, filename, level=logging.NOTSET):
        super().__init__(level)
        self.filename = filename
        self.file_handler = None  # Handler plikowy nie jest tworzony od razu

    def emit(self, record):
        if not self.file_handler:
            # Twórz FileHandler dopiero przy pierwszym logu
            self.file_handler = logging.FileHandler(self.filename)
            self.file_handler.setFormatter(self.formatter)  # Użyj tego samego formattera
            self.file_handler.setLevel(self.level)

        # Emituj log za pomocą FileHandler
        self.file_handler.emit(record)

def setup_logger(script_name):
    """
    Tworzy logger z niestandardowym handlerem, który tworzy plik logów dopiero przy pierwszym zapisie.
    :param script_name: Nazwa skryptu (bez rozszerzenia).
    :return: Obiekt loggera.
    """
    # Utwórz nazwę pliku logów
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filepath = os.path.join(LOGS_DIR, f"{script_name}_{timestamp}.log")

    # Stwórz logger
    logger = logging.getLogger(script_name)
    logger.setLevel(log_level_numeric)

    # Unikaj dodawania wielu handlerów do tego samego loggera
    if not logger.handlers:
        # Utwórz niestandardowy handler DelayedFileHandler
        delayed_file_handler = DelayedFileHandler(log_filepath, level=log_level_numeric)
        formatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
        delayed_file_handler.setFormatter(formatter)
        # Dodaj handler do loggera
        logger.addHandler(delayed_file_handler)

    return logger


def log_debug(logger, message):
    logger.debug(message)

def log_info(logger, message):
    logger.info(message)

def log_warning(logger, message):
    logger.warning(message)

def log_error(logger, message):
    logger.error(message)

def log_critical(logger, message):
    logger.critical(message)
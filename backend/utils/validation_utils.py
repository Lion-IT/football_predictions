import sys
import os
import pytz

from dateutil import parser
from datetime import datetime

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.sql import text
from config.db_connection import SessionLocal
from utils.logging_utils import log_error, setup_logger

# Setup logger for validation
logger = setup_logger("validation")

# Funkcja do przetwarzania dat na offset-aware
def parse_date_to_local(date_str: str) -> datetime:
    """
    Parses a date string to an offset-aware datetime object in UTC.
    Args: date_str (str): The date string to parse.
    Returns: datetime: A datetime object with timezone information set to UTC.
    """
    parsed_date = parser.isoparse(date_str)  # Obsługuje offset-aware i offset-naive daty
    if parsed_date.tzinfo is None:
        parsed_date = parsed_date.replace(tzinfo=pytz.utc)  # Ustaw UTC, jeśli brak informacji o strefie czasowej

    target_timezone = pytz.timezone("Europe/Warsaw")
    return parsed_date.astimezone(target_timezone)

def is_table_empty(table_name: str) -> bool:
    """
    Check if a given table is empty.
    Args: table_name (str): Name of the table to check.
    Returns: bool: True if the table is empty, False otherwise.
    """
    query = text(f"SELECT COUNT(*) FROM {table_name};")
    session = SessionLocal()

    try:
        result = session.execute(query).fetchone()
        if result and result[0] is not None:  # Używamy indeksu 0 zamiast klucza 'count'
            return result[0] == 0
    except Exception as e:
        log_error(logger, f"Error checking if table {table_name} is empty: {e}")
        return False
    finally:
        session.close()

# def run():
#     try:
#         table_check = input("Enter table name to check is EMPTY: ")
#         teams = is_table_empty(table_check)
#         print(teams)
#     except ValueError:
#         log_error(logger, "Invalid input. Please provide numeric values for league ID and season.")
#     except Exception as e:
#         log_error(logger, f"Nieoczekiwany błąd w run: {e}")

# if __name__ == "__main__":
#     run()
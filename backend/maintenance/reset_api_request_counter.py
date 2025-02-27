import sys
import os
import pytz

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timezone, time
from config.db_connection import get_redis_connection
from utils.logging_utils import setup_logger, log_info, log_error
from utils.validation_utils import parse_date_to_local

# Initialize redis
redis_client = get_redis_connection()

# Setup logger
logger = setup_logger("reset_counter")

def reset_daily_counter(redis_client, daily_key):
    """
    Resetuje dzienny licznik żądań API i ustawia jego TTL do północy.
    """
    try:
        # Resetowanie klucza
        redis_client.set(daily_key, 0)
        now_utc = datetime.now(timezone.utc)
        now_local = parse_date_to_local(now_utc.isoformat())
        end_of_day_local = datetime.combine(now_local.date(), time(23, 59, 59))
        end_of_day_utc = end_of_day_local.astimezone(pytz.utc)
        ttl = int((end_of_day_utc - now_utc).total_seconds())
        redis_client.expire(daily_key, ttl)
        log_info(logger, f"Zresetowano dzienny licznik żądań API o {now_local}.")
        log_info(logger, f"Ustawiono TTL dla {daily_key} na {ttl} sekund (do {end_of_day_local.isoformat()} lokalnego czasu).")
    except Exception as e:
        log_error(logger, f"Błąd przy resetowaniu dziennego licznika: {e}")

def reset_or_validate_daily_counter():
    """
    Validate or reset the daily API request counter in Redis.
    If the counter does not exist or has no TTL, reset it.
    """
    daily_key = "api_requests_daily"

    try:
        ttl = redis_client.ttl(daily_key)

        if ttl == -2:  # Key does not exist
            log_info(logger, f"Key {daily_key} does not exist. Resetting daily counter.")
            reset_daily_counter(redis_client, daily_key)

        elif ttl == -1:  # Key exists but has no TTL
            log_info(logger, f"TTL for {daily_key} is missing. Resetting daily counter.")
            reset_daily_counter(redis_client, daily_key)

        elif ttl > 0:  # Key exists and TTL is valid
            log_info(logger, f"Key {daily_key} exists with valid TTL: {ttl} seconds. No reset needed.")
        else:
            log_error(logger, f"Unexpected TTL value ({ttl}) for key {daily_key}. Investigating further.")

    except Exception as e:
        log_error(logger, f"Error validating/resetting daily counter: {e}")

def run():
    """
    Entry point function for the script.
    This function is used to integrate with the main ETL pipeline.
    """
    reset_or_validate_daily_counter()

if __name__ == "__main__":
    run()
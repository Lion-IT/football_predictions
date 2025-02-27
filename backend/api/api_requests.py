import sys
import requests
import os
import time
import redis
import json

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from threading import Lock

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_connection import get_redis_connection
from utils.logging_utils import setup_logger, log_info, log_warning, log_error
from utils.notification_utils import add_to_batch_notification

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# API details
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY is not set in the .env file.")

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise ValueError("BASE_URL is not set in the .env file.")

BASE_HOST = os.getenv("BASE_HOST")
if not BASE_HOST:
    raise ValueError("BASE_HOST is not set in the .env file.")

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": BASE_HOST
}

# Variables
redis_client = get_redis_connection()
logger = setup_logger("api_requests")

# Global rate limit lock
lock = Lock()
last_request_time = 0
REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", 30))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 100))
REQUEST_INTERVAL = 60 / REQUESTS_PER_MINUTE  # Time between requests to stay within the limit

def get_ttl_to_midnight():
    now = datetime.now()
    next_midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
    return max(int((next_midnight - now).total_seconds()), 0)

def can_execute_request():
    alert_threshold = 0.9
    daily_key = "api_requests_daily"

    # Pobranie pozostałych zapytań API z Redisa
    remaining_requests = redis_client.get("X-RateLimit-Remaining")
    if remaining_requests is None:
        log_warning(logger, "⚠️ Nie znaleziono 'X-RateLimit-Remaining' w Redisie, pobieranie domyślnej wartości.")
        remaining_requests = REQUESTS_PER_MINUTE  # Domyślna wartość
    else:
        try:
            remaining_requests = int(remaining_requests)
        except ValueError:
            log_warning(logger, f"⚠️ Nieprawidłowa wartość 'X-RateLimit-Remaining' = {remaining_requests}, resetowanie.")
            remaining_requests = REQUESTS_PER_MINUTE

    # Inkrementacja dziennego licznika
    daily_count = redis_client.incr(daily_key)
    # Logowanie ostrzeżenia przy przekroczeniu progu 90%
    if daily_count / DAILY_LIMIT >= alert_threshold:
        log_warning(logger, f"⚠️ Zbliżasz się do limitu API: {daily_count}/{DAILY_LIMIT}")
        add_to_batch_notification(body=f"Obecne użycie API: {daily_count}/{DAILY_LIMIT} ({(daily_count / DAILY_LIMIT) * 100:.1f}%).")

    # Sprawdzanie limitu
    if daily_count >= DAILY_LIMIT or remaining_requests < 1:
        log_warning(logger, f"⛔ Osiągnięto dzienny limit API: {daily_count}/{DAILY_LIMIT}, Pozostałe: {remaining_requests}")
        add_to_batch_notification(body=f"Osiągnięto dzienny limit {DAILY_LIMIT} zapytań API.")
        return False
    return True

def fetch_from_api(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
    except requests.RequestException as e:
        log_error(logger, f"⚠️ Błąd połączenia z API: {e}")
        return None

    # Logowanie nagłówków odpowiedzi API
    # log_info(logger, f"Response headers: {response.headers}")

    # Obsługa przekroczenia limitu
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 5))
        log_warning(logger, f"API Rate Limit Exceeded! Retrying after {retry_after} seconds...")
        time.sleep(retry_after)
        return fetch_from_api(endpoint, params)

    if response.status_code >= 500:
        log_warning(logger, f"⚠️ Serwer API zwrócił {response.status_code}, spróbujemy ponownie...")
        time.sleep(5)
        return fetch_from_api(endpoint, params)

    if response.status_code >= 400:
        log_error(logger, f"⚠️ API zwróciło błąd: {response.status_code} - {response.text}")
        return None

    # Pobranie rzeczywistej wartości "X-RateLimit-requests-Remaining"
    remaining = response.headers.get("X-RateLimit-requests-Remaining")
    get_reset_time = response.headers.get("X-RateLimit-requests-Reset", 60)
    reset_time = min(int(get_reset_time), 3600)

    if remaining is not None:
        try:
            remaining = int(remaining)
            redis_client.setex("X-RateLimit-Remaining", int(reset_time), remaining)
            log_info(logger, f"✅ Aktualna liczba pozostałych zapytań API: {remaining}")
        except ValueError:
            log_warning(logger, f"⚠️ Błąd konwersji 'X-RateLimit-Remaining' = {remaining}")
    else:
        log_warning(logger, "⚠️ API nie zwróciło 'X-RateLimit-requests-Remaining'!")

    return response.json()

def rate_limited_fetch(fetch_function, endpoint, params):
    global last_request_time
    with lock:
        now = time.time()
        elapsed = now - last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        last_request_time = time.time()
    return fetch_function(endpoint, params)

def get_data(endpoint, params=None, cache_ttl=None):
    if cache_ttl is None:
        cache_ttl = get_ttl_to_midnight()

    daily_key = "api_requests_daily"
    daily_count = int(redis_client.get(daily_key) or 0)
    log_info(logger, f"Daily API requests made: {daily_count}/{DAILY_LIMIT}")

    cache_key = f"api_cache:{endpoint}:{json.dumps(params, sort_keys=True)}" if params else f"api_cache:{endpoint}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        try:
            data = json.loads(cached_data)
            if data == "NO_DATA":
                log_info(logger, f"No data found (cached) for {endpoint} with params {params}")
                return None
            log_info(logger, f"Cache hit for {endpoint} with params {params}")
            return data
        except json.JSONDecodeError:
            redis_client.delete(cache_key)

    log_info(logger, f"Cache miss for {endpoint} with params {params}")
    if not can_execute_request():
        return None

    start_time = time.time()
    data = rate_limited_fetch(fetch_from_api, endpoint, params)
    elapsed_time = time.time() - start_time

    if elapsed_time > 2:
        log_warning(logger, f"Slow request: {endpoint} with params {params} took {elapsed_time:.2f} seconds")

    if not data or 'response' not in data or not data['response']:
        redis_client.setex(cache_key, cache_ttl, json.dumps("NO_DATA"))
        return None

    redis_client.setex(cache_key, cache_ttl, json.dumps(data))
    return data
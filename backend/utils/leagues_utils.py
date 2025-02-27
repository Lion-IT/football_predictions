import sys
import os
import json
import pandas as pd

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from api.api_requests import get_data
from utils.progress_utils import create_progress_bar
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_error, log_info

# Setup logger for notifications
logger = setup_logger("leagues_utils")

# Cache time-to-live
cache_ttl = 15552000

def fetch_league_data(league):
    try:
        current_season = next((season for season in league['seasons'] if season.get('current', False)), None)
        league_data = {
            'league_id': league['league']['id'],
            'name': league['league']['name'],
            'country': league['country']['name'],
            'country_code': league['country']['code'] if league['country']['code'] else None,
            'flag_url': league['country']['flag'] if league['country']['flag'] else None,
            'logo_url': league['league'].get('logo', None),
            'type': league['league']['type'],
            'current_season': current_season['year'] if current_season else None,
            'start_date': current_season['start'] if current_season else None,
            'end_date': current_season['end'] if current_season else None
        }
        log_info(logger, f"Pobieranie danych o ligach: {league_data['name']} ({league_data['league_id']})")
        return league_data
    except Exception as e:
        log_error(logger, f"ERROR fetching league data: {e}")
        return None


def fetch_and_insert_leagues():
    cache_key = "leagues"

    # Check Redis cache
    redis_client = get_redis_connection()
    cached_data = redis_client.get(cache_key)
    if cached_data:
        log_info(logger, "Dane lig pobrane z cache Redis.")
        leagues = json.loads(cached_data)
    else:
        # Fetch data from API
        log_info(logger, "Pobieranie danych z API...")
        response = get_data("leagues")
        if not response or 'response' not in response:
            log_info(logger, "Brak danych do pobrania")
            return

        leagues = response['response']
        redis_client.setex(cache_key, cache_ttl, json.dumps(leagues))

    # Process data using multithreading
    with ThreadPoolExecutor(max_workers=4) as executor:
        processed_leagues = []
        with create_progress_bar(total=len(leagues), desc="Processing leagues data") as pbar:
            for league in executor.map(fetch_league_data, leagues):
                if league:
                    processed_leagues.append(league)
                pbar.update(1)

    # Remove invalid entries
    processed_leagues = [league for league in processed_leagues if league]

    # Convert to DataFrame
    df = pd.DataFrame(processed_leagues)

    # Manual cleaning and validation
    log_info(logger, "Ręczne czyszczenie i walidacja danych...")
    df = df.drop_duplicates()

    # Fill missing values for specific columns
    df['flag_url'] = df['flag_url'].fillna('')
    df['logo_url'] = df['logo_url'].fillna('')
    df['current_season'] = df['current_season'].fillna(0)
    df['country_code'] = df['country_code'].fillna('')

    # Ensure required columns are present
    required_columns = ['league_id', 'name', 'country', 'country_code', 'flag_url',
                        'logo_url', 'type', 'current_season', 'start_date', 'end_date']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Ensure no null values in required columns
    if df[required_columns].isnull().any().any():
        raise ValueError("Data contains null values in required columns.")

    # Prepare data for database insertion
    rows = df.to_dict(orient='records')

    # Insert or update database
    query = text("""
    INSERT INTO leagues (
        league_id, name, country, country_code, flag_url, logo_url, type,
        current_season, start_date, end_date
    )
    VALUES (:league_id, :name, :country, :country_code, :flag_url, :logo_url, :type,
            :current_season, :start_date, :end_date)
    ON DUPLICATE KEY UPDATE
        name=VALUES(name), country=VALUES(country), country_code=VALUES(country_code),
        flag_url=VALUES(flag_url), logo_url=VALUES(logo_url), type=VALUES(type),
        current_season=VALUES(current_season), start_date=VALUES(start_date),
        end_date=VALUES(end_date)
    """)

    rows_affected = 0
    # Use SQLAlchemy session
    with SessionLocal() as session:
        try:
            # Batch insert
            result = session.execute(query, rows)
            session.commit()
            rows_affected = result.rowcount
            log_info(logger, f"{rows_affected} rows actually inserted/updated in the database.")
            if rows_affected == 0:
                log_info(logger, "No changes detected. The database is up-to-date.")
        except SQLAlchemyError as e:
            session.rollback()
            log_error(logger, f"Database error: {e}")
            raise

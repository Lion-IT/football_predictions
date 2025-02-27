import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Dict
from dotenv import load_dotenv
from datetime import datetime, timedelta

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from api.api_requests import get_data, get_ttl_to_midnight
from config.db_connection import get_redis_connection, SessionLocal
from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_info, log_error, log_warning
from utils.validation_utils import is_table_empty, parse_date_to_local
from utils.special_football_functions import get_current_season

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Import leagues from config
fetch_days_config = os.getenv("FETCH_DAYS", "0")
fetch_days = list(map(int, fetch_days_config.split(",")))

# Setup logger for notifications
logger = setup_logger("future_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = get_ttl_to_midnight()

def fetch_future_away_team() -> List[Dict]:
    """Fetch a list of predictions matches from DB."""

    query = text("SELECT away_team_id FROM future_matches")
    try:
        with SessionLocal() as session:
            matches = session.execute(query).fetchall()
            return [row[0] for row in matches]
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching available matches: {e}")
        return []

def fetch_future_home_team() -> List[Dict]:
    """Fetch a list of predictions matches from DB."""

    query = text("SELECT home_team_id FROM future_matches")
    try:
        with SessionLocal() as session:
            matches = session.execute(query).fetchall()
            return [row[0] for row in matches]
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching available matches: {e}")
        return []

def fetch_match_ids(league_id: int, match_date: str) -> List[int]:
    """ Fetch match IDs for a specific league and date. """
    params = {
        "league": league_id,
        "date": match_date,
        "season": get_current_season(league_id),
        "status": "NS"
    }
    try:
        response = get_data("fixtures", params=params)
        if not response:
            log_warning(logger, f"Empty API response for league {league_id} on {match_date}.")
            return []
        if not isinstance(response, dict) or 'response' not in response:
            log_error(logger, f"Invalid API response: {response}")
            return []
        match_ids = [match.get('fixture', {}).get('id') for match in response['response'] if isinstance(match, dict)]
        if not match_ids:
            log_info(logger, f"No match IDs found for league {league_id} on {match_date}.")

        return [m_id for m_id in match_ids if m_id is not None]
    except Exception as e:
        log_error(logger, f"Error fetching match IDs for league {league_id} on {match_date}: {e}")
        return []

def fetch_matches_by_ids(match_ids: List[int]) -> List[Dict]:
    """ Fetch match data based on a list of match IDs. """
    matches = []
    for match_id in match_ids:
        redis_key = f"future_match:{match_id}"
        cached_data = redis_client.get(redis_key)
        if cached_data:
            matches.append(json.loads(cached_data))
        else:
            try:
                response = get_data("fixtures", params={"id": match_id})
                if response and 'response' in response:
                    match = response['response'][0]
                    redis_client.setex(redis_key, 86400, json.dumps(match))  # Cache for a day
                    matches.append(match)
            except Exception as e:
                log_error(logger, f"Error fetching match data for match ID {match_id}: {e}")
    return matches

def fetch_and_insert_future_matches_hset(league_ids: list):
    """
    Fetch and insert future matches for a list of league IDs into the database.
    """
    all_match_ids = []

    # Check if the table is empty and load data from Redis if so
    if is_table_empty("future_matches"):
        log_info(logger, "Table 'future_matches' is empty. Check data from Redis.")
        redis_keys = redis_client.keys("future_match_db:*")
        rows = []
        for key in redis_keys:
            raw_match = redis_client.get(key)
            if raw_match:
                match = json.loads(raw_match)
                if isinstance(match, dict) and "match_id" in match:
                    rows.append({
                        "match_id": match['match_id'],
                        "league_id": match.get('league_id'),
                        "home_team_id": match.get('home_team_id'),
                        "away_team_id": match.get('away_team_id'),
                        "match_date": match.get('match_date'),
                        "stadium": match.get('stadium'),
                        "referee": match.get('referee'),
                        "status": match.get('status'),
                        "last_data_insert": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    log_error(logger, f"Invalid match format from Redis: {match}")
            else:
                log_error(logger, f"Empty match data in Redis for key: {key}")

        if rows:
            try:
                with SessionLocal() as session:
                    query = text("""
                        INSERT INTO future_matches (
                            match_id, league_id, home_team_id, away_team_id, match_date, stadium, referee, status, last_data_insert
                        ) VALUES (
                            :match_id, :league_id, :home_team_id, :away_team_id, :match_date, :stadium, :referee, :status, NOW()
                        ) ON DUPLICATE KEY UPDATE
                            league_id=VALUES(league_id), home_team_id=VALUES(home_team_id),
                            away_team_id=VALUES(away_team_id), match_date=VALUES(match_date),
                            stadium=VALUES(stadium), referee=VALUES(referee), status=VALUES(status), last_data_insert=NOW()
                    """)
                    session.execute(query, rows)
                    session.commit()
                log_info(logger, f"Inserted {len(rows)} rows from Redis into the database.")
            except SQLAlchemyError as e:
                log_error(logger, f"Error inserting Redis data into database: {e}")
            return
        else:
            log_info(logger, "Brak danych w REDIS, pobieram dane z API...")

    # Generate the list of dates to fetch based on FETCH_DAYS
    today = datetime.now()
    dates_to_fetch = [(today + timedelta(days=day)).strftime("%Y-%m-%d") for day in fetch_days]

    with ThreadPoolExecutor(max_workers=2) as executor:
        with create_progress_bar(total=len(league_ids) * len(dates_to_fetch), desc="Sprawdzanie meczy...") as pbar:
            futures = [
                executor.submit(fetch_match_ids, league_id, match_date)
                for league_id in league_ids
                for match_date in dates_to_fetch
            ]
            for future in futures:
                try:
                    match_ids = future.result()
                    if not match_ids:
                        continue
                    all_match_ids.extend(match_ids)
                except Exception as e:
                    log_error(logger, f"Error fetching match IDs: {e}")
                finally:
                    pbar.update(1)

    all_matches = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        with create_progress_bar(total=len(all_match_ids) // 20 + 1, desc="Sprawdzanie szczegolow...") as pbar:
            futures = [executor.submit(fetch_matches_by_ids, all_match_ids[i:i + 20]) for i in range(0, len(all_match_ids), 20)]
            for future in futures:
                try:
                    matches = future.result()
                    all_matches.extend(matches)
                except Exception as e:
                    log_error(logger, f"Error fetching match details: {e}")
                finally:
                    pbar.update(1)

    unique_matches = {}
    for match in all_matches:
        if isinstance(match, dict) and 'fixture' in match and 'id' in match['fixture']:
            unique_matches[match['fixture']['id']] = {
                'match_id': match['fixture']['id'],
                'league_id': match.get('league', {}).get('id'),
                'home_team_id': match.get('teams', {}).get('home', {}).get('id'),
                'away_team_id': match.get('teams', {}).get('away', {}).get('id'),
                'match_date': parse_date_to_local(match.get('fixture', {}).get('date')).strftime('%Y-%m-%d %H:%M:%S') if match.get('fixture', {}).get('date') else None,
                'stadium': match.get('fixture', {}).get('venue', {}).get('name', None),
                'referee': match.get('fixture', {}).get('referee', None),
                'status': match.get('fixture', {}).get('status', {}).get('short')
            }
        else:
            log_error(logger, f"Invalid match format: {match}")

    unique_matches = unique_matches.values()

    try:
        with SessionLocal() as session:
            for match in unique_matches:
                redis_key = f"future_match_db:{match['match_id']}"
                cached_row = redis_client.get(redis_key)
                if cached_row and json.loads(cached_row) == match:
                    log_info(logger, f"No changes detected for match ID {match['match_id']}, skipping DB update.")
                    continue
                redis_client.setex(redis_key, cache_ttl, json.dumps(match))

                query = text("""
                    INSERT INTO future_matches (
                        match_id, league_id, home_team_id, away_team_id, match_date, stadium, referee, status, last_data_insert
                    ) VALUES (
                        :match_id, :league_id, :home_team_id, :away_team_id, :match_date, :stadium, :referee, :status, NOW()
                    ) ON DUPLICATE KEY UPDATE
                        league_id=VALUES(league_id), home_team_id=VALUES(home_team_id),
                        away_team_id=VALUES(away_team_id), match_date=VALUES(match_date),
                        stadium=VALUES(stadium), referee=VALUES(referee), status=VALUES(status), last_data_insert=NOW()
                """)
                session.execute(query, match)
            session.commit()
            log_info(logger, f"Inserted/updated {len(unique_matches)} matches into the database.")

            return unique_matches
    except SQLAlchemyError as e:
        log_error(logger, f"Error inserting matches into database: {e}")
import sys
import os
import json
import datetime

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Dict
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from api.api_requests import get_data
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_error, log_info, log_warning
from utils.players_utils import fetch_and_insert_player
from utils.progress_utils import create_progress_bar

# Setup logger for match events
logger = setup_logger("match_events_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = 15552000

VALID_EVENT_TYPES = {'goal','yellow_card','second_yellow_card','red_card','penalty_goal'}

def get_valid_season(player_id: int):
    """Determine the most recent valid season by checking API responses."""
    current_year = datetime.datetime.now().year
    for year in range(current_year, current_year - 10, -1):
        response = get_data("players", params={"id": player_id, "season": year})
        if response and 'response' in response and response['response']:
            return year
    return current_year  # Fallback to the current year if nothing is found

def player_exists(session: SessionLocal, player_id: int) -> bool:
    """Check if player_id exists in the players table."""
    if player_id is None:
        return False  # Jeśli player_id jest None, zwracamy False zamiast True

    result = session.execute(text("SELECT 1 FROM players WHERE player_id = :player_id LIMIT 1"),
                             {"player_id": player_id}).fetchone()
    return result is not None

def fetch_match_events(match_id: int) -> List[Dict]:
    """Fetch match events (goals, cards, substitutions) from the API."""
    endpoint = "fixtures/events"
    redis_key = f"match_events:{match_id}"

    if (cached_data := redis_client.get(redis_key)):
        log_info(logger, f"Match events for match ID {match_id} retrieved from Redis.")
        return json.loads(cached_data)

    try:
        response = get_data(endpoint, params={"fixture": match_id})
        if not response or 'response' not in response or not isinstance(response['response'], list):
            log_warning(logger, f"Unexpected API response structure for match ID {match_id}: {response}")
            return []
        match_events = response['response']

        # Cache in Redis
        try:
            if match_events:
                redis_client.setex(redis_key, cache_ttl, json.dumps(match_events))
                log_info(logger, f"Match events for match ID {match_id} cached in Redis.")
        except Exception as e:
            log_error(logger, f"Error saving match events to Redis for match ID {match_id}: {str(e)}")

        return match_events
    except Exception as e:
        log_error(logger, f"Error fetching match events for match ID {match_id}: {str(e)}")
        return []

def parse_match_events(match_id: int, response: List[Dict]) -> List[Dict]:
    """Parse match events response for database insertion."""
    if not response:
        log_warning(logger, f"No event data to parse for match ID {match_id}. Skipping.")
        return []

    events = []
    with SessionLocal() as session:
        for event in response:
            team_id = event.get('team', {}).get('id')
            player_id = event.get('player', {}).get('id')
            assist_player_id = event.get('assist', {}).get('id')
            event_type = event.get('type').lower()
            event_detail = event.get('detail', '') or ''
            event_time = event.get('time', {}).get('elapsed')
            extra_time = event.get('time', {}).get('extra')
            is_penalty = 1 if event_detail and "Penalty" in event_detail else 0

            if event_time is not None and event_time < 0:
                log_info(logger, f"Invalid event_time ({event_time}) detected for match {match_id}. Setting to 0.")
                event_time = 0

            if extra_time is not None and extra_time < 0:
                log_info(logger, f"Invalid extra_time ({extra_time}) detected for match {match_id}. Setting to NULL.")
                extra_time = None  # Ustawiamy na NULL zamiast ujemnej wartości

            if player_id and not player_exists(session, player_id):
                season = get_valid_season(player_id)
                fetch_and_insert_player(player_id, season)
                if not player_exists(session, player_id):
                    log_warning(logger, f"Player {player_id} not found even after insertion. Setting to NULL.")
                    player_id = None  # Ustawiamy NULL zamiast pomijać event

            if assist_player_id and not player_exists(session, assist_player_id):
                season = get_valid_season(assist_player_id)
                fetch_and_insert_player(assist_player_id, season)
                if not player_exists(session, assist_player_id):
                    log_warning(logger, f"Assist player {assist_player_id} not found even after insertion. Setting to NULL.")
                    assist_player_id = None  # Ustawiamy NULL zamiast pomijać event

            # Convert event_type to match database ENUM values
            if event_type == "goal" and is_penalty:
                event_type = "penalty_goal"
            elif event_type == "card":
                if "Yellow Card" in event_detail:
                    event_type = "yellow_card"
                elif "Red Card" in event_detail:
                    event_type = "red_card"
                elif "Second Yellow Card" in event_detail:
                    event_type = "second_yellow_card"
                else:
                    log_warning(logger, f"Unknown card type: {event_detail}")
                    continue

            if event_type not in VALID_EVENT_TYPES:
                log_info(logger, f"Invalid event_type detected: {event_type}. Skipping event.")
                continue

            events.append({
                "match_id": match_id,
                "team_id": team_id,
                "player_id": player_id,
                "assist_player_id": assist_player_id,
                "event_type": event_type,
                "event_time": event_time,
                "extra_time": extra_time,
                "event_detail": event_detail,
                "is_penalty": is_penalty,
            })
    return events

def insert_match_events_to_db(events: List[Dict]):
    """Insert parsed match events into the database."""
    if not events:
        return log_warning(logger, "No match events to insert into the database.")

    query = text("""
        INSERT INTO match_events (
            match_id, team_id, player_id, assist_player_id, event_type, event_time, extra_time, event_detail, is_penalty
        ) VALUES (
            :match_id, :team_id, :player_id, :assist_player_id, :event_type, :event_time, :extra_time, :event_detail, :is_penalty
        )
        ON DUPLICATE KEY UPDATE
            event_type = VALUES(event_type),
            event_time = VALUES(event_time),
            extra_time = VALUES(extra_time),
            event_detail = VALUES(event_detail),
            is_penalty = VALUES(is_penalty);
    """)

    try:
        with SessionLocal() as session:
            session.execute(query, [dict(row) for row in events])
            session.commit()
            log_info(logger, f"Successfully inserted/updated {len(events)} match events.")
    except SQLAlchemyError as e:
        log_error(logger, f"Error inserting match events into database: {e}")
        session.rollback()

def run_all_proccess_event_match_with_progress_bar(match_id: int):
    total_steps = 3  # Total number of steps in the ETL process
    try:
        with create_progress_bar(total_steps, "Processing Match Events", "matches") as pbar:
            events_data = fetch_match_events(match_id)
            pbar.update(1)  # Update progress after fetching events
            parsed_events = parse_match_events(match_id, events_data)
            pbar.update(1)  # Update progress after parsing events
            insert_match_events_to_db(parsed_events)
            pbar.update(1)  # Update progress after inserting events into DB
    except Exception as e:
        log_error(logger, f"Unexpected error while processing match {match_id}: {str(e)}")

def run_all_proccess_event_match(match_id: int):
    try:
        events_data = fetch_match_events(match_id)
        parsed_events = parse_match_events(match_id, events_data)
        insert_match_events_to_db(parsed_events)
    except ValueError:
        log_error(logger, "Invalid input. Please provide a numeric value for Match ID.")
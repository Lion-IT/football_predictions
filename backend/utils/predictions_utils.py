import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Dict
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from api.api_requests import get_data, get_ttl_to_midnight
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_info, log_error, log_warning

# Setup logger for notifications
logger = setup_logger("predictions_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = get_ttl_to_midnight()

def fetch_predictions_matches() -> List[Dict]:
    """Fetch a list of predictions matches from DB."""

    query = text("SELECT p.fixture_id FROM predictions p LEFT JOIN h2h_matches h ON p.fixture_id = h.fixture_id WHERE h.fixture_id IS NULL;")
    try:
        with SessionLocal() as session:
            matches = session.execute(query).fetchall()
            return [row[0] for row in matches]
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching available matches: {e}")
        return []

def fetch_h2h_from_predictions(fixtures_ids: List[int]) -> List[Dict]:
    """Pobiera dane H2H na podstawie listy `fixture_id` i zwraca tylko mecze H2H."""

    matches = []
    for match_id in fixtures_ids:
        redis_key = f"predictions_h2h:{match_id}"
        cached_data = redis_client.get(redis_key)
        if cached_data:
            h2h_matches = json.loads(cached_data).get("h2h", [])
            matches.extend(h2h_matches)
            continue
        try:
            response = get_data("predictions", params={"fixture": match_id})
            if response and 'response' in response and response['response']:
                match_data = response['response'][0]
                h2h_matches = match_data.get("h2h", [])
                redis_client.setex(redis_key, 86400, json.dumps({"h2h": h2h_matches}))
                matches.extend(h2h_matches)
            else:
                log_error(logger, f"⚠️ Brak danych H2H w API dla Meczu o ID: {match_id}")
        except Exception as e:
            log_error(logger, f"Błąd podczas pobierania H2H dla fixture_id {match_id}: {e}")
    return matches

def fetch_predictions_for_match(match_id: int, progress_bar=None) -> None:
    """Pobierz predykcje dla danego ID meczu, sprawdź cache Redis i zapisz je w bazie danych."""

    predictions_key = f"predictions:{match_id}"
    try:
        cached_data = redis_client.get(predictions_key)
        if cached_data:
            log_info(logger, f"Cache hit for predictions of match ID {match_id}")
            predictions = json.loads(cached_data)
        else:
            log_info(logger, f"Fetching predictions for match ID {match_id}")
            response = get_data("predictions", {"fixture": match_id})

            if not response or 'response' not in response or not response['response']:
                log_info(logger, f"No prediction data found for match ID {match_id}.")
                return

            predictions = response['response'][0]
            redis_client.setex(predictions_key, cache_ttl, json.dumps(predictions))

        predictions_data = {
			"fixture_id": match_id,
			"winner_team_id": predictions['predictions']['winner']['id'] if predictions['predictions']['winner'] else None,
			"winner_name": predictions['predictions']['winner']['name'] if predictions['predictions']['winner'] else None,
			"advice": predictions['predictions']['advice'],
			"home_win_percent": float(predictions['predictions']['percent']['home'].replace('%', '')),
			"draw_percent": float(predictions['predictions']['percent']['draw'].replace('%', '')),
			"away_win_percent": float(predictions['predictions']['percent']['away'].replace('%', '')),
			"goals_home": predictions['predictions']['goals']['home'] if predictions['predictions']['goals']['home'] is not None else 0,
			"goals_away": predictions['predictions']['goals']['away'] if predictions['predictions']['goals']['away'] is not None else 0,
		}

        query = text("""
            INSERT INTO predictions (
                fixture_id, winner_team_id, winner_name, advice,
                home_win_percent, draw_percent, away_win_percent,
                goals_home, goals_away
            )
            VALUES (:fixture_id, :winner_team_id, :winner_name, :advice,
                    :home_win_percent, :draw_percent, :away_win_percent,
                    :goals_home, :goals_away)
            ON DUPLICATE KEY UPDATE
                winner_team_id = VALUES(winner_team_id),
                winner_name = VALUES(winner_name),
                advice = VALUES(advice),
                home_win_percent = VALUES(home_win_percent),
                draw_percent = VALUES(draw_percent),
                away_win_percent = VALUES(away_win_percent),
                goals_home = COALESCE(VALUES(goals_home), 0),
    			goals_away = COALESCE(VALUES(goals_away), 0);
        """)

        with SessionLocal() as session:
            session.execute(query, predictions_data)
            session.commit()
            log_info(logger, f"Inserted/updated predictions for match ID {match_id}.")

        if progress_bar:
            progress_bar.update(1)
    except SQLAlchemyError as e:
        log_error(logger, f"Error inserting predictions into database: {e}")

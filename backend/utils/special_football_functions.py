import sys
import os

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Dict
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from config.db_connection import SessionLocal
from utils.logging_utils import setup_logger, log_error, log_info
from datetime import datetime

# Setup logger for notifications
logger = setup_logger("special_football_functions")

def get_current_season(league_id: int):
    """Pobiera bieżący sezon dla danej ligi z tabeli `leagues`."""
    query = text("SELECT current_season FROM leagues WHERE league_id = :league_id")
    try:
        with SessionLocal() as session:
            result = session.execute(query, {"league_id": league_id}).fetchone()
            return result[0] if result else None
    except SQLAlchemyError as e:
        log_error(logger, f"Error in get_current_season: {e}")
        raise

def calculate_season_for_matches(match_date: str) -> int:
    """
    Calculate the season year based on the match date.
    Args: match_date (str): The match date in ISO 8601 format (e.g., '2024-12-19T17:00:00+00:00').
    Returns: int: The season year.
    """
    match_datetime = datetime.strptime(match_date, "%Y-%m-%dT%H:%M:%S%z")
    if match_datetime.month >= 7:
        return match_datetime.year
    else:
        return match_datetime.year - 1

def calculate_season(match_date: str) -> int:
    """Calculate the football season based on the match date."""

    if isinstance(match_date, str):
        match_date = datetime.strptime(match_date, "%Y-%m-%d")
    elif not isinstance(match_date, datetime):
        raise ValueError("match_date must be a datetime object or string in 'YYYY-MM-DD' format.")

    return match_date.year - 1 if match_date.month <= 6 else match_date.year

def calculate_match_duration(fixture: Dict) -> int:
    """Calculate match duration based on fixture data."""

    elapsed = fixture['status'].get('elapsed', 90)
    extra = fixture['status'].get('extra', 0)

    elapsed = int(elapsed) if elapsed is not None else 90
    extra = int(extra) if extra is not None else 0

    return elapsed + extra

def get_match_result(score_home: int, score_away: int) -> str:
    """ Determine the match result based on home and away scores."""

    if score_home is None or score_away is None:
        return 'unknown'

    if score_home > score_away:
        return 'win'
    elif score_home < score_away:
        return 'loss'
    else:
        return 'draw'

def fetch_available_matches() -> List[Dict]:
    """Fetch a list of available matches for user selection."""

    query = text("SELECT match_id, home_team_id, away_team_id, match_date FROM future_matches WHERE match_date >= NOW() ORDER BY match_date ASC;")
    try:
        with SessionLocal() as session:
            matches = session.execute(query).fetchall()
            log_info(logger, f"Fetched {len(matches)} available matches from the database.")
            return [dict(row._asdict()) for row in matches]  # Poprawka!
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching available matches: {e}")
        return []

def fetch_league_id_for_match(match_id: int) -> int:
    """Fetch the league_id for a specific match."""

    query = text("SELECT league_id FROM future_matches WHERE match_id = :match_id")
    try:
        with SessionLocal() as session:
            result = session.execute(query, {"match_id": match_id}).fetchone()
            return result['league_id'] if result else None
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching league ID for match {match_id}: {e}")
        return None

def fetch_team_ids_from_db(match_id: int) -> Dict[str, List[Dict]]:
    """Fetch team IDs and names for a specific match from the local database."""

    query = text("""
        SELECT
            fm.home_team_id, t1.name AS home_team_name,
            fm.away_team_id, t2.name AS away_team_name
        FROM future_matches fm
        LEFT JOIN teams t1 ON fm.home_team_id = t1.team_id
        LEFT JOIN teams t2 ON fm.away_team_id = t2.team_id
        WHERE fm.match_id = :match_id;
    """)
    try:
        with SessionLocal() as session:
            results = session.execute(query, {"match_id": match_id}).fetchall()
            teams = []
            missing_team_ids = []
            for row in results:
                row_dict = dict(row._asdict())
                if not row_dict['home_team_name']:
                    missing_team_ids.append(row_dict['home_team_id'])
                else:
                    teams.append({"team_id": row_dict['home_team_id'], "name": row_dict['home_team_name']})
                if not row_dict['away_team_name']:
                    missing_team_ids.append(row_dict['away_team_id'])
                else:
                    teams.append({"team_id": row_dict['away_team_id'], "name": row_dict['away_team_name']})
            return {"teams": teams, "missing_teams": list(set(missing_team_ids))}
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching team IDs and names for match {match_id}: {e}")
        return {"teams": [], "missing_teams": []}
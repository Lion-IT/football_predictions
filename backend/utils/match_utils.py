import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from typing import List, Dict

from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from api.api_requests import get_data
from config.db_connection import get_redis_connection, SessionLocal
from utils.progress_utils import create_progress_bar
from utils.logging_utils import setup_logger, log_error, log_info, log_warning
from utils.special_football_functions import get_current_season, calculate_match_duration, get_match_result
from utils.teams_utils import check_missing_teams

# Setup logger for notifications
logger = setup_logger("match_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = 15552000

def get_unique_matches_ids():
    query = text("SELECT match_id FROM matches")
    with SessionLocal() as session:
        results = session.execute(query).fetchall()
        return [row[0] for row in results]

def get_unique_matches_ids_for_future_matches(home_id, away_id):
    query = text("""
    	SELECT match_id
    	FROM matches
    	WHERE (home_team_id = :home_id AND away_team_id = :away_id) OR (home_team_id = :away_id AND away_team_id = :home_id)
    """)
    with SessionLocal() as session:
        results = session.execute(query, {"home_id": home_id, "away_id": away_id}).fetchall()
        return [row[0] for row in results]

def get_unique_fixture_ids():
    query = text("SELECT DISTINCT fixture_id FROM h2h_matches")
    with SessionLocal() as session:
        results = session.execute(query).fetchall()
        return [row[0] for row in results]

def get_unique_fixture_ids_for_future_matches(home_id, away_id):
    query = text("""
    	SELECT fixture_id
    	FROM h2h_matches
    	WHERE (home_team_id = :home_id AND away_team_id = :away_id) OR (home_team_id = :away_id AND away_team_id = :home_id)
    """)
    with SessionLocal() as session:
        results = session.execute(query, {"home_id": home_id, "away_id": away_id}).fetchall()
        return [row[0] for row in results]

def match_id_exists(match_id):
    query = text("SELECT 1 FROM matches WHERE match_id = :match_id")
    with SessionLocal() as session:
        result = session.execute(query, {"match_id": match_id}).scalar()
        return result is not None

def fetch_matches_for_team(team_id: int, number_of_matches=10) -> List[Dict]:
    """Fetch the last matches for a given team from the API."""
    try:
        response = get_data("fixtures", params={"team": team_id, "last": number_of_matches})
        # Sprawdzenie, czy odpowiedź jest poprawna
        if not response or not isinstance(response, dict) or 'response' not in response:
            log_warning(logger, f"No matches found for team ID {team_id}. API response: {response}")
            return []

        if response and 'response' in response:
            for match in response['response']:
                redis_key = f"match:{match['fixture']['id']}"
                if redis_client.get(redis_key):
                    logger.info(f"Match data for fixture ID {match['fixture']['id']} retrieved from Redis.")
                    continue
                redis_client.setex(redis_key, cache_ttl, json.dumps(match))
            return response['response']
        log_warning(logger, f"No matches found for team ID {team_id}.")
        return []
    except Exception as e:
        log_error(logger, f"Error fetching matches for team ID {team_id}: {e}")
        return []

def fetch_match_from_id(fixture_ids: List[int], max_workers=4) -> List[Dict]:
    fetched_matches = []
    tasks = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Tworzymy pasek postępu z całkowitą liczbą zapytań
        with create_progress_bar(total=len(fixture_ids), desc="Fetching match data", unit="matches") as pbar:
            for fixture_id in fixture_ids:
                redis_key = f"match:{fixture_id}"
                cached_match = redis_client.get(redis_key)
                if cached_match:
                    fetched_matches.append(json.loads(cached_match))
                    pbar.update(1)  # ✅ Aktualizacja progress bara dla cache hit
                else:
                    # Dodajemy zadanie do pobrania z API
                    tasks[executor.submit(get_data, "fixtures", {"id": fixture_id})] = fixture_id
            # Obsługa pobierania danych z API
            for future in as_completed(tasks):
                fixture_id = tasks[future]
                try:
                    response = future.result()
                    if response and 'response' in response and response['response']:
                        match = response['response'][0]
                        if match:
                            redis_client.setex(f"match:{fixture_id}", cache_ttl, json.dumps(match))
                            fetched_matches.append(match)
                    else:
                        log_warning(logger, f"No match found for ID {fixture_id}.")
                except Exception as e:
                    log_error(logger, f"Error fetching data for fixture ID {fixture_id}: {e}")
                finally:
                    pbar.update(1)  # ✅ Aktualizacja progress bara dla danych z API
    return fetched_matches

def insert_matches_to_db(matches: List[Dict]):
    rows = []

    # Tworzymy pasek postępu dla przetwarzania meczów
    with create_progress_bar(total=len(matches), desc="Processing matches", unit="match") as pbar:
        for match in matches:
            fixture = match.get('fixture', {})
            league = match.get('league', {})
            teams = match.get('teams', {})
            goals = match.get('goals', {})
            score = match.get('score', {})

            if not fixture or not league or not teams:
                log_warning(logger, f"Skipping match due to missing data: {match}")
                pbar.update(1)  # ✅ Aktualizacja progress bara
                continue

            match_id = fixture['id']

            # ✅ Sprawdzamy, czy mecz już istnieje w bazie i pomijamy go
            if match_id_exists(match_id):
                log_info(logger, f"Match {match_id} already exists in DB. Skipping...")
                pbar.update(1)  # ✅ Aktualizacja progress bara
                continue

            match_duration = calculate_match_duration(fixture)
            league_id = league['id']
            home_team_id = teams['home']['id']
            away_team_id = teams['away']['id']
            season = get_current_season(league_id)

            existing_teams, missing_team_ids = check_missing_teams(
                [home_team_id, away_team_id],
                league_id=league_id,
                season=season
            )

            if missing_team_ids:
                log_error(logger, f"Cannot insert match {fixture['id']}. Missing teams: {missing_team_ids}")
                pbar.update(1)  # ✅ Aktualizacja progress bara
                continue

            match_date = datetime.strptime(fixture['date'], "%Y-%m-%dT%H:%M:%S%z").strftime("%Y-%m-%d %H:%M:%S")
            try:
                home_goals = goals.get('home', 0)
                away_goals = goals.get('away', 0)
                match_result = get_match_result(home_goals, away_goals)
            except Exception as e:
                log_error(logger, f"Error determining match result for match {fixture['id']}: {e}")
                match_result = 'unknown'

            rows.append({
                "match_id": match_id,
                "league_id": league_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "date": match_date,
                "result": match_result,
                "score_home": goals.get('home', 0),
                "score_away": goals.get('away', 0),
                "referee_name": str(fixture.get('referee', 'Unknown')),
                "stadium_name": str(fixture.get('venue', {}).get('name', 'Unknown')),
                "match_duration": match_duration,
                "match_type": str(league['name']),
                "penalties_awarded": score.get('penalty', {}).get('away', None),
            })

            pbar.update(1)  # ✅ Aktualizacja progress bara po każdym meczu

    if not rows:
        log_warning(logger, "No matches to insert due to missing team data or already existing matches.")
        return

    query = text("""
        INSERT INTO matches (
            match_id, league_id, home_team_id, away_team_id, date, result,
            score_home, score_away, referee_name, stadium_name, match_duration,
            match_type, penalties_awarded
        )
        VALUES (
            :match_id, :league_id, :home_team_id, :away_team_id, :date, :result,
            :score_home, :score_away, :referee_name, :stadium_name, :match_duration,
            :match_type, :penalties_awarded
        )
        ON DUPLICATE KEY UPDATE
            score_home=VALUES(score_home), score_away=VALUES(score_away),
            result=VALUES(result), referee_name=VALUES(referee_name),
            stadium_name=VALUES(stadium_name), match_duration=VALUES(match_duration),
            match_type=VALUES(match_type), penalties_awarded=VALUES(penalties_awarded)
    """)

    try:
        with SessionLocal() as session:
            session.execute(query, rows)
            session.commit()
            log_info(logger, f"{len(rows)} new rows successfully inserted/updated.")
    except SQLAlchemyError as e:
        session.rollback()
        log_error(logger, f"Database error while inserting matches: {e}")
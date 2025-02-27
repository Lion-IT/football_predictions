import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Dict
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

from api.api_requests import get_data
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_error, log_info, log_warning

# Setup logger for notifications
logger = setup_logger("match_statitics_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = 15552000

def parse_percentage(value: str) -> float:
    if not value or value in ["-", "N/A"]:
        return 0.0
    try:
        return float(value.strip('%'))
    except ValueError:
        return 0.0

def fetch_match_statistics(match_id: int) -> List[Dict]:
    """Fetch detailed match statistics from the API."""

    endpoint = "fixtures/statistics"
    redis_key = f"match_statistics:{match_id}"
    if (cached_data := redis_client.get(redis_key)):
        log_info(logger, f"Match statistics for match ID {match_id} retrieved from Redis.")
        return json.loads(cached_data)
    try:
        response = get_data(endpoint, params={"fixture": match_id})
        if not response or 'response' not in response or not response['response']:
            log_warning(logger, f"Unexpected API response structure for match ID {match_id}: {response}")
            return []
        match_stats = response['response']
         # Zapis do Redis tylko jeśli mamy poprawne dane
        try:
            if match_stats:
                redis_client.setex(redis_key, cache_ttl, json.dumps(match_stats))
                log_info(logger, f"Match statistics for match ID {match_id} cached in Redis.")
        except Exception as e:
            log_error(logger, f"Error saving match statistics to Redis for match ID {match_id}: {str(e)}")

        return match_stats
    except Exception as e:
        log_error(logger, f"Error fetching detailed statistics for match ID {match_id}: {str(e)}")
        return []

def parse_match_statistics(match_id: int, response: List[Dict]) -> List[Dict]:
    """Parse match statistics response for database insertion."""

    if not response:
        log_warning(logger, f"No data to parse for match ID {match_id}. Skipping.")
        return []

    statistics = []
    for team_stats in response:
        if 'team' not in team_stats or 'statistics' not in team_stats:
            log_error(logger, f"Invalid team statistics structure for match ID {match_id}: {team_stats}")
            continue

        # team_id = team_stats['team']['id']
        team_id = team_stats.get('team', {}).get('id')
        if not team_id:
            log_error(logger, f"Missing team ID for match ID {match_id}. Skipping entry: {team_stats}")
            continue

        stats = {stat['type']: stat.get('value', 0) or 0 for stat in team_stats['statistics']}
        passes_percentage = parse_percentage(stats.get('Passes %', '0%'))
        ball_possession = parse_percentage(stats.get('Ball Possession', '0%'))
        statistics.append({
            "match_id": match_id,
            "team_id": team_id,
            "shots_on_goal": stats.get('Shots on Goal', 0),
            "shots_off_goal": stats.get('Shots off Goal', 0),
            "total_shots": stats.get('Total Shots', 0),
            "blocked_shots": stats.get('Blocked Shots', 0),
            "shots_inside_box": stats.get('Shots insidebox', 0),
            "shots_outside_box": stats.get('Shots outsidebox', 0),
            "fouls": stats.get('Fouls', 0),
            "corner_kicks": stats.get('Corner Kicks', 0),
            "offsides": stats.get('Offsides', 0),
            "ball_possession": ball_possession,
            "yellow_cards": stats.get('Yellow Cards', 0),
            "red_cards": stats.get('Red Cards', 0),
            "goalkeeper_saves": stats.get('Goalkeeper Saves', 0),
            "total_passes": stats.get('Total passes', 0),
            "passes_accurate": stats.get('Passes accurate', 0),
            "passes_percentage": passes_percentage,
            "expected_goals": float(stats.get('expected_goals', 0.0) or 0.0),
            "goals_prevented": float(stats.get('goals_prevented', 0.0) or 0.0),
        })
    return statistics

def insert_match_statistics_to_db(statistics: List[Dict]):
    """Insert parsed match statistics into the database."""

    if not statistics:
        return log_warning(logger, "No statistics to insert into the database.")

    query = text("""
        INSERT INTO match_statistics (
            match_id, team_id, shots_on_goal, shots_off_goal, total_shots, blocked_shots,
            shots_inside_box, shots_outside_box, fouls, corner_kicks, offsides, ball_possession,
            yellow_cards, red_cards, goalkeeper_saves, total_passes, passes_accurate, passes_percentage,
            expected_goals, goals_prevented
        ) VALUES (
            :match_id, :team_id, :shots_on_goal, :shots_off_goal, :total_shots, :blocked_shots,
            :shots_inside_box, :shots_outside_box, :fouls, :corner_kicks, :offsides, :ball_possession,
            :yellow_cards, :red_cards, :goalkeeper_saves, :total_passes, :passes_accurate, :passes_percentage,
            :expected_goals, :goals_prevented
        )
        ON DUPLICATE KEY UPDATE
            shots_on_goal = VALUES(shots_on_goal),
            shots_off_goal = VALUES(shots_off_goal),
            total_shots = VALUES(total_shots),
            blocked_shots = VALUES(blocked_shots),
            ball_possession = VALUES(ball_possession),
            yellow_cards = VALUES(yellow_cards),
            red_cards = VALUES(red_cards),
            goalkeeper_saves = VALUES(goalkeeper_saves),
            passes_accurate = VALUES(passes_accurate),
            expected_goals = VALUES(expected_goals);
    """)

    try:
        with SessionLocal() as session:
            session.execute(query, [dict(row) for row in statistics])
            session.commit()
            log_info(logger, f"Successfully inserted/updated {len(statistics)} match statistics.")
    except SQLAlchemyError as e:
        session.rollback()
        log_error(logger, f"Error inserting match statistics into database: {e}")
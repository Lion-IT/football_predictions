import sys
import os

from datetime import datetime
from flask import Blueprint, jsonify
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_connection import SessionLocal
from utils.logging_utils import setup_logger, log_error

# Setup logger for notifications
logger = setup_logger("routes_matches")

matches_blueprint = Blueprint('matches', __name__)

@matches_blueprint.route('/h2h/<int:team1_id>/<int:team2_id>', methods=['GET'])
def get_h2h_matches(team1_id, team2_id):
    query = text("""
        SELECT h2h.*, ht.name AS home_team_name, at.name AS away_team_name
        FROM h2h_matches h2h
        JOIN teams ht ON h2h.home_team_id = ht.team_id
        JOIN teams at ON h2h.away_team_id = at.team_id
        WHERE (h2h.home_team_id = :team1_id AND h2h.away_team_id = :team2_id)
           OR (h2h.home_team_id = :team2_id AND h2h.away_team_id = :team1_id)
        ORDER BY h2h.match_date DESC
    """)

    try:
        with SessionLocal() as session:
            result = session.execute(query, {"team1_id": team1_id, "team2_id": team2_id})
            matches = result.mappings().all()
            formatted_matches = [format_match_data(dict(match)) for match in matches]
            return jsonify(formatted_matches)
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching H2H matches: {e}")
        return jsonify({'error': str(e)}), 500

@matches_blueprint.route('/future_matches', methods=['GET'])
def get_future_matches():
    """
    Pobiera wszystkie mecze zaplanowane na dzisiejszy dzień z tabeli future_matches,
    dołączając szczegóły ligi i przewidywania.
    """
    query = text("""
        SELECT
            fm.*,
            ht.name AS home_team_name,
            at.name AS away_team_name,
            l.name AS league_name,
            l.country AS league_country,
            l.flag_url AS league_flag_url,
            l.logo_url AS league_logo_url,
            l.type AS league_type,
            l.current_season AS league_current_season,
            l.start_date AS league_start_date,
            l.end_date AS league_end_date,
            p.winner_team_id,
            p.winner_name,
            p.advice,
            p.home_win_percent,
            p.draw_percent,
            p.away_win_percent,
            p.goals_home,
            p.goals_away
        FROM future_matches fm
        JOIN teams ht ON fm.home_team_id = ht.team_id
        JOIN teams at ON fm.away_team_id = at.team_id
        JOIN leagues l ON fm.league_id = l.league_id
        LEFT JOIN predictions p ON fm.match_id = p.fixture_id
        WHERE fm.match_date >= NOW() AND fm.match_date < DATE_ADD(NOW(), INTERVAL 1 DAY) AND fm.status IN ('NS')
        ORDER BY fm.match_date ASC
    """)

    try:
        with SessionLocal() as session:
            result = session.execute(query)
            matches = result.mappings().all()
            formatted_matches = [format_future_match_data(dict(match)) for match in matches]
            return jsonify(formatted_matches)
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching future matches: {e}")
        return jsonify({'error': str(e)}), 500

def format_future_match_data(match):
    """Format future match data for frontend."""

    match_date = match.get("match_date")
    if isinstance(match_date, datetime):
        match_date = match_date.strftime('%Y-%m-%d %H:%M:%S')

    return {
        "match_id": match.get("match_id"),
        "league": {
            "id": match.get("league_id"),
            "name": match.get("league_name"),
            "country": match.get("league_country"),
            "flag_url": match.get("league_flag_url"),
            "logo_url": match.get("league_logo_url"),
            "type": match.get("league_type"),
            "current_season": match.get("league_current_season"),
            "start_date": match.get("league_start_date"),
            "end_date": match.get("league_end_date")
        },
        "home_team_id": match.get("home_team_id"),
        "away_team_id": match.get("away_team_id"),
        "home_team_name": match.get("home_team_name"),
        "away_team_name": match.get("away_team_name"),
        "match_date": match_date,
        "stadium": match.get("stadium"),
        "referee": match.get("referee"),
        "weather_conditions": match.get("weather_conditions"),
        "status": match.get("status"),
        "predictions": {
            "winner_team_id": match.get("winner_team_id"),
            "winner_name": match.get("winner_name"),
            "advice": match.get("advice"),
            "home_win_percent": match.get("home_win_percent"),
            "draw_percent": match.get("draw_percent"),
            "away_win_percent": match.get("away_win_percent"),
            "goals_home": match.get("goals_home"),
            "goals_away": match.get("goals_away")
        }
    }

def format_match_data(match):
    """
    Format match data for frontend.
    """
    match_date = match.get("match_date")
    if isinstance(match_date, datetime):
        match_date = match_date.strftime('%Y-%m-%d %H:%M:%S')

    return {
        "id": match.get("id"),
        "fixture_id": match.get("fixture_id"),
        "match_date": match_date,
        "home_team_id": match.get("home_team_id"),
        "home_team_name": match.get("home_team_name"),
        "away_team_id": match.get("away_team_id"),
        "away_team_name": match.get("away_team_name"),
        "score": f"{match.get('home_goals', 0)}-{match.get('away_goals', 0)}",
        "venue": match.get("venue"),
        "referee": match.get("referee"),
        "yellow_cards_home": match.get("yellow_cards_home", 0),
        "yellow_cards_away": match.get("yellow_cards_away", 0),
        "red_cards_home": match.get("red_cards_home", 0),
        "red_cards_away": match.get("red_cards_away", 0),
        "fouls_home": match.get("fouls_home", 0),
        "fouls_away": match.get("fouls_away", 0),
        "winner_team": match.get("winner_team_id")
    }
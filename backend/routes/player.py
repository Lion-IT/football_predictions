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
logger = setup_logger("routes_player")

player_blueprint = Blueprint('player', __name__)

@player_blueprint.route('/<int:player_id>', methods=['GET'])
def get_player_stats(player_id):
    match_query = text("""
        SELECT
            m.match_id,
            m.league_id,
            l.name AS league_name,
            m.date AS match_date,
            m.home_team_id,
            th.name AS home_team_name,
            m.away_team_id,
            ta.name AS away_team_name,
            m.score_home,
            m.score_away,
            CASE
                WHEN m.home_team_id = :team_id AND m.score_home > m.score_away THEN 'win'
                WHEN m.away_team_id = :team_id AND m.score_away > m.score_home THEN 'win'
                WHEN m.score_home = m.score_away THEN 'draw'
                ELSE 'loss'
            END AS corrected_result,

            -- Statystyki meczu
            s.shots_on_goal,
            s.shots_off_goal,
            s.total_shots,
            s.blocked_shots,
            s.shots_inside_box,
            s.shots_outside_box,
            s.fouls,
            s.corner_kicks,
            s.offsides,
            s.ball_possession,
            s.yellow_cards,
            s.red_cards,
            s.goalkeeper_saves,
            s.total_passes,
            s.passes_accurate,
            s.passes_percentage,
            s.expected_goals,
            s.goals_prevented
        FROM matches m
        JOIN match_statistics s ON m.match_id = s.match_id AND s.team_id = :team_id
        JOIN teams th ON m.home_team_id = th.team_id
        JOIN teams ta ON m.away_team_id = ta.team_id
        JOIN leagues l ON m.league_id = l.league_id
        WHERE :team_id IN (m.home_team_id, m.away_team_id)
        ORDER BY m.date DESC
        LIMIT 10;
    """)

    team_query = text("""
        SELECT
            team_id, name AS team_name, country AS team_country,
            logo_url AS team_logo, coach_name AS team_coach,
            home_stadium AS team_stadium, stadium_capacity AS team_stadium_capacity
        FROM teams
        WHERE team_id = :team_id;
    """)

    stats_avg_query = text("""
        SELECT
            ROUND(AVG(s.shots_on_goal), 2) AS avg_shots_on_goal,
            ROUND(AVG(s.shots_off_goal), 2) AS avg_shots_off_goal,
            ROUND(AVG(s.total_shots), 2) AS avg_total_shots,
            ROUND(AVG(s.blocked_shots), 2) AS avg_blocked_shots,
            ROUND(AVG(s.shots_inside_box), 2) AS avg_shots_inside_box,
            ROUND(AVG(s.shots_outside_box), 2) AS avg_shots_outside_box,
            ROUND(AVG(s.fouls), 2) AS avg_fouls,
            ROUND(AVG(s.corner_kicks), 2) AS avg_corner_kicks,
            ROUND(AVG(s.offsides), 2) AS avg_offsides,
            ROUND(AVG(s.ball_possession), 2) AS avg_ball_possession,
            ROUND(AVG(s.yellow_cards), 2) AS avg_yellow_cards,
            ROUND(AVG(s.red_cards), 2) AS avg_red_cards,
            ROUND(AVG(s.goalkeeper_saves), 2) AS avg_goalkeeper_saves,
            ROUND(AVG(s.total_passes), 2) AS avg_total_passes,
            ROUND(AVG(s.passes_accurate), 2) AS avg_passes_accurate,
            ROUND(AVG(s.passes_percentage), 2) AS avg_passes_percentage,
            ROUND(AVG(s.expected_goals), 2) AS avg_expected_goals,
            ROUND(AVG(s.goals_prevented), 2) AS avg_goals_prevented
        FROM matches m
        JOIN match_statistics s ON m.match_id = s.match_id AND s.team_id = :team_id
        WHERE :team_id IN (m.home_team_id, m.away_team_id)
        ORDER BY m.date DESC
        LIMIT 10;
    """)

    try:
        with SessionLocal() as session:
            # Pobranie informacji o drużynie
            team_result = session.execute(team_query, {"team_id": team_id}).mappings().first()
            if not team_result:
                return jsonify({"message": "Team not found"}), 404

            team_info = dict(team_result)

            # Pobranie ostatnich 10 meczów
            result = session.execute(match_query, {"team_id": team_id})
            matches = result.mappings().all()
            last10_matches = [dict(match) for match in matches]

            # Pobranie średnich statystyk
            avg_result = session.execute(stats_avg_query, {"team_id": team_id}).mappings().first()
            stats_average = dict(avg_result) if avg_result else {}

            return jsonify({
                "info": team_info,
                "stats_matches": last10_matches,
                "stats_average": stats_average
            })

    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

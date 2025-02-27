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
logger = setup_logger("routes_team")

team_blueprint = Blueprint('team', __name__)

@team_blueprint.route('/<int:team_id>', methods=['GET'])
def get_team_stats(team_id):
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
        SELECT t.*, ts.*, l.name AS league_name
        FROM teams t
        LEFT JOIN teams_standing ts ON t.team_id = ts.team_id
        LEFT JOIN leagues l ON ts.league_id = l.league_id
        WHERE t.team_id = :team_id
    """)

    stats_avg_query = text("""
        SELECT
            ROUND(AVG(s.shots_on_goal), 1) AS strzaly_celne,
            ROUND(AVG(s.shots_off_goal), 1) AS strzaly_niecelne,
            ROUND(AVG(s.total_shots), 1) AS liczba_strzalow,
            ROUND(AVG(s.blocked_shots), 1) AS zablokowane_strzaly,
            ROUND(AVG(s.shots_inside_box), 1) AS strzaly_w_polu_karnym,
            ROUND(AVG(s.shots_outside_box), 1) AS strzaly_poza_polem_karnym,
            ROUND(AVG(s.fouls), 1) AS faule,
            ROUND(AVG(s.corner_kicks), 1) AS rzuty_rozne,
            ROUND(AVG(s.offsides), 1) AS spalone,
            ROUND(AVG(s.ball_possession), 1) AS posiadanie_pilki,
            ROUND(AVG(s.yellow_cards), 1) AS zolte_kartki,
            ROUND(AVG(s.red_cards), 1) AS czerwone_kartki,
            ROUND(AVG(s.goalkeeper_saves), 1) AS obrony_bramkarza,
            ROUND(AVG(s.total_passes), 1) AS laczna_liczba_podan,
            ROUND(AVG(s.passes_accurate), 1) AS celne_podania,
            ROUND(AVG(s.passes_percentage), 1) AS skutecznosc_podan,
            ROUND(AVG(s.expected_goals), 1) AS oczekiwane_gole,
            ROUND(AVG(s.goals_prevented), 1) AS gole_zapobiegniete

        FROM matches m
        JOIN match_statistics s ON m.match_id = s.match_id AND s.team_id = :team_id
        WHERE :team_id IN (m.home_team_id, m.away_team_id)
        ORDER BY m.date DESC
        LIMIT 10;
    """)

    try:
        with SessionLocal() as session:
                # Pobranie informacji o drużynie (wiele lig)
                team_results = session.execute(team_query, {"team_id": team_id}).mappings().all()
                if not team_results:
                    return jsonify({"message": "Team not found"}), 404

                # Pobranie unikalnych informacji o drużynie
                team_info = {
                    "team_id": team_results[0]["team_id"],
                    "name": team_results[0]["name"],
                    "logo_url": team_results[0]["logo_url"],
                    "country": team_results[0]["country"],
                    "founded": team_results[0]["founded"],
                    "home_stadium": team_results[0]["home_stadium"],
                    "stadium_capacity": team_results[0]["stadium_capacity"],
                    "stadium_city": team_results[0]["stadium_city"],
                    "stadium_surface": team_results[0]["stadium_surface"],
                    "stadium_address": team_results[0]["stadium_address"],
                    "coach_name": team_results[0]["coach_name"],
                    "current_form": team_results[0]["current_form"],
                    "form": team_results[0]["form"],
                    "form_percentage": team_results[0]["form_percentage"],
                    "play_style": team_results[0]["play_style"],
                    "last_data_insert": team_results[0]["last_data_insert"],
                    "leagues": []
                }

                # Pobranie statystyk dla każdej ligi
                for result in team_results:
                    if result["league_id"] and result["league_name"]:
                        team_info["leagues"].append({
                            "league_id": result["league_id"],
                            "league_name": result["league_name"],
                            "season": result["season"],
                            "rank": result["rank"],
                            "points": result["points"],
                            "form": result["form"],
                            "goals_for": result["goals_for"],
                            "goals_against": result["goals_against"],
                            "goals_difference": result["goals_difference"],
                            "home_played": result["home_played"],
                            "home_wins": result["home_wins"],
                            "home_draws": result["home_draws"],
                            "home_losses": result["home_losses"],
                            "home_goals_for": result["home_goals_for"],
                            "home_goals_against": result["home_goals_against"],
                            "away_played": result["away_played"],
                            "away_wins": result["away_wins"],
                            "away_draws": result["away_draws"],
                            "away_losses": result["away_losses"],
                            "away_goals_for": result["away_goals_for"],
                            "away_goals_against": result["away_goals_against"],
                            "status": result["status"],
                            "description": result["description"]
                        })

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
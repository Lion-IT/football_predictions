import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from api.api_requests import get_data
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_error, log_info, log_warning

# Setup logger for notifications
logger = setup_logger("utils_teams_standing")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = 1209600

def fetch_team_standing(team_id, season):
    # Redis cache key
    cache_key = f"team_standing_data:{team_id}:{season}"

    # Check cache in Redis
    cached_data = redis_client.get(cache_key)
    if cached_data:
        log_info(logger, "Dane drużyny pobrane z cache Redis.")
        return json.loads(cached_data)  # Zwracamy od razu

    # Wyszukiwanie danych dla kolejnych sezonów, zaczynając od podanego sezonu
    while True:
        log_info(logger, f"Pobieram dane z API dla drużyny {team_id} na sezon {season}")
        params = {"season": season, "team": team_id}
        data = get_data("standings", params=params)

        if data and 'response' in data and data['response']:
            team = data['response']
            redis_client.setex(cache_key, cache_ttl, json.dumps(team))
            log_info(logger, f"Pełne dane drużyny zapisane w Redis na okres 14 dni (sezon {season})")
            return team
        else:
            log_info(logger, f"Brak danych o drużynie o ID {team_id} na sezon {season}")
            season -= 1  # Zmiana sezonu na poprzedni
            if season < 2020:  # Możemy przyjąć, że nie mamy danych sprzed 1900 roku
                break

    return []  # Zwracamy pustą listę, jeśli nie znaleziono danych w żadnym sezonie

def insert_team_standing_to_db(standings_data):
    """ Wstawia lub aktualizuje dane klasyfikacji drużyn w bazie danych. :param standings_data: Dane z API (może być lista lub pojedynczy słownik) """

    # Sprawdzamy, czy dane są listą, jeśli nie, zamieniamy je na listę
    if not isinstance(standings_data, list):
        standings_data = [standings_data]

    # 🔹 Rozpakowanie listy jeśli mamy dodatkowy poziom zagnieżdżenia
    if isinstance(standings_data[0], list):
        standings_data = standings_data[0]  # Spłaszczamy listę

    rows = []

    for league_data in standings_data:  # Iterujemy po listach lig
        if not isinstance(league_data, dict):  # Upewniamy się, że to słownik
            log_error(logger, f"Nieprawidłowy format danych ligi: {league_data}")
            continue

        league_info = league_data.get("league", {})
        league_id = league_info.get("id")
        season = league_info.get("season")
        teams = league_info.get("standings")

        if not teams or not isinstance(teams, list) or not teams[0]:  # Jeśli brak danych
            log_info(logger, f"Brak danych w klasyfikacji dla ligi ID {league_id}")
            continue

        # Pobranie wszystkich drużyn w tej lidze
        teams = teams[0]

        for team in teams:
            if not isinstance(team, dict):  # Sprawdzamy, czy team to słownik
                log_error(logger, f"Nieprawidłowy format danych drużyny: {team}")
                continue

            row = {
                "league_id": league_id,
                "season": season,
                "team_id": team.get('team', {}).get('id'),
                "rank": team.get('rank'),
                "points": team.get('points'),
                "form": team.get('form', ""),
                "goals_for": team.get('all', {}).get('goals', {}).get('for', 0),
                "goals_against": team.get('all', {}).get('goals', {}).get('against', 0),
                "goals_difference": team.get('goalsDiff', 0),

                "home_played": team.get('home', {}).get('played', 0),
                "home_wins": team.get('home', {}).get('win', 0),
                "home_draws": team.get('home', {}).get('draw', 0),
                "home_losses": team.get('home', {}).get('lose', 0),
                "home_goals_for": team.get('home', {}).get('goals', {}).get('for', 0),
                "home_goals_against": team.get('home', {}).get('goals', {}).get('against', 0),

                "away_played": team.get('away', {}).get('played', 0),
                "away_wins": team.get('away', {}).get('win', 0),
                "away_draws": team.get('away', {}).get('draw', 0),
                "away_losses": team.get('away', {}).get('lose', 0),
                "away_goals_for": team.get('away', {}).get('goals', {}).get('for', 0),
                "away_goals_against": team.get('away', {}).get('goals', {}).get('against', 0),

                "status": team.get("status", "same"),
                "description": team.get("description", "")
            }
            rows.append(row)

    if not rows:
        log_info(logger, "Brak danych do zapisania.")
        return

    query = text("""
        INSERT INTO teams_standing (
            league_id, season, team_id, rank, points, form, goals_for, goals_against,
            goals_difference, home_played, home_wins, home_draws, home_losses, home_goals_for,
            home_goals_against, away_played, away_wins, away_draws, away_losses, away_goals_for,
            away_goals_against, status, description
        )
        VALUES (
            :league_id, :season, :team_id, :rank, :points, :form, :goals_for, :goals_against,
            :goals_difference, :home_played, :home_wins, :home_draws, :home_losses, :home_goals_for,
            :home_goals_against, :away_played, :away_wins, :away_draws, :away_losses, :away_goals_for,
            :away_goals_against, :status, :description
        )
        ON DUPLICATE KEY UPDATE
            rank=VALUES(rank), points=VALUES(points), form=VALUES(form),
            goals_for=VALUES(goals_for), goals_against=VALUES(goals_against),
            goals_difference=VALUES(goals_difference),
            home_played=VALUES(home_played), home_wins=VALUES(home_wins),
            home_draws=VALUES(home_draws), home_losses=VALUES(home_losses),
            home_goals_for=VALUES(home_goals_for), home_goals_against=VALUES(home_goals_against),
            away_played=VALUES(away_played), away_wins=VALUES(away_wins),
            away_draws=VALUES(away_draws), away_losses=VALUES(away_losses),
            away_goals_for=VALUES(away_goals_for), away_goals_against=VALUES(away_goals_against),
            status=VALUES(status), description=VALUES(description)
    """)

    try:
        with SessionLocal() as session:
            session.execute(query, rows)  # Można tu użyć `executemany()`
            session.commit()
            log_info(logger, f"Wstawiono/aktualizowano {len(rows)} rekordów w bazie danych.")
    except SQLAlchemyError as e:
        log_error(logger, f"Błąd podczas wstawiania do bazy: {e}")
        raise
import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.progress_utils import create_progress_bar
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_info, log_error, log_warning
from utils.validation_utils import parse_date_to_local
from utils.match_statistics_utils import fetch_match_statistics

# Load environment variables from .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Setup logger for notifications
logger = setup_logger("h2h_utils")

# Global Redis connection
redis_client = get_redis_connection()

def batch_match_id_exists(match_ids):
    """ Sprawdza wiele meczów naraz za pomocą pojedynczego zapytania SQL. """
    if not match_ids:
        return set()
    query = text("SELECT match_id FROM matches WHERE match_id IN :match_ids")
    with SessionLocal() as session:
        result = session.execute(query, {"match_ids": tuple(match_ids)})
        existing_matches = {row[0] for row in result.fetchall()}
    return existing_matches

def filter_new_matches(h2h_matches, max_workers=8):
    """ Sprawdza, które mecze już są w bazie, wykorzystując równoległe zapytania do bazy. """
    new_matches = []
    chunk_size = max(1, len(h2h_matches) // max_workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = {}
        with create_progress_bar(total=len(h2h_matches), desc="Checking DB for existing matches", unit="match") as pbar:
            for i in range(0, len(h2h_matches), chunk_size):
                chunk = h2h_matches[i:i + chunk_size]
                future = executor.submit(batch_match_id_exists, chunk)
                tasks[future] = chunk
            for future in as_completed(tasks):
                chunk = tasks[future]
                existing_matches = future.result()
                # Każdy mecz w paczce sprawdzamy i aktualizujemy pasek postępu
                for match_id in chunk:
                    if match_id not in existing_matches:
                        new_matches.append(match_id)
                    pbar.update(1)
    return new_matches

def store_h2h_matches(h2h_data: list) -> None:
    """Store head-to-head (H2H) match data and their statistics in the database."""

    if not h2h_data:
        log_warning(logger, "Brak danych H2H do przetworzenia.")
        return

    log_info(logger, f"🔄 Rozpoczynamy przetwarzanie {len(h2h_data)} meczów H2H...")

    records = []
    pbar = create_progress_bar(len(h2h_data), "Przetwarzanie H2H...", "mecz")

    for match in h2h_data:
        try:
            fixture_id = match['fixture']['id']
            home_team_id = match['teams']['home']['id']
            away_team_id = match['teams']['away']['id']

            # Pobranie statystyk dla danego meczu
            stats = fetch_match_statistics(fixture_id)
            if not stats:
                # log_info(logger, f"No statistics available for fixture ID {fixture_id}.")
                pbar.update(1)
                continue

            # Mapowanie statystyk do ID drużyn
            stats_map = {team_stat['team']['id']: team_stat['statistics'] for team_stat in stats}

            # Wyciągnięcie statystyk dla drużyny domowej i wyjazdowej
            home_stats = stats_map.get(home_team_id, [])
            away_stats = stats_map.get(away_team_id, [])

            # Ekstrakcja statystyk
            yellow_cards_home = next((stat['value'] for stat in home_stats if stat['type'] == "Yellow Cards"), 0)
            yellow_cards_away = next((stat['value'] for stat in away_stats if stat['type'] == "Yellow Cards"), 0)
            red_cards_home = next((stat['value'] for stat in home_stats if stat['type'] == "Red Cards"), 0)
            red_cards_away = next((stat['value'] for stat in away_stats if stat['type'] == "Red Cards"), 0)
            fouls_home = next((stat['value'] for stat in home_stats if stat['type'] == "Fouls"), 0)
            fouls_away = next((stat['value'] for stat in away_stats if stat['type'] == "Fouls"), 0)

            match_date = parse_date_to_local(match['fixture']['date'])
            league_id = match['league']['id']
            season = match['league']['season']
            round_name = match['league'].get('round', 'Unknown')
            venue = match['fixture']['venue'].get('name', 'Unknown')
            referee = match['fixture'].get('referee', 'Unknown')
            winner_team_id = home_team_id if match['teams']['home'].get('winner') else away_team_id

            # Statystyki meczu
            home_goals = match['goals'].get('home', 0)
            away_goals = match['goals'].get('away', 0)

            halftime = match['score'].get('halftime', {})
            halftime_home_goals = halftime.get('home', 0)
            halftime_away_goals = halftime.get('away', 0)
            halftime_home_goals = 0 if halftime_home_goals is None else halftime_home_goals
            halftime_away_goals = 0 if halftime_away_goals is None else halftime_away_goals

            fulltime = match['score'].get('fulltime', {})
            fulltime_home_goals = fulltime.get('home', 0)
            fulltime_away_goals = fulltime.get('away', 0)
            fulltime_home_goals = 0 if fulltime_home_goals is None else fulltime_home_goals
            fulltime_away_goals = 0 if fulltime_away_goals is None else fulltime_away_goals

            extratime = match['score'].get('extratime', {})
            extratime_home_goals = extratime.get('home', 0)
            extratime_away_goals = extratime.get('away', 0)
            extratime_home_goals = 0 if extratime_home_goals is None else extratime_home_goals
            extratime_away_goals = 0 if extratime_away_goals is None else extratime_away_goals

            penalty = match['score'].get('penalty', {})
            penalty_home_goals = penalty.get('home', 0)
            penalty_away_goals = penalty.get('away', 0)
            penalty_home_goals = 0 if penalty_home_goals is None else penalty_home_goals
            penalty_away_goals = 0 if penalty_away_goals is None else penalty_away_goals

            records.append({
                "fixture_id": fixture_id,
                "league_id": league_id,
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "match_date": match_date,
                "season": season,
                "round": round_name,
                "venue": venue,
                "referee": referee,
                "winner_team_id": winner_team_id,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "halftime_home_goals": halftime_home_goals,
                "halftime_away_goals": halftime_away_goals,
                "fulltime_home_goals": fulltime_home_goals,
                "fulltime_away_goals": fulltime_away_goals,
                "extratime_home_goals": extratime_home_goals,
                "extratime_away_goals": extratime_away_goals,
                "penalty_home_goals": penalty_home_goals,
                "penalty_away_goals": penalty_away_goals,
                "yellow_cards_home": yellow_cards_home,
                "yellow_cards_away": yellow_cards_away,
                "red_cards_home": red_cards_home,
                "red_cards_away": red_cards_away,
                "fouls_home": fouls_home,
                "fouls_away": fouls_away,
            })
        except KeyError as e:
            log_error(logger, f"KeyError while processing H2H match data for fixture ID {fixture_id}: {e}")
        except Exception as e:
            log_error(logger, f"Unexpected error while processing H2H match data: {e}")

        pbar.update(1)
    pbar.close()

    if records:
        query = text("""
            INSERT INTO h2h_matches (
                fixture_id, league_id, home_team_id, away_team_id, match_date, season, round, venue, referee,
                winner_team_id, home_goals, away_goals, halftime_home_goals, halftime_away_goals, fulltime_home_goals, fulltime_away_goals,
                extratime_home_goals, extratime_away_goals, penalty_home_goals, penalty_away_goals, yellow_cards_home, yellow_cards_away,
                red_cards_home, red_cards_away, fouls_home, fouls_away
            )
            VALUES (
                :fixture_id, :league_id, :home_team_id, :away_team_id, :match_date, :season, :round, :venue, :referee,
                :winner_team_id, :home_goals, :away_goals, :halftime_home_goals, :halftime_away_goals, :fulltime_home_goals, :fulltime_away_goals,
                :extratime_home_goals, :extratime_away_goals, :penalty_home_goals, :penalty_away_goals, :yellow_cards_home, :yellow_cards_away,
                :red_cards_home, :red_cards_away, :fouls_home, :fouls_away
            )
            ON DUPLICATE KEY UPDATE
                home_goals = VALUES(home_goals), away_goals = VALUES(away_goals),
                halftime_home_goals = VALUES(halftime_home_goals), halftime_away_goals = VALUES(halftime_away_goals),
                fulltime_home_goals = VALUES(fulltime_home_goals), fulltime_away_goals = VALUES(fulltime_away_goals),
                extratime_home_goals = VALUES(extratime_home_goals), extratime_away_goals = VALUES(extratime_away_goals),
                penalty_home_goals = VALUES(penalty_home_goals), penalty_away_goals = VALUES(penalty_away_goals),
                yellow_cards_home = VALUES(yellow_cards_home), yellow_cards_away = VALUES(yellow_cards_away),
                red_cards_home = VALUES(red_cards_home), red_cards_away = VALUES(red_cards_away),
                fouls_home = VALUES(fouls_home), fouls_away = VALUES(fouls_away);
        """)

        try:
            with SessionLocal() as session:
                session.execute(query, records)
                session.commit()
                log_info(logger, f"Inserted/updated {len(records)} H2H matches into the database.")
        except SQLAlchemyError as e:
            log_error(logger, f"Error inserting H2H matches into database: {e}")
import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import text

from api.api_requests import get_data
from utils.progress_utils import create_progress_bar
from config.db_connection import get_redis_connection, SessionLocal
from utils.logging_utils import setup_logger, log_error, log_info, log_warning

# Setup logger for notifications
logger = setup_logger("players_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = 15552000

def fetch_players_data(team_id: int, season: int) -> list:
    """
    Fetch player data for a specific team and season.

    :param team_id: ID of the team
    :param season: Season year (e.g., 2023)
    :return: List of player dictionaries
    """
    try:
        players_endpoint = "players"
        players_params = {"team": team_id, "season": season}
        players_response = get_data(players_endpoint, params=players_params)

        if not players_response or 'response' not in players_response:
            log_error(logger, f"Invalid API response structure for team_id={team_id}, season={season}: {players_response}")
            return []

        return players_response['response'] if 'response' in players_response else []
    except Exception as e:
        log_error(logger, f"Error fetching players data for team {team_id}: {e}")
        return []

def prepare_player_data(players_data: list) -> list:
    """
    Prepare player data for insertion into the database.
    :param players_data: List of player dictionaries
    :return: List of dictionaries ready for database insertion
    """
    rows = []
    for entry in players_data:
        player = entry.get('player', {})
        if not player or 'id' not in player or 'name' not in player:
            log_error(logger, f"Invalid player data structure: {entry}")
            continue

        rows.append({
            "player_id": player.get('id'),
            "name": player.get('name'),
            "firstname": player.get('firstname'),
            "lastname": player.get('lastname'),
            "age": player.get('age'),
            "birth_date": player.get('birth', {}).get('date'),
            "birth_place": player.get('birth', {}).get('place'),
            "birth_country": player.get('birth', {}).get('country'),
            "nationality": player.get('nationality'),
            "height": player.get('height'),
            "weight": player.get('weight'),
            "injured": int(player.get('injured', False)),
            "photo": player.get('photo')
        })

    return rows

def fetch_and_insert_player(player_id: int, season: int) -> None:
    """ Pobiera zawodnika/zawodników na podstawie pojedynczego player_id """

    if player_id:
        log_info(logger, f"Fetching missing player ID: {player_id}")
        player_response = get_data("players", params={"id": player_id, "season": season})
        if not player_response or 'response' not in player_response:
            log_error(logger, f"Invalid API response for player ID {player_id}: {player_response}")
            return
        player_data = player_response['response']

    if not player_data:
        log_error(logger, "Brak danych zawodników do wstawienia do bazy.")
        return

    row = prepare_player_data(player_data)
    query = text("""
        INSERT INTO players (
            player_id, name, firstname, lastname, age, birth_date, birth_place,
            birth_country, nationality, height, weight, injured, photo
        )
        VALUES (
            :player_id, :name, :firstname, :lastname, :age, :birth_date, :birth_place,
            :birth_country, :nationality, :height, :weight, :injured, :photo
        )
        ON DUPLICATE KEY UPDATE
            name=VALUES(name), firstname=VALUES(firstname), lastname=VALUES(lastname),
            age=VALUES(age), birth_date=VALUES(birth_date), birth_place=VALUES(birth_place),
            birth_country=VALUES(birth_country), nationality=VALUES(nationality),
            height=VALUES(height), weight=VALUES(weight), injured=VALUES(injured),
            photo=VALUES(photo);
    """)
    try:
        with SessionLocal() as session:
            session.execute(query, row)
            session.commit()
            log_info(logger, f"Pomyślnie zapisano zawodnika {player_id} do bazy danych.")
    except SQLAlchemyError as e:
        log_error(logger, f"Error inserting data into database: {e}")

def fetch_and_insert_players(team_id: int, season: int) -> None:
    """
    Fetches player data for a specific team and season, caches it in Redis, and inserts it into the database.
    :param team_id: ID of the team
    :param season: Season year (e.g., 2023)
    """
    # Validate inputs
    if not isinstance(team_id, int) or not isinstance(season, int):
        log_error(logger, f"Invalid input types: team_id={team_id}, season={season}. Expected integers.")
        return

    try:
        # Redis key generation
        redis_key = f"players_data:team:{team_id}:season:{season}"

        # Check if data is in Redis cache
        cached_data = redis_client.get(redis_key)
        if cached_data:
            log_info(logger, f"Dane zawodników znalezione w Redis dla klucza: {redis_key}")
            try:
                players_data = json.loads(cached_data)
            except json.JSONDecodeError as e:
                log_error(logger, f"Error decoding Redis data: {e}")
                players_data = []
        else:
            log_info(logger, f"Dane zawodników nie znalezione w Redis. Pobieranie z API...")
            initial_response = get_data("players", params={"team": team_id, "season": season})

            if not initial_response or 'response' not in initial_response:
                log_error(logger, f"Invalid API response structure for team_id={team_id}, season={season}: {initial_response}")
                return

            total_pages = initial_response.get('paging', {}).get('total', 1)
            players_data = []

            with create_progress_bar(total=total_pages, desc="Fetching players data") as pbar:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    def fetch_page(page):
                        try:
                            players_params = {"team": team_id, "season": season, "page": page}
                            response = get_data("players", params=players_params)
                            if pbar:
                                pbar.update(1)
                            return response['response'] if 'response' in response else []
                        except Exception as e:
                            log_error(logger, f"Error fetching page {page}: {e}")
                            return []

                    pages = list(executor.map(fetch_page, range(1, total_pages + 1)))
                # Flatten the list of players from all pages
                players_data = [player for page_data in pages for player in page_data]

            if players_data:
                redis_client.setex(redis_key, cache_ttl, json.dumps(players_data))
                log_info(logger, f"Dane zawodników zapisane w Redis dla klucza: {redis_key}")
            else:
                log_error(logger, f"Nie udało się pobrać danych zawodników dla team_id={team_id}, season={season}")
                return

        # Prepare data for database insertion
        if not players_data:
            log_error(logger, f"No players data found for team_id={team_id}, season={season}")
            return

        log_info(logger, f"Preparing data for {len(players_data)} players...")
        rows = prepare_player_data(players_data)
        log_info(logger, f"Prepared {len(rows)} rows for database insertion.")

        # Insert data into the database using SQLAlchemy
        query = text("""
            INSERT INTO players (
                player_id, name, firstname, lastname, age, birth_date, birth_place,
                birth_country, nationality, height, weight, injured, photo
            )
            VALUES (
                :player_id, :name, :firstname, :lastname, :age, :birth_date, :birth_place,
                :birth_country, :nationality, :height, :weight, :injured, :photo
            )
            ON DUPLICATE KEY UPDATE
                name=VALUES(name), firstname=VALUES(firstname), lastname=VALUES(lastname),
                age=VALUES(age), birth_date=VALUES(birth_date), birth_place=VALUES(birth_place),
                birth_country=VALUES(birth_country), nationality=VALUES(nationality),
                height=VALUES(height), weight=VALUES(weight), injured=VALUES(injured),
                photo=VALUES(photo);
        """)

        try:
            with SessionLocal() as session:
                session.execute(query, rows)
                session.commit()
                log_info(logger, f"Pomyślnie zapisano dane zawodników do bazy danych dla team_id {team_id}, season {season}")
        except SQLAlchemyError as e:
            log_error(logger, f"Error inserting data into database: {e}")
            raise

    except Exception as e:
        log_error(logger, f"Błąd w fetch_and_insert_players: {e}")
import sys
import os
import json
import datetime

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
logger = setup_logger("teams_utils")

# Global Redis connection
redis_client = get_redis_connection()
cache_ttl = 15552000

def get_all_teams_from_db():
    """
    Pobiera wszystkie ID drużyn z tabeli teams i zwraca je jako listę.
    Returns:
        List[int]: Lista team_id
    """
    query = text("SELECT team_id FROM teams")

    try:
        with SessionLocal() as session:
            teams = session.execute(query).fetchall()
            return [team[0] for team in teams]  # Pobieramy tylko pierwszą wartość z krotki (team_id)
    except SQLAlchemyError as e:
        log_error(logger, f"❌ Błąd pobierania drużyn z bazy: {e}")
        return []

def check_season_has_fixtures(team_id: int, season: int):
    """Sprawdza, czy dla danego zespołu i sezonu są dostępne rozegrane mecze"""
    fixtures_endpoint = "fixtures"
    fixtures_params = {"team": team_id, "season": season, "last": 5}
    fixtures_response = get_data(fixtures_endpoint, params=fixtures_params)

    if fixtures_response and 'response' in fixtures_response and fixtures_response['response']:
        return True
    return False

def get_latest_team_season(team_id: int):
    try:
        team_endpoint = "teams/seasons"
        team_params = {"team": team_id}
        team_response = get_data(team_endpoint, params=team_params)
        if not team_response or 'response' not in team_response or not team_response['response']:
            log_error(logger, f"No season data found for team {team_id}")
            return None
        # Pobieramy sezony i sortujemy malejąco (najwyższy najpierw)
        seasons = sorted(team_response['response'], reverse=True)
        for season in seasons:
            if check_season_has_fixtures(team_id, season):
                return season
        log_error(logger, f"No available seasons with fixtures for team {team_id}")
        return None
    except Exception as e:
        log_error(logger, f"Error processing team season data: {e}")
        return None

def get_teams_name():
    """
    Get teams name from table teams
    Returns:
        List of dictionaries with team_id and name
    """
    query = "SELECT team_id, name FROM teams"

    try:
        with SessionLocal() as session:
            teams = session.execute(text(query)).fetchall()
            return [dict(team._asdict()) for team in teams]
    except SQLAlchemyError as e:
        log_error(logger, f"Error fetching available teams: {e}")
        return []

def check_missing_teams(team_ids, league_id, season):
    """Check if all team IDs exist in the 'teams' table and log missing teams."""

    if not team_ids:
        return {}, []
    placeholders = ", ".join([f":id_{i}" for i in range(len(team_ids))])
    query = f"SELECT team_id, name FROM teams WHERE team_id IN ({placeholders})"

    try:
        with SessionLocal() as session:
            params = {f"id_{i}": team_id for i, team_id in enumerate(team_ids)}
            existing_teams = {
                row[0]: row[1]
                for row in session.execute(text(query), params).fetchall()
            }
            missing_team_ids = set(team_ids) - set(existing_teams.keys())
            if missing_team_ids:
                log_warning(logger, f"Brakujące drużyny w bazie danych: {missing_team_ids}")
                fetch_and_insert_teams(league_id=league_id, season=season)

            return existing_teams, list(missing_team_ids)
    except SQLAlchemyError as e:
        log_error(logger, f"Error checking missing teams: {e}")
        return {}, []

def fetch_team_data(team, season, current_form=5, pbar=None):
    try:
        team_data = team['team']

        # Fetch coach data
        coach_name = None
        coach_endpoint = "coachs"
        coach_params = {"team": team_data['id']}
        coach_response = get_data(coach_endpoint, params=coach_params)

        if coach_response and 'response' in coach_response and coach_response['response']:
            current_date = datetime.date.today()
            latest_start = datetime.date.min
            last_coach = None

            for coach in coach_response['response']:
                for career in coach.get("career", []):
                    if career["team"]["id"] == team_data['id'] and career["end"] is None:
                        start_date = datetime.datetime.strptime(career["start"], "%Y-%m-%d").date()
                        if start_date <= current_date and start_date > latest_start:
                            latest_start = start_date
                            last_coach = coach
            if last_coach:
                coach_name = last_coach.get("name", None)

        if pbar:
            pbar.update(1)  # Update progress bar after fetching coach data

        # Fetch current form (last 5 matches)
        fixtures_endpoint = "fixtures"
        fixtures_params = {"team": team_data['id'], "season": season, "last": current_form}
        fixtures_response = get_data(fixtures_endpoint, params=fixtures_params)
        current_form = "W0-D0-L0"
        form_percentage = 0
        if fixtures_response and 'response' in fixtures_response and fixtures_response['response']:
            last_matches = fixtures_response['response']
            results = []
            for match in last_matches:
                if match['teams']['home']['id'] == team_data['id']:
                    results.append(match['teams']['home']['winner'])
                else:
                    results.append(match['teams']['away']['winner'])

            wins = results.count(True)
            losses = results.count(False)
            draws = results.count(None)

            # Calculate form percentage
            form_percentage = (wins * 20) + (draws * 10)
            current_form = f"W{wins}-D{draws}-L{losses}"

        if pbar:
            pbar.update(1) # Update progress bar after fetching form data

        # Add processed data to team object
        team['coach_name'] = coach_name
        team['current_form'] = current_form
        team['form_percentage'] = form_percentage

        if pbar:
            pbar.update(1)  # Update progress bar after final processing

        return team
    except Exception as e:
        log_error(logger, f"Error processing team data: {e}")
        return None

def fetch_and_insert_team(team_id, season):
    """
    Fetches and processes detailed team data for a specific team ID and season,
    then inserts it into the database.

    :param team_id: ID of the team
    :param season: Season year (e.g., 2023)
    """
    # Redis cache key
    cache_key = f"team_full_data:{team_id}:{season}"

    # Check cache in Redis
    cached_data = redis_client.get(cache_key)
    if cached_data:
        log_info(logger, "Dane drużyny pobrane z cache Redis.")
        team = json.loads(cached_data)
    else:
        # Fetch team data from API
        log_info(logger, f"Pobieram dane z API dla drużyny {team_id}")
        params = {"id": team_id}
        data = get_data("teams", params=params)
        if not data or 'response' not in data:
            log_info(logger, f"Brak danych o drużynie o ID {team_id}")
            print(f"Brak danych o drużynie o ID {team_id}")
            return []

        # Extract single team data
        team = data['response'][0] if data['response'] else None
        if not team:
            log_warning(logger, f"Nie znaleziono danych dla drużyny o ID {team_id}.")
            return []

        # Use fetch_team_data to process additional details
        team = fetch_team_data(team, season, current_form=5)
        if not team:
            log_warning(logger, f"Nie udało się przetworzyć danych dla drużyny o ID {team_id}.")
            return []

        # Store full data in Redis for 1 day
        redis_client.setex(cache_key, 86400, json.dumps(team))
        log_info(logger, "Pełne dane drużyny zapisane w Redis na okres 1 dnia")

    # Prepare data for database insertion
    insert_teams_to_db([team])

    # Return the team ID for further processing
    return team_id

def fetch_and_insert_teams(league_id, season):
    """
    Fetches team data for a specific league and season, validates it, and inserts it into the database.

    :param league_id: ID of the league
    :param season: Season year (e.g., 2023)
    """
    # Redis cache key
    cache_key = f"teams_full_data:{league_id}:{season}"

    # Check cache in Redis
    cached_data = redis_client.get(cache_key)
    if cached_data:
        log_info(logger, "Dane drużyn pobrane z cache Redis.")
        teams = json.loads(cached_data)
    else:
        # Fetch basic team data from API
        log_info(logger, "Pobieram dane z API...")
        params = {"league": league_id, "season": season}
        data = get_data("teams", params=params)
        if not data or 'response' not in data:
            log_info(logger, "Brak danych o drużynach")
            print(logger, "Brak danych o drużynach")
            return []

        teams = data['response']

        # Tworzenie paska postępu
        with create_progress_bar(total=len(teams) * 3, desc="Processing team data", unit="steps") as pbar:
            with ThreadPoolExecutor(max_workers=4) as executor:
                teams = list(executor.map(lambda t: fetch_team_data(t, season, pbar=pbar), teams))

        # Store full data in Redis for 30 days
        redis_client.setex(cache_key, cache_ttl, json.dumps(teams))
        log_info(logger, "Pełne dane drużyn zapisane w Redis.")

    # Insert to database
    insert_teams_to_db(teams)

    # Extract and return Team IDs
    try:
        team_ids = [team['team']['id'] for team in teams if 'team' in team and 'id' in team['team']]
        return team_ids
    except KeyError as e:
        log_error(logger, f"Error extracting team IDs: {e}")
        return []

def insert_teams_to_db(teams):
    """
    Inserts or updates team data into the database.
    :param teams: List of team dictionaries with processed data
    """
    # Prepare data for database insertion
    rows = [
        {
            "team_id": team['team']['id'],
            "name": team['team']['name'],
            "country": team['team']['country'],
            "founded": team['team'].get('founded', None),
            "logo_url": team['team'].get('logo', None),
            "home_stadium": team['venue'].get('name', None),
            "stadium_capacity": team['venue'].get('capacity', None),
            "stadium_address": team['venue'].get('address', None),
            "stadium_city": team['venue'].get('city', None),
            "stadium_surface": team['venue'].get('surface', None),
            "stadium_image": team['venue'].get('image', None),
            "coach_name": team.get('coach_name', None),
            "current_form": team.get('current_form', None),
            "form_percentage": team.get('form_percentage', None)
        }
        for team in teams if 'team' in team and 'id' in team['team']
    ]

    query = text("""
        INSERT INTO teams (
            team_id, name, country, founded, logo_url, home_stadium, stadium_capacity,
            stadium_address, stadium_city, stadium_surface, stadium_image, coach_name, current_form, form_percentage, last_data_insert
        )
        VALUES (
            :team_id, :name, :country, :founded, :logo_url, :home_stadium, :stadium_capacity,
            :stadium_address, :stadium_city, :stadium_surface, :stadium_image, :coach_name, :current_form, :form_percentage, NOW()
        )
        ON DUPLICATE KEY UPDATE
            name=VALUES(name), country=VALUES(country), founded=VALUES(founded),
            logo_url=VALUES(logo_url), home_stadium=VALUES(home_stadium),
            stadium_capacity=VALUES(stadium_capacity), stadium_address=VALUES(stadium_address),
            stadium_city=VALUES(stadium_city), stadium_surface=VALUES(stadium_surface),
            stadium_image=VALUES(stadium_image), coach_name=VALUES(coach_name),
            current_form=VALUES(current_form), form_percentage=VALUES(form_percentage), last_data_insert=NOW()
    """)

    try:
        with SessionLocal() as session:
            session.execute(query, rows)
            session.commit()
            log_info(logger, f"Attempted to insert/update {len(rows)} rows in total.")
    except SQLAlchemyError as e:
        log_error(logger, f"Error inserting data into database: {e}")
        raise
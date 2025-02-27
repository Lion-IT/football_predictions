import os
import sys

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logging_utils import setup_logger, log_info, log_warning
from utils.progress_utils import create_progress_bar
from utils.notification_utils import send_batch_notifications
from utils.special_football_functions import fetch_team_ids_from_db, fetch_available_matches
from utils.match_statistics_utils import fetch_match_statistics, parse_match_statistics, insert_match_statistics_to_db
from utils.match_utils import fetch_matches_for_team, insert_matches_to_db, match_id_exists
from utils.teams_utils import get_teams_name, get_latest_team_season
from utils.match_events_utils import run_all_proccess_event_match
from utils.players_utils import fetch_and_insert_players

# Initialize logger
logger = setup_logger("etl_matches_all_data")

def run():
    while True:
        retry = False

        # Pobierz wszystkie dostępne mecze
        available_matches = fetch_available_matches()
        if not available_matches:
            log_warning(logger, "Brak dostępnych meczów do analizy. Spróbuj pobrać nowe mecze na dany dzień! [etl_future_matches]")
            print("Brak dostępnych meczów do analizy. Spróbuj pobrać nowe mecze na dany dzień! [etl_future_matches]")
            return

        # Pobierz dane drużyn z bazy danych
        all_teams = get_teams_name()
        team_mapping = {team['team_id']: team['name'] for team in all_teams}

        # Wyświetl mecze z nazwami drużyn
        for idx, match in enumerate(available_matches):
            home_team_name = team_mapping.get(match['home_team_id'], f"Unknown Team ({match['home_team_id']})")
            away_team_name = team_mapping.get(match['away_team_id'], f"Unknown Team ({match['away_team_id']})")
            print(f"{idx + 1}. ID Meczu: {match['match_id']} | {home_team_name} vs {away_team_name} | Data meczu: {match['match_date']}")

        # Przetwarzaj każdy mecz
        for selected_match in available_matches:
            match_id = selected_match['match_id']
            # Pobierz drużyny powiązane z meczem
            team_data = fetch_team_ids_from_db(match_id)
            if not team_data['teams']:
                log_warning(logger, f"Nie znaleziono drużyn dla meczu {match_id}. Nieznane drużyny: {team_data['missing_teams']}")
                # Tutaj wstawic pobieranie druzyn jesli nie znajdzie ich w bazie
                continue
            else:
                # Wyświetl drużyny dla analizy
                print(f"Przetwarzanie meczu {match_id}:")
                for team in team_data['teams']:
                    print(f"ID: {team['team_id']}, Nazwa: {team['name']}")
                    log_info(logger, f"ID: {team['team_id']}, Nazwa: {team['name']}")
                    # Pobierz i wstaw ostatnie mecze drużyny
                    last_matches = fetch_matches_for_team(team['team_id'], 10)
                    # last_season = get_latest_team_season(team['team_id'])
                    # fetch_and_insert_players(team['team_id'], last_season)

                    if last_matches:
                        try:
                            insert_matches_to_db(last_matches)
                        except Exception as e:
                            log_warning(logger, f"Błąd podczas wstawiania meczu: {e}")

                        # Pobierz szczegółowe statystyki dla meczu
                        progress_bar = create_progress_bar(len(last_matches), "Przetwarzanie meczów...", unit="mecz")
                        for match in last_matches:
                            match_id = match['fixture']['id']
                            run_all_proccess_event_match(match_id)
                            if match_id_exists(match_id):
                                match_statistics = fetch_match_statistics(match_id)
                                if match_statistics:
                                    parsed_statistics = parse_match_statistics(match_id, match_statistics)
                                    insert_match_statistics_to_db(parsed_statistics)
                                    log_info(logger, f"Statystyki meczu {match_id} zostały zapisane w bazie.")
                                else:
                                    log_warning(logger, f"Nie udało się pobrać szczegółowych statystyk dla meczu {match_id}.")
                            else:
                                log_warning(logger, f"Mecz {match_id} nie istnieje w tabeli `matches`. Pomijanie statystyk.")
                            # Zwiększamy progress bar
                            progress_bar.update(1)
                        # Zamykamy progress bar po zakończeniu pętli
                        progress_bar.close()

        if not retry:
            break  # Zakończ pętlę, jeśli nie trzeba ponownie uruchamiać procesu

    # Send email notifications
    send_batch_notifications()

if __name__ == "__main__":
    run()

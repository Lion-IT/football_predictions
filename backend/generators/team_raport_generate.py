import requests
import os
import sys
import time
import json

from html import escape
from dotenv import load_dotenv
from datetime import datetime

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

from utils.logging_utils import setup_logger, log_info, log_error, log_warning

API_URL = "http://10.0.0.8:53502/api/team/{team_id}"
OUTPUT_DIR = os.path.abspath(os.path.join("Football/frontend/public/team/"))

# Konfiguracja logowania
logger = setup_logger("team_report_generate")

def fetch_data(api_url, retries=5, delay=5):
    """ Pobiera dane z API i ponawia próbę w przypadku błędu 500. """
    for attempt in range(retries):
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 500:
                log_warning(logger, f"API zwróciło 500. Próba ponowna za {delay} sek. (Podejście {attempt+1}/{retries})")
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log_error(logger, f"Błąd pobierania danych z API: {e}")
            time.sleep(delay)

    log_error(logger, f"API nie odpowiedziało poprawnie po {retries} próbach.")
    return None

def generate_team_html(data):
    """Generuje raport HTML dla danej drużyny."""

    team_info = data.get("info", {})
    team_info_lagues = team_info.get("leagues", [])
    stats_average = data.get("stats_average", {})
    last10_matches = data.get("stats_matches", [])

    team_name = team_info.get("name", "Brak danych")
    country = team_info.get("country", "Brak danych")
    logo_url = team_info.get("logo_url", "")
    coach = team_info.get("coach_name", "Brak danych")
    stadium = team_info.get("home_stadium", "Brak danych")
    stadium_city = team_info.get("stadium_city", "Brak danych")
    stadium_capacity = team_info.get("stadium_capacity", "Brak danych")
    current_form = team_info.get("current_form", "Brak danych")
    form_percentage = team_info.get("form_percentage", "Brak danych")

    html_report = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Raport drużyny {team_name}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                padding: 20px;
            }}
            .container {{
                margin: auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0px 0px 10px #ccc;
            }}
            h1 {{
                text-align: center;
                font-size: 28px;
            }}
            .team-info {{
                display: flex;
                align-items: center;
                gap: 20px;
                border-bottom: 2px solid #ddd;
                padding-bottom: 15px;
            }}
            .team-info img {{
                width: 100px;
                display: block;
            }}
            .stadium-info {{
                display: flex;
                align-items: center;
                gap: 20px;
                margin-top: 15px;
            }}
            .stadium-info img {{
                width: 220px;
                border-radius: 10px;
            }}
            .stats {{
                margin-top: 20px;
            }}
            .table-container {{
                overflow-x: auto;
            }}
            .matches-table, .stats-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .matches-table th, .matches-table td, .stats-table th, .stats-table td {{
                padding: 10px;
                border: 1px solid #ddd;
                text-align: center;
            }}
            .matches-table thead, .stats-table thead {{
                background-color: #007bff;
                color: white;
            }}
            .matches-table tbody tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
            .matches-table tbody tr:hover {{
                background-color: #f1f1f1;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{team_name}</h1>

            <div class="team-info">
                <img src="{logo_url}" alt="{team_name}">
                <div>
                    <p><strong>🏳️ Kraj:</strong> {country}</p>
                    <p><strong>👔 Trener:</strong> {coach}</p>
                    <p><strong>🔥 Forma:</strong> {form_percentage}% ({current_form})</p>
                </div>
            </div>

            <div class="stadium-info">
                <p><strong>🏟️ Stadion:</strong> {stadium} - {stadium_city} (Pojemność: {stadium_capacity})</p>
            </div>

            <div class="stats">
                <h2>📊 Średnie statystyki z ostatnich 10 meczów</h2>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>Statystyka</th>
                            <th>Średnia wartość</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for key, value in stats_average.items():
        html_report += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"

    html_report += """
                    </tbody>
                </table>
            </div>

            <div class="table-container">
                <h2>📅 Ostatnie 10 meczów</h2>
                <table class="matches-table">
                    <thead>
                        <tr>
                            <th>📆 Data</th>
                            <th>🤝 Przeciwnik</th>
                            <th>⚽ Wynik</th>
                            <th>🏆 Rezultat</th>
                            <th>🔥 Posiadanie (%)</th>
                            <th>🎯 Celne</th>
                            <th>🛑 Niecelne</th>
                            <th>💪 Zablokowane</th>
                            <th>🚀 Strzały</th>
                            <th>🥅 Rożne</th>
                            <th>🟨 kartki</th>
                            <th>🟥 kartki</th>
                            <th>🤕 Faule</th>
                            <th>🎭 Spalone</th>
                        </tr>
                    </thead>
                    <tbody>
    """

    for match in last10_matches:

        date_str = match.get("match_date", "Brak")
        if date_str != "Brak":
            date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT").strftime("%d.%m.%Y")
        else:
            date = "Brak"
        opponent = match["away_team_name"] if match["home_team_id"] == team_info["team_id"] else match["home_team_name"]
        score = f"{match.get('score_home', 0)} - {match.get('score_away', 0)}"
        result = match.get("corrected_result", "N/A")
        possession = match.get("ball_possession", "N/A")
        shots_on_goal = match.get("shots_on_goal", "N/A")
        shots_off_goal = match.get("shots_off_goal", "N/A")
        blocked_shots = match.get("blocked_shots", "N/A")
        total_shots = match.get("total_shots", "N/A")
        corners = match.get("corner_kicks", "N/A")
        fouls = match.get("fouls", "N/A")
        yellow_cards = match.get("yellow_cards", "N/A")
        red_cards = match.get("red_cards", "N/A")
        offsides = match.get("offsides", "N/A")

        html_report += f"""
                        <tr>
                            <td>{date}</td>
                            <td>{opponent}</td>
                            <td>{score}</td>
                            <td>{result}</td>
                            <td>{possession}</td>
                            <td>{shots_on_goal}</td>
                            <td>{shots_off_goal}</td>
                            <td>{blocked_shots}</td>
                            <td>{total_shots}</td>
                            <td>{corners}</td>
                            <td>{yellow_cards}</td>
                            <td>{red_cards}</td>
                            <td>{fouls}</td>
                            <td>{offsides}</td>
                        </tr>
        """

    html_report += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return html_report

def save_html_report(team_id, html_content):
    """Zapisuje wygenerowany raport HTML do pliku."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    file_path = os.path.join(OUTPUT_DIR, f"{team_id}.html")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(html_content)

    log_info(logger, f"Raport HTML zapisany: {file_path}")
    return file_path

def generate_team_report(team_id):
    """Generuje raport HTML dla danej drużyny na podstawie API."""
    api_url = API_URL.format(team_id=team_id)
    data = fetch_data(api_url)

    if not data:
        log_error(logger, f"Nie udało się pobrać danych dla drużyny ID {team_id}.")
        return None

    html_content = generate_team_html(data)
    file_path = save_html_report(team_id, html_content)
    return file_path

def run():
    team_id = int(input("Enter the Team ID: "))
    report_path = generate_team_report(team_id)
    if report_path:
        print(f"Raport wygenerowany: {report_path}")

if __name__ == "__main__":
    run()
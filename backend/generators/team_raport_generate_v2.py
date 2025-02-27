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
logger = setup_logger("team_report_generate_v2")

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
    last_update = team_info.get("last_data_insert", "Brak danych")

    html_report = f"""
         <!DOCTYPE html>
            <html lang="pl">
                <head>
                  <meta charset="UTF-8">
                  <title>Dashboard - Barcelona</title>
                      <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        * {{
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }}

                        body {{
                            font-family: Arial, sans-serif;
                            background-color: #f4f6f8;
                            color: #333;
                            line-height: 1.6;
                        }}

                        a {{
                            text-decoration: none;
                            color: inherit;
                        }}

                        /* Nagłówek */
                        .header {{
                            background-color: #003366;
                            color: #fff;
                            padding: 20px;
                            text-align: center;
                            position: relative;
                        }}

                        .header img.team-logo {{
                            width: 80px;
                            height: auto;
                            vertical-align: middle;
                        }}

                        .header h1 {{
                            display: inline-block;
                            margin-left: 10px;
                            font-size: 2rem;
                            vertical-align: middle;
                        }}

                        .last-update {{
                            display: block;
                            font-size: 0.9rem;
                            margin-top: 5px;
                        }}

                        .menu {{
                            margin-top: 10px;
                        }}

                        .menu ul {{
                            list-style: none;
                            display: flex;
                            justify-content: center;
                            gap: 20px;
                        }}

                        .menu li {{
                            padding: 5px 10px;
                            transition: background-color 0.3s;
                        }}

                        .menu li:hover {{
                            background-color: #0055a5;
                            border-radius: 4px;
                        }}

                        .hamburger {{
                            display: none;
                            font-size: 1.8rem;
                            cursor: pointer;
                            position: absolute;
                            right: 20px;
                            top: 20px;
                        }}

                        .mobile-menu {{
                            display: none;
                            background-color: #003366;
                            position: absolute;
                            top: 60px;
                            right: 20px;
                            width: 200px;
                            border-radius: 4px;
                            overflow: hidden;
                            z-index: 1000;
                        }}

                        .mobile-menu ul {{
                            list-style: none;
                            padding: 0;
                            margin: 0;
                        }}

                        .mobile-menu li {{
                            border-bottom: 1px solid #0055a5;
                        }}

                        .mobile-menu li:last-child {{
                            border-bottom: none;
                        }}

                        .mobile-menu a {{
                            display: block;
                            padding: 10px;
                            color: #fff;
                            text-align: center;
                            transition: background-color 0.3s;
                        }}

                        .mobile-menu a:hover {{
                            background-color: #0055a5;
                        }}

                        section {{
                            margin: 20px auto;
                            max-width: 1200px;
                            padding: 20px;
                            background-color: #fff;
                            border-radius: 8px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        }}

                        section h2 {{
                            margin-bottom: 15px;
                            color: #003366;
                            border-bottom: 2px solid #eaeaea;
                            padding-bottom: 5px;
                            width: 100%;
                        }}

                        .team-overview p {{
                            margin-bottom: 10px;
                            font-size: 1rem;
                        }}

                        .league-summary {{
                            display: flex;
                            flex-wrap: wrap;
                            gap: 20px;
                        }}

                        .league-card {{
                            flex: 1 1 45%;
                            background-color: #eaf2f8;
                            padding: 15px;
                            border-radius: 6px;
                            transition: transform 0.3s ease;
                        }}

                        .league-card:hover {{
                            transform: scale(1.02);
                        }}

                        .league-card h3 {{
                            margin-bottom: 10px;
                            color: #002244;
                        }}

                        /* Przegląd Statystyk */
                        .stats-cards {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                            gap: 15px;
                        }}

                        .stats-card {{
                            background-color: #f0f4f8;
                            padding: 10px;
                            border-radius: 6px;
                            text-align: center;
                            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                            transition: background-color 0.3s;
                        }}

                        .stats-card:hover {{
                            background-color: #e0e8ef;
                        }}

                        /* Tabela z meczami */
                        .match-details table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}

                        .match-details th,
                        .match-details td {{
                            padding: 10px;
                            border: 1px solid #ddd;
                            text-align: center;
                        }}

                        .match-details th {{
                            background-color: #003366;
                            color: #fff;
                        }}

                        .match-details tr:nth-child(even) {{
                            background-color: #f9f9f9;
                        }}

                        /* Stopka */
                        .footer {{
                            text-align: center;
                            padding: 15px;
                            background-color: #003366;
                            color: #fff;
                            margin-top: 20px;
                        }}

                        /* Responsywność */
                        @media (max-width: 768px) {{
                            .menu {{
                                display: none;
                            }}
                            .hamburger {{
                                display: block;
                            }}
                            .league-summary {{
                                flex-direction: column;
                            }}
                        }}

                        .match-details table {{
                            width: 100%;
                            border-collapse: collapse;
                        }}

                        .match-details th,
                        .match-details td {{
                            padding: 10px;
                            border: 1px solid #ddd;
                            text-align: center;
                        }}

                        .match-details th {{
                            background-color: #003366;
                            color: #fff;
                        }}

                        /* Dla ekranów poniżej 768px – karty */
                        @media (max-width: 768px) {{
                            /* Ukrywamy standardowe nagłówki tabeli */
                            .match-details thead {{
                                display: none;
                            }}

                            .match-details table,
                            .match-details tbody,
                            .match-details tr,
                            .match-details td {{
                                display: block;
                                width: 100%;
                            }}

                            .match-details tr {{
                                margin-bottom: 1rem; /* odstęp między „kartami” */
                                border: 1px solid #ddd;
                                border-radius: 6px;
                                overflow: hidden;
                            }}

                            .match-details td {{
                                position: relative;
                                padding-left: 50%;
                                text-align: left;
                                border: none; /* usuwamy obramowanie między kolumnami */
                                border-bottom: 1px solid #ddd;
                            }}

                            /* Ostatnia komórka w wierszu bez dolnej kreski */
                            .match-details td:last-child {{
                                border-bottom: none;
                            }}

                            /* Tworzymy etykiety z nagłówków w pseudo-elementach :before */
                            .match-details td:before {{
                                content: attr(data-label);
                                position: absolute;
                                left: 1rem;
                                font-weight: bold;
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <header class="header">
                        <img src="{logo_url}" alt="Logo {team_name}" class="team-logo">
                        <h1>{team_name}</h1>
                        <span class="last-update">Ostatnia aktualizacja: {last_update}</span>
                        <!-- Menu desktopowe -->
                        <nav class="menu">
                        <ul>
                            <li><a href="#team-overview">Drużyna</a></li>
                            <li><a href="#league-summary">Ligi</a></li>
                            <li><a href="#stats-overview">Statystyki</a></li>
                            <li><a href="#match-details">Mecze</a></li>
                        </ul>
                        </nav>
                        <!-- Hamburger dla mobilnych -->
                        <div class="hamburger">&#9776;</div>
                        <div class="mobile-menu" id="mobileMenu">
                        <ul>
                            <li><a href="#team-overview" onclick="toggleMobileMenu()">Drużyna</a></li>
                            <li><a href="#league-summary" onclick="toggleMobileMenu()">Ligi</a></li>
                            <li><a href="#stats-overview" onclick="toggleMobileMenu()">Statystyki</a></li>
                            <li><a href="#match-details" onclick="toggleMobileMenu()">Mecze</a></li>
                        </ul>
                        </div>
                    </header>
                    <section id="team-overview" class="team-overview">
                        <h2>Informacje ogólne:</h2>
                        <p><strong>Trener:</strong> {coach} | <strong>Kraj:</strong> {country} | <strong>Aktualna forma (ostatnie 5 meczy):</strong> {current_form} ({form_percentage} %)</p>
                    </section>
    """
    html_report += """
            <!-- Podsumowanie Lig -->
            <section id="league-summary" class="league-summary">
                <h2>Podsumowanie wyników w rozgrywkach</h2>"""

    for leagues in team_info_lagues:
        league_name = leagues.get("league_name", "Brak danych")
        points = leagues.get("points", "Brak danych")
        rank = leagues.get("rank", "")
        season = leagues.get("season", "Brak danych")
        away_draws = leagues.get("away_draws", "Brak danych")
        away_goals_against = leagues.get("away_goals_against", "Brak danych")
        away_goals_for = leagues.get("away_goals_for", "Brak danych")
        away_losses = leagues.get("away_losses", "Brak danych")
        away_played = leagues.get("away_played", "Brak danych")
        away_wins = leagues.get("away_wins", "Brak danych")
        description = leagues.get("description", "Brak danych")
        form = leagues.get("form", "Brak danych")
        goals_against = leagues.get("goals_against", "Brak danych")
        goals_difference = leagues.get("goals_difference", "Brak danych")
        goals_for = leagues.get("goals_for", "Brak danych")
        home_draws = leagues.get("home_draws", "Brak danych")
        home_goals_against = leagues.get("home_goals_against", "Brak danych")
        home_goals_for = leagues.get("home_goals_for", "Brak danych")
        home_losses = leagues.get("home_losses", "Brak danych")
        home_played = leagues.get("home_played", "Brak danych")
        home_wins = leagues.get("home_wins", "Brak danych")

        html_report += f"""
                <div class="league-card">
                    <h3>{league_name}</h3>
                    <p><strong>Pozycja:</strong> {rank} | <strong>Punkty:</strong> {points} | <strong>Sezon:</strong> {season} | <strong>Forma: </strong>{form}</p>
                    <p><strong>U siebie ({home_played}):</strong> Wygrane: {home_wins}, Remisy: {home_draws}, Porażki: {home_losses} (Gole: {home_goals_for}/{home_goals_against})</p>
                    <p><strong>Na wyjeździe ({away_played}):</strong> Wygrane: {away_wins}, Remisy: {away_draws}, Porażki: {away_losses} (Gole: {away_goals_for}/{away_goals_against})</p>
                    <p><strong>Łącznie:</strong> Gole: {goals_for}, Strata: {goals_against}, Różnica: {goals_difference}</p>
                </div>"""

    html_report += """</section>"""

    html_report += """
        <section id="stats-overview" class="stats-overview">
            <h2>Średnie statystyki (ost. 10 meczy)</h2>
            <div class="stats-cards">"""
    for key, value in stats_average.items():
            html_report += f"""<div class="stats-card"><p><strong>{key.replace('_', ' ').title()}</strong>: {value}</p></div>"""
    html_report += """</div></section>"""

    html_report += """
        <section id="match-details" class="match-details">
         <h2>Szczegóły Meczów</h2>
         <table>
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Rywal</th>
                    <th>Wynik</th>
                    <th>Rezultat</th>
                    <th>Posiadanie</th>
                    <th>Strzały</th>
                    <th>Rożne</th>
                    <th>Kartki</th>
                    <th>Faule</th>
                    <th>Spalone</th>
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
                        <tr class="match-result-win">
                            <td data-label="Data">{date}</td>
                            <td data-label="Rywal">{opponent}</td>
                            <td data-label="Wynik">{score}</td>
                            <td data-label="Rezultat">{result}</td>
                            <td data-label="Posiadanie">{possession}</td>
                            <td data-label="Strzały">Celne: {shots_on_goal} / Wszystkie: {total_shots}</td>
                            <td data-label="Rzuty rożne">{corners}</td>
                            <td data-label="Kartki">Żółte {yellow_cards} / Czerwone: {red_cards}</td>
                            <td data-label="Faule">{fouls}</td>
                            <td data-label="Spalone">{offsides}</td>
                        </tr>
        """

    html_report += """
                    </tbody>
                </table>
            </section>
            <footer class="footer">
                <p>Copyright © Lion-IT 2015 - 2025. Wszelkie prawa zastrzeżone.</p>
            </footer>
            <script>
                // Prosta obsługa menu hamburger dla urządzeń mobilnych
                const hamburger = document.querySelector('.hamburger');
                const mobileMenu = document.getElementById('mobileMenu');

                function toggleMobileMenu() {
                mobileMenu.style.display = mobileMenu.style.display === 'block' ? 'none' : 'block';
                }

                hamburger.addEventListener('click', toggleMobileMenu);

                // Opcjonalnie: ukryj menu przy kliknięciu poza nim
                document.addEventListener('click', (e) => {
                if (!mobileMenu.contains(e.target) && !hamburger.contains(e.target)) {
                    mobileMenu.style.display = 'none';
                }
                });
            </script>
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
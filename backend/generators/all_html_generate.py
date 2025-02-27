import requests
import os
import sys
import time

from html import escape
from dotenv import load_dotenv
from datetime import date, datetime

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

from utils.logging_utils import setup_logger, log_info, log_warning, log_error
from maintenance.clean_folder import clean_folder
from generators.team_raport_generate_v2 import generate_team_report

# Set up logging
logger = setup_logger("all_html_generate")

# Configuration
PREDICTIONS_API_URL = "http://10.0.0.8:53502/api/matches/future_matches"
H2H_API_URL_TEMPLATE = "http://10.0.0.8:53502/api/matches/h2h/{home_team_id}/{away_team_id}"
OUTPUT_DIR = os.path.abspath(os.path.join('Football/frontend/public/'))
HTML_FILE_NAME = "match_predictions.html"  # HTML file name


def fetch_data(api_url, retries=5, delay=5):
    """ Pobiera dane z API i ponawia próbę w przypadku błędu 500. """

    for attempt in range(retries):
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 500:
                log_warning(logger, f"API returned 500. Retrying in {delay} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log_error(logger, f"Error fetching data from API: {e}")
            time.sleep(delay)

    log_error(logger, f"API failed after {retries} retries.")
    return None

def fetch_h2h_data(home_team_id, away_team_id, retries=5, delay=5):
    """ Fetch H2H data for the given teams. """
    api_url = H2H_API_URL_TEMPLATE.format(home_team_id=home_team_id, away_team_id=away_team_id)
    for attempt in range(retries):
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 500:
                log_warning(logger, f"API returned 500. Retrying in {delay} seconds... (Attempt {attempt+1}/{retries})")
                time.sleep(delay)  # Czekaj przed ponowną próbą
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log_error(logger, f"Error fetching data from API: {e}")
            time.sleep(delay)

    log_error(logger, f"API failed after {retries} retries.")
    return None

def generate_h2h_html(home_team_id, away_team_id, home_team_name, away_team_name, h2h_data):
    """
    Generate an HTML file for H2H data.
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>H2H: {home_team_name} vs {away_team_name}</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <style>
            body {{
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Poppins', sans-serif;
                font-size: 1rem;
                font-weight: 400;
                line-height: 1.5;
                color: #212529;
                background-color: #fff;
            }}

            #h2h-table_length {{
                padding: 1rem;
                color: #ddd;
            }}

            #h2h-table_info {{
                padding: 1rem;
                color: #ddd;
            }}

            #h2h-table_paginate {{
                padding: 1rem;
            }}

            #h2h-table_paginate a {{
                color: #ddd !important;
            }}

            #h2h-table_filter {{
                padding: 1rem;
                color: #ddd;
            }}

            #h2h-table {{
                border-radius: 0.8rem;
            }}

            .limiter {{
                width: 100%;
                margin: 0 auto;
            }}

            .container-table100 {{
                min-height: 100vh;
                background: #c850c0;
                background: -webkit-linear-gradient(45deg, #4158d0, #c850c0);
                background: -o-linear-gradient(45deg, #4158d0, #c850c0);
                background: -moz-linear-gradient(45deg, #4158d0, #c850c0);
                background: linear-gradient(45deg, #4158d0, #c850c0);
                display: -webkit-box;
                display: -webkit-flex;
                display: -moz-box;
                display: -ms-flexbox;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-wrap: wrap;
                padding: 20px 20px;
            }}

            .wrap-table100 {{
                width: 1600px;
            }}

            table {{
                border-spacing: 1;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                width: 100%;
                margin: 0 auto;
                position: relative;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            }}

            table thead tr {{
                height: 70px;
                background: #36304a;
            }}

            table tbody tr {{
                font-size: 16px;
                line-height: 1.4;
                text-align: center;
            }}

            table tbody td {{
                padding: 12px 15px; /* Większe odstępy w komórkach */
                vertical-align: middle; /* Środkowe wyrównanie treści w pionie */
                border-bottom: 1px solid #ddd; /* Delikatne linie oddzielające wiersze */
            }}

            .table100-head th {{
                font-size: 15px;
                color: #fff;
                font-weight: unset !important;
                text-transform: uppercase;
            }}

            .column_th {{
                text-align: center !important;
            }}

            tbody tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}

            tbody tr:nth-child(odd) {{
                background-color: #ffffff;
            }}

            tbody tr:hover {{
                background-color: #f1f1f1;
                cursor: pointer;
                transition: background-color 0.3s ease; /* Płynna zmiana koloru na hover */
            }}

            th.th-sort-asc::after {{
                content: " 🔼";
            }}

            th.th-sort-desc::after {{
                content: " 🔽";
            }}

            .league-logo {{
                height: 25px;
                vertical-align: middle;
                margin-right: 10px;
            }}

            .center {{
                text-align: center;
            }}

            .winner {{
                font-weight: 600;
                color: #2E8B57;
                text-transform: uppercase;
            }}

            .red {{
                color: #DC143C;
                font-weight: 600;
            }}

            .yellow {{
                color: #FF803E;
                font-weight: 600;
            }}

            .blue {{
                color: blue;
                text-transform: uppercase;
                font-weight: 600;
            }}

            .green {{
                color: #2E8B57;
                font-weight: 600;
            }}

            /* Responsive Design */
            @media screen and (max-width: 768px) {{
                table thead {{
                    display: none; /* Hide table headers */
                }}

                table, table tbody, table tr, table td {{
                    display: block;
                    width: 94%;
                    padding: 0.5rem;
                }}

                table tr {{
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                    padding: 10px;
                }}

                table td {{
                    text-align: right;
                    padding: 10px;
                    border: none;
                    position: relative;
                }}

                table td::before {{
                    content: attr(data-label); /* Add a label for each row item */
                    position: absolute;
                    left: 10px;
                    font-weight: bold;
                    text-align: left;
                }}

                .center {{
                    text-align: right;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="limiter">
            <div class="container-table100">
                <div class="wrap-table100">
                    <div class="table100">
                        <table id="h2h-table" class="display">
                            <thead>
                                <tr class="table100-head">
                                    <th class="column_th">Data</th>
                                    <th class="column_th">Gospodarze</th>
                                    <th class="column_th">Goście</th>
                                    <th class="column_th">Wynik</th>
                                    <th class="column_th">Żółte kartki</th>
                                    <th class="column_th">Czerwone kartki</th>
                                    <th class="column_th">Faule</th>
                                    <th class="column_th">Sędzia</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows}
                            </tbody>
                        </table>
                       </div>
                </div>
            </div>
        </div>
        <script>
            $(document).ready(function() {{
                $('#h2h-table').DataTable({{
                    paging: true,
                    searching: true,
                    info: true,
                    ordering: true,
                    order: [[0, 'desc']],
                    columnDefs: [
                        {{ type: "datetime", orderable: true, targets: "_all" }}
                    ],
                    language: {{
                        url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pl.json"
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """

    rows = []
    for match in h2h_data:
        winner_team_id = match.get('winner_team')  # ID zwycięskiej drużyny
        home_team_id = match.get('home_team_id')
        away_team_id = match.get('away_team_id')

        yellow_card_home = match.get('yellow_cards_home') or 0
        yellow_card_away = match.get('yellow_cards_away') or 0

        yellow_card_class_home = 'class="yellow" ' if yellow_card_home > 0 else ""
        yellow_card_class_away = 'class="yellow" ' if yellow_card_away > 0 else ""

        red_card_home = match.get('red_cards_home') or 0
        red_card_away = match.get('red_cards_away') or 0

        red_card_class_home = 'class="red" ' if red_card_home > 0 else ""
        red_card_class_away = 'class="red" ' if red_card_away > 0 else ""

        home_class = 'class="winner" ' if home_team_id == winner_team_id else ""
        away_class = 'class="winner" ' if away_team_id == winner_team_id else ""

        formatted_date = datetime.strptime(match.get('match_date'), '%Y-%m-%d %H:%M:%S').isoformat()

        rows.append(f"""
        <tr>
            <td data-order="{formatted_date}" data-label="Data">{escape(str(match.get('match_date') or 'Brak danych'))}</td>
            <td {home_class}data-label="Gospodarze">{escape(str(match.get('home_team_name') or 'Brak danych'))}</td>
            <td {away_class}data-label="Goście">{escape(str(match.get('away_team_name') or 'Brak danych'))}</td>
            <td data-label="Wynik">{escape(str(match.get('score') or 'Brak danych'))}</td>
            <td data-label="Żółte kartki"><span {yellow_card_class_home}>{yellow_card_home}</span> - <span {yellow_card_class_away}>{yellow_card_away}</span></td>
            <td data-label="Czerwone kartki"><span {red_card_class_home}>{match.get('red_cards_home', 0) or 0}</span> - <span {red_card_class_away}>{match.get('red_cards_away', 0) or 0}</span></td>
            <td data-label="Faule">{match.get('fouls_home', 0) or 0} - {match.get('fouls_away', 0) or 0}</td>
            <td data-label="Sędzia">{escape(str(match.get('referee') or 'Brak danych'))}</td>
        </tr>
        """)

    html_content = html_template.format(
        home_team_name=escape(home_team_name),
        away_team_name=escape(away_team_name),
        rows=''.join(rows)
    )

    output_dir = os.path.join(OUTPUT_DIR, 'h2h')
    os.makedirs(output_dir, exist_ok=True)
    file_name = f"h2h_{home_team_id}_{away_team_id}.html"
    file_path = os.path.join(output_dir, f"h2h_{home_team_id}_{away_team_id}.html")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(html_content)

    log_info(logger, f"H2H HTML file generated for {home_team_name} vs {away_team_name}: {file_path}")
    return file_name

def generate_html(matches):
    """
    Generate static HTML from match data with H2H links.
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Future Matches with H2H</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <style>
            body {{
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Poppins', sans-serif;
                font-size: 1rem;
                font-weight: 400;
                line-height: 1.5;
                color: #212529;
                background-color: #fff;
            }}

            #predictions-table_length {{
                padding: 1rem;
                color: #ddd;
            }}

            #predictions-table_info {{
                padding: 1rem;
                color: #ddd;
            }}

            #predictions-table_paginate {{
                padding: 1rem;
            }}

            #predictions-table_paginate a {{
                color: #ddd !important;
            }}

            #predictions-table_filter {{
                padding: 1rem;
                color: #ddd;
            }}

            #predictions-table {{
                border-radius: 0.8rem;
            }}

            .limiter {{
                width: 100%;
                margin: 0 auto;
            }}

            .container-table100 {{
                min-height: 100vh;
                background: #c850c0;
                background: -webkit-linear-gradient(45deg, #4158d0, #c850c0);
                background: -o-linear-gradient(45deg, #4158d0, #c850c0);
                background: -moz-linear-gradient(45deg, #4158d0, #c850c0);
                background: linear-gradient(45deg, #4158d0, #c850c0);
                display: -webkit-box;
                display: -webkit-flex;
                display: -moz-box;
                display: -ms-flexbox;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-wrap: wrap;
                padding: 20px 20px;
            }}

            .wrap-table100 {{
                width: 90%;
            }}

            table {{
                border-spacing: 1;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                width: 100%;
                margin: 0 auto;
                position: relative;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            }}

            table thead tr {{
                height: 70px;
                background: #36304a;
            }}

            table tbody tr {{
                font-size: 16px;
                line-height: 1.4;
            }}

            table tbody td {{
                padding: 12px 15px; /* Większe odstępy w komórkach */
                vertical-align: middle; /* Środkowe wyrównanie treści w pionie */
                border-bottom: 1px solid #ddd; /* Delikatne linie oddzielające wiersze */
            }}

            .table100-head th {{
                font-size: 15px;
                color: #fff;
                font-weight: unset !important;
                text-transform: uppercase;
            }}

            .column_th {{
                text-align: center !important;
            }}

            tbody tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}

            tbody tr:nth-child(odd) {{
                background-color: #ffffff;
            }}

            tbody tr:hover {{
                background-color: #f1f1f1; d
                transition: background-color 0.3s ease; /* Płynna zmiana koloru na hover */
            }}

            th.th-sort-asc::after {{
                content: " 🔼";
            }}

            th.th-sort-desc::after {{
                content: " 🔽";
            }}

            .league-logo {{
                height: 25px;
                vertical-align: middle;
                margin-right: 10px;
            }}

            .center {{
                text-align: center;
            }}

            .red {{
                color: red;
                font-weight: 600;
            }}

            .blue {{
                color: blue;
                font-weight: 600;
            }}

            .green {{
                color: green;
                font-weight: 600;
            }}

            /* Responsive Design */
            @media screen and (max-width: 768px) {{
                header {{
                    font-size: 10px;
                }}

                table thead {{
                    display: none; /* Hide table headers */
                }}

                table, table tbody, table tr, table td {{
                    display: block;
                    width: 94%;
                    padding: 0.5rem;
                }}

                table tr {{
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
                    padding: 10px;
                }}

                table td {{
                    text-align: right;
                    padding: 10px;
                    border: none;
                    position: relative;
                }}

                table td::before {{
                    content: attr(data-label); /* Add a label for each row item */
                    position: absolute;
                    left: 10px;
                    font-weight: bold;
                    text-align: left;
                }}

                .center {{
                    text-align: right;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="limiter">
            <div class="container-table100">
                <div class="wrap-table100">
                    <div class="table100">
                        <table id="predictions-table" class="display">
                            <thead>
                                <tr class="table100-head">
                                    <th>Lp.</th>
                                    <th class="column_th">Data</th>
                                    <th class="column_th">Gospodarze</th>
                                    <th class="column_th">Goście</th>
                                    <th class="column_th">Sędzia</th>
                                    <th class="column_th">Liga</th>
                                    <th class="column_th">Predykcja</th>
                                    <th class="column_th">Bonus</th>
                                    <th class="column_th">H2H</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            $(document).ready(function() {{
                $('#predictions-table').DataTable({{
                    paging: true,
                    searching: true,
                    info: true,
                    ordering: true,
                    columnDefs: [
                        {{ orderable: true, targets: "_all" }}
                    ],
                    language: {{
                        url: "//cdn.datatables.net/plug-ins/1.13.6/i18n/pl.json"
                    }}
                }});
            }});
        </script>
    </body>
    </html>
    """

    rows = []
    for i, match in enumerate(matches, start=1):
        home_team_id = match.get('home_team_id')
        away_team_id = match.get('away_team_id')
        home_team_name = match.get('home_team_name', 'Brak danych')
        away_team_name = match.get('away_team_name', 'Brak danych')

        # Pobierz dane H2H i wygeneruj link do HTML
        h2h_data = fetch_h2h_data(home_team_id, away_team_id)
        h2h_file = generate_h2h_html(home_team_id, away_team_id, home_team_name, away_team_name, h2h_data)
        h2h_link = f"https://lionscore.pl/h2h/{h2h_file}" if h2h_file else "#"
        h2h_link_html = f'<a href="{h2h_link}" target="_blank" title="Link do H2H" style="padding:1rem;margin-right:1rem">Stats</a>'

        # Link do statsow druzyny
        team_data_home = generate_team_report(home_team_id)
        team_data_away = generate_team_report(away_team_id)
        team_link_home = f"https://lionscore.pl/team/{home_team_id}.html" if team_data_home else "#"
        team_link_away = f"https://lionscore.pl/team/{away_team_id}.html" if team_data_away else "#"

        league_info = f"""
            <img src="{escape(str(match.get('league', {}).get('logo_url', 'No logo')))}" alt="League Logo" class="league-logo">
            {escape(str(match.get('league', {}).get('name', 'No league')))}
        """
        predictions = match.get('predictions') or {}
        prediction_info = f"""
            Wygra: {escape(str(predictions.get('winner_name') or 'Brak'))}<br>
            Gospodarze: {float(predictions.get('home_win_percent', 0) or 0)}%<br>
            Remis: {float(predictions.get('home_win_percent', 0) or 0)}%<br>
            Goście: {float(predictions.get('home_win_percent', 0) or 0)}%
        """ if predictions else "Brak predykcji"

        rows.append(f"""
        <tr>
            <td class="center" data-label="Lp.">{i}.</td>
            <td class="green" data-label="Data">{escape(match.get('match_date', 'Brak'))}</td>
            <td data-label="Gospodarze"><a class="blue" href="{team_link_home}" target="_blank" title="Statystyki {home_team_name}">{escape(match.get('home_team_name', 'Brak'))}</a></td>
            <td data-label="Goście"><a class="red" href="{team_link_away}" target="_blank" title="Statystyki {away_team_name}">{escape(match.get('away_team_name', 'Brak'))}</a></td>
            <td data-label="Sędzia">{escape(str(match.get('referee') or 'Brak'))}</td>
            <td data-label="Liga">{league_info}</td>
            <td data-label="Predykcja">{prediction_info}</td>
            <td data-label="">{escape(predictions.get('advice', 'Brak') or 'Brak')}</td>
            <td data-label="H2H">{h2h_link_html}</td>
        </tr>
        """)

    return html_template.format(rows=''.join(rows))

def save_html_file(content, output_dir, file_name):
    """
    Save generated HTML to a file.
    """
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, file_name)
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    log_info(logger, f"HTML file saved to: {file_path}")
    return file_path


def run():
    matches = fetch_data(PREDICTIONS_API_URL)
    if not matches:
        log_error(logger, "No match data fetched from API.")
        return

    clean_folder(OUTPUT_DIR)
    html_content = generate_html(matches)
    save_html_file(html_content, OUTPUT_DIR, HTML_FILE_NAME)

# if __name__ == "__main__":
#     if "generators.all_html_generate" not in sys.modules:
#         run()
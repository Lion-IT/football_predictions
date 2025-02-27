import requests
import os
import sys
from html import escape
from dotenv import load_dotenv
from datetime import date

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

from utils.logging_utils import setup_logger, log_info, log_error
from utils.email_utils import send_email_alert
from utils.validation_utils import parse_date_to_local

# Set up logging
logger = setup_logger("predictions_html_generate")

# Configuration
API_URL = "http://10.0.0.8:53502/api/matches/future_matches"
OUTPUT_DIR = os.path.abspath(os.path.join('frontend/public/'))
HTML_FILE_NAME = "match_predictions.html"  # HTML file name


def fetch_data(api_url):
    """
    Fetch data from the API.
    """
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        log_error(logger, f"Error fetching data from API: {e}")
        return []


def generate_html(matches):
    """
    Generate static HTML from match data.
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Future Matches</title>
        <head>
            <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        </head>
        <style>
            body {{
                font-family: 'Roboto', sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(to bottom right, #6a11cb, #2575fc);
                color: #333;
            }}

            header {{
                text-align: center;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }}

            #predictions-table_length {{
                padding: 1rem;
            }}

            #predictions-table_info {{
                padding: 1rem;
            }}

            #predictions-table_paginate {{
                padding: 1rem;
            }}

            #predictions-table_filter {{
                padding: 1rem;
            }}

            #predictions-table {{
                border-radius: 0;
            }}

            .table-container {{
                width: 90%;
                margin: 30px auto;
                overflow-x: auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                border-radius: 10px;
                overflow: hidden;
            }}

            thead {{
                background-color: #343a40;
                color: white;
            }}

            th, td {{
                padding: 15px;
                text-align: left;
                font-size: 14px;
            }}

            th {{
                font-weight: bold;
            }}

            tbody tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}

            tbody tr:nth-child(odd) {{
                background-color: #ffffff;
            }}

            tbody tr:hover {{
                background-color: #e9ecef;
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
        <header>
            <h1>Predykcje na dzisiaj</h1>
        </header>
        <div class="table-container">
            <table id="predictions-table" class="display">
                <thead>
                    <tr>
                        <th>Lp.</th>
                        <th>Data</th>
                        <th>Gospodarze</th>
                        <th>Goście</th>
                        <th>Sędzia</th>
                        <th>Liga</th>
                        <th>Predykcja z API FOOTBALL</th>
                        <th>Bonus</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
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
        league_info = f"""
            <img src="{escape(match['league'].get('logo_url', 'No logo'))}" alt="League Logo" class="league-logo">
            {escape(match['league'].get('name', 'No league'))}
        """
        predictions = match.get('predictions', {})
        prediction_info = f"""
            Wygra: {escape(predictions.get('winner_name', 'Brak'))}<br>
            Gospodarze: {predictions.get('home_win_percent', 0)}%<br>
            Remis: {predictions.get('draw_percent', 0)}%<br>
            Goście: {predictions.get('away_win_percent', 0)}%
        """ if predictions else "Brak predykcji"

        rows.append(f"""
        <tr>
            <td class="center" data-label="Lp.">{i}.</td>
            <td data-label="Data">{escape(match.get('match_date', 'Brak'))}</td>
            <td data-label="Gospodarze">{escape(match.get('home_team_name', 'Brak'))}</td>
            <td data-label="Goście">{escape(match.get('away_team_name', 'Brak'))}</td>
            <td data-label="Sędzia">{escape(str(match.get('referee', 'Brak')))}</td>
            <td data-label="Liga">{league_info}</td>
            <td data-label="Predykcja">{prediction_info}</td>
            <td data-label="">{escape(predictions.get('advice', 'Brak'))}</td>
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
    matches = fetch_data(API_URL)
    if not matches:
        log_error(logger, "No match data fetched from API.")
        return

    log_info(logger, f"Fetched {len(matches)} matches.")
    html_content = generate_html(matches)
    save_html_file(html_content, OUTPUT_DIR, HTML_FILE_NAME)

if __name__ == "__main__":
    run()

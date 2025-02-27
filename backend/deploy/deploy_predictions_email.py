import sys
import os
import json

from dotenv import load_dotenv

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_connection import get_redis_connection, execute_query
from utils.logging_utils import setup_logger, log_info, log_error
from utils.email_utils import send_email_alert

# Add the necessary directories to the Python path
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
if not os.path.exists(env_path):
    raise FileNotFoundError(f".env file not found at: {env_path}")
load_dotenv(env_path)

# Set up logging
logger = setup_logger("predictions_send")

# Global Redis connection
redis_client = get_redis_connection()

def fetch_predictions():
    """
    Fetch predictions from the database.
    Returns:
        List[Dict]: List of predictions data.
    """
    query = """
        SELECT fixture_id, winner_name, advice, home_win_percent, draw_percent, away_win_percent
        FROM predictions
        ORDER BY fixture_id;
    """
    try:
        return execute_query(query)
    except Exception as e:
        log_error(logger, f"Error fetching predictions: {e}")
        return []

def generate_html_report(predictions):
    """
    Generate an HTML report for the predictions.
    Args:
        predictions (List[Dict]): Predictions data.
    Returns:
        str: HTML string.
    """
    html = """
    <html>
        <head>
            <style>
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; }
                th { background-color: #f4f4f4; text-align: left; }
            </style>
        </head>
        <body>
            <h2>Daily Predictions Report</h2>
            <table>
                <tr>
                    <th>Fixture ID</th>
                    <th>Predicted Winner</th>
                    <th>Advice</th>
                    <th>Home Win %</th>
                    <th>Draw %</th>
                    <th>Away Win %</th>
                </tr>
    """
    for prediction in predictions:
        html += f"""
        <tr>
            <td>{prediction['winner_name'] or 'N/A'}</td>
            <td>{prediction['advice']}</td>
            <td>{prediction['home_win_percent']}%</td>
            <td>{prediction['draw_percent']}%</td>
            <td>{prediction['away_win_percent']}%</td>
        </tr>
        """
    html += """
            </table>
        </body>
    </html>
    """
    return html

def send_predictions_email():
    """
    Fetch predictions, generate a report, and send it via email.
    """
    predictions = fetch_predictions()
    if not predictions:
        log_info(logger, "No predictions available to send.")
        return

    html_report = generate_html_report(predictions)

    subject = "Typu meczów na dzisiaj"
    recipients = ["radoslawtkacz@gmail.com"]  # Replace with your recipient list
    try:
        send_email_alert(subject, html_report, body_type="html", recipients=recipients)
        log_info(logger, "predictions_email", "Predictions email sent successfully.")
    except Exception as e:
        log_error("predictions_email", f"Error sending predictions email: {e}")

if __name__ == "__main__":
    send_predictions_email()

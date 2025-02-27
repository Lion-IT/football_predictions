import sys
import os
import json

# Add the necessary directories to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from utils.email_utils import send_email_alert
from utils.logging_utils import log_info, log_error, setup_logger
from config.db_connection import get_redis_connection

# Setup logger for notifications
logger = setup_logger("notifications_utils")
redis_client = get_redis_connection()

# Shared batch notifications list
EMAIL_SEND_FLAG_KEY = "email_send_flag"
EMAIL_SENT_DATE_KEY = "email_sent_date"
BATCH_NOTIFICATIONS_KEY = "batch_notifications"

def add_to_batch_notification(body):
    """
    Add a notification to the batch list.
    """
    try:
        # Add notification to Redis list
        redis_client.set(BATCH_NOTIFICATIONS_KEY, json.dumps({"body": body}))
        redis_client.set(EMAIL_SEND_FLAG_KEY, 1)  # Set the flag to True
    except Exception as e:
        log_error(logger, f"Error adding to batch notifications: {e}")
        return

def send_batch_notifications():
    """
    Send all batched notifications as a single email.
    """
    try:
        # Check the email send date
        today_date = datetime.now().strftime("%Y-%m-%d")
        last_sent_date = redis_client.get(EMAIL_SENT_DATE_KEY)

		# Sprawdź, czy Redis zwraca bytes, i przekonwertuj, jeśli to konieczne
        if isinstance(last_sent_date, bytes):
            last_sent_date = last_sent_date.decode("utf-8")

        if last_sent_date == today_date:
            log_info(logger, f"Email already sent today ({today_date}). Skipping.")
            return

        # Check if email_send_flag is set
        email_send_flag = redis_client.get(EMAIL_SEND_FLAG_KEY)
        if not email_send_flag:
            log_info(logger, "No notifications to send. Skipping email.")
            return

        # Retrieve last notifications
        notification = redis_client.get(BATCH_NOTIFICATIONS_KEY)
        if not notification:
            log_info(logger, "Batch is empty, but email_send_flag is set. Skipping email.")
            return

        try:
            notification_data = json.loads(notification)
            body = notification_data.get("body", "No details available.")
        except json.JSONDecodeError as e:
            log_error(logger, f"Failed to decode notification data: {e}")
            return

        # Prepare email content
        subject = "⚠️ LIONSCORE ALERT: API Usage Alerts"

        # Send the email
        send_email_alert(subject=subject, body=body)
        # log_info(logger, "E-mail notifications sent successfully.")

        # Clear notifications and reset the flag
        redis_client.delete(BATCH_NOTIFICATIONS_KEY)
        redis_client.delete(EMAIL_SEND_FLAG_KEY)

        # Update the last sent date in Redis
        redis_client.set(EMAIL_SENT_DATE_KEY, today_date)
    except Exception as e:
        log_error(logger, f"Error sending e-mail notifications: {e}")
        return

# if __name__ == "__main__":
#     # Test instructions
#     send_batch_notifications()

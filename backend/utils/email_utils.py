import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from utils.logging_utils import log_error, setup_logger

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def send_email_alert(subject, body, body_type="plain", recipients=None):
    """
    Sends an email alert with the given subject and body.
    :param subject: Subject of the email.
    :param body: Content of the email (plain text or HTML).
    :param body_type: Content type of the email body ("plain" or "html").
    :param recipients: List of recipient emails. Defaults to ALERT_RECIPIENT from .env.
    """
    try:
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_email = os.getenv("SMTP_EMAIL")
        smtp_password = os.getenv("SMTP_PASSWORD")
        default_recipient = os.getenv("ALERT_RECIPIENT")

		# Use default recipient if no custom recipients are provided
        if recipients is None:
            recipients = [default_recipient]

        if not (smtp_server and smtp_port and smtp_email and smtp_password and recipients):
            logger = setup_logger("emails")
            log_error(logger, "SMTP configuration is incomplete. Email alert not sent.")
            return

         # Create email content
        msg = MIMEMultipart()
        msg["From"] = smtp_email
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, body_type))

         # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, recipients, msg.as_string())
        print(f"Email alert sent successfully to: {', '.join(recipients)}.")
    except Exception as e:
        logger = setup_logger("emails")
        log_error(logger, f"Error sending email alert: {type(e).__name__}: {e}")

# if __name__ == "__main__":
#     send_email_alert(
#         subject="Test Email",
#         body="This is a test email sent to verify the alert system."
#     )
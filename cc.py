# === SERVER: server_app.py ===

from mcp.server.fastmcp import FastMCP
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from ReduceReuseRecycleGENAI import get_ser_conn

# Initialize MCP server
mcp = FastMCP("email-server")

env = "preprod"
region_nm = "us-east-1"

@mcp.tool(
    name="send_test_email",
    description="Sends a simple HTML email via enterprise SMTP connection."
)
def send_test_email(subject: str, body: str, receivers: str) -> str:
    """
    Send an HTML email.
    Args:
        subject: email subject
        body: HTML body
        receivers: comma-separated recipient emails
    Returns:
        status message
    """
    try:
        sender = 'noreply-arb-info@elevancehealth.com'
        recipients = [email.strip() for email in receivers.split(',')]

        # Compose email
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(body, 'html'))  # HTML body

        # Send via enterprise SMTP
        smtp_obj = get_ser_conn(
            logger,
            env=env,
            region_name=region_nm,
            aplctn_cd="aedl",
            port=None,
            tls=True,
            debug=False
        )
        smtp_obj.sendmail(sender, recipients, msg.as_string())
        smtp_obj.quit()

        logger.info("Email sent successfully.")
        return "Email sent successfully."
    except Exception as e:
        error = f"Error sending email: {e}"
        logger.error(error)
        return error

# Run as an HTTP API server for stable client connections
if __name__ == "__main__":
    print("Starting MCP Email Server (HTTP) on port 8000...")
    mcp.run(transport="http", host="0.0.0.0", port=8000)


# === CLIENT: client_app.py ===

import requests

# Replace with your EC2 MCP server address
SERVER_URL = "http://10.126.192.183:8000/tools/send_test_email"

payload = {
    "subject": "MCP Email Test",
    "body": "<p>Hello from HTTP MCP client!</p>",
    "receivers": "gentela.vnsaipavan@carelon.com"
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def send_email():
    try:
        resp = requests.post(SERVER_URL, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    send_email()

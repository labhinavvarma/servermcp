from pydantic import BaseModel
from typing import Dict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from loguru import logger

# --- Configurations ---
ENV = "preprod"
REGION_NAME = "us-east-1"
SENDER_EMAIL = 'AbhinavVarma.Lakamraju@elevancehealth.com'

# Define expected input structure
class EmailRequest(BaseModel):
    subject: str
    body: str
    receivers: str  # Comma-separated email addresses

# === Unified MCP Tool ===
@mcp.tool(name="mcp-send-email", description="Send an email with a subject and HTML body to recipients.")
def mcp_send_email(request: EmailRequest) -> Dict:
    try:
        recipients = [email.strip() for email in request.receivers.split(",")]

        msg = MIMEMultipart()
        msg['Subject'] = request.subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(request.body, 'html'))

        smtp = get_ser_conn(logger, env=ENV, region_name=REGION_NAME, aplctn_cd="aedl", port=None, tls=True, debug=False)
        smtp.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        smtp.quit()

        logger.info("Email sent successfully.")
        return {"status": "success", "message": "Email sent successfully."}
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return {"status": "error", "message": str(e)}

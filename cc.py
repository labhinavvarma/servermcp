# === SERVER: server_app.py ===

from mcp.server.fastmcp import FastMCP
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from ReduceReuseRecycleGENAI import get_ser_conn

# Initialize MCP server
env = "preprod"
region_nm = "us-east-1"

mcp = FastMCP("email-server")

@mcp.tool(name="send_test_email", description="Send a basic HTML email via enterprise SMTP.")
def send_test_email(subject: str, body: str, receivers: str) -> str:
    """
    Sends an HTML email.
    Args:
        subject: Email subject
        body: HTML body of the email
        receivers: Comma-separated recipient emails
    Returns:
        Status message
    """
    try:
        sender = 'noreply-arb-info@elevancehealth.com'
        recipients = [email.strip() for email in receivers.split(',')]

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(body, 'html'))

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

# Start the MCP Email Server using SSE transport
if __name__ == "__main__":
    print("🚀 MCP Email Server is running in SSE mode and waiting for client invocations...", flush=True)
    mcp.run(transport="sse")

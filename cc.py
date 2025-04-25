# === SERVER: server_app.py ===
"""
A simple HTTP server using FastAPI to send emails with enterprise SMTP connection.
Run via: python server_app.py
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ReduceReuseRecycleGENAI import get_ser_conn

app = FastAPI()

env = "preprod"
region_nm = "us-east-1"

class EmailRequest(BaseModel):
    subject: str
    body: str
    receivers: str  # comma-separated emails

@app.post("/send_test_email")
def send_test_email(req: EmailRequest):
    try:
        sender = 'noreply-arb-info@elevancehealth.com'
        recipients = [email.strip() for email in req.receivers.split(",")]

        # Compose message
        msg = MIMEMultipart()
        msg['Subject'] = req.subject
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg.attach(MIMEText(req.body, 'html'))

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
        return {"status": "success", "message": "Email sent successfully."}
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Email Server on http://0.0.0.0:8000 ...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)


# === CLIENT: client_app.py ===
"""
A simple HTTP client to invoke the email sending server.
"""
import requests

SERVER_URL = "http://10.126.192.183:8000/send_test_email"  # Replace with your EC2 IP

payload = {
    "subject": "Test Email",
    "body": "<p>Hello from FastAPI client!</p>",
    "receivers": "gentela.vnsaipavan@carelon.com"
}

headers = {
    "Content-Type": "application/json"
}

def send_email():
    try:
        resp = requests.post(SERVER_URL, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    send_email()

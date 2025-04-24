from fastmcp import FastMCP, MCP_Request, MCP_Response, MCP_EventSourceResponse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from ReduceReuseRecycleGENAI import get_ser_conn
from typing import Dict, Any, List, Optional, Union, AsyncIterator
import json
import asyncio
import uuid

# Initialize FastMCP
app = FastMCP()

# Configuration
ENV = "preprod"
REGION_NM = "us-east-1"
DEFAULT_SENDER = 'noreply-arb-info@elevancehealth.com'

# Store active connections
active_connections = {}

# Email Service
class EmailService:
    @staticmethod
    def send_email(
        subject: str, 
        body: str, 
        receivers: Union[str, List[str]], 
        sender: Optional[str] = None,
        content_type: str = 'html'
    ) -> Dict[str, Any]:
        """
        Send an email using SMTP.
        
        Args:
            subject: Email subject
            body: Email body content
            receivers: Single email address or list of email addresses
            sender: Sender email address (uses default if None)
            content_type: 'html' or 'plain'
            
        Returns:
            Dict with success status and message
        """
        try:
            # Use default sender if not provided
            actual_sender = sender or DEFAULT_SENDER
            
            # Handle receivers as string or list
            receiver_list = [receivers] if isinstance(receivers, str) else receivers
            receivers_str = ", ".join(receiver_list)
            
            # Set up email message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = actual_sender
            msg['To'] = receivers_str
            
            # Add plain text or HTML body
            msg.attach(MIMEText(body, content_type))
            
            # Use existing connection method
            smtpObj = get_ser_conn(
                logger, 
                env=ENV, 
                region_name=REGION_NM, 
                aplctn_cd="aedl", 
                port=None, 
                tls=True, 
                debug=False
            )
            
            # Send the email
            smtpObj.sendmail(actual_sender, receiver_list, msg.as_string())
            logger.info(f"Email sent successfully to {receivers_str}")
            smtpObj.quit()
            
            return {
                "success": True, 
                "message": f"Email sent successfully to {receivers_str}"
            }
            
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False, 
                "message": error_msg
            }

# SSE Event Stream Generator
async def event_generator(client_id: str, email_data: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
    """
    Generate SSE events for the email sending process.
    
    Args:
        client_id: Unique client identifier
        email_data: Email data for sending
        
    Yields:
        Dict containing event data
    """
    try:
        # Store connection for potential later use
        active_connections[client_id] = True
        
        # Initial event - process started
        yield {
            "event": "process_start",
            "id": client_id,
            "data": json.dumps({
                "message": "Email process started",
                "status": "processing"
            })
        }
        
        # Simulate validation step
        await asyncio.sleep(0.5)
        yield {
            "event": "validation",
            "id": client_id,
            "data": json.dumps({
                "message": "Email data validated",
                "status": "processing"
            })
        }
        
        # Simulate connection step
        await asyncio.sleep(0.5)
        yield {
            "event": "connecting",
            "id": client_id,
            "data": json.dumps({
                "message": "Connecting to email server",
                "status": "processing"
            })
        }
        
        # Actually send the email
        result = EmailService.send_email(
            subject=email_data["subject"],
            body=email_data["body"],
            receivers=email_data["receivers"],
            sender=email_data.get("sender"),
            content_type=email_data.get("content_type", "html")
        )
        
        # Final event - process complete
        yield {
            "event": "complete",
            "id": client_id,
            "data": json.dumps({
                "message": result["message"],
                "status": "complete" if result["success"] else "failed",
                "success": result["success"]
            })
        }
        
    except Exception as e:
        # Error event
        error_msg = f"Error processing email: {str(e)}"
        logger.error(error_msg)
        yield {
            "event": "error",
            "id": client_id,
            "data": json.dumps({
                "message": error_msg,
                "status": "failed",
                "success": False
            })
        }
    
    finally:
        # Clean up connection
        if client_id in active_connections:
            del active_connections[client_id]


# FastMCP Endpoints
@app.post("/email/send/sse")
async def send_email_sse_endpoint(request: MCP_Request) -> MCP_EventSourceResponse:
    """SSE endpoint to send an email with real-time updates"""
    try:
        # Parse request body
        data = request.json
        
        # Validate required fields
        required_fields = ["subject", "body", "receivers"]
        for field in required_fields:
            if field not in data:
                return MCP_Response(
                    status_code=400,
                    content=json.dumps({
                        "success": False,
                        "message": f"Missing required field: {field}"
                    })
                )
        
        # Generate unique client ID
        client_id = str(uuid.uuid4())
        
        # Return SSE response
        return MCP_EventSourceResponse(event_generator(client_id, data))
        
    except Exception as e:
        logger.error(f"Unexpected error in send_email_sse_endpoint: {e}")
        return MCP_Response(
            status_code=500,
            content=json.dumps({
                "success": False,
                "message": f"Server error: {str(e)}"
            })
        )

@app.post("/email/send")
async def send_email_endpoint(request: MCP_Request) -> MCP_Response:
    """Regular endpoint to send an email (non-SSE)"""
    try:
        # Parse request body
        data = request.json
        
        # Validate required fields
        required_fields = ["subject", "body", "receivers"]
        for field in required_fields:
            if field not in data:
                return MCP_Response(
                    status_code=400,
                    content=json.dumps({
                        "success": False,
                        "message": f"Missing required field: {field}"
                    })
                )
        
        # Send the email
        result = EmailService.send_email(
            subject=data["subject"],
            body=data["body"],
            receivers=data["receivers"],
            sender=data.get("sender"),
            content_type=data.get("content_type", "html")
        )
        
        # Return response
        status_code = 200 if result["success"] else 500
        return MCP_Response(
            status_code=status_code,
            content=json.dumps(result)
        )
        
    except Exception as e:
        logger.error(f"Unexpected error in send_email_endpoint: {e}")
        return MCP_Response(
            status_code=500,
            content=json.dumps({
                "success": False,
                "message": f"Server error: {str(e)}"
            })
        )

@app.get("/health")
async def health_check(request: MCP_Request) -> MCP_Response:
    """Health check endpoint"""
    return MCP_Response(
        status_code=200,
        content=json.dumps({
            "status": "healthy",
            "service": "email-service",
            "environment": ENV,
            "active_connections": len(active_connections)
        })
    )

# Run the server
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Email MCP Server in {ENV} environment")
    uvicorn.run("email_service:app", host="0.0.0.0", port=8000, reload=True)














import json
import sseclient
import requests

class EmailSSEClient:
    """
    Client for the Email MCP Service using Server-Sent Events (SSE)
    """
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.sse_endpoint = f"{base_url}/email/send/sse"
        
    def send_email_with_updates(self, email_data, callback=None):
        """
        Send an email using SSE to get real-time updates
        
        Args:
            email_data: Dict containing email data (subject, body, receivers)
            callback: Optional callback function to process events
            
        Returns:
            Dict with final result
        """
        headers = {'Content-Type': 'application/json'}
        
        # Make initial request to start SSE connection
        response = requests.post(
            self.sse_endpoint,
            data=json.dumps(email_data),
            headers=headers,
            stream=True  # Important for SSE
        )
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                return {
                    "success": False,
                    "message": error_data.get("message", "Request failed")
                }
            except:
                return {
                    "success": False, 
                    "message": f"Request failed with status code {response.status_code}"
                }
        
        # Process SSE events
        client = sseclient.SSEClient(response)
        final_result = None
        
        try:
            for event in client.events():
                # Parse event data
                data = json.loads(event.data)
                event_type = event.event or "message"
                
                # Call the callback if provided
                if callback:
                    callback(event_type, data)
                else:
                    # Default printing of events
                    print(f"Event: {event_type} - {data['message']}")
                
                # Store final result when complete
                if event_type == "complete":
                    final_result = data
                    break
                
                # Exit on error
                if event_type == "error":
                    final_result = data
                    break
                    
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing SSE events: {str(e)}"
            }
        finally:
            client.close()
            
        return final_result or {"success": False, "message": "No final result received"}


# Example usage
def event_callback(event_type, data):
    """Custom callback to handle events"""
    status_emoji = "🟡"
    if data["status"] == "complete":
        status_emoji = "✅"
    elif data["status"] == "failed":
        status_emoji = "❌"
        
    print(f"{status_emoji} {event_type.upper()}: {data['message']}")


def send_test_email():
    """Example function to test the email SSE client"""
    # Create client
    client = EmailSSEClient()
    
    # Example email data
    email_data = {
        "subject": "This is a test email",
        "body": "<h3>Hello!</h3><p>This is a test email sent via the Email MCP Service with SSE updates.</p>",
        "receivers": "gentela.vnsaipavan@carelon.com",
        "content_type": "html"
    }
    
    print("Sending email with real-time updates...")
    
    # Send email with custom callback
    result = client.send_email_with_updates(email_data, callback=event_callback)
    
    if result["success"]:
        print("\nEmail sent successfully!")
    else:
        print(f"\nFailed to send email: {result['message']}")


if __name__ == "__main__":
    send_test_email()

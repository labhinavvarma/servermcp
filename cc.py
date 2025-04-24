from flask import Flask, request, jsonify
from mcp_sdk import mcp_tool, register_tool
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from ReduceReuseRecycleGENAI import get_ser_conn
import time
import socket
import threading
import os
import signal
import sys
from typing import Dict, Any, List, Optional
import json

# Configuration
ENV = "preprod"
REGION_NM = "us-east-1"
APPLICATION_CODE = "aedl"
SERVER_PORT = 8080
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
CONNECTION_TIMEOUT = 30  # seconds
MAX_CONNECTIONS = 100  # Maximum concurrent connections

# Configure logging
os.makedirs("logs", exist_ok=True)
logger.remove()  # Remove default handler
logger.add(
    "logs/mcp_server.log",
    rotation="10 MB",
    compression="zip",
    level="DEBUG",
    backtrace=True,
    diagnose=True
)
logger.add(sys.stderr, level="INFO")

# Initialize Flask app
app = Flask(__name__)

# Connection management
active_connections = 0
connection_lock = threading.Lock()

# Health metrics
server_metrics = {
    "start_time": time.time(),
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "active_connections": 0,
    "smtp_errors": 0
}
metrics_lock = threading.Lock()

def update_metrics(key: str, increment: int = 1):
    """Update server metrics safely."""
    with metrics_lock:
        if key in server_metrics:
            server_metrics[key] += increment


class ConnectionManager:
    """Context manager for tracking active connections."""
    
    def __enter__(self):
        global active_connections
        with connection_lock:
            if active_connections >= MAX_CONNECTIONS:
                logger.warning(f"Connection limit reached: {active_connections}/{MAX_CONNECTIONS}")
                raise ConnectionError("Server connection limit reached")
            active_connections += 1
            update_metrics("active_connections", 1)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        global active_connections
        with connection_lock:
            active_connections -= 1
            update_metrics("active_connections", -1)


@mcp_tool(
    name="send_test_email",
    description="Sends an HTML email via SMTP using enterprise connection with improved stability."
)
def send_test_email(subject: str, body: str, receivers: str) -> Dict[str, Any]:
    """
    Send HTML email with improved error handling and connection management.
    
    Args:
        subject: Email subject
        body: HTML email body
        receivers: Comma-separated list of recipient email addresses
        
    Returns:
        Status message indicating success or failure with details
    """
    update_metrics("total_requests")
    request_id = f"req-{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] Email request received")
    
    try:
        with ConnectionManager():
            # Parse recipients
            try:
                recipients = [email.strip() for email in receivers.split(",") if email.strip()]
                if not recipients:
                    logger.error(f"[{request_id}] No valid recipients provided")
                    update_metrics("failed_requests")
                    return {"status": "error", "message": "No valid recipients provided"}
            except Exception as e:
                logger.error(f"[{request_id}] Failed to parse recipients: {e}")
                update_metrics("failed_requests")
                return {"status": "error", "message": f"Failed to parse recipients: {e}"}
            
            # Set up email message
            try:
                sender = 'noreply-vkhvkm'
                
                msg = MIMEMultipart()
                msg['Subject'] = subject
                msg['From'] = sender
                msg['To'] = ', '.join(recipients)
                msg.attach(MIMEText(body, 'html'))
                
                message_string = msg.as_string()
            except Exception as e:
                logger.error(f"[{request_id}] Failed to create email message: {e}")
                update_metrics("failed_requests")
                return {"status": "error", "message": f"Failed to create email message: {e}"}
            
            # Send email with retry logic
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(f"[{request_id}] Connecting to SMTP server (attempt {attempt}/{MAX_RETRIES})...")
                    
                    # Set connection timeout
                    socket.setdefaulttimeout(CONNECTION_TIMEOUT)
                    
                    # Get connection with detailed logging
                    smtpObj = get_ser_conn(
                        logger, 
                        env=ENV, 
                        region_name=REGION_NM, 
                        aplctn_cd=APPLICATION_CODE, 
                        port=None, 
                        tls=True, 
                        debug=(attempt == MAX_RETRIES)  # Enable debug mode on final attempt
                    )
                    
                    # Log connection success
                    logger.info(f"[{request_id}] SMTP connection established successfully")
                    
                    # Send email
                    smtpObj.sendmail(sender, recipients, message_string)
                    
                    # Close connection properly
                    try:
                        smtpObj.quit()
                    except Exception as close_err:
                        logger.warning(f"[{request_id}] Non-critical error during SMTP disconnect: {close_err}")
                    
                    logger.info(f"[{request_id}] Email sent successfully")
                    update_metrics("successful_requests")
                    return {"status": "success", "message": "Email sent successfully", "request_id": request_id}
                    
                except (socket.timeout, ConnectionRefusedError) as conn_err:
                    logger.error(f"[{request_id}] Connection error (attempt {attempt}/{MAX_RETRIES}): {conn_err}")
                    if attempt < MAX_RETRIES:
                        logger.info(f"[{request_id}] Retrying in {RETRY_DELAY} seconds...")
                        time.sleep(RETRY_DELAY)
                    else:
                        update_metrics("failed_requests")
                        update_metrics("smtp_errors")
                        return {
                            "status": "error", 
                            "message": f"Connection error after {MAX_RETRIES} attempts: {conn_err}",
                            "request_id": request_id
                        }
                        
                except Exception as e:
                    logger.error(f"[{request_id}] Error sending email (attempt {attempt}/{MAX_RETRIES}): {e}")
                    if attempt < MAX_RETRIES:
                        logger.info(f"[{request_id}] Retrying in {RETRY_DELAY} seconds...")
                        time.sleep(RETRY_DELAY)
                    else:
                        update_metrics("failed_requests")
                        update_metrics("smtp_errors")
                        return {
                            "status": "error", 
                            "message": f"Error sending email after {MAX_RETRIES} attempts: {e}",
                            "request_id": request_id
                        }
    
    except ConnectionError as e:
        logger.error(f"[{request_id}] Server connection limit reached: {e}")
        update_metrics("failed_requests")
        return {"status": "error", "message": str(e), "request_id": request_id}
        
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {e}")
        update_metrics("failed_requests")
        return {"status": "error", "message": f"Unexpected error: {e}", "request_id": request_id}


@mcp_tool(
    name="health_check",
    description="Check server health and connectivity"
)
def health_check() -> Dict[str, Any]:
    """
    Performs basic health check of the server and its dependencies.
    
    Returns:
        Status message with server health information
    """
    request_id = f"health-{int(time.time() * 1000)}"
    logger.info(f"[{request_id}] Health check requested")
    
    # Calculate uptime
    uptime = time.time() - server_metrics["start_time"]
    
    # Check SMTP connectivity
    smtp_status = "unknown"
    smtp_error = None
    
    try:
        socket.setdefaulttimeout(10)
        smtpObj = get_ser_conn(
            logger, 
            env=ENV, 
            region_name=REGION_NM, 
            aplctn_cd=APPLICATION_CODE, 
            port=None, 
            tls=True, 
            debug=False
        )
        smtpObj.noop()  # NOOP command to test connection
        smtpObj.quit()
        smtp_status = "connected"
    except Exception as e:
        smtp_status = "disconnected"
        smtp_error = str(e)
        logger.error(f"[{request_id}] SMTP health check failed: {e}")
    
    # Get current metrics
    with metrics_lock:
        current_metrics = server_metrics.copy()
    
    # Return server status
    health_data = {
        "status": "healthy" if smtp_status == "connected" else "degraded",
        "environment": ENV,
        "region": REGION_NM,
        "timestamp": time.time(),
        "uptime_seconds": uptime,
        "smtp_status": smtp_status,
        "metrics": current_metrics
    }
    
    if smtp_error:
        health_data["smtp_error"] = smtp_error
    
    logger.info(f"[{request_id}] Health check completed: {health_data['status']}")
    return health_data


# Register API routes with Flask
@app.route('/send_test_email', methods=['POST'])
def api_send_test_email():
    """API endpoint for send_test_email tool."""
    try:
        data = request.json
        subject = data.get('subject', '')
        body = data.get('body', '')
        receivers = data.get('receivers', '')
        
        result = send_test_email(subject, body, receivers)
        return jsonify(result)
    except Exception as e:
        logger.error(f"API error in send_test_email: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health_check', methods=['GET'])
def api_health_check():
    """API endpoint for health_check tool."""
    try:
        result = health_check()
        status_code = 200 if result["status"] == "healthy" else 503
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"API error in health_check: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Graceful shutdown handler
def shutdown_server(signum, frame):
    """Handle graceful server shutdown."""
    logger.info(f"Received signal {signum}, shutting down...")
    # Perform cleanup
    logger.info("Server shutdown complete")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, shutdown_server)
signal.signal(signal.SIGINT, shutdown_server)


if __name__ == "__main__":
    # Register MCP tools with the MCP SDK
    register_tool(send_test_email)
    register_tool(health_check)
    
    logger.info(f"Starting MCP server on port {SERVER_PORT}")
    
    # Start the server with increased worker threads
    from waitress import serve
    serve(app, host="0.0.0.0", port=SERVER_PORT, threads=20)



############client#################################
import requests
import time
import json
import logging
import socket
import os
from typing import Dict, Any, Optional, Union, List

# Setup client logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/mcp_client.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp_client")

class MCPClient:
    """
    Client for interacting with MCP server with robust connection handling.
    """
    
    def __init__(
        self, 
        server_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 5,
        retry_delay: int = 2,
        retry_backoff_factor: float = 1.5,
        verify_ssl: bool = True
    ):
        """
        Initialize MCP client.
        
        Args:
            server_url: URL of the MCP server
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of connection retry attempts
            retry_delay: Initial delay between retries in seconds
            retry_backoff_factor: Multiplicative factor for retry delay
            verify_ssl: Whether to verify SSL certificates
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff_factor = retry_backoff_factor
        self.verify_ssl = verify_ssl
        
        # Client ID for tracking requests
        self.client_id = f"client-{int(time.time())}"
        
        # Session for connection pooling
        self.session = requests.Session()
        
        # Add default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'MCPClient/1.0 ({self.client_id})'
        })
        
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
        
        logger.info(f"Client initialized: {self.client_id}")
    
    def _make_request(
        self, 
        endpoint: str, 
        method: str = 'GET',
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to MCP server with retry logic.
        
        Args:
            endpoint: API endpoint
            method: HTTP method (GET, POST, etc.)
            params: URL parameters
            data: Request body data
            timeout: Custom timeout for this request (overrides instance timeout)
            
        Returns:
            Response data as dictionary
        """
        url = f"{self.server_url}/{endpoint.lstrip('/')}"
        json_data = json.dumps(data) if data else None
        request_timeout = timeout or self.timeout
        request_id = f"{self.client_id}-{int(time.time() * 1000)}"
        
        logger.info(f"[{request_id}] Starting request to {endpoint}")
        
        current_delay = self.retry_delay
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[{request_id}] Making {method} request to {url} (attempt {attempt}/{self.max_retries})")
                
                # Set a socket timeout as a safety net
                socket.setdefaulttimeout(request_timeout + 5)
                
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    data=json_data,
                    timeout=request_timeout,
                    verify=self.verify_ssl
                )
                
                # Log response status
                logger.info(f"[{request_id}] Response status: {response.status_code}")
                
                # Raise exception for HTTP errors
                response.raise_for_status()
                
                try:
                    result = response.json()
                    logger.info(f"[{request_id}] Request successful")
                    return result
                except ValueError:
                    logger.warning(f"[{request_id}] Response not JSON: {response.text[:100]}...")
                    return {"status": "success", "raw_response": response.text}
                
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                logger.error(f"[{request_id}] Connection error (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    logger.info(f"[{request_id}] Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= self.retry_backoff_factor  # Exponential backoff
                    
            except requests.exceptions.Timeout as e:
                last_exception = e
                logger.error(f"[{request_id}] Request timeout (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    logger.info(f"[{request_id}] Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= self.retry_backoff_factor
                    
            except requests.exceptions.HTTPError as e:
                last_exception = e
                logger.error(f"[{request_id}] HTTP error: {e}")
                
                # Don't retry on client errors (4xx) except for 429 (Too Many Requests)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    try:
                        error_data = e.response.json()
                        logger.error(f"[{request_id}] Server error response: {error_data}")
                        return error_data
                    except ValueError:
                        raise
                
                if attempt < self.max_retries:
                    # Use server-suggested retry time for 429 errors if available
                    if e.response.status_code == 429 and 'Retry-After' in e.response.headers:
                        retry_after = int(e.response.headers['Retry-After'])
                        logger.info(f"[{request_id}] Server requested retry after {retry_after} seconds")
                        time.sleep(retry_after)
                    else:
                        logger.info(f"[{request_id}] Retrying in {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= self.retry_backoff_factor
                else:
                    raise
                    
            except Exception as e:
                last_exception = e
                logger.error(f"[{request_id}] Unexpected error (attempt {attempt}/{self.max_retries}): {e}")
                if attempt < self.max_retries:
                    logger.info(f"[{request_id}] Retrying in {current_delay} seconds...")
                    time.sleep(current_delay)
                    current_delay *= self.retry_backoff_factor
                else:
                    raise
        
        # If we got here, all retries failed
        logger.error(f"[{request_id}] All {self.max_retries} attempts failed")
        if last_exception:
            raise last_exception
        else:
            raise ConnectionError(f"Failed to connect to MCP server after {self.max_retries} attempts")
    
    def check_server_health(self) -> Dict[str, Any]:
        """
        Check if the MCP server is healthy.
        
        Returns:
            Server health status information
        """
        logger.info("Checking server health...")
        return self._make_request('health_check', method='GET')
    
    def send_email(
        self,
        subject: str,
        body: str,
        receivers: Union[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Send HTML email via MCP server.
        
        Args:
            subject: Email subject
            body: HTML email body
            receivers: Comma-separated string or list of recipient email addresses
            
        Returns:
            Response from the server
        """
        # Convert list of receivers to comma-separated string if needed
        if isinstance(receivers, list):
            receivers = ",".join(receivers)
            
        logger.info(f"Sending email to {receivers}")
        
        data = {
            'subject': subject,
            'body': body,
            'receivers': receivers
        }
        
        return self._make_request('send_test_email', method='POST', data=data)
    
    def wait_for_server(self, max_attempts: int = 30, delay: int = 10) -> bool:
        """
        Wait for server to become available and healthy.
        
        Args:
            max_attempts: Maximum number of health check attempts
            delay: Delay between attempts in seconds
            
        Returns:
            True if server became healthy, False otherwise
        """
        logger.info(f"Waiting for server to become available (max {max_attempts} attempts)...")
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Health check attempt {attempt}/{max_attempts}...")
                health = self.check_server_health()
                
                if health.get("status") == "healthy":
                    logger.info("Server is healthy!")
                    return True
                else:
                    logger.warning(f"Server is not healthy: {health.get('status')}")
                
            except Exception as e:
                logger.error(f"Health check failed (attempt {attempt}/{max_attempts}): {e}")
            
            if attempt < max_attempts:
                logger.info(f"Waiting {delay} seconds before next attempt...")
                time.sleep(delay)
        
        logger.error(f"Server did not become healthy after {max_attempts} attempts")
        return False
    
    def close(self):
        """Close the client session."""
        logger.info(f"Closing client {self.client_id}")
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Example usage
if __name__ == "__main__":
    try:
        # Create client
        client = MCPClient(
            server_url="http://localhost:8080",
            timeout=30,
            max_retries=3
        )
        
        # Wait for server to be available
        if client.wait_for_server(max_attempts=5, delay=5):
            # Check server health
            health = client.check_server_health()
            print(f"Server health: {health['status']}")
            
            # Send test email
            result = client.send_email(
                subject="Test Email",
                body="<h1>Hello World</h1><p>This is a test email from the MCP client.</p>",
                receivers="test@example.com"
            )
            print(f"Email result: {result['status']}")
        else:
            print("Server is not available. Please check server status.")
        
    except Exception as e:
        print(f"Error: {e}")
        
    finally:
        # Ensure client is closed
        client.close()

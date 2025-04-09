#!/usr/bin/env python3
"""
SMTP MCP Server for Claude
This MCP server allows Claude to send emails via SMTP protocol.
"""

import os
import logging
import smtplib
import json
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import FastMCP from the correct module
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        # Try the alternate import path
        from fastmcp import FastMCP
    except ImportError:
        print("ERROR: Required modules not found. Please install with:")
        print("pip install mcp-sdk fastmcp")
        exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("smtp-mcp")

# Initialize the MCP server with the name "smtp"
logger.info("Starting SMTP MCP Server...")
mcp = FastMCP("smtp")

# Default configuration (can be overridden)
# For Docker, use a path that's in a mounted volume
DEFAULT_CONFIG_PATH = os.environ.get('CONFIG_PATH', '/app/config/smtp_config.json')
if not os.path.exists(os.path.dirname(DEFAULT_CONFIG_PATH)):
    # Fall back to home directory if the container path doesn't exist
    DEFAULT_CONFIG_PATH = os.path.expanduser("~/.smtp_mcp_config.json")

DEFAULT_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "use_tls": True,
    "email": "",  # Empty by default for security
    "password": ""  # Empty by default for security
}

def load_config():
    """Load SMTP configuration from file or use defaults."""
    try:
        if os.path.exists(DEFAULT_CONFIG_PATH):
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded config from {DEFAULT_CONFIG_PATH}")
                return config
        else:
            logger.warning(f"Config file not found at {DEFAULT_CONFIG_PATH}, using defaults")
            return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save SMTP configuration to file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DEFAULT_CONFIG_PATH), exist_ok=True)
        
        with open(DEFAULT_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved config to {DEFAULT_CONFIG_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {str(e)}")
        return False

# Load initial configuration
config = load_config()

@mcp.tool()
def configure_smtp(smtp_server: str = "", smtp_port: int = 0, 
                  use_tls: bool = True, email: str = "", password: str = "") -> str:
    """
    Configure SMTP server settings for sending emails.
    
    Args:
        smtp_server: SMTP server hostname (e.g., smtp.gmail.com)
        smtp_port: SMTP server port (e.g., 587 for TLS, 465 for SSL)
        use_tls: Whether to use TLS encryption
        email: Email address to send from
        password: Email password or app password
        
    Returns:
        A confirmation message
    """
    global config
    
    # Only update values that were provided
    if smtp_server:
        config["smtp_server"] = smtp_server
    if smtp_port:
        config["smtp_port"] = smtp_port
    if email:
        config["email"] = email
    if password:
        config["password"] = password
    
    config["use_tls"] = use_tls
    
    # Save the updated configuration
    if save_config(config):
        return f"SMTP configuration updated successfully. Server: {config['smtp_server']}, Port: {config['smtp_port']}, Email: {config['email']}"
    else:
        return "Failed to save SMTP configuration."

@mcp.tool()
def test_smtp_connection() -> str:
    """
    Test the SMTP server connection with configured settings.
    
    Returns:
        A success or error message
    """
    try:
        # Create an SMTP connection
        smtp_conn = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
        
        # Start TLS if configured
        if config["use_tls"]:
            smtp_conn.starttls()
        
        # Login if credentials are provided
        if config["email"] and config["password"]:
            smtp_conn.login(config["email"], config["password"])
        
        # Quit the connection
        smtp_conn.quit()
        
        return f"Successfully connected to SMTP server: {config['smtp_server']}:{config['smtp_port']}"
    except Exception as e:
        logger.error(f"SMTP connection test failed: {str(e)}")
        return f"Failed to connect to SMTP server: {str(e)}"

@mcp.tool()
def send_email(to: str, subject: str, body: str, html_body: str = "", cc: str = "", bcc: str = "") -> str:
    """
    Send an email using the configured SMTP settings.
    
    Args:
        to: Recipient email address(es), comma-separated for multiple
        subject: Email subject line
        body: Plain text email body
        html_body: Optional HTML email body
        cc: Optional CC recipients, comma-separated
        bcc: Optional BCC recipients, comma-separated
        
    Returns:
        A success or error message
    """
    # Verify configuration
    if not config["smtp_server"] or not config["email"] or not config["password"]:
        return "SMTP is not fully configured. Use configure_smtp tool first."
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config["email"]
        msg["To"] = to
        
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        
        # Add plain text body
        msg.attach(MIMEText(body, "plain"))
        
        # Add HTML body if provided
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        
        # Determine all recipients
        all_recipients = [addr.strip() for addr in to.split(",")]
        if cc:
            all_recipients.extend([addr.strip() for addr in cc.split(",")])
        if bcc:
            all_recipients.extend([addr.strip() for addr in bcc.split(",")])
        
        # Connect to SMTP server
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as smtp_conn:
            if config["use_tls"]:
                smtp_conn.starttls()
            
            smtp_conn.login(config["email"], config["password"])
            smtp_conn.send_message(msg)
        
        logger.info(f"Email sent to {to}")
        return f"Email sent successfully to {to}"
    
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return f"Failed to send email: {str(e)}"

@mcp.tool()
def get_smtp_config() -> str:
    """
    Get the current SMTP configuration (excludes password).
    
    Returns:
        Current SMTP configuration as a string
    """
    # Create a copy without the password for security
    safe_config = config.copy()
    safe_config["password"] = "********" if safe_config["password"] else ""
    
    return json.dumps(safe_config, indent=2)

if __name__ == "__main__":
    logger.info(f"SMTP MCP Server initialized with config: {config['smtp_server']}:{config['smtp_port']}")
    
    # If no email is configured, log a warning
    if not config["email"] or not config["password"]:
        logger.warning("SMTP credentials not configured. Use configure_smtp tool to set up.")
    
    # Command-line arguments for transport control
    parser = argparse.ArgumentParser(description='Run SMTP MCP Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (for HTTP transport)')
    parser.add_argument('--port', type=int, default=5000, help='Port to listen on (for HTTP transport)')
    parser.add_argument('--transport', choices=['stdio', 'http'], default='stdio',
                      help='Transport protocol to use (stdio or http)')
    
    args = parser.parse_args()
    
    # Run the MCP server using the specified transport
    if args.transport == 'http':
        logger.info(f"Starting MCP server with HTTP transport on {args.host}:{args.port}")
        mcp.run(transport='http', host=args.host, port=args.port)
    else:
        logger.info("Starting MCP server with stdio transport")
        mcp.run(transport='stdio')
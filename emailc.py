import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

# MCP server SSE endpoint
SERVER_URL = "http://localhost:8000/sse"  # Change this if your server is remote

# Email request payload
email_payload = {
    "subject": "MCP Email Test",
    "body": "<h3>Hello from MCP!</h3><p>This is a test email.</p>",
    "receivers": "your.email@domain.com"  # Change to a valid recipient
}

# Tool name exactly as defined
TOOL_NAME = "mcp-send-email"

async def run():
    print("Connecting to MCP server...")
    async with sse_client(url=SERVER_URL) as connection:
        async with ClientSession(*connection) as session:
            await session.initialize()
            print("✓ Session initialized")

            # Invoke the email tool
            response = await session.invoke_tool(TOOL_NAME, email_payload)

            print("\n🟢 Tool Invocation Response:")
            print(response)

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(run())

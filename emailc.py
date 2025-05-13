import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

# --- Apply patch to allow nested asyncio in interactive environments
nest_asyncio.apply()

# --- MCP Server SSE URL
SERVER_URL = "http://localhost:8000/sse"  # change to your EC2 public IP if needed

# --- Email tool parameters
email_payload = {
    "subject": "Test Email from MCP",
    "body": "<p>This is a <b>test email</b> sent via MCP tool.</p>",
    "receivers": "someone@example.com"  # replace with a real email
}

# --- Tool name exactly as registered
TOOL_NAME = "mcp-send-email"

async def run():
    print("🔌 Connecting to:", SERVER_URL)
    async with sse_client(url=SERVER_URL) as connection:
        async with ClientSession(*connection) as session:
            await session.initialize()
            print("✅ MCP session initialized")

            # Call the MCP tool
            result = await session.invoke_tool(TOOL_NAME, email_payload)

            print("\n📬 Email Tool Result:")
            print(result)

# --- Entry point
if __name__ == "__main__":
    asyncio.run(run())

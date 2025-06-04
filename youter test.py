from fastapi import FastAPI, APIRouter, HTTPException
from mcp import ClientSession
from mcp.client.sse import sse_client

# Define the router
router = APIRouter()

@router.get("/mcp/connect", summary="Connect to MCP SSE server and create session")
async def connect_mcp_sse():
    """
    Connects to the MCP SSE server and initializes a client session.
    """
    server_url = "http://10.126.192.183:8001/sse"

    try:
        async with sse_client(url=server_url) as sse_connection:
            print("✅ SSE connection established")

            async with ClientSession(*sse_connection) as session:
                print("✅ MCP ClientSession started")
                return {
                    "status": "✅ MCP SSE connection and session established",
                    "server": server_url
                }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ MCP connection failed: {str(e)}")

# Set up FastAPI app and include router
app = FastAPI(title="MCP SSE Connector")
app.include_router(router)

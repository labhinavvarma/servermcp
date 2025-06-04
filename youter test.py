from fastapi import FastAPI, APIRouter
import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

# Initialize FastAPI app and router
app = FastAPI(title="MCP Client Connector")
router = APIRouter()

# ✅ Replace with your EC2 MCP server's public IP and port
EC2_MCP_SERVER_URL = "http://<YOUR_EC2_PUBLIC_IP>:8001/sse"  # Example: http://3.110.45.78:8001/sse

@router.get("/connect-mcp")
async def connect_to_mcp():
    """
    Establish a client session with the MCP server running on EC2 via SSE.
    """
    try:
        async with sse_client(url=EC2_MCP_SERVER_URL) as sse_connection:
            async with ClientSession(*sse_connection) as session:
                # Optionally log or perform actions with the session
                return {"status": "✓ Connected to MCP on EC2"}
    except Exception as e:
        return {"error": str(e)}

# Mount the router to the app
app.include_router(router)

# Run this app manually (e.g., python app.py)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

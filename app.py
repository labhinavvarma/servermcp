import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport
from starlette.routing import Mount
import logging
from loguru import logger

# Import your MCP server implementation
from server_implementation import mcp, analyze

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create FastAPI app
app = FastAPI(title="DataFlyWheel MCP Analyzer")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up SSE transport for MCP
sse = SseServerTransport("/messages")
app.router.routes.append(Mount("/messages", app=sse.handle_post_message))

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint to verify the server is running"""
    return {"message": "DataFlyWheel MCP Analyzer is running"}

@app.get("/messages", tags=["MCP"], include_in_schema=True)
def messages_docs(session_id: str):
    """
    Messages endpoint for SSE communication
    This endpoint is used for posting messages to SSE clients.
    Note: This route is for documentation purposes only.
    The actual implementation is handled by the SSE transport.
    """
    pass  # This is just for documentation, the actual handler is mounted above

@app.get("/sse", tags=["MCP"])
async def handle_sse(request: Request):
    """
    SSE endpoint that connects to the MCP server
    This endpoint establishes a Server-Sent Events connection with the client
    and forwards communication to the Model Context Protocol server.
    """
    logger.info("New SSE connection established")
    # Use sse.connect_sse to establish an SSE connection with the MCP server
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        # Run the MCP server with the established streams
        logger.info("Running MCP server with SSE streams")
        await mcp._mcp_server.run(
            read_stream,
            write_stream,
            mcp._mcp_server.create_initialization_options(),
        )

# Add a traditional REST endpoint as a fallback for the analyze function
@app.post("/analyze", tags=["Analysis"])
async def analyze_endpoint(request: Request):
    """
    Traditional REST endpoint for the analyze function
    This provides compatibility with clients that can't use the MCP protocol
    """
    data = await request.json()
    if "data" in data and "operation" in data:
        result = await analyze(data["data"], data["operation"])
        return result
    else:
        return {"status": "error", "error": "Missing data or operation parameter"}

# Include your other routes if needed
# from router import route
# app.include_router(route)

if __name__ == "__main__":
    logger.info("Starting MCP Analyzer server on port 8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

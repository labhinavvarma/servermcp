# === SERVER: server_confluence_resource.py ===
"""
FastMCP server exposing Confluence as an MCP Resource and a tool to query it.
Run with:
    python server_confluence_resource.py
"""
from mcp.server.fastmcp import FastMCP, Context
from atlassian import Confluence
from loguru import logger

# Initialize MCP server
mcp = FastMCP("confluence-server")

# Confluence configuration (could also be injected via env or config)
CONF_URL = "https://confluence.elevancehealth.com/"
CONF_TOKEN = "your_confluence_api_token_here"
CONF_SPACE = "EDAEPE"
CONF_PAGES = ["Intake-2024A"]
CONF_BASE_PAGE_URL = "https://confluence.elevancehealth.com/pages/viewpage.action?pageId=524564762"

@mcp.resource(
    name="confluence",
    description="High-priority Confluence RAG Resource",
    priority=1
)
class ConfluenceResource:
    def __init__(self, config: Context):
        # You could use config to pass in credentials
        self.client = Confluence(
            url=CONF_URL.rstrip("/"),
            token=CONF_TOKEN,
            verify_ssl=False
        )
        self.space = CONF_SPACE
        self.pages = CONF_PAGES
        self.base_url = CONF_BASE_PAGE_URL

    async def search(self, query: str) -> str | None:
        for title in self.pages:
            try:
                page = self.client.get_page_by_title(space=self.space, title=title)
                if not page:
                    continue
                page_id = page.get("id")
                content = self.client.get_page_by_id(page_id, expand='body.storage')
                html = content.get("body", {}).get("storage", {}).get("value", "")
                if query.lower() in html.lower():
                    snippet = html[:1000] + '...' if len(html) > 1000 else html
                    return (
                        f"Found in Confluence page '{title}':\n{snippet}\n"
                        f"View: {self.base_url}"
                    )
            except Exception as e:
                logger.error(f"Error searching page {title}: {e}")
                return f"Error searching Confluence: {e}"
        return None

    async def list(self) -> dict:
        return {
            "space": self.space,
            "pages": self.pages,
            "base_url": self.base_url
        }

@mcp.tool(
    name="query_confluence",
    description="Searches Confluence pages and returns relevant content if found."
)
async def query_confluence(confluence: ConfluenceResource, query: str) -> str:
    result = await confluence.search(query)
    return result if result else "No relevant info found in Confluence."

# Start the MCP server in SSE mode
if __name__ == "__main__":
    print("🚀 MCP Confluence Resource Server running (SSE)...", flush=True)
    mcp.run(transport="sse")


# === CLIENT: client_confluence_query.py ===
"""
SSE client to invoke the query_confluence tool using the Confluence resource.
Install aiohttp: pip install aiohttp
Run with:
    python client_confluence_query.py
"""
import aiohttp
import asyncio
import json

class SSEClientAgent:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.session = aiohttp.ClientSession()

    async def run_query(self, tool: str, args: dict):
        url = f"{self.base}/{tool}"
        print(f"POSTing to {url} with args: {args}")
        headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
        async with self.session.post(url, json=args, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"HTTP {resp.status}: {text}")
                return
            async for line in resp.content:
                if line.startswith(b"data: "):
                    data = line[6:].decode().strip()
                    if data == '[DONE]':
                        print("✅ Done.")
                        break
                    print(f"📨 {data}")

    async def close(self):
        await self.session.close()

async def main():
    server = "http://<EC2-IP>:8000/sse"  # replace with actual
    agent = SSEClientAgent(server)
    query_text = "example search term"
    await agent.run_query("query_confluence", {"query": query_text})
    await agent.close()

if __name__ == '__main__':
    asyncio.run(main())


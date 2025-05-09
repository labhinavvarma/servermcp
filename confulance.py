from fastmcp import FastMCP
from pydantic import BaseModel
import requests
from atlassian import Confluence

# === Hardcoded Configuration ===
BASE_URL = "https://confluence.elevancehealth.com"
PAT = 

# === Initialize FastMCP server ===
mcp = FastMCP("Confluence MCP Server")

# === Initialize Confluence client with PAT ===
confluence = Confluence(
    url=BASE_URL,
    token=PAT,
    verify_ssl=True  # Set to False if using self-signed certificates
)

# === Define input model for search tool ===
class SearchInput(BaseModel):
    query: str
    limit: int = 10

# === Tool: Search Confluence content ===
@mcp.tool()
def search_confluence(input: SearchInput) -> list:
    """
    Search Confluence content using CQL.
    """
    try:
        cql_query = f'text~"{input.query}"'
        url = f"{BASE_URL}/rest/api/search?cql={cql_query}&limit={input.limit}"
        headers = {
            "Authorization": f"Bearer {PAT}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, verify=True)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return [
                {
                    "title": result.get("title"),
                    "url": f"{BASE_URL}{result.get('_links', {}).get('webui')}"
                }
                for result in results
            ]
        else:
            return [{"error": f"Search failed: {response.status_code} {response.text}"}]
    except Exception as e:
        return [{"error": str(e)}]

# === Resource: Expose Confluence content ===
@mcp.resource()
def confluence_resource(uri: str) -> dict:
    """
    Expose Confluence content as an MCP resource.
    URI format: confluence://<space_key>/<page_title>
    """
    try:
        if not uri.startswith("confluence://"):
            return {"error": "Invalid URI scheme."}
        path = uri[len("confluence://"):]
        parts = path.split("/", 1)
        if len(parts) != 2:
            return {"error": "Invalid URI format. Expected confluence://<space_key>/<page_title>"}
        space_key, page_title = parts
        # Fetch the page by title
        page = confluence.get_page_by_title(space=space_key, title=page_title)
        if page:
            # Retrieve the page content
            content = confluence.get_page_by_id(page_id=page["id"], expand="body.storage")
            return {
                "id": page["id"],
                "title": page["title"],
                "url": f"{BASE_URL}/pages/viewpage.action?pageId={page['id']}",
                "content": content["body"]["storage"]["value"]
            }
        else:
            return {"error": "Page not found."}
    except Exception as e:
        return {"error": str(e)}

# === Run the MCP server ===
if __name__ == "__main__":
    mcp.run()

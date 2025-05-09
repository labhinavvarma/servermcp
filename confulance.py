from atlassian import Confluence
from fastmcp import FastMCP
from pydantic import BaseModel
import requests

# === Hardcoded Configuration ===
BASE_URL = "https://confluence.elevancehealth.com"
PAT = 

# === Initialize Confluence client with PAT ===
confluence = Confluence(
    url=BASE_URL,
    token=PAT,
    verify_ssl=True  # Set to False if using self-signed certificates
)

# === Initialize FastMCP server ===
mcp = FastMCP("Confluence MCP Server")

# === Define input model for get_page tool ===
class PageInput(BaseModel):
    space_key: str
    page_title: str

# === Tool: Test Confluence connection ===
@mcp.tool()
def test_confluence_connection() -> dict:
    """
    Test the Confluence connection using the provided PAT.
    """
    try:
        # Direct REST API call to get current user
        url = f"{BASE_URL}/rest/api/user/current"
        headers = {
            "Authorization": f"Bearer {PAT}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, verify=True)  # Set verify=False if using self-signed certificates
        if response.status_code == 200:
            user_info = response.json()
            return {
                "status": "success",
                "message": f"Connected as {user_info.get('displayName', 'Unknown User')}."
            }
        else:
            return {
                "status": "failure",
                "message": f"Connection failed: {response.status_code} {response.text}"
            }
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Connection failed: {str(e)}"
        }

# === Tool: List all Confluence spaces ===
@mcp.tool()
def list_spaces() -> list:
    """
    List all Confluence spaces.
    """
    try:
        spaces = confluence.get_all_spaces()
        return [{"key": s["key"], "name": s["name"]} for s in spaces.get("results", [])]
    except Exception as e:
        return [{"error": str(e)}]

# === Tool: Retrieve a specific page by space key and title ===
@mcp.tool()
def get_page(input: PageInput) -> dict:
    """
    Retrieve a Confluence page by space key and title.
    """
    try:
        page = confluence.get_page_by_title(space=input.space_key, title=input.page_title)
        if page:
            return {
                "id": page["id"],
                "title": page["title"],
                "url": f"{BASE_URL}/pages/viewpage.action?pageId={page['id']}"
            }
        else:
            return {"error": "Page not found."}
    except Exception as e:
        return {"error": str(e)}

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
        page = confluence.get_page_by_title(space=space_key, title=page_title)
        if page:
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

# === Run the MCP server with startup connection test on port 8000 ===
if __name__ == "__main__":
    # Perform connection test before starting the server
    result = test_confluence_connection()
    if result["status"] == "success":
        print(f"✅ {result['message']}")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp")
    else:
        print(f"❌ {result['message']}")
        # Optionally, exit the program if the connection fails
        # import sys
        # sys.exit(1)

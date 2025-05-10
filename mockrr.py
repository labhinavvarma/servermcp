import streamlit as st
import asyncio
import nest_asyncio
import json
import aiohttp
from mcp import ClientSession
from mcp.client.sse import sse_client

nest_asyncio.apply()
st.set_page_config(page_title="MCP Analyzer", page_icon="📊")

st.title("📊 JSON Analyzer via MCP")

# MCP Server Configuration
server_url = st.sidebar.text_input("MCP Server URL", "http://<YOUR-EC2-IP>:8000/sse")

# Display connection status
async def check_mcp_connection():
    try:
        async with sse_client(url=server_url) as sse_conn:
            async with ClientSession(*sse_conn) as session:
                await session.initialize()
                return True
    except Exception as e:
        st.sidebar.error(f"Connection failed: {e}")
        return False

# Async function to call analyze tool
async def analyze_json(json_data, operation):
    try:
        async with sse_client(url=server_url) as sse_conn:
            async with ClientSession(*sse_conn) as session:
                await session.initialize()
                result = await session.call_tool("analyze", {
                    "data": json_data,
                    "operation": operation
                })
                return result
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Sidebar - Choose Operation
operation = st.sidebar.selectbox("Select Operation", ["sum", "mean", "median", "min", "max"])

# File uploader
uploaded_file = st.file_uploader("Upload a JSON file", type="json")

# Parse and analyze JSON
if uploaded_file:
    try:
        json_content = json.load(uploaded_file)
        st.json(json_content)

        if st.button("Analyze"):
            with st.spinner("Analyzing..."):
                result = asyncio.run(analyze_json(json_content, operation))
            if result["status"] == "success":
                st.success(f"✅ Result: {result['result']}")
            else:
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        st.error(f"Invalid JSON: {e}")

# Show connection status
if st.sidebar.button("Check MCP Connection"):
    if asyncio.run(check_mcp_connection()):
        st.sidebar.success("✅ MCP Server is reachable")
    else:
        st.sidebar.error("❌ MCP Server not reachable")

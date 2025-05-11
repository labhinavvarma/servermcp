import streamlit as st
import asyncio
import nest_asyncio
import json
from typing import Dict, Any, List, Union

from mcp.client.sse import sse_client
from mcp import ClientSession

# Setup
nest_asyncio.apply()
st.set_page_config(page_title="MCP JSON Analyzer", page_icon="📊")

st.title("📊 MCP JSON Analyzer")

# Sidebar: MCP Server
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")
operation = st.sidebar.selectbox("Select Operation", ["sum", "mean", "median", "min", "max", "average"])
show_server_info = st.sidebar.checkbox("🔍 Show MCP Tools Info")

# Upload JSON
uploaded_file = st.file_uploader("Upload JSON File", type=["json"])
json_data = None

if uploaded_file is not None:
    try:
        json_data = json.load(uploaded_file)
        st.json(json_data)
    except Exception as e:
        st.error(f"Invalid JSON file: {e}")
        json_data = None

# Run analysis
async def analyze_with_mcp(json_input: Union[List, Dict], operation: str) -> Dict[str, Any]:
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            return await session.call_tool("analyze", {"data": json_input, "operation": operation})

# Button trigger
if st.button("Run Analysis") and json_data:
    with st.spinner("Analyzing..."):
        try:
            result = asyncio.run(analyze_with_mcp(json_data, operation))
            st.success("Analysis Completed")
            st.write(result)
        except Exception as e:
            st.error(f"Failed to analyze: {e}")

# Optional: Show server info
async def show_mcp_tools():
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            tools = await session.list_tools()
            st.sidebar.markdown("### 🧰 Available Tools:")
            for tool in tools.tools:
                st.sidebar.markdown(f"- **{tool.name}**: {tool.description}")

if show_server_info:
    asyncio.run(show_mcp_tools())

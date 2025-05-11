import streamlit as st
import asyncio
import nest_asyncio
import json
from typing import Dict, Any, List, Union
from mcp.client.sse import sse_client
from mcp import ClientSession

# Enable nested async for Streamlit
nest_asyncio.apply()

# Streamlit page config
st.set_page_config(page_title="MCP JSON Analyzer", page_icon="📊")
st.title("📊 MCP JSON Analyzer")

# Sidebar: MCP Server config
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")
operation = st.sidebar.selectbox("Select Operation", ["sum", "mean", "median", "min", "max", "average"])
show_server_info = st.sidebar.checkbox("🔍 Show MCP Tools")

# File Upload
uploaded_file = st.file_uploader("Upload a JSON file to analyze", type=["json"])
json_data = None

if uploaded_file is not None:
    try:
        json_data = json.load(uploaded_file)
        st.subheader("📄 Uploaded JSON:")
        st.json(json_data)
    except Exception as e:
        st.error(f"❌ Failed to parse JSON: {e}")
        json_data = None

# MCP analyze tool caller
async def analyze_with_mcp(json_input: Union[List, Dict], operation: str) -> Dict[str, Any]:
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            return await session.call_tool("analyze", {"data": json_input, "operation": operation})

# Optional: list tools
async def show_mcp_tools():
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            tools = await session.list_tools()
            st.sidebar.markdown("### 🧰 Available Tools:")
            for tool in tools.tools:
                st.sidebar.markdown(f"- **{tool.name}**: {tool.description}")

if show_server_info:
    try:
        asyncio.run(show_mcp_tools())
    except Exception as e:
        st.sidebar.error(f"Error fetching tools: {e}")

# Run Analysis button
if st.button("▶️ Run Analysis") and json_data:
    with st.spinner("Analyzing..."):
        try:
            result = asyncio.run(analyze_with_mcp(json_data, operation))
            if result.get("status") == "success":
                st.success("✅ Analysis Result")
                st.write(result["result"])
            else:
                st.error("⚠️ Analysis Error")
                st.write(result)
        except Exception as e:
            st.error("❌ Failed to run analyze tool")
            st.exception(e)

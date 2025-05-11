import streamlit as st
import asyncio
import nest_asyncio
import json
from typing import Dict, Any, List, Union

from mcp.client.sse import sse_client
from mcp import ClientSession

# Enable nested event loop for Streamlit
nest_asyncio.apply()

# Streamlit page config
st.set_page_config(page_title="MCP JSON Analyzer", page_icon="📊")
st.title("📊 MCP JSON Analyzer")

# Sidebar: MCP Server input
server_url = st.sidebar.text_input("🔌 MCP Server URL", "http://localhost:8000/sse")
operation = st.sidebar.selectbox("📈 Select Operation", ["sum", "mean", "median", "min", "max", "average"])
show_server_info = st.sidebar.checkbox("🧰 Show Available MCP Tools")

# JSON File Upload
uploaded_file = st.file_uploader("📤 Upload JSON file to analyze", type=["json"])
json_data = None

if uploaded_file is not None:
    try:
        json_data = json.load(uploaded_file)
        st.subheader("📄 Uploaded JSON")
        st.json(json_data)
    except Exception as e:
        st.error(f"❌ Invalid JSON file: {e}")
        json_data = None

# MCP: Call analyze tool
async def analyze_with_mcp(json_input: Union[List, Dict], operation: str) -> Dict[str, Any]:
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            return await session.call_tool("analyze", {"data": json_input, "operation": operation})

# MCP: List available tools
async def show_mcp_tools():
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            tools = await session.list_tools()
            st.sidebar.markdown("### 🧠 Tools")
            for tool in tools.tools:
                st.sidebar.markdown(f"- **{tool.name}**: {tool.description}")

# Show tools if checkbox enabled
if show_server_info:
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(show_mcp_tools())
    except Exception as e:
        st.sidebar.error(f"⚠️ Could not fetch tools: {e}")

# Run analysis
if st.button("▶️ Run Analysis") and json_data:
    with st.spinner("Analyzing..."):
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(analyze_with_mcp(json_data, operation))

            # Show raw result for debugging
            st.subheader("📦 Raw Server Response")
            st.write(result)

            # Parse output
            if result.get("status") == "success":
                st.success("✅ Analysis Result")
                st.subheader("🔍 Result")
                st.json(result["result"])
            else:
                st.error("⚠️ Analysis Error")
                st.write(result.get("error", "Unknown error"))
        except Exception as e:
            st.error("❌ Exception occurred while analyzing")
            st.exception(e)

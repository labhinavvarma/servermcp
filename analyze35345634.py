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

# Sidebar inputs
server_url = st.sidebar.text_input("🔌 MCP Server URL", "http://localhost:8000/sse")
operation = st.sidebar.selectbox("📈 Select Operation", ["sum", "mean", "median", "min", "max", "average"])
show_server_info = st.sidebar.checkbox("🧰 Show Available MCP Tools")

# Upload JSON file
uploaded_file = st.file_uploader("📤 Upload a JSON file to analyze", type=["json"])
json_data = None

if uploaded_file is not None:
    try:
        json_data = json.load(uploaded_file)
        st.subheader("📄 Uploaded JSON")
        st.json(json_data)
    except Exception as e:
        st.error(f"❌ Invalid JSON file: {e}")
        json_data = None

# Async tool call
async def analyze_with_mcp(json_input: Union[List, Dict], operation: str) -> Union[str, Dict[str, Any]]:
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            return await session.call_tool("analyze", {"data": json_input, "operation": operation})

# List tools from server
async def show_mcp_tools():
    async with sse_client(url=server_url) as sse_conn:
        async with ClientSession(*sse_conn) as session:
            await session.initialize()
            tools = await session.list_tools()
            st.sidebar.markdown("### 🧠 Tools")
            for tool in tools.tools:
                st.sidebar.markdown(f"- **{tool.name}**: {tool.description}")

# Display available tools if selected
if show_server_info:
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(show_mcp_tools())
    except Exception as e:
        st.sidebar.error(f"⚠️ Could not fetch tools: {e}")

# Button to run analysis
if st.button("▶️ Run Analysis") and json_data:
    with st.spinner("Analyzing..."):
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(analyze_with_mcp(json_data, operation))

            st.subheader("📦 Raw Server Response")
            st.write(result)

            # Ensure result is a dict
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    st.error("❌ Failed to parse JSON response.")
                    st.stop()

            if isinstance(result, dict) and result.get("status") == "success":
                st.success("✅ Analysis Result")
                st.subheader("🔍 Result")
                st.json(result["result"])
            else:
                st.error("⚠️ Analysis Error")
                st.write(result.get("error", "Unknown error") if isinstance(result, dict) else result)

        except Exception as e:
            st.error("❌ Exception occurred while analyzing")
            st.exception(e)

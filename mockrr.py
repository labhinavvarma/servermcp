import streamlit as st
import asyncio
import nest_asyncio
import json

from mcp.client.sse import sse_client
from mcp import ClientSession
from mcp.client.client import ToolResult
from mcp.client.multi import MultiServerMCPClient

nest_asyncio.apply()
st.set_page_config(page_title="MCP Tool Client", page_icon="🛠️")
st.title("🛠️ MCP Tool Client: Calculator + Analyzer")

# === MCP Server URL ===
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")
mode = st.sidebar.radio("Select Mode", ["Calculator", "JSON Analyzer"], horizontal=True)

# === Core Tool Call Function ===
async def call_mcp_tool(tool_name: str, arguments: dict):
    async with MultiServerMCPClient(
        {"MCPServer": {"url": server_url, "transport": "sse"}}
    ) as client:
        result: ToolResult = await client.call_tool("MCPServer", tool_name, arguments)
        return result.content[0].json()

# === Calculator UI ===
if mode == "Calculator":
    st.subheader("🔢 Calculator Tool")
    expr = st.text_input("Enter Expression (e.g., 3+4*2):")
    if st.button("Evaluate"):
        try:
            output = asyncio.run(call_mcp_tool("calculator", {"expression": expr}))
            st.success("✅ Result")
            st.code(str(output))
        except Exception as e:
            st.error(f"❌ Error: {e}")

# === JSON Analyzer UI ===
elif mode == "JSON Analyzer":
    st.subheader("📊 Analyze JSON Data")
    uploaded_file = st.file_uploader("Upload JSON File", type=["json"])
    operation = st.selectbox("Select Operation", ["sum", "mean", "median", "min", "max", "average"])

    if uploaded_file:
        try:
            json_data = json.load(uploaded_file)
            st.code(json.dumps(json_data, indent=2), language="json")
            if st.button("Run Analysis"):
                try:
                    output = asyncio.run(call_mcp_tool("analyze", {
                        "data": json_data,
                        "operation": operation
                    }))
                    st.success("✅ Analysis Output")
                    st.code(json.dumps(output, indent=2))
                except Exception as e:
                    st.error(f"❌ MCP Tool Error: {e}")
        except Exception as e:
            st.error(f"❌ Invalid JSON: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("📡 MCP Client (No LangGraph)")

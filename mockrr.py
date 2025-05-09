import streamlit as st
import asyncio
import nest_asyncio
import json
import yaml

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain.tools import tool
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI  # Placeholder, won't be used
from langchain.agents.agent_toolkits import Tool
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory

nest_asyncio.apply()
st.set_page_config(page_title="Mock MCP Client", page_icon="🧪")
st.title("🧪 Mock MCP Client: Calculator + Analyzer")

# === MCP Server URL ===
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")
mode = st.sidebar.radio("Mode", ["Calculator", "JSON Analyzer"], horizontal=True)

# === Mock LLM Response ===
class MockLLM:
    def __init__(self):
        self.history = []

    async def ainvoke(self, input_dict):
        messages = input_dict.get("messages", "")
        return {"mock_response": (None, type("Resp", (), {"content": f"Mock LLM received: {messages}"})())}

# === MCP Tool Invocation ===
async def call_tool(tool_name, args):
    async with MultiServerMCPClient(
        {"MockServer": {"url": server_url, "transport": "sse"}}
    ) as client:
        result = await client.call_tool("MockServer", tool_name=tool_name, arguments=args)
        return result.content[0].json()

# === Calculator Mode ===
if mode == "Calculator":
    expr = st.text_input("Enter an arithmetic expression (e.g., 3+5*2):")
    if st.button("Evaluate"):
        try:
            result = asyncio.run(call_tool("calculator", {"expression": expr}))
            st.success(f"✅ {result}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# === Analyzer Mode ===
elif mode == "JSON Analyzer":
    st.subheader("📊 Upload JSON for Analysis")
    uploaded_file = st.file_uploader("Upload JSON", type=["json"])
    operation = st.selectbox("Operation", ["sum", "mean", "median", "min", "max", "average"])

    if uploaded_file:
        try:
            json_data = json.load(uploaded_file)
            st.code(json.dumps(json_data, indent=2), language="json")
            if st.button("Analyze"):
                try:
                    result = asyncio.run(call_tool("analyze", {
                        "data": json_data,
                        "operation": operation
                    }))
                    st.success("✅ Result:")
                    st.code(json.dumps(result, indent=2))
                except Exception as e:
                    st.error(f"❌ Error during analysis: {e}")
        except Exception as e:
            st.error(f"❌ Invalid JSON file: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("MCP Client (Mock Mode)")

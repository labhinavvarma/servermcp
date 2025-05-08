import streamlit as st
import requests
import json
import uuid
import urllib3
import asyncio
import nest_asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

# Enable nested asyncio loop for Streamlit
nest_asyncio.apply()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURATION ===
CORTEX_API_URL = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"
API_KEY = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
APP_ID = "edadip"
APLCTN_CD = "edagnai"
MODEL = "llama3.1-70b"
SYS_MSG = "You are a powerful AI assistant. Provide accurate, concise answers based on context."

MCP_SSE_URL = "http://localhost:8000/sse"

# === INIT STREAMLIT ===
st.set_page_config(page_title="Cortex + MCP Chatbot", page_icon="🤖")
st.title("🤖 Cortex + MCP Chatbot")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "mcp_tools" not in st.session_state:
    st.session_state.mcp_tools = []
    st.session_state.mcp_ready = False

# === MCP TOOL CONNECTION ===
@st.cache_data(show_spinner="Connecting to MCP Server...")
def fetch_mcp_tools():
    async def inner():
        try:
            async with sse_client(MCP_SSE_URL) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    result = await session.call_tool("list-tools", {})
                    tools = json.loads(result.content[0].text).get("tools", [])
                    return tools
        except Exception as e:
            return f"Error: {e}"

    return asyncio.run(inner())

# === FETCH MCP TOOLS ON START ===
if not st.session_state.mcp_ready:
    tools = fetch_mcp_tools()
    if isinstance(tools, list):
        st.session_state.mcp_tools = tools
        st.session_state.mcp_ready = True
        st.success(f"✅ MCP Connected with {len(tools)} tools")
    else:
        st.error(f"❌ MCP Connection Failed: {tools}")

# === INPUT FORM ===
with st.form("chat_form", clear_on_submit=True):
    user_query = st.text_input("Ask a question", key="chat_input", placeholder="e.g. What is 5 + 7?")
    submitted = st.form_submit_button("Send")

# === ROUTING LOGIC ===
def should_use_mcp_tool(question: str) -> bool:
    # Simple keyword-based check — customize for your use case
    keywords = ["analyze", "json", "calculate", "weather", "email"]
    return any(k in question.lower() for k in keywords)

# === HANDLE CHAT SUBMISSION ===
if submitted and user_query:
    if should_use_mcp_tool(user_query):
        # === USE MCP TOOL ===
        async def call_tool():
            try:
                async with sse_client(MCP_SSE_URL) as sse:
                    async with ClientSession(*sse) as session:
                        await session.initialize()
                        result = await session.call_tool("analyze", {"input": user_query})
                        return result.content[0].text
            except Exception as e:
                return f"Error using MCP tool: {e}"

        response_text = asyncio.run(call_tool())
        tool_used = "MCP Tool"
    else:
        # === USE CORTEX ===
        session_id = str(uuid.uuid4())
        payload = {
            "query": {
                "aplctn_cd": APLCTN_CD,
                "app_id": APP_ID,
                "api_key": API_KEY,
                "method": "cortex",
                "model": MODEL,
                "sys_msg": SYS_MSG,
                "limit_convs": "0",
                "prompt": {
                    "messages": [
                        {
                            "role": "user",
                            "content": user_query
                        }
                    ]
                },
                "app_lvl_prefix": "",
                "user_id": "",
                "session_id": session_id
            }
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "Authorization": f'Snowflake Token="{API_KEY}"'
        }

        try:
            response = requests.post(CORTEX_API_URL, headers=headers, json=payload, verify=False)
            if response.status_code == 200:
                raw = response.text
                if "end_of_stream" in raw:
                    answer, _, _ = raw.partition("end_of_stream")
                    response_text = answer.strip()
                else:
                    response_text = raw.strip()
                tool_used = "Cortex"
            else:
                response_text = f"❌ Cortex Error {response.status_code}: {response.text}"
                tool_used = "Cortex"
        except Exception as e:
            response_text = f"❌ Cortex Exception: {str(e)}"
            tool_used = "Cortex"

    # === Save Conversation ===
    st.session_state.messages.append(("user", user_query))
    st.session_state.messages.append(("bot", f"[{tool_used}] {response_text}"))

# === DISPLAY CHAT ===
st.divider()
for role, message in reversed(st.session_state.messages):
    if role == "user":
        st.markdown(f"🧑 **You:** {message}")
    else:
        st.markdown(f"🤖 **Bot:** {message}")

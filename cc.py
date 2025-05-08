import streamlit as st
import requests
import json
import uuid
import asyncio
import nest_asyncio
import yaml
from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_mcp_adapters.client import MultiServerMCPClient

# === Initial Setup ===
nest_asyncio.apply()
st.set_page_config(page_title="Cortex + MCP Chat", page_icon="🤖")
st.title("🤖 Cortex + MCP Chatbot")

# === Cortex LLM Config ===
API_URL = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"
API_KEY = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
APP_ID = "edadip"
APLCTN_CD = "edagnai"
MODEL = "llama3.1-70b"
SYS_MSG = "You are a powerful AI assistant. Provide accurate, concise answers based on context."

# === Session State ===
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_window" not in st.session_state:
    st.session_state.context_window = []
if "yaml_models" not in st.session_state:
    st.session_state.yaml_models = {}

# === MCP Server URL ===
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")

# === YAML Model Viewer ===
async def load_yaml_models():
    models = {}
    try:
        async with sse_client(server_url) as sse:
            async with ClientSession(*sse) as session:
                await session.initialize()
                yaml_content = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                if hasattr(yaml_content, 'contents'):
                    for item in yaml_content.contents:
                        if hasattr(item, 'text'):
                            parsed = yaml.safe_load(item.text)
                            models[item.name] = yaml.dump(parsed, sort_keys=False)
    except Exception as e:
        st.sidebar.error(f"YAML load error: {e}")
    return models

if st.sidebar.button("🔄 Load YAML Models"):
    st.session_state.yaml_models = asyncio.run(load_yaml_models())

if st.session_state.yaml_models:
    selected_yaml = st.sidebar.selectbox("📄 Select YAML Model", list(st.session_state.yaml_models.keys()))
    if selected_yaml:
        st.sidebar.code(st.session_state.yaml_models[selected_yaml], language="yaml")

# === Upload JSON ===
uploaded_file = st.sidebar.file_uploader("📂 Upload JSON for Analyze Tool", type=["json"])
if uploaded_file:
    try:
        uploaded_json = json.load(uploaded_file)
        st.sidebar.success("JSON loaded successfully!")
    except:
        st.sidebar.error("Invalid JSON file")

# === Display Chat History ===
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# === Chat Input ===
query = st.chat_input("Type your question...")

# === Prompt Type Detection ===
def detect_prompt_type(text):
    if any(w in text.lower() for w in ["weather", "forecast", "rain"]):
        return "weather-prompt"
    elif any(w in text.lower() for w in ["hedis", "measure", "cbp", "hcpcs"]):
        return "hedis-prompt"
    elif any(sym in text for sym in ["+", "-", "*", "/", "sqrt", "^"]):
        return "calculator-prompt"
    return "general-prompt"

# === Call Cortex LLM ===
def call_cortex_llm(text, context_window):
    session_id = str(uuid.uuid4())
    history = "\n".join(context_window[-5:])
    full_prompt = f"{SYS_MSG}\n{history}\nUser: {text}"

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
                    {"role": "user", "content": full_prompt}
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
        response = requests.post(API_URL, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            raw = response.text
            if "end_of_stream" in raw:
                answer, _, _ = raw.partition("end_of_stream")
                return answer.strip()
            return raw.strip()
        else:
            return f"❌ Cortex Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"❌ Cortex Exception: {str(e)}"

# === Call MCP Analyze Tool ===
async def call_analyze_tool(data):
    try:
        async with MultiServerMCPClient({"DataFlyWheelServer": {"url": server_url, "transport": "sse"}}) as client:
            result = await client.call_tool("analyze", {"json": data})
            return result.content[0].text, "analyze"
    except Exception as e:
        return f"❌ MCP Error: {e}", "analyze"

# === Process Query ===
if query or uploaded_file:
    st.session_state.messages.append({"role": "user", "content": query if query else "Uploaded JSON analysis"})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Processing...")

        if uploaded_file:
            tool_result, tool_used = asyncio.run(call_analyze_tool(uploaded_json))
            final_output = f"{tool_result}\n\n🛠️ Tool used: `{tool_used}`"
        else:
            prompt_type = detect_prompt_type(query)
            response = call_cortex_llm(query, st.session_state.context_window)
            final_output = response
            st.session_state.context_window.append(f"User: {query}\nBot: {response}")

        placeholder.markdown(final_output)
        st.session_state.messages.append({"role": "assistant", "content": final_output})

# === Clear Chat Button ===
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []
    st.session_state.context_window = []
    st.experimental_rerun()

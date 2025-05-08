import streamlit as st
import requests
import json
import uuid
import asyncio
import nest_asyncio
import yaml
from functools import partial
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
if "mcp_info" not in st.session_state:
    st.session_state.mcp_info = {"resources": [], "tools": [], "prompts": [], "yaml": []}
if "uploaded_json" not in st.session_state:
    st.session_state.uploaded_json = None

# === MCP Server URL ===
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")

# === JSON File Upload ===
uploaded_file = st.sidebar.file_uploader("📂 Upload JSON for Analyze Tool", type=["json"])
if uploaded_file:
    try:
        st.session_state.uploaded_json = json.load(uploaded_file)
        st.sidebar.success("✅ JSON loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Failed to parse JSON: {e}")

# === MCP Metadata Fetch ===
async def fetch_mcp_info():
    result = {"resources": [], "tools": [], "prompts": [], "yaml": []}
    try:
        async with sse_client(server_url) as sse_connection:
            async with ClientSession(*sse_connection) as session:
                await session.initialize()
                resources = await session.list_resources()
                if hasattr(resources, 'resources'):
                    for r in resources.resources:
                        result["resources"].append({"name": r.name, "description": r.description})
                tools = await session.list_tools()
                if hasattr(tools, 'tools'):
                    for t in tools.tools:
                        result["tools"].append({"name": t.name, "description": getattr(t, 'description', 'No description')})
                prompts = await session.list_prompts()
                if hasattr(prompts, 'prompts'):
                    for p in prompts.prompts:
                        args = [f"{arg.name} ({'Required' if arg.required else 'Optional'}): {arg.description}"
                                for arg in getattr(p, 'arguments', [])]
                        result["prompts"].append({
                            "name": p.name,
                            "description": getattr(p, 'description', ''),
                            "args": args
                        })
                try:
                    yaml_content = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                    if hasattr(yaml_content, 'contents'):
                        for item in yaml_content.contents:
                            if hasattr(item, 'text'):
                                parsed = yaml.safe_load(item.text)
                                result["yaml"].append({"name": item.name, "content": yaml.dump(parsed, sort_keys=False)})
                except Exception as e:
                    result["yaml"].append({"name": "YAML Load Error", "content": str(e)})
    except Exception as e:
        st.sidebar.error(f"❌ MCP Error: {e}")
    return result

if st.sidebar.button("🔍 Load MCP Info"):
    st.session_state.mcp_info = asyncio.run(fetch_mcp_info())

# === MCP Info Display ===
with st.sidebar.expander("📦 Resources"):
    for r in st.session_state.mcp_info["resources"]:
        st.markdown(f"**{r['name']}**\n\n{r['description']}")

with st.sidebar.expander("🛠 Tools"):
    for t in st.session_state.mcp_info["tools"]:
        st.markdown(f"**{t['name']}**\n\n{t['description']}")
        tool_name = t['name']
        if st.sidebar.button(f"▶️ Run {tool_name}", key=f"run_{tool_name}"):
            async def run_tool(name):
                try:
                    async with sse_client(server_url) as sse_connection:
                        async with ClientSession(*sse_connection) as session:
                            await session.initialize()
                            result = await session.call_tool(name, {})
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"🛠️ Tool `{name}` executed:\n\n{result.content[0].text}"
                            })
                except Exception as e:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ Tool `{name}` error: {e}"
                    })
            asyncio.run(run_tool(tool_name))

with st.sidebar.expander("🧠 Prompts"):
    for p in st.session_state.mcp_info["prompts"]:
        st.markdown(f"**{p['name']}**\n\n{p['description']}")
        if p["args"]:
            st.markdown("Arguments:")
            for a in p["args"]:
                st.markdown(f"- {a}")

with st.sidebar.expander("📄 YAML Models"):
    for y in st.session_state.mcp_info["yaml"]:
        st.markdown(f"**{y['name']}**")
        st.code(y['content'], language="yaml")

# === Chat Display ===
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# === Chat Input ===
query = st.chat_input("Ask something or describe your task")

# === Prompt Type Detection ===
def detect_prompt_type(text):
    if any(w in text.lower() for w in ["weather", "forecast", "rain"]):
        return "weather-prompt"
    elif any(w in text.lower() for w in ["hedis", "measure", "cbp", "hcpcs"]):
        return "hedis-prompt"
    elif any(sym in text for sym in ["+", "-", "*", "/", "sqrt", "^"]):
        return "calculator-prompt"
    return "general-prompt"

# === Cortex LLM Request ===
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

# === Analyze Tool Request ===
async def call_analyze_tool(data):
    try:
        async with sse_client(server_url) as sse_connection:
            async with ClientSession(*sse_connection) as session:
                await session.initialize()
                result = await session.call_tool("analyze", {"json": data})
                return result.content[0].text
    except Exception as e:
        return f"❌ MCP Analyze Tool Error: {e}"

# === Handle Submission ===
if query or st.session_state.uploaded_json:
    if query:
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("Thinking...")

            prompt_type = detect_prompt_type(query)
            response = call_cortex_llm(query, st.session_state.context_window)
            placeholder.markdown(response)

            st.session_state.context_window.append(f"User: {query}\nBot: {response}")
            st.session_state.messages.append({"role": "assistant", "content": response})

    if st.session_state.uploaded_json:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("Analyzing uploaded JSON...")
            result = asyncio.run(call_analyze_tool(st.session_state.uploaded_json))
            placeholder.markdown(f"{result}\n\n🛠️ Tool used: `analyze`")
            st.session_state.messages.append({"role": "assistant", "content": f"{result}\n\n🛠️ Tool used: `analyze`"})
        st.session_state.uploaded_json = None

# === Clear Chat Button ===
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []
    st.session_state.context_window = []
    st.session_state.uploaded_json = None
    st.experimental_rerun()

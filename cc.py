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
st.set_page_config(
    page_title="Cortex + MCP Chat", 
    page_icon="🤖",
    layout="wide"
)

# === Styling ===
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #4B61D1;
        margin-bottom: 20px;
    }
    .tool-title {
        color: #4B61D1;
        font-weight: bold;
    }
    .tool-description {
        margin-bottom: 15px;
    }
    .sidebar-section {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# === Page Header ===
st.markdown("<h1 class='main-title'>🤖 Cortex + MCP Chatbot</h1>", unsafe_allow_html=True)

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
if "tool_args" not in st.session_state:
    st.session_state.tool_args = {}

# === MCP Server URL ===
server_url = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/sse")

# === Sidebar Layout ===
st.sidebar.markdown("## 🔧 Tools & Resources")

# === JSON File Upload ===
st.sidebar.markdown("### 📂 Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload JSON for Analyze Tool", type=["json"])
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
                # Fetch Resources
                resources = await session.list_resources()
                if hasattr(resources, 'resources'):
                    for r in resources.resources:
                        result["resources"].append({
                            "name": r.name, 
                            "description": r.description if hasattr(r, 'description') else "No description"
                        })
                
                # Fetch Tools
                tools = await session.list_tools()
                if hasattr(tools, 'tools'):
                    for t in tools.tools:
                        result["tools"].append({
                            "name": t.name, 
                            "description": getattr(t, 'description', 'No description')
                        })
                
                # Fetch Prompts
                prompts = await session.list_prompts()
                if hasattr(prompts, 'prompts'):
                    for p in prompts.prompts:
                        args = [
                            f"{arg.name} ({'Required' if arg.required else 'Optional'}): {arg.description}"
                            for arg in getattr(p, 'arguments', [])
                        ]
                        result["prompts"].append({
                            "name": p.name,
                            "description": getattr(p, 'description', ''),
                            "args": args
                        })
                
                # Fetch YAML Models
                try:
                    yaml_content = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                    if hasattr(yaml_content, 'contents'):
                        for item in yaml_content.contents:
                            if hasattr(item, 'text'):
                                parsed = yaml.safe_load(item.text)
                                result["yaml"].append({
                                    "name": item.name, 
                                    "content": yaml.dump(parsed, sort_keys=False)
                                })
                except Exception as e:
                    result["yaml"].append({
                        "name": "YAML Load Error", 
                        "content": str(e)
                    })
    except Exception as e:
        st.sidebar.error(f"❌ MCP Connection Error: {e}")
        
    return result

if st.sidebar.button("🔍 Load MCP Info"):
    # Using a progress message instead of spinner for compatibility
    progress_placeholder = st.sidebar.empty()
    progress_placeholder.info("Loading MCP data...")
    st.session_state.mcp_info = asyncio.run(fetch_mcp_info())
    progress_placeholder.success("✅ MCP data loaded successfully!")

# === MCP Info Display ===
with st.sidebar.expander("📦 Resources"):
    for r in st.session_state.mcp_info["resources"]:
        st.markdown(f"**{r['name']}**\n\n{r['description']}")

# === Tools Section ===
with st.sidebar.expander("🛠 Tools"):
    for t in st.session_state.mcp_info["tools"]:
        tool_name = t['name']
        st.markdown(f"<div class='tool-title'>{tool_name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='tool-description'>{t['description']}</div>", unsafe_allow_html=True)
        
        # === Tool-specific UI ===
        if tool_name == "calculator":
            # Calculator tool arguments
            calc_expr = st.text_input("Expression", key=f"expr_{tool_name}")
            if st.button(f"▶️ Run {tool_name}", key=f"run_{tool_name}"):
                if not calc_expr.strip():
                    st.warning("❗ Please enter a valid expression.")
                else:
                    async def run_calculator(expression):
                        try:
                            async with sse_client(server_url) as sse_connection:
                                async with ClientSession(*sse_connection) as session:
                                    await session.initialize()
                                    # Properly format arguments for calculator tool
                                    result = await session.call_tool(tool_name, {"expression": expression})
                                    return f"🧮 Calculator Result:\n\n{result.content[0].text}"
                        except Exception as e:
                            return f"❌ Tool `{tool_name}` error: {str(e)}"
                    
                    # Use a progress message instead of spinner
                    progress_placeholder = st.empty()
                    progress_placeholder.info(f"Running {tool_name}...")
                    result = asyncio.run(run_calculator(calc_expr))
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result
                    })
                    # Note: Removed st.experimental_rerun() as it's deprecated in newer versions
# If you're using an older version, you can uncomment this line:
# st.experimental_rerun()
        
        elif tool_name == "analyze":
            # Analyze tool arguments
            st.markdown("**Required arguments:**")
            st.markdown("- data: JSON data to analyze")
            st.markdown("- operation: Analysis operation to perform")
            
            operation = st.selectbox(
                "Operation", 
                ["mean", "median", "sum", "min", "max", "std"], 
                key=f"operation_{tool_name}"
            )
            
            if st.button(f"▶️ Run {tool_name} on uploaded JSON", key=f"run_{tool_name}"):
                if st.session_state.uploaded_json is None:
                    st.warning("❗ Please upload a JSON file first.")
                else:
                    async def run_analyze(json_data, operation):
                        try:
                            async with sse_client(server_url) as sse_connection:
                                async with ClientSession(*sse_connection) as session:
                                    await session.initialize()
                                    # Properly format arguments for analyze tool
                                    result = await session.call_tool(tool_name, {
                                        "data": json_data,
                                        "operation": operation
                                    })
                                    return f"📊 Analysis Result ({operation}):\n\n{result.content[0].text}"
                        except Exception as e:
                            return f"❌ Tool `{tool_name}` error: {str(e)}"
                    
                    # Use a progress message instead of spinner
                    progress_placeholder = st.empty()
                    progress_placeholder.info(f"Running {tool_name}...")
                    result = asyncio.run(run_analyze(st.session_state.uploaded_json, operation))
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result
                    })
                    st.experimental_rerun()
        
        elif tool_name == "mcp-send-email":
            # Email tool arguments
            st.markdown("**Required arguments:**")
            st.markdown("- subject: Email subject")
            st.markdown("- body: Email body")
            st.markdown("- receivers: Email recipients (comma-separated)")
            
            subject = st.text_input("Subject", key=f"subject_{tool_name}")
            body = st.text_area("Body", key=f"body_{tool_name}")
            receivers = st.text_input("Recipients (comma-separated)", key=f"receivers_{tool_name}")
            
            if st.button(f"▶️ Send Email", key=f"run_{tool_name}"):
                if not subject or not body or not receivers:
                    st.warning("❗ All fields are required to send an email.")
                else:
                    async def send_email(subject, body, receivers):
                        try:
                            async with sse_client(server_url) as sse_connection:
                                async with ClientSession(*sse_connection) as session:
                                    await session.initialize()
                                    # Properly format arguments for email tool
                                    result = await session.call_tool(tool_name, {
                                        "subject": subject,
                                        "body": body,
                                        "receivers": receivers.split(",")
                                    })
                                    return f"📧 Email Sent:\n\n{result.content[0].text}"
                        except Exception as e:
                            return f"❌ Tool `{tool_name}` error: {str(e)}"
                    
                    # Use a progress message instead of spinner
                    progress_placeholder = st.empty()
                    progress_placeholder.info("Sending email...")
                    result = asyncio.run(send_email(subject, body, receivers))
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result
                    })
                    st.experimental_rerun()
        
        else:
            # Generic tool run button for other tools
            if st.button(f"▶️ Run {tool_name}", key=f"run_{tool_name}"):
                async def run_tool(name):
                    try:
                        async with sse_client(server_url) as sse_connection:
                            async with ClientSession(*sse_connection) as session:
                                await session.initialize()
                                result = await session.call_tool(name, {})
                                return f"🛠️ Tool `{name}` executed:\n\n{result.content[0].text}"
                    except Exception as e:
                        return f"❌ Tool `{name}` error: {str(e)}"
                
                # Use a progress message instead of spinner
                progress_placeholder = st.empty()
                progress_placeholder.info(f"Running {tool_name}...")
                result = asyncio.run(run_tool(tool_name))
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result
                })
                st.experimental_rerun()

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

# === Chat Display Section ===
st.markdown("### 💬 Chat")

# Display chat messages
chat_container = st.container()
with chat_container:
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

# === Handle Submission ===
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
        st.experimental_rerun()

# === Clear Chat Button ===
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []
    st.session_state.context_window = []
    st.session_state.uploaded_json = None
    st.experimental_rerun()

# === Footer ===
st.markdown("---")
st.markdown("Powered by Cortex + MCP | © 2025")

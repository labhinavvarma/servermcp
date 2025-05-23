import streamlit as st
import asyncio
import json
import uuid
import requests
import yaml

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_mcp_adapters.client import MultiServerMCPClient

# === Cortex LLM Configuration ===
API_URL = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"
API_KEY = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
APP_ID = "edadip"
APLCTN_CD = "edagnai"
MODEL = "llama3.1-70b"
SYS_MSG = "You are a powerful AI assistant. Provide accurate, concise answers based on context."

# === Streamlit Page Setup ===
st.set_page_config(page_title="Healthcare AI Chat", page_icon="🏥", layout="wide")
st.title("🏥 Healthcare AI Chat")

# === Session States ===
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_window" not in st.session_state:
    st.session_state.context_window = []

# === Sidebar Configuration ===
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8001/sse")
show_server_info = st.sidebar.checkbox("🛡 Show MCP Server Info", value=False)

# === Cortex API Call ===
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
                "messages": [{"role": "user", "content": full_prompt}]
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

# === Server Info View ===
if show_server_info:
    async def fetch_mcp_info():
        result = {"resources": [], "tools": [], "prompts": [], "yaml": [], "search": []}
        try:
            async with sse_client(url=server_url) as sse_connection:
                async with ClientSession(*sse_connection) as session:
                    await session.initialize()
                    resources = await session.list_resources()
                    if hasattr(resources, 'resources'):
                        for r in resources.resources:
                            result["resources"].append({"name": r.name})
                    tools = await session.list_tools()
                    hidden_tools = {"add-frequent-questions", "add-prompts", "suggested_top_prompts"}
                    if hasattr(tools, 'tools'):
                        for t in tools.tools:
                            if t.name not in hidden_tools:
                                result["tools"].append({"name": t.name})
                    prompts = await session.list_prompts()
                    if hasattr(prompts, 'prompts'):
                        for p in prompts.prompts:
                            args = []
                            if hasattr(p, 'arguments'):
                                for arg in p.arguments:
                                    args.append(f"{arg.name} ({'Required' if arg.required else 'Optional'}): {arg.description}")
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
                                    result["yaml"].append(yaml.dump(parsed, sort_keys=False))
                    except Exception as e:
                        result["yaml"].append(f"YAML error: {e}")
        except Exception as e:
            st.sidebar.error(f"❌ MCP Connection Error: {e}")
        return result

    mcp_data = asyncio.run(fetch_mcp_info())
    with st.sidebar.expander("📦 Resources", expanded=False):
        for r in mcp_data["resources"]:
            display_name = "Cortex Search" if "cortex_search/search_obj/list" in r["name"] else r["name"]
            st.markdown(f"**{display_name}**")
    with st.sidebar.expander("Schematic Layer", expanded=False):
        for y in mcp_data["yaml"]:
            st.code(y, language="yaml")
    with st.sidebar.expander("🛠 Tools", expanded=False):
        for t in mcp_data["tools"]:
            st.markdown(f"**{t['name']}**")
    with st.sidebar.expander("🧐 Prompts", expanded=False):
        for p in mcp_data["prompts"]:
            st.markdown(f"**{p['name']}**")

# === Chatbot Mode ===
else:
    prompt_type = st.sidebar.radio("Select Prompt Type", ["Calculator", "HEDIS Expert", "Weather", "No Context"])
    prompt_map = {
        "Calculator": "calculator-prompt",
        "HEDIS Expert": "hedis-prompt",
        "Weather": "weather-prompt",
        "No Context": None
    }

    examples = {
        "Calculator": ["(4+5)/2.0", "sqrt(16) + 7", "3^4 - 12"],
        "HEDIS Expert": [],
        "Weather": [
            "What is the present weather in Richmond?",
            "What's the weather forecast for Atlanta?",
            "Is it raining in New York City today?"
        ],
        "No Context": ["Who won the world cup in 2022?", "Summarize climate change impact on oceans"]
    }

    if prompt_type == "HEDIS Expert":
        async def fetch_hedis_examples():
            async with sse_client(url=server_url) as sse_connection:
                async with ClientSession(*sse_connection) as session:
                    await session.initialize()
                    content = await session.read_resource("genaiplatform://hedis/frequent_questions/Initialization")
                    if hasattr(content, "contents"):
                        for item in content.contents:
                            if hasattr(item, "text"):
                                examples["HEDIS Expert"].extend(json.loads(item.text))
        asyncio.run(fetch_hedis_examples())

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    with st.sidebar.expander("Example Queries", expanded=True):
        for example in examples[prompt_type]:
            if st.button(example, key=example):
                st.session_state.query_input = example

    query = st.chat_input("Type your query here...")
    if "query_input" in st.session_state:
        query = st.session_state.query_input
        del st.session_state.query_input

    def process_query(query_text):
        st.session_state.messages.append({"role": "user", "content": query_text})
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.text("Processing...")

            try:
                prompt_name = prompt_map[prompt_type]
                required_args = {}
                if prompt_name:
                    async def get_prompt_content():
                        async with MultiServerMCPClient({"DataFlyWheelServer": {"url": server_url, "transport": "sse"}}) as client:
                            prompt_metadata = await client.list_prompts()
                            for p in prompt_metadata.prompts:
                                if p.name == prompt_name:
                                    for arg in p.arguments:
                                        if arg.required:
                                            user_val = st.sidebar.text_input(f"{arg.name} ({arg.description})", key=arg.name)
                                            required_args[arg.name] = user_val
                            prompt = await client.get_prompt(
                                server_name="DataFlyWheelServer",
                                prompt_name=prompt_name,
                                arguments=required_args
                            )
                            return prompt[0].content if prompt else ""
                    prompt_template = asyncio.run(get_prompt_content())
                else:
                    prompt_template = ""

                formatted_prompt = prompt_template.format(query=query_text) if "{query}" in prompt_template else prompt_template + query_text
                result = call_cortex_llm(formatted_prompt, st.session_state.context_window)
                message_placeholder.text(result)
                st.session_state.context_window.append(f"User: {query_text}\nBot: {result}")
                st.session_state.messages.append({"role": "assistant", "content": result})

            except Exception as e:
                error_message = f"Error: {str(e)}"
                message_placeholder.text(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

    if query:
        process_query(query)

    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.context_window = []
        st.experimental_rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("Healthcare AI Chat v1.0")

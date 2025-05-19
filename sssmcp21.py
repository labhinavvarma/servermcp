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

# === Chatbot Mode ===
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
            prompt_template = ""

            if prompt_name:
                async def handle_prompt_or_tool():
                    async with sse_client(url=server_url) as sse_connection:
                        async with ClientSession(*sse_connection) as session:
                            await session.initialize()
                            all_prompts = await session.list_prompts()
                            for p in all_prompts.prompts:
                                if p.name == prompt_name:
                                    for arg in p.arguments:
                                        if arg.required:
                                            required_args[arg.name] = st.sidebar.text_input(f"{arg.name} ({arg.description})", key=arg.name)

                            # If Calculator, call tool directly
                            if prompt_type == "Calculator":
                                tool_response = await session.call_tool("calculator", required_args)
                                return tool_response.content[0].text

                            # Otherwise, fetch prompt and return formatted
                            prompt = await session.get_prompt(prompt_name=prompt_name, arguments=required_args)
                            return prompt[0].content.format(query=query_text) if "{query}" in prompt[0].content else prompt[0].content + query_text

                result_or_prompt = asyncio.run(handle_prompt_or_tool())

                if prompt_type == "Calculator":
                    final_response = result_or_prompt  # already tool result
                else:
                    final_response = call_cortex_llm(result_or_prompt, st.session_state.context_window)
            else:
                final_response = call_cortex_llm(query_text, st.session_state.context_window)

            message_placeholder.text(final_response)
            st.session_state.context_window.append(f"User: {query_text}\nBot: {final_response}")
            st.session_state.messages.append({"role": "assistant", "content": final_response})

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

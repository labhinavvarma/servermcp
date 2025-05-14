import streamlit as st
import asyncio
import nest_asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from dependencies import SnowFlakeConnector
from llmobject_wrapper import ChatSnowflakeCortex
from snowflake.snowpark import Session

nest_asyncio.apply()

# Page config
st.set_page_config(page_title="HEDIS MCP Chatbot", page_icon="💬")
st.title("📊 HEDIS MCP Chatbot")

# MCP Server Configuration
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")

# Dynamic fetch of HEDIS FAQ from MCP
@st.cache_data
def fetch_hedis_faq():
    try:
        async def fetch():
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    resource_uri = "genaiplatform://hedis/frequent_questions/Initialization"
                    content = await session.read_resource(resource_uri)
                    return [q["prompt"] for q in content.dict().get("questions", []) if "prompt" in q]
        return asyncio.run(fetch())
    except Exception as e:
        return [f"❌ Error fetching FAQ: {e}"]

# Prompt configuration
prompt_map = {
    "Calculator": "caleculator-promt",
    "HEDIS Expert": "hedis-prompt",
    "Weather": "weather-prompt"
}

# Sidebar prompt selector
prompt_type = st.sidebar.radio("Select Prompt Type", ["Calculator", "HEDIS Expert", "Weather"])

examples = {
    "Calculator": ["(4+5)/2.0", "sqrt(16) + 7", "3^4 - 12"],
    "HEDIS Expert": fetch_hedis_faq(),
    "Weather": ["What's the weather in Richmond?", "Forecast for Atlanta?", "Rain in New York City?"]
}

with st.sidebar.expander("Example Queries", expanded=True):
    for example in examples[prompt_type]:
        if st.button(example, key=example):
            st.session_state.query_input = example

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Handle query input
query = st.chat_input("Enter your query...")
if "query_input" in st.session_state:
    query = st.session_state.query_input
    del st.session_state.query_input

# Initialize Snowflake and LLM connection
@st.cache_resource
def get_snowflake_conn():
    return SnowFlakeConnector.get_conn('aedl', '')

@st.cache_resource
def get_model():
    sf_conn = get_snowflake_conn()
    return ChatSnowflakeCortex(
        model="llama3.1-70b-elevance",
        cortex_function="complete",
        session=Session.builder.configs({"connection": sf_conn}).getOrCreate()
    )

async def run_query(prompt_type, query):
    async with MultiServerMCPClient({"DataFlyWheelServer": {"url": server_url, "transport": "sse"}}) as client:
        model = get_model()
        agent = create_react_agent(model=model, tools=client.get_tools())
        prompt_name = prompt_map[prompt_type]
        prompt_template = await client.get_prompt("DataFlyWheelServer", prompt_name, {})
        prompt_text = prompt_template[0].content
        formatted_prompt = prompt_text.replace("{query}", query) if "{query}" in prompt_text else f"{prompt_text}\n{query}"
        response = await agent.ainvoke({"messages": formatted_prompt})
        return list(response.values())[0][1].content

# Run query if provided
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Running query..._")
        try:
            result = asyncio.run(run_query(prompt_type, query))
            placeholder.write(result)
        except Exception as e:
            placeholder.error(f"❌ Error: {e}")
            result = f"Error: {e}"
        st.session_state.messages.append({"role": "assistant", "content": result})

# Clear chat history
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("🔌 Connected to DataFlyWheel MCP Server")

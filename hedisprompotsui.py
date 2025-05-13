import streamlit as st
import asyncio
import json
import nest_asyncio

from mcp import ClientSession
from mcp.client.sse import sse_client

# Required for nested async loop in Streamlit
nest_asyncio.apply()

# UI Config
st.set_page_config(page_title="HEDIS MCP Client", page_icon="🩺")
st.title("🩺 HEDIS MCP Client")

server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8001/sse")

# Cache the session once established
@st.cache_resource
def get_event_loop():
    return asyncio.new_event_loop()

async def get_session():
    async with sse_client(url=server_url) as sse_connection:
        session = ClientSession(*sse_connection)
        await session.initialize()
        return session

async def list_prompts(session):
    prompts = await session.list_prompts()
    return [p.name for p in prompts]

async def read_prompt(session, uri):
    content = await session.read_resource(uri)
    return content

async def call_add_prompt_tool(session, prompt_name, description, content):
    return await session.call_tool(
        name="add-prompts",
        arguments={
            "uri": f"genaiplatform://hedis/prompts/{prompt_name}",
            "prompt": {
                "prompt_name": prompt_name,
                "description": description,
                "content": content
            }
        }
    )

async def get_prompt_response(session, prompt_name, query):
    return await session.get_prompt(
        name=prompt_name,
        arguments={"query": query}
    )

# Interface tabs
tab1, tab2, tab3 = st.tabs(["➕ Add Prompt", "📖 View Prompt", "🧠 Run Prompt"])

# Add prompt tab
with tab1:
    st.subheader("➕ Add a New Prompt")
    prompt_name = st.text_input("Prompt Name")
    description = st.text_area("Prompt Description")
    content = st.text_area("Prompt Content")

    if st.button("Add Prompt"):
        loop = get_event_loop()
        session = loop.run_until_complete(get_session())
        result = loop.run_until_complete(call_add_prompt_tool(session, prompt_name, description, content))
        st.success("Prompt added successfully!")
        st.json(result)

# View prompt tab
with tab2:
    st.subheader("📖 View Prompt Content")
    selected_prompt = st.text_input("Prompt Name to View", "example-prompt")
    if st.button("Read Prompt"):
        loop = get_event_loop()
        session = loop.run_until_complete(get_session())
        content = loop.run_until_complete(read_prompt(session, f"genaiplatform://hedis/prompts/{selected_prompt}"))
        st.code(json.dumps(content, indent=2), language="json")

# Run prompt tab
with tab3:
    st.subheader("🧠 Run Prompt")
    loop = get_event_loop()
    session = loop.run_until_complete(get_session())
    prompt_list = loop.run_until_complete(list_prompts(session))
    selected = st.selectbox("Select Prompt", prompt_list)
    query = st.text_area("Your Query", "What is the age criteria for BCS Measure?")
    if st.button("Run"):
        response = loop.run_until_complete(get_prompt_response(session, selected, query))
        st.markdown("### Response")
        st.code(json.dumps(response, indent=2), language="json")

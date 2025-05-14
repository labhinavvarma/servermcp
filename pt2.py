import streamlit as st
import asyncio
import nest_asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

# Page config
st.set_page_config(page_title="Prompt Tester", page_icon="💬")
st.title("🧪 MCP Prompt Tester (No LLM)")

nest_asyncio.apply()

# MCP server configuration
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")
resource_uri = st.sidebar.text_input("Prompt Types Resource URI", "genaiplatform://hedis/frequent_questions/Initialization")

# --- Fetch prompt types and prompt map ---
@st.cache_data
def fetch_prompt_type_map():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch():
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    content = await session.read_resource(resource_uri)
                    return content.dict()
        return loop.run_until_complete(fetch())
    except Exception as e:
        return {"error": str(e)}

prompt_data = fetch_prompt_type_map()
available_types = []
prompt_map = {}

if "error" not in prompt_data and isinstance(prompt_data.get("questions"), list):
    for q in prompt_data["questions"]:
        ptype = q.get("user_context", "").strip()
        pname = q.get("prompt_name", "").strip() or q.get("prompt", "").strip()
        if ptype and pname and ptype not in prompt_map:
            available_types.append(ptype)
            prompt_map[ptype] = pname

# --- Prompt Type Selection ---
if not available_types:
    st.warning("No prompt types found in resource.")
else:
    selected_type = st.sidebar.radio("Select Prompt Type", available_types)
    selected_prompt_name = prompt_map[selected_type]

    # --- Read the prompt template ---
    async def get_prompt_template():
        try:
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    prompt = await session.get_prompt(name=selected_prompt_name, arguments={})
                    return prompt[0].content
        except Exception as e:
            return f"❌ Error fetching prompt: {e}"

    prompt_template = asyncio.run(get_prompt_template())

    st.subheader(f"📋 Prompt Template for `{selected_type}`")
    st.text_area("Template", value=prompt_template, height=200, disabled=True)

    # --- Query insertion ---
    query_input = st.text_input("🗣️ Enter a query to insert into the prompt")

    if query_input and prompt_template:
        if "{query}" in prompt_template:
            formatted = prompt_template.replace("{query}", query_input)
        else:
            formatted = f"{prompt_template}\n\n{query_input}"

        st.subheader("📨 Final Prompt Sent to LLM")
        st.code(formatted, language="markdown")

import streamlit as st
import asyncio
import nest_asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

# Page config
st.set_page_config(page_title="Prompt Box Tester", page_icon="💬")
st.title("🧪 MCP Prompt Box Tester")

nest_asyncio.apply()

# MCP server config
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")
resource_uri = st.sidebar.text_input("Prompt Types Resource URI", "genaiplatform://hedis/frequent_questions/Initialization")

# Fetch prompt types and prompt_name mapping
@st.cache_data
def get_prompt_type_map():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch_prompt_types():
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    content = await session.read_resource(resource_uri)
                    return content.dict()

        return loop.run_until_complete(fetch_prompt_types())
    except Exception as e:
        return {"error": str(e)}

prompt_data = get_prompt_type_map()
available_types = []
prompt_map = {}

if "error" not in prompt_data and isinstance(prompt_data.get("questions"), list):
    for q in prompt_data["questions"]:
        ptype = q.get("user_context", "").strip()
        pname = q.get("prompt_name", "").strip() or q.get("prompt", "").strip()
        if ptype and pname and ptype not in prompt_map:
            available_types.append(ptype)
            prompt_map[ptype] = pname

if not available_types:
    st.warning("No prompt types found in resource.")
else:
    selected_type = st.sidebar.radio("Select Prompt Type", available_types)
    selected_prompt_name = prompt_map[selected_type]

    # Read and show the prompt template
    async def get_prompt_text():
        try:
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    prompt = await session.get_prompt(name=selected_prompt_name, arguments={})
                    return prompt[0].content
        except Exception as e:
            return f"❌ Error fetching prompt: {e}"

    prompt_text = asyncio.run(get_prompt_text())

    st.subheader(f"📦 Prompt: `{selected_prompt_name}`")
    st.text_area("Prompt Template", value=prompt_text, height=200)

import streamlit as st
import asyncio
import nest_asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

nest_asyncio.apply()

st.set_page_config(page_title="MCP Prompt Tester", page_icon="💬")
st.title("📊 HEDIS MCP Prompt Tester with Mock LLM")

# MCP server input
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")

# Prompt selection
prompt_type = st.sidebar.radio("Select Prompt Type", ["Calculator", "HEDIS Expert", "Weather"])

# Prompt mapping
prompt_map = {
    "Calculator": "caleculator-promt",
    "HEDIS Expert": "hedis-prompt",
    "Weather": "weather-prompt"
}

# Read FAQ dynamically for "HEDIS Expert"
@st.cache_data
def fetch_hedis_questions():
    try:
        async def fetch():
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    uri = "genaiplatform://hedis/frequent_questions/Initialization"
                    content = await session.read_resource(uri)
                    return [q["prompt"] for q in content.dict().get("questions", []) if "prompt" in q]
        return asyncio.run(fetch())
    except Exception as e:
        return [f"⚠️ Error: {e}"]

# Static examples for other prompt types
examples = {
    "Calculator": ["(4+5)/2.0", "sqrt(16) + 7", "3^4 - 12"],
    "HEDIS Expert": fetch_hedis_questions(),
    "Weather": ["What's the weather in Richmond?", "Forecast for Atlanta?", "Rain in NYC?"]
}

# Sidebar suggestions
with st.sidebar.expander("Example Queries", expanded=True):
    for example in examples[prompt_type]:
        if st.button(example, key=example):
            st.session_state.query_input = example

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input or suggestion
query = st.chat_input("Ask your question...")
if "query_input" in st.session_state:
    query = st.session_state.query_input
    del st.session_state.query_input

# Read prompt template
def get_prompt_template(prompt_name: str):
    try:
        async def fetch():
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    prompt = await session.get_prompt(name=prompt_name, arguments={})
                    return prompt[0].content
        return asyncio.run(fetch())
    except Exception as e:
        return f"❌ Failed to load prompt: {e}"

# "Mock LLM" — just echoes the final formatted prompt
def mock_llm(prompt_text: str) -> str:
    return f"🤖 [Mock LLM Output]\n\n{prompt_text}"

# Process user input
if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("_Loading prompt..._")

        prompt_template = get_prompt_template(prompt_map[prompt_type])
        if "{query}" in prompt_template:
            final_prompt = prompt_template.replace("{query}", query)
        else:
            final_prompt = f"{prompt_template.strip()}\n\n{query}"

        result = mock_llm(final_prompt)

        placeholder.markdown("### 🧪 Mock LLM Output")
        placeholder.code(result, language="markdown")
        st.session_state.messages.append({"role": "assistant", "content": result})

# Clear chat
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("🧪 Testing Mode — Mock LLM only. No agent or Snowflake connection.")

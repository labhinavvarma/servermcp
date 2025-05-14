import streamlit as st
import asyncio
import nest_asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

# Setup
st.set_page_config(page_title="HEDIS Prompt Chat", page_icon="💬")
st.title("📊 HEDIS Prompt Tester with FAQ")

nest_asyncio.apply()

# Config
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")
faq_uri = st.sidebar.text_input("FAQ Resource URI", "genaiplatform://hedis/frequent_questions/Initialization")
prompt_name = "hedis-prompt"

# Fetch FAQ questions
@st.cache_data
def fetch_faq_questions():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def fetch():
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    content = await session.read_resource(faq_uri)
                    return content.dict()
        return loop.run_until_complete(fetch())
    except Exception as e:
        return {"error": str(e)}

# Get prompt template
async def fetch_prompt_template():
    try:
        async with sse_client(url=server_url) as sse:
            async with ClientSession(*sse) as session:
                await session.initialize()
                prompt = await session.get_prompt(name=prompt_name, arguments={})
                return prompt[0].content
    except Exception as e:
        return f"❌ Error fetching prompt: {e}"

# Display previously sent messages
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Sidebar: Suggested Questions
faq_data = fetch_faq_questions()
if "error" in faq_data:
    st.sidebar.error(faq_data["error"])
elif isinstance(faq_data.get("questions"), list):
    st.sidebar.markdown("### 💡 Suggested HEDIS Questions")
    for idx, item in enumerate(faq_data["questions"]):
        question = item.get("prompt", "")
        if st.sidebar.button(question, key=f"suggest_{idx}"):
            st.session_state.query_input = question

# Chat input
query = st.chat_input("Ask about HEDIS...")

# Trigger from suggestion
if "query_input" in st.session_state:
    query = st.session_state.query_input
    del st.session_state.query_input

# Process Query via Prompt Only (No LLM)
if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("_Fetching prompt..._")

        prompt_template = asyncio.run(fetch_prompt_template())

        if "{query}" in prompt_template:
            final_prompt = prompt_template.replace("{query}", query)
        else:
            final_prompt = f"{prompt_template}\n\n{query}"

        message_placeholder.markdown("### 📝 Prompt Sent to LLM")
        message_placeholder.code(final_prompt, language="markdown")

        st.session_state.messages.append({"role": "assistant", "content": final_prompt})

# Clear chat
if st.sidebar.button("🧹 Clear Chat"):
    st.session_state.messages = []
    st.experimental_rerun()

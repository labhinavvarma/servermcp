import streamlit as st
import asyncio
import nest_asyncio
import json
import yaml
import random

from mcp.client.sse import sse_client
from mcp import ClientSession

nest_asyncio.apply()
st.set_page_config(page_title="MCP Client Chat", page_icon="🧠")
st.title("🧠 MCP Client Chat Interface")

# --- State Init ---
for key in ["mcp_data", "read_content", "tool_result", "mock_llm", "inserted_prompt"]:
    if key not in st.session_state:
        st.session_state[key] = (
            {"resources": [], "tools": [], "prompts": [], "yaml": [], "search": []}
            if key == "mcp_data" else None
        )

# --- Sidebar UI ---
# --- Sidebar Configuration ---
server_url = st.sidebar.text_input("MCP Server URL", "http://0.0.0.0:8000/sse")
show_server_info = st.sidebar.checkbox("🛡 Show MCP Server Info", value=False)
show_prompts_info = st.sidebar.checkbox(" Show prompts", value=False)
show_select_tool = st.sidebar.checkbox("Tool selection", value=False)

# --- Show Server Information ---
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
                            result["resources"].append({"name": r.name, "description": r.description})
 
                    tools = await session.list_tools()
                    if hasattr(tools, 'tools'):
                        for t in tools.tools:
                            result["tools"].append({"name": t.name, "description": getattr(t, 'description', 'No description')})
 
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
            st.markdown(f"**{r['name']}**\n\n{r['description']}")
 
    with st.sidebar.expander("🛠 Tools", expanded=False):
        for t in mcp_data["tools"]:
            st.markdown(f"**{t['name']}**\n\n{t['description']}")
 
    with st.sidebar.expander("🧐 Prompts", expanded=False):
        for p in mcp_data["prompts"]:
            st.markdown(f"**{p['name']}**\n\n{p['description']}")
            if p["args"]:
                st.markdown("Arguments:")
                for a in p["args"]:
                    st.markdown(f"- {a}")
 
    with st.sidebar.expander("📄 YAML", expanded=False):
        for y in mcp_data["yaml"]:
            st.code(y, language="yaml")
                


# --- Read Resource and Suggest Questions ---
st.header("📖 Read MCP Resource")
uri_input = st.text_input("Resource URI", "genaiplatform://hedis/frequent_questions/Initialization")
if st.button("📂 Read URI"):
    async def read_resource(uri):
        try:
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    content = await session.read_resource(uri)
                    st.session_state["read_content"] = content.dict()
        except Exception as e:
            st.error(f"❌ Read failed: {e}")
    asyncio.run(read_resource(uri_input))

read_data = st.session_state.get("read_content", {})
if read_data and isinstance(read_data.get("questions"), list):
    st.markdown("### 💡 Suggested Questions")
    for idx, q in enumerate(read_data["questions"]):
        msg = q.get("prompt", "").strip()
        if msg:
            if st.button(f"❓ {msg}", key=f"suggest_q_{idx}"):
                st.session_state["inserted_prompt"] = msg
else:
    if read_data:
        with st.expander("📘 Raw Resource Output"):
            st.json(read_data)

# --- Prompt Resource Reader ---
st.header("📚 Prompt Resource Reader")
prompt_list = [p["name"] for p in st.session_state["mcp_data"]["prompts"]]
selected_prompt = st.selectbox("Choose a Prompt", prompt_list)
if st.button("📖 Read Prompt Resource"):
    prompt_uri = f"genaiplatform://hedis/frequent_questions/{selected_prompt}"
    async def read_prompt_resource():
        try:
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    result = await session.read_resource(prompt_uri)
                    st.session_state["read_content"] = result.dict()
        except Exception as e:
            st.error(f"❌ Prompt read failed: {e}")
    asyncio.run(read_prompt_resource())

# --- Tool Call ---
st.header("🛠 Add Frequent Question Tool")
user_context = st.text_input("User Context", "Initialization")
question_prompt = st.text_input("Prompt Text", "What is the age criteria for CBP?")
if st.button("➕ Add Question"):
    async def call_tool():
        try:
            async with sse_client(url=server_url) as sse:
                async with ClientSession(*sse) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        name="add-frequent-questions",
                        arguments={
                            "uri": uri_input,
                            "questions": [{"user_context": user_context, "prompt": question_prompt}]
                        }
                    )
                    st.session_state["tool_result"] = result.dict()
        except Exception as e:
            st.error(f"❌ Tool call failed: {e}")
    asyncio.run(call_tool())

if st.session_state["tool_result"]:
    with st.expander("✅ Tool Result", expanded=True):
        st.json(st.session_state["tool_result"])

# --- Chat Interface (Mock LLM) ---
st.header("💬 Chat")
chat_input = st.text_area("Compose your message", value=st.session_state.get("inserted_prompt", ""), key="chat_input_box")
if st.button("🎯 Send to Mock LLM"):
    responses = [
        "CBP is the Controlling High Blood Pressure measure for adults aged 18–85.",
        "It checks if the patient's blood pressure is under 140/90 mmHg.",
        "Documentation must include at least one outpatient visit."
    ]
    st.session_state["mock_llm"] = random.choice(responses)

if st.session_state["mock_llm"]:
    st.success(f"🧠 LLM Response: {st.session_state['mock_llm']}")
    st.session_state["inserted_prompt"] = ""

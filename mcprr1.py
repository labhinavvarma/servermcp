import streamlit as st
import asyncio
import nest_asyncio
import json
import yaml

from mcp.client.sse import sse_client
from mcp import ClientSession
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from dependencies import SnowFlakeConnector
from llmobject_wrapper import ChatSnowflakeCortex
from snowflake.snowpark import Session

nest_asyncio.apply()
st.set_page_config(page_title="Healthcare AI Chat", page_icon="🏥")
st.title("Healthcare AI Chat")

# === MCP Server URL ===
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")
mode = st.sidebar.radio("Mode", ["Chat", "JSON Analyzer"], horizontal=True)
show_server_info = st.sidebar.checkbox("🛡 Show Server Info", value=False)

# === Fetch MCP Server Info ===
@st.cache_resource(show_spinner="Connecting to MCP server...")
def fetch_mcp_info():
    result = {"resources": [], "tools": [], "prompts": [], "yaml": []}
    try:
        async def fetch():
            async with sse_client(url=server_url) as sse_connection:
                async with ClientSession(*sse_connection) as session:
                    await session.initialize()

                    resources = await session.list_resources()
                    if hasattr(resources, "resources"):
                        result["resources"] = [{"name": r.name, "description": r.description} for r in resources.resources]

                    tools = await session.list_tools()
                    if hasattr(tools, "tools"):
                        result["tools"] = [{"name": t.name, "description": getattr(t, "description", "")} for t in tools.tools]

                    prompts = await session.list_prompts()
                    if hasattr(prompts, "prompts"):
                        for p in prompts.prompts:
                            args = []
                            if hasattr(p, "arguments"):
                                for a in p.arguments:
                                    args.append(f"{a.name} ({'Required' if a.required else 'Optional'}): {a.description}")
                            result["prompts"].append({
                                "name": p.name,
                                "description": getattr(p, "description", ""),
                                "args": args
                            })

                    # Try to fetch a YAML resource (optional)
                    try:
                        yaml_res = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                        if hasattr(yaml_res, 'contents'):
                            for y in yaml_res.contents:
                                if hasattr(y, 'text'):
                                    parsed = yaml.safe_load(y.text)
                                    result["yaml"].append(yaml.dump(parsed, sort_keys=False))
                    except Exception as e:
                        result["yaml"].append(f"YAML fetch error: {e}")
        asyncio.run(fetch())
    except Exception as e:
        st.sidebar.error(f"❌ Error connecting to MCP server: {e}")
    return result

mcp_info = fetch_mcp_info() if show_server_info else {}

if show_server_info:
    with st.sidebar.expander("📦 Resources", expanded=False):
        for r in mcp_info.get("resources", []):
            st.markdown(f"**{r['name']}**\n{r['description']}")

    with st.sidebar.expander("🛠 Tools", expanded=False):
        for t in mcp_info.get("tools", []):
            st.markdown(f"**{t['name']}**\n{t['description']}")

    with st.sidebar.expander("📚 Prompts", expanded=False):
        for p in mcp_info.get("prompts", []):
            st.markdown(f"**{p['name']}**\n{p['description']}")
            if p["args"]:
                for a in p["args"]:
                    st.markdown(f"- {a}")

    with st.sidebar.expander("📄 YAML", expanded=False):
        for y in mcp_info.get("yaml", []):
            st.code(y, language="yaml")

# === Chat Mode ===
if mode == "Chat":
    prompt_type = st.sidebar.selectbox("Prompt Type", [
        "mcp-prompt-calculator", "hedis-prompt", "mcp-prompt-weather", "Confluence-prompt"
    ])
    example_queries = {
        "mcp-prompt-calculator": ["(4+5)/2.0", "3+7*2"],
        "hedis-prompt": ["What are the codes for Colonoscopy?", "Describe COA measure."],
        "mcp-prompt-weather": ["Weather in Atlanta", "Is it raining in NYC?"],
        "Confluence-prompt": ["What is Cortex?", "How to access CyberArk?"]
    }

    @st.cache_resource
    def get_model():
        sf_conn = SnowFlakeConnector.get_conn("aedl", "")
        return ChatSnowflakeCortex(
            model="llama3.1-70b-elevance",
            cortex_function="complete",
            session=Session.builder.configs({"connection": sf_conn}).getOrCreate()
        )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    with st.sidebar.expander("💡 Examples"):
        for q in example_queries.get(prompt_type, []):
            if st.button(q, key=q):
                st.session_state.query_input = q

    query = st.chat_input("Type your question...")
    if "query_input" in st.session_state:
        query = st.session_state.query_input
        del st.session_state.query_input

    async def process_chat_query(prompt_name, query_text):
        st.session_state.messages.append({"role": "user", "content": query_text})
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.text("Thinking...")
            try:
                async with MultiServerMCPClient(
                    {"DataFlyWheelServer": {"url": server_url, "transport": "sse"}}
                ) as client:
                    model = get_model()
                    agent = create_react_agent(model=model, tools=client.get_tools())
                    prompt = await client.get_prompt("DataFlyWheelServer", prompt_name, arguments={})
                    template = prompt[0].content
                    full_prompt = template.format(query=query_text) if "{query}" in template else template + query_text
                    result = await agent.ainvoke({"messages": full_prompt})
                    final = list(result.values())[0][1].content
                    placeholder.text(final)
                    st.session_state.messages.append({"role": "assistant", "content": final})
            except Exception as e:
                error = f"❌ {e}"
                placeholder.text(error)
                st.session_state.messages.append({"role": "assistant", "content": error})

    if query:
        asyncio.run(process_chat_query(prompt_type, query))

    if st.sidebar.button("🗑 Clear Chat"):
        st.session_state.messages = []
        st.experimental_rerun()

# === JSON Analyzer Mode ===
elif mode == "JSON Analyzer":
    st.subheader("📊 Upload JSON for Analysis")
    uploaded_file = st.file_uploader("Upload your JSON", type=["json"])
    operation = st.selectbox("Statistical Operation", ["sum", "mean", "median", "min", "max", "average"])

    if uploaded_file:
        try:
            json_data = json.load(uploaded_file)
            st.code(json.dumps(json_data, indent=2), language="json")
            if st.button("Analyze"):
                async def analyze_json():
                    async with MultiServerMCPClient(
                        {"DataFlyWheelServer": {"url": server_url, "transport": "sse"}}
                    ) as client:
                        result = await client.call_tool(
                            "DataFlyWheelServer",
                            tool_name="analyze",
                            arguments={"data": json_data, "operation": operation}
                        )
                        st.success("✅ Analysis Complete")
                        st.code(json.dumps(result.content[0].json(), indent=2))
                asyncio.run(analyze_json())
        except Exception as e:
            st.error(f"Invalid JSON file: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("🧠 MCP Client v2.0 • Prompt + Analyzer + Server Info")

import streamlit as st
import asyncio
import nest_asyncio
import json
import yaml

from mcp.client.sse import sse_client
from mcp import ClientSession

# Page config
st.set_page_config(page_title="Healthcare AI Chat", page_icon="🏥")
st.title("Healthcare AI Chat")

nest_asyncio.apply()

# --- Sidebar Configuration ---
server_url = st.sidebar.text_input("MCP Server URL", "http://10.126.192.183:8000/sse")
show_server_info = st.sidebar.checkbox("🛡 Show MCP Server Info", value=False)

# --- Show Server Information ---
if show_server_info:
    async def fetch_mcp_info():
        result = {"resources": [], "tools": [], "prompts": [], "yaml": []}
        try:
            async with sse_client(url=server_url) as sse_connection:
                async with ClientSession(*sse_connection) as session:
                    await session.initialize()

                    # --- Resources ---
                    resources = await session.list_resources()
                    if hasattr(resources, 'resources'):
                        for r in resources.resources:
                            result["resources"].append({"name": r.name, "description": r.description})

                            # Attempt to read and parse YAML from resource
                            try:
                                content = await session.read_resource(r.name)
                                if hasattr(content, 'contents'):
                                    for item in content.contents:
                                        if hasattr(item, 'text'):
                                            parsed = yaml.safe_load(item.text)
                                            result["yaml"].append(f"# {r.name}\n" + yaml.dump(parsed, sort_keys=False))
                            except Exception as e:
                                result["yaml"].append(f"# {r.name}\nYAML error: {e}")

                    # --- Tools ---
                    tools = await session.list_tools()
                    if hasattr(tools, 'tools'):
                        for t in tools.tools:
                            result["tools"].append({
                                "name": t.name,
                                "description": getattr(t, 'description', 'No description')
                            })

                    # --- Prompts ---
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

        except Exception as e:
            st.sidebar.error(f"❌ MCP Connection Error: {e}")
        return result

    # Run async call to fetch info
    mcp_data = asyncio.run(fetch_mcp_info())

    # --- Display in Sidebar ---
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

    with st.sidebar.expander("📄 YAML (All Resources)", expanded=False):
        for y in mcp_data["yaml"]:
            st.code(y, language="yaml")

else:
    st.warning("Enable 'Show MCP Server Info' in sidebar to connect and view resources.")

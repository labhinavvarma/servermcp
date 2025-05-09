from mcp import ClientSession
from mcp.client.sse import sse_client
import asyncio
import json
import yaml

async def run():
    server_url = 'http://10.126.192.183:8001/sse'

    print("=" * 50)
    print("🚀 MCP CLIENT CONNECTION")
    print("=" * 50)

    async with sse_client(url=server_url) as sse_connection:
        print("✓ Session Established")

        async with ClientSession(*sse_connection) as session:
            await session.initialize()
            print("✓ Session Initialized")
            print("=" * 50)

            # --- RESOURCES ---
            print("\nRESOURCES:")
            print("-" * 50)
            try:
                resources_response = await session.list_resources()
                resources = getattr(resources_response, 'resources', [])

                if not resources:
                    print("  No resources found")
                else:
                    for i, resource in enumerate(resources, start=1):
                        print(f"#{i} • Name: {resource.name}")
                        print(f"   Description: {resource.description}")
                        if "{" in resource.name:
                            print("   [PARAMETRIC] Parameters:")
                            current_pos = 0
                            while True:
                                param_start = resource.name.find("{", current_pos)
                                if param_start == -1:
                                    break
                                param_end = resource.name.find("}", param_start)
                                if param_end == -1:
                                    break
                                param_name = resource.name[param_start + 1:param_end]
                                print(f"     - {param_name}")
                                current_pos = param_end + 1
                        print("-" * 30)
            except Exception as e:
                print(f"❌ Failed to list resources: {e}")

            # --- TOOLS ---
            print("\nTOOLS:")
            print("-" * 50)
            try:
                tools_response = await session.list_tools()
                tools = getattr(tools_response, 'tools', [])
                if not tools:
                    print("  No tools found")
                else:
                    seen_tools = set()
                    for tool in tools:
                        if tool.name not in seen_tools:
                            seen_tools.add(tool.name)
                            print(f"• Name: {tool.name}")
                            print(f"  Description: {tool.description or 'No description'}")
                            print("-" * 30)
            except Exception as e:
                print(f"❌ Failed to list tools: {e}")

            # --- PROMPTS ---
            print("\nPROMPTS:")
            print("-" * 50)
            try:
                prompts_response = await session.list_prompts()
                prompts = getattr(prompts_response, 'prompts', [])
                if not prompts:
                    print("  No prompts found")
                else:
                    seen_prompts = set()
                    for prompt in prompts:
                        if prompt.name not in seen_prompts:
                            seen_prompts.add(prompt.name)
                            print(f"• Name: {prompt.name}")
                            print(f"  Description: {prompt.description or 'No description'}")
                            if hasattr(prompt, 'arguments') and prompt.arguments:
                                print("  Arguments:")
                                for arg in prompt.arguments:
                                    required = "[Required]" if arg.required else "[Optional]"
                                    print(f"    - {arg.name} {required}: {arg.description}")
                            print("-" * 30)
            except Exception as e:
                print(f"❌ Failed to list prompts: {e}")

            # --- YAML RESOURCE CONTENT ---
            print("\nYAML CONTENT:")
            print("-" * 50)
            try:
                yaml_response = await session.read_resource("schematiclayer://cortex_analyst/schematic_models/hedis_stage_full/list")
                if hasattr(yaml_response, 'contents') and yaml_response.contents:
                    for item in yaml_response.contents:
                        if hasattr(item, 'text'):
                            try:
                                parsed_yaml = yaml.safe_load(item.text)
                                formatted_yaml = yaml.dump(parsed_yaml, default_flow_style=False, sort_keys=False)
                                print(formatted_yaml)
                            except yaml.YAMLError as e:
                                print(f"⚠️ Failed to parse YAML: {e}")
                                print(f"Raw content:\n{item.text}")
                else:
                    print("  No YAML content found")
            except Exception as e:
                print(f"❌ Error reading YAML content: {e}")

            # --- SEARCH OBJECTS ---
            print("\nSEARCH OBJECTS:")
            print("-" * 50)
            try:
                search_response = await session.read_resource("search://cortex_search/search_obj/list")
                if hasattr(search_response, 'contents') and isinstance(search_response.contents, list):
                    for item in search_response.contents:
                        if hasattr(item, 'text'):
                            try:
                                objects = json.loads(item.text)
                                for obj in objects:
                                    print(obj)
                                break  # Only print once
                            except Exception as e:
                                print(f"⚠️ Failed to parse search object JSON: {e}")
                else:
                    print("  No search objects found")
            except Exception as e:
                print(f"❌ Error reading search objects: {e}")

    print("=" * 50)
    print("✅ CONNECTION CLOSED")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(run())

import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters


# STDIO-based server launch (optional if you're not using subprocess MCP server)
async def run_stdio():
    server_params = StdioServerParameters(
        command="python",
        args=["mcpserver.py"],  # Ensure this path is correct
        env=None
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resources = await session.list_resources()
            print("Resources:", resources)

            tools = await session.list_tools()
            print("Tools:", tools)


# MCP SSE client execution
async def sse_run():
    async with sse_client(url='http://10.126.192.183:8001/sse') as sse_connection:
        async with ClientSession(*sse_connection) as session:
            await session.initialize()

            print("\n✅ Connected and Initialized")

            # --- Call tool: add-prompts ---
            tool_response = await session.call_tool(
                name="add-prompts",
                arguments={
                    "uri": "genaiplatform://hedis/prompts/example-prompt",
                    "prompt": {
                        "prompt_name": "example-prompt",
                        "description": "Prompts to test the adding new prompts",
                        "content": "You are expert to answer HEDIS questions"
                    }
                }
            )
            print("\n📩 Tool Response (add-prompts):")
            print(tool_response)

            # --- Read the prompt back ---
            resource_content = await session.read_resource("genaiplatform://hedis/prompts/example-prompt")
            print("\n📘 Resource Content:")
            print(resource_content.text)

            # --- List prompts ---
            prompts = await session.list_prompts()
            print("\n📋 Prompt List:")
            for p in prompts.prompts:
                print(f"- {p.name}: {p.description}")

            # --- Use the prompt with input ---
            result = await session.get_prompt(
                name="example-prompt",
                arguments={"query": "What is the age criteria for CBP Measure?"}
            )
            print("\n💬 Prompt Completion Result:")
            print(result.text)


if __name__ == "__main__":
    asyncio.run(sse_run())

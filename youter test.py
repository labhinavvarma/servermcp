import asyncio
import httpx
from httpx_sse import connect_sse

async def test_sse():
    url = "http://10.126.192.183:8001/sse"  # Your SSE endpoint

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # ✅ Pass both the client and URL
            async with connect_sse(client, url) as event_source:
                print("✅ Connected to MCP SSE server at", url)
                async for event in event_source.aiter_sse():
                    print("📨 Event received:")
                    print("➡️  ID:", event.id)
                    print("📄 Data:", event.data)
                    break  # stop after first event

    except Exception as e:
        print("❌ Error during SSE connection:", e)

if __name__ == "__main__":
    asyncio.run(test_sse())

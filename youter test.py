import asyncio
import httpx
from httpx_sse import connect_sse

async def test_sse():
    url = "http://13.58.22.105:8000/messages"  # Replace with your actual EC2 IP/DNS

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            async with connect_sse(client, url) as event_source:
                print("✅ Connected to MCP SSE")
                async for event in event_source.aiter_sse():
                    print(f"📨 Event Received: {event.data}")
                    break  # Stop after one event
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sse())
import asyncio
import httpx
from httpx_sse import connect_sse

async def test_sse():
    url = "http://13.58.22.105:8000/messages"  # Replace with your actual EC2 IP/DNS

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            async with connect_sse(client, url) as event_source:
                print("✅ Connected to MCP SSE")
                async for event in event_source.aiter_sse():
                    print(f"📨 Event Received: {event.data}")
                    break  # Stop after one event
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sse())

# === CLIENT: client_app.py ===
# Connects to the MCP Email Server via SSE and invokes send_test_email

import aiohttp
import asyncio
import json

class SimpleSSEAgent:
    def __init__(self, server_url: str):
        # Base URL for MCP SSE endpoint, e.g., http://<EC2-IP>:8000/sse
        self.server_url = server_url.rstrip('/')
        self.session = aiohttp.ClientSession()

    async def connect(self):
        print(f"✅ Connected to MCP server at {self.server_url}")

    async def send_email(self, subject: str, body: str, receivers: str):
        """
        Invoke the send_test_email tool on the MCP server via SSE.
        """
        url = f"{self.server_url}/send_test_email"
        headers = {
            "Accept": "text/event-stream",
            "Content-Type": "application/json"
        }
        payload = {
            "subject": subject,
            "body": body,
            "receivers": receivers
        }

        print(f"🚀 Sending email request to: {url}")
        async with self.session.post(url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                print(f"❌ Request failed with HTTP status {resp.status}")
                text = await resp.text()
                print(f"Response: {text}")
                return

            # Stream SSE events
            async for line in resp.content:
                # SSE lines start with 'data: '
                if line.startswith(b"data: "):
                    data = line[len(b"data: "):].decode('utf-8').strip()
                    if data == '[DONE]':
                        print("✅ Email tool invocation completed.")
                        break
                    print(f"📨 {data}")

    async def close(self):
        await self.session.close()

async def main():
    # Replace <EC2_IP> with your server's address
    server_base = "http://10.126.192.183:8000/sse"
    agent = SimpleSSEAgent(server_base)
    await agent.connect()

    # Example email parameters
    subject = "Test Email via SSE Client"
    body = "<p>Hello from MCP SSE client!</p>"
    receivers = "gentela.vnsaipavan@carelon.com"

    await agent.send_email(subject, body, receivers)
    await agent.close()

if __name__ == '__main__':
    asyncio.run(main())

import streamlit as st
import requests
import json
import uuid
import asyncio
import nest_asyncio
import yaml
import re
from mcp.client.sse import sse_client
from mcp import ClientSession

# Apply nest_asyncio for running async code
nest_asyncio.apply()

# Basic page config
st.set_page_config(page_title="Cortex + MCP Chat", page_icon="🤖")
st.title("🤖 Cortex + MCP Chatbot")

# Cortex LLM Config
API_URL = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"
API_KEY = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
APP_ID = "edadip"
APLCTN_CD = "edagnai"
MODEL = "llama3.1-70b"
SYS_MSG = """You are a powerful AI assistant with access to MCP tools. 
When the user asks a question that requires using tools, analyze the request and use the appropriate tool.
For calculations, use the 'calculator' tool.
For data analysis, use the 'analyze' tool.
For sending emails, use the 'mcp-send-email' tool.
When you use a tool, clearly indicate which tool you're using and the results."""

# Session State initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "context_window" not in st.session_state:
    st.session_state.context_window = []
if "mcp_info" not in st.session_state:
    st.session_state.mcp_info = {"resources": [], "tools": [], "prompts": []}
if "uploaded_json" not in st.session_state:
    st.session_state.uploaded_json = None
if "available_tools" not in st.session_state:
    st.session_state.available_tools = {}

# MCP Server URL input
server_url = st.text_input("MCP Server URL", "http://localhost:8000/sse")

# Connect to MCP button
if st.button("Connect to MCP"):
    status_text = st.empty()
    status_text.text("Connecting to MCP server...")
    
    # Define async function to fetch MCP info
    async def fetch_mcp_info():
        result = {"resources": [], "tools": [], "prompts": []}
        try:
            async with sse_client(server_url) as sse_connection:
                async with ClientSession(*sse_connection) as session:
                    await session.initialize()
                    
                    # Fetch Tools
                    status_text.text("Loading MCP tools...")
                    tools = await session.list_tools()
                    if hasattr(tools, 'tools'):
                        for t in tools.tools:
                            tool_name = t.name
                            tool_desc = getattr(t, 'description', 'No description')
                            result["tools"].append({
                                "name": tool_name, 
                                "description": tool_desc
                            })
                            st.session_state.available_tools[tool_name] = {
                                "description": tool_desc
                            }
                    
                    # Fetch Resources
                    status_text.text("Loading MCP resources...")
                    resources = await session.list_resources()
                    if hasattr(resources, 'resources'):
                        for r in resources.resources:
                            result["resources"].append({
                                "name": r.name, 
                                "description": r.description if hasattr(r, 'description') else "No description"
                            })
                    
                    # Fetch Prompts
                    status_text.text("Loading MCP prompts...")
                    prompts = await session.list_prompts()
                    if hasattr(prompts, 'prompts'):
                        for p in prompts.prompts:
                            args = [
                                f"{arg.name} ({'Required' if arg.required else 'Optional'}): {arg.description}"
                                for arg in getattr(p, 'arguments', [])
                            ]
                            result["prompts"].append({
                                "name": p.name,
                                "description": getattr(p, 'description', ''),
                                "args": args
                            })
                    
                    status_text.text("Connected to MCP server successfully!")
            
            st.session_state.mcp_info = result
            return "Connected successfully!"
        except Exception as e:
            status_text.text(f"MCP Connection Error: {e}")
            return f"Error: {e}"
    
    # Run the async function
    result = asyncio.run(fetch_mcp_info())
    status_text.text(result)

# JSON File Upload
uploaded_file = st.file_uploader("Upload JSON for Analysis", type=["json"])
if uploaded_file:
    try:
        st.session_state.uploaded_json = json.load(uploaded_file)
        st.success("JSON loaded successfully!")
    except Exception as e:
        st.error(f"Failed to parse JSON: {e}")

# Display Available Tools
st.subheader("Available MCP Tools")
if st.session_state.available_tools:
    for tool_name, tool_info in st.session_state.available_tools.items():
        st.text(f"{tool_name}: {tool_info['description']}")
else:
    st.info("No tools loaded. Connect to the MCP server to load available tools.")

# Tool Execution Functions
async def execute_tool(tool_name, args):
    try:
        async with sse_client(server_url) as sse_connection:
            async with ClientSession(*sse_connection) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                return result.content[0].text if hasattr(result, 'content') else "No content returned"
    except Exception as e:
        return f"Tool Error: {str(e)}"

# Calculator Tool
async def run_calculator(expression):
    return await execute_tool("calculator", {"expression": expression})

# Analyze Tool
async def run_analyze(data, operation):
    return await execute_tool("analyze", {
        "data": data,
        "operation": operation
    })

# Email Tool
async def send_email(subject, body, receivers):
    # Convert receivers to list if it's a string
    if isinstance(receivers, str):
        receivers = [r.strip() for r in receivers.split(",")]
    
    return await execute_tool("mcp-send-email", {
        "subject": subject,
        "body": body,
        "receivers": receivers
    })

# Detect Tool Intent
def detect_tool_intent(text):
    # Check for calculator intent
    if re.search(r'calculate|compute|evaluate|math|equation|formula|[+\-*/^√()]', text, re.IGNORECASE):
        matches = re.search(r'(\d+[\s+\-*/^√().\d\s]+\d+)', text)
        if matches:
            return {
                "tool": "calculator",
                "args": {"expression": matches.group(1).strip()}
            }
    
    # Check for analyze intent
    if re.search(r'analyze|analyse|statistics|mean|average|median|sum|min|max|std|standard deviation', text, re.IGNORECASE):
        operation = "mean"  # Default operation
        if "median" in text.lower():
            operation = "median"
        elif "sum" in text.lower():
            operation = "sum"
        elif "min" in text.lower():
            operation = "min"
        elif "max" in text.lower():
            operation = "max"
        elif "std" in text.lower() or "standard deviation" in text.lower():
            operation = "std"
        
        if st.session_state.uploaded_json:
            return {
                "tool": "analyze",
                "args": {
                    "data": st.session_state.uploaded_json,
                    "operation": operation
                }
            }
    
    # Check for email intent
    email_match = re.search(r'send\s+email|email\s+to|send\s+mail|mail\s+to', text, re.IGNORECASE)
    if email_match:
        # Extract email components
        subject_match = re.search(r'subject\s*[:=]\s*["\'](.*?)["\']|subject\s*[:=]\s*(\S.*?)(?=\s+body|\s+to|\s*$)', text, re.IGNORECASE)
        body_match = re.search(r'body\s*[:=]\s*["\'](.*?)["\']|body\s*[:=]\s*(\S.*?)(?=\s+subject|\s+to|\s*$)', text, re.IGNORECASE)
        to_match = re.search(r'to\s*[:=]\s*["\'](.*?)["\']|to\s*[:=]\s*(\S.*?)(?=\s+subject|\s+body|\s*$)', text, re.IGNORECASE)
        
        subject = (subject_match.group(1) or subject_match.group(2)) if subject_match else "No subject"
        body = (body_match.group(1) or body_match.group(2)) if body_match else "No body"
        to = (to_match.group(1) or to_match.group(2)) if to_match else ""
        
        if to:
            return {
                "tool": "mcp-send-email",
                "args": {
                    "subject": subject,
                    "body": body,
                    "receivers": to
                }
            }
    
    # No tool intent detected
    return None

# Process User Message
async def process_user_message(user_message):
    # Check if the message indicates a tool should be used
    tool_intent = detect_tool_intent(user_message)
    
    if tool_intent:
        tool_name = tool_intent["tool"]
        tool_args = tool_intent["args"]
        
        # Execute the appropriate tool based on detected intent
        if tool_name == "calculator":
            expression = tool_args["expression"]
            result = await run_calculator(expression)
            return f"📊 I detected a calculation request. Using the calculator tool:\n\nExpression: `{expression}`\n\nResult: {result}"
        
        elif tool_name == "analyze" and st.session_state.uploaded_json:
            operation = tool_args["operation"]
            data = tool_args["data"]
            result = await run_analyze(data, operation)
            return f"📈 I detected a data analysis request. Using the analyze tool with operation '{operation}':\n\nResult: {result}"
        
        elif tool_name == "mcp-send-email":
            subject = tool_args["subject"]
            body = tool_args["body"]
            receivers = tool_args["receivers"]
            result = await send_email(subject, body, receivers)
            return f"📧 I detected an email request. Using the email tool:\n\nTo: {receivers}\nSubject: {subject}\nBody: {body}\n\nResult: {result}"
    
    # Fall back to LLM if no tool intent is detected or no tool is available
    return call_cortex_llm(user_message, st.session_state.context_window)

# Cortex LLM Request
def call_cortex_llm(text, context_window):
    session_id = str(uuid.uuid4())
    
    # Create a more detailed system message with available tools
    enhanced_sys_msg = SYS_MSG
    if st.session_state.available_tools:
        enhanced_sys_msg += "\n\nAvailable tools:\n"
        for tool_name, tool_info in st.session_state.available_tools.items():
            enhanced_sys_msg += f"- {tool_name}: {tool_info['description']}\n"
    
    history = "\n".join(context_window[-5:])
    full_prompt = f"{enhanced_sys_msg}\n{history}\nUser: {text}"

    payload = {
        "query": {
            "aplctn_cd": APLCTN_CD,
            "app_id": APP_ID,
            "api_key": API_KEY,
            "method": "cortex",
            "model": MODEL,
            "sys_msg": enhanced_sys_msg,
            "limit_convs": "0",
            "prompt": {
                "messages": [
                    {"role": "user", "content": full_prompt}
                ]
            },
            "app_lvl_prefix": "",
            "user_id": "",
            "session_id": session_id
        }
    }

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "Authorization": f'Snowflake Token="{API_KEY}"'
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, verify=False)
        if response.status_code == 200:
            raw = response.text
            if "end_of_stream" in raw:
                answer, _, _ = raw.partition("end_of_stream")
                return answer.strip()
            return raw.strip()
        else:
            return f"Cortex Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Cortex Exception: {str(e)}"

# Chat Display
st.subheader("Chat")
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.text_input("User:", msg["content"], disabled=True)
    else:
        st.text_area("Assistant:", msg["content"], height=200, disabled=True)

# Chat Input
query = st.text_input("Ask me anything or request tool usage:")
send_button = st.button("Send")

if query and send_button:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": query})
    
    # Process user message
    status_text = st.empty()
    status_text.text("Thinking...")
    
    # Process the message and detect tool usage
    response = asyncio.run(process_user_message(query))
    status_text.empty()
    
    # Save the assistant's response
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Update context window for future messages
    st.session_state.context_window.append(f"User: {query}\nBot: {response}")
    
    # Refresh the page to show the new messages
    st.experimental_rerun()

# Clear Chat Button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.context_window = []
    st.experimental_rerun()

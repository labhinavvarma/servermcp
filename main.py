from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from loguru import logger
import statistics
from typing import Union, List, Dict
import uvicorn

# Initialize FastAPI and MCP
app = FastAPI(title="MCP JSON Server")
mcp = FastMCP("MCP JSON Analyzer", app=app)

#  Use @mcp.tool decorator
@mcp.tool(name="analyze-data", description="Analyze numeric list/dict with summary stats. Ignores text.")
async def analyze_data_tool(data: Union[List, Dict[str, List]]):
    try:
        if isinstance(data, list):
            numbers = [float(n) for n in data if isinstance(n, (int, float)) or (isinstance(n, str) and n.replace('.', '', 1).isdigit())]
            if not numbers:
                return {"status": "error", "error": "No valid numeric data in the list"}
            mean_val = statistics.mean(numbers)
            return {"status": "success", "result": {
                "sum": sum(numbers),
                "mean": mean_val,
                "average": mean_val,
                "median": statistics.median(numbers),
                "min": min(numbers),
                "max": max(numbers),
            }}
        elif isinstance(data, dict):
            result = {}
            for key, values in data.items():
                if not isinstance(values, list):
                    continue
                numbers = [float(n) for n in values if isinstance(n, (int, float)) or (isinstance(n, str) and n.replace('.', '', 1).isdigit())]
                if not numbers:
                    continue
                mean_val = statistics.mean(numbers)
                result[key] = {
                    "sum": sum(numbers),
                    "mean": mean_val,
                    "average": mean_val,
                    "median": statistics.median(numbers),
                    "min": min(numbers),
                    "max": max(numbers),
                }
            if not result:
                return {"status": "error", "error": "No valid numeric data found"}
            return {"status": "success", "result": result}
        else:
            return {"status": "error", "error": f"Unsupported data type: {type(data).__name__}"}
    except Exception as e:
        logger.exception("Tool failed")
        return {"status": "error", "error": str(e)}

#  Run the server using app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
import streamlit as st
import requests
import json

# MCP server endpoint
MCP_SERVER_URL = "http://localhost:8000/tool/analyze-data"

st.set_page_config(page_title="MCP JSON Analyzer", layout="centered")
st.title("📊 JSON Analyzer using MCP")

# File uploader
uploaded_file = st.file_uploader("Upload your JSON file (array or dict of arrays)", type=["json"])

if uploaded_file:
    try:
        json_data = json.load(uploaded_file)
        st.success("✅ File successfully loaded!")
        st.json(json_data)

        # Button to call MCP tool
        if st.button("Run Analysis"):
            with st.spinner("Calling MCP server..."):
                try:
                    response = requests.post(
                        MCP_SERVER_URL,
                        json={"data": json_data},
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    result = response.json()
                    if result.get("status") == "success":
                        st.subheader("📈 Result")
                        st.json(result["result"])
                    else:
                        st.error(f"❌ Error: {result.get('error')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"🚨 Connection failed: {str(e)}")
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON file. Please upload a proper JSON array or dict.")

# Footer
st.markdown("---")
st.caption("MCP Client powered by Streamlit")

import streamlit as st
import requests
import json

# MCP endpoint for the analyzserve tool
MCP_URL = "http://localhost:8000/tool/analyzserve"

st.set_page_config(page_title="MCP Analyzer Client", layout="centered")
st.title("📊 MCP JSON Analyzer Client")

# Upload JSON
uploaded_file = st.file_uploader("Upload a JSON file (list or dict of lists)", type=["json"])

# Operation selection
operation = st.selectbox("Select Operation", ["sum", "mean", "median", "min", "max"])

if uploaded_file:
    try:
        json_data = json.load(uploaded_file)
        st.success("✅ JSON file loaded successfully.")
        st.json(json_data)

        if st.button("Analyze"):
            with st.spinner("Sending data to MCP server..."):
                try:
                    response = requests.post(
                        MCP_URL,
                        headers={"Content-Type": "application/json"},
                        json={"data": json_data, "operation": operation},
                        timeout=10
                    )
                    result = response.json()

                    if result.get("status") == "success":
                        st.subheader("✅ Result")
                        st.json(result["result"])
                    else:
                        st.error(f"❌ Error: {result.get('error')}")

                except requests.exceptions.RequestException as e:
                    st.error(f"🔌 Failed to reach MCP server: {e}")
    except json.JSONDecodeError:
        st.error("❌ Uploaded file is not valid JSON.")

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit and MCP")

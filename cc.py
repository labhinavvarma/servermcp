import streamlit as st
import requests
import json
import uuid
import urllib3

# Disable SSL warnings (only do this in internal/dev environments)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Configuration ===
API_URL = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"
API_KEY = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
APP_ID = "edadip"
APLCTN_CD = "edagnai"
MODEL = "llama3.1-70b"
SYS_MSG = (
    "You are a powerful AI assistant. Provide accurate, concise answers based on context."
)

# === Page Setup ===
st.set_page_config(page_title="Cortex Chatbot", page_icon="🤖")
st.title("🤖 Snowflake Cortex Chatbot")

# === Session State Setup ===
if "messages" not in st.session_state:
    st.session_state.messages = []

# === Chat Input Form ===
with st.form("chat_form", clear_on_submit=True):
    user_query = st.text_input("Ask a question", key="chat_input", placeholder="e.g. What is 5 + 7?")
    submitted = st.form_submit_button("Send")

# === When Form Submitted ===
if submitted and user_query:
    session_id = str(uuid.uuid4())  # Unique session ID per message

    # === Build Payload ===
    payload = {
        "query": {
            "aplctn_cd": APLCTN_CD,
            "app_id": APP_ID,
            "api_key": API_KEY,
            "method": "cortex",
            "model": MODEL,
            "sys_msg": SYS_MSG,
            "limit_convs": "0",
            "prompt": {
                "messages": [
                    {
                        "role": "user",
                        "content": user_query
                    }
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
                bot_reply = answer.strip()
            else:
                bot_reply = raw.strip()

            # Save messages to history
            st.session_state.messages.append(("user", user_query))
            st.session_state.messages.append(("bot", bot_reply))

        else:
            st.error(f"❌ Error {response.status_code}: {response.text}")

    except Exception as e:
        st.error(f"❌ Request failed: {str(e)}")

# === Display Chat History ===
st.divider()
for role, message in reversed(st.session_state.messages):
    if role == "user":
        st.markdown(f"🧑 **You:** {message}")
    else:
        st.markdown(f"🤖 **Bot:** {message}")

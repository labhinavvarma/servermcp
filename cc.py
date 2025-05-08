import streamlit as st
import requests
import json
import uuid
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Configuration ===
API_URL = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"
API_KEY = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
APP_ID = "edadip"
APLCTN_CD = "edagnai"
MODEL = "llama3.1-70b"
SYS_MSG = "You are powerful AI assistant in providing accurate answers always. Be Concise in providing answers based on context."

# === Session State ===
if "messages" not in st.session_state:
    st.session_state.messages = []

# === Streamlit Page Config ===
st.set_page_config(page_title="Cortex Chatbot", page_icon="🤖", layout="centered")
st.title("🤖 Snowflake Cortex Chatbot")

# === User Input ===
user_input = st.text_input("Ask me anything:", placeholder="e.g. Who is the president of the USA?", key="input")

# === Send to Cortex on submit ===
if user_input:
    session_id = str(uuid.uuid4())  # Optional: new session per question

    # === Construct Payload ===
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
                        "content": user_input
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

            st.session_state.messages.append(("user", user_input))
            st.session_state.messages.append(("bot", bot_reply))

            # Clear input field
            st.session_state.input = ""

        else:
            st.error(f"Error {response.status_code}: {response.text}")

    except Exception as e:
        st.error(f"❌ Request failed: {str(e)}")

# === Display Chat History ===
for role, message in reversed(st.session_state.messages):
    if role == "user":
        st.markdown(f"**🧑 You:** {message}")
    else:
        st.markdown(f"**🤖 Bot:** {message}")

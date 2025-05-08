import requests
import json
import uuid
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === Cortex API Endpoint ===
url = "https://sfassist.edagenaidev.awsdns.internal.das/api/cortex/complete"

# === Static Fields ===
api_key = "78a799ea-a0f6-11ef-a0ce-15a449f7a8b0"
app_id = "edadip"
aplctn_cd = "edagnai"
model = "llama3.1-70b"
sys_msg = "You are powerful AI assistant in providing accurate answers always. Be Concise in providing answers based on context."
session_id = str(uuid.uuid4())  # Optional: generate a new UUID for session

# === Headers with Authorization ===
headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json",
    "Authorization": f'Snowflake Token="{api_key}"'
}

# === Main Chatbot Loop ===
print("🤖 Snowflake Cortex Chatbot Ready!")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ["exit", "quit"]:
        print("👋 Chat ended.")
        break

    # === Build Request Body ===
    payload = {
        "query": {
            "aplctn_cd": aplctn_cd,
            "app_id": app_id,
            "api_key": api_key,
            "method": "cortex",
            "model": model,
            "sys_msg": sys_msg,
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

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        print(f"✅ Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"🤖 Bot: {data.get('text', 'No response received')}\n")
        else:
            print("⚠️ Error Response:")
            try:
                print(json.dumps(response.json(), indent=2), "\n")
            except:
                print(response.text)

    except Exception as e:
        print("❌ Request Failed:", str(e), "\n")

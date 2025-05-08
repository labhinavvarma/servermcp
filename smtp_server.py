import streamlit as st
import requests
import json
import pandas as pd
import io
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"  # Replace with your actual server URL
DEFAULT_TIMEOUT = 30  # seconds

# Page setup
st.set_page_config(
    page_title="MCP Data Utility Tools",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .tool-header {
        font-size: 1.8rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f0f2f6;
    }
    .tool-description {
        font-size: 1rem;
        margin-bottom: 1.5rem;
        color: #586069;
    }
    .success-box {
        padding: 1rem;
        background-color: #e6f4ea;
        border-radius: 0.5rem;
        border-left: 4px solid #34a853;
    }
    .error-box {
        padding: 1rem;
        background-color: #fce8e6;
        border-radius: 0.5rem;
        border-left: 4px solid #ea4335;
    }
    .info-box {
        padding: 1rem;
        background-color: #e8f0fe;
        border-radius: 0.5rem;
        border-left: 4px solid #4285f4;
    }
</style>
""", unsafe_allow_html=True)

# --- Utility Functions ---
def check_api_health():
    """Check if the API is available"""
    try:
        response = requests.get(f"{API_URL}/check", timeout=5)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"API returned status code {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

def get_available_tools():
    """Get list of available tools from the API"""
    try:
        response = requests.get(f"{API_URL}/mcp-tools", timeout=5)
        if response.status_code == 200:
            return response.json().get("registered_tools", [])
        else:
            return []
    except requests.exceptions.RequestException:
        return []

def display_json_preview(json_data):
    """Display a formatted preview of JSON data"""
    st.code(json.dumps(json_data, indent=2), language="json")

def display_result(success, data, error_message=None):
    """Display API call results with appropriate styling"""
    if success:
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown("#### ✅ Success!")
        if isinstance(data, dict):
            display_json_preview(data)
        else:
            st.write(data)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="error-box">', unsafe_allow_html=True)
        st.markdown("#### ❌ Error")
        if error_message:
            st.write(error_message)
        if data:
            if isinstance(data, dict):
                display_json_preview(data)
            else:
                st.write(data)
        st.markdown('</div>', unsafe_allow_html=True)

def parse_numeric_data(uploaded_file):
    """Parse numeric data from uploaded file (JSON or CSV)"""
    try:
        # Get file extension
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'json':
            # Parse JSON file
            data = json.load(uploaded_file)
            return True, data, None
        elif file_extension == 'csv':
            # Parse CSV file
            df = pd.read_csv(uploaded_file)
            
            # Convert DataFrame to dictionary format expected by the analyze tool
            data_dict = {}
            for column in df.columns:
                # Only include numeric columns
                if pd.api.types.is_numeric_dtype(df[column]):
                    data_dict[column] = df[column].tolist()
            
            if not data_dict:
                return False, None, "No numeric columns found in the CSV file."
            
            return True, data_dict, None
        else:
            return False, None, f"Unsupported file extension: {file_extension}. Please upload a JSON or CSV file."
    except Exception as e:
        return False, None, f"Error parsing file: {str(e)}"

def visualize_analysis_results(data, operation):
    """Create visualizations based on the analysis results"""
    if not data or "status" not in data or data["status"] != "success":
        return
    
    result = data.get("result")
    
    if isinstance(result, dict):
        # Multiple columns/series
        df = pd.DataFrame({"Category": list(result.keys()), "Value": list(result.values())})
        
        # Create bar chart
        fig = px.bar(
            df, 
            x="Category", 
            y="Value", 
            title=f"{operation.capitalize()} Values by Category",
            labels={"Value": operation.capitalize()},
            color="Category"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Create table
        st.dataframe(df, use_container_width=True)
    else:
        # Single value result - show as big number with caption
        st.metric(label=f"{operation.capitalize()} Value", value=f"{result:.4f}")

# --- Sidebar ---
st.sidebar.markdown('<h1 class="main-header">MCP Data Utility Tools</h1>', unsafe_allow_html=True)
st.sidebar.markdown("---")

# Check API health
api_ok, api_message = check_api_health()
if api_ok:
    st.sidebar.success("✅ API is online")
else:
    st.sidebar.error(f"❌ API is offline: {api_message.get('error', 'Unknown error')}")

# Navigation
tool_options = [
    "Data Analyzer",
    "Calculator",
    "Weather Forecast",
    "Email Sender",
    "HEDIS Text-to-SQL",
    "HEDIS Document Search"
]

selected_tool = st.sidebar.radio("Select Tool", tool_options)

st.sidebar.markdown("---")
st.sidebar.info("""
This application provides a user interface for the MCP Data Utility Tools API. 
Select a tool from the menu to get started.
""")

# --- Main Content ---
st.markdown(f'<h1 class="tool-header">{selected_tool}</h1>', unsafe_allow_html=True)

# === Data Analyzer Tool ===
if selected_tool == "Data Analyzer":
    st.markdown('<p class="tool-description">Upload JSON or CSV data files and perform statistical analysis.</p>', unsafe_allow_html=True)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload a JSON or CSV file", type=["json", "csv"])
    
    if uploaded_file is not None:
        # Parse the uploaded file
        success, data, error_message = parse_numeric_data(uploaded_file)
        
        if success:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("#### 📄 Parsed Data Preview")
            display_json_preview(data)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Operation selection
            operation = st.selectbox(
                "Select statistical operation",
                ["mean", "median", "sum", "min", "max"]
            )
            
            # Submit button
            if st.button("Analyze Data"):
                with st.spinner("Analyzing data..."):
                    try:
                        # Call the analyze endpoint
                        response = requests.post(
                            f"{API_URL}/analyze",
                            json={"data": data, "operation": operation},
                            timeout=DEFAULT_TIMEOUT
                        )
                        
                        if response.status_code == 200:
                            result_data = response.json()
                            display_result(True, result_data)
                            
                            # Visualize the results
                            st.markdown("### Visualization")
                            visualize_analysis_results(result_data, operation)
                        else:
                            display_result(False, response.json(), f"API returned status code {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        display_result(False, None, f"API request failed: {str(e)}")
        else:
            display_result(False, None, error_message)

# === Calculator Tool ===
elif selected_tool == "Calculator":
    st.markdown('<p class="tool-description">Evaluate arithmetic expressions safely.</p>', unsafe_allow_html=True)
    
    expression = st.text_input("Enter arithmetic expression", placeholder="e.g., (5 + 10) * 2")
    
    if st.button("Calculate") and expression:
        with st.spinner("Calculating..."):
            try:
                # Call the calculator endpoint
                response = requests.post(
                    f"{API_URL}/calculate",
                    json={"expression": expression},
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    display_result(True, result)
                else:
                    display_result(False, response.json(), f"API returned status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                display_result(False, None, f"API request failed: {str(e)}")

# === Weather Forecast Tool ===
elif selected_tool == "Weather Forecast":
    st.markdown('<p class="tool-description">Get current weather forecasts for any location.</p>', unsafe_allow_html=True)
    
    place = st.text_input("Enter location", placeholder="e.g., New York, NY")
    
    if st.button("Get Weather") and place:
        with st.spinner(f"Getting weather for {place}..."):
            try:
                # Call the weather endpoint
                response = requests.post(
                    f"{API_URL}/get_weather",
                    json={"place": place},
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Check if result is a string or dict
                    if isinstance(result, str):
                        display_result(True, result)
                    else:
                        display_result(True, result)
                else:
                    display_result(False, response.json(), f"API returned status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                display_result(False, None, f"API request failed: {str(e)}")

# === Email Sender Tool ===
elif selected_tool == "Email Sender":
    st.markdown('<p class="tool-description">Send emails to multiple recipients.</p>', unsafe_allow_html=True)
    
    subject = st.text_input("Subject", placeholder="e.g., Meeting Reminder")
    receivers = st.text_input("Recipients (comma-separated)", placeholder="e.g., user1@example.com, user2@example.com")
    
    # Email body with rich text editor
    st.write("Email Body:")
    body = st.text_area("", height=200, placeholder="Enter email content here...")
    
    if st.button("Send Email") and subject and receivers and body:
        with st.spinner("Sending email..."):
            try:
                # Call the email endpoint
                response = requests.post(
                    f"{API_URL}/send_test_email",
                    json={"subject": subject, "body": body, "receivers": receivers},
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        display_result(True, result)
                    else:
                        display_result(False, result, "Email could not be sent")
                else:
                    display_result(False, response.json(), f"API returned status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                display_result(False, None, f"API request failed: {str(e)}")

# === HEDIS Text-to-SQL Tool ===
elif selected_tool == "HEDIS Text-to-SQL":
    st.markdown('<p class="tool-description">Convert natural language queries to SQL for HEDIS datasets.</p>', unsafe_allow_html=True)
    
    prompt = st.text_area("Enter your question about HEDIS codes", 
                         placeholder="e.g., What are the codes in Breast Cancer Value Set?", 
                         height=100)
    
    if st.button("Generate SQL") and prompt:
        with st.spinner("Converting to SQL..."):
            try:
                # Call the text2sql endpoint
                response = requests.post(
                    f"{API_URL}/DFWAnalyst",
                    json={"prompt": prompt},
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract SQL if available
                    sql = None
                    if isinstance(result, dict) and "message" in result:
                        message = result["message"]
                        if isinstance(message, dict) and "content" in message:
                            for content_item in message["content"]:
                                if content_item.get("type") == "sql":
                                    sql = content_item.get("statement")
                    
                    if sql:
                        st.markdown("### Generated SQL")
                        st.code(sql, language="sql")
                    
                    display_result(True, result)
                else:
                    display_result(False, response.json(), f"API returned status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                display_result(False, None, f"API request failed: {str(e)}")

# === HEDIS Document Search Tool ===
elif selected_tool == "HEDIS Document Search":
    st.markdown('<p class="tool-description">Search HEDIS measure specification documents for relevant information.</p>', unsafe_allow_html=True)
    
    query = st.text_area("Enter your search query", 
                        placeholder="e.g., What is the age criteria for BCS Measure?", 
                        height=100)
    
    if st.button("Search") and query:
        with st.spinner("Searching HEDIS documents..."):
            try:
                # Call the search endpoint
                response = requests.post(
                    f"{API_URL}/DFWSearch",
                    json={"query": query},
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract and display search results in a more readable format
                    if isinstance(result, dict) and "results" in result:
                        st.markdown("### Search Results")
                        
                        for i, item in enumerate(result["results"]):
                            st.markdown(f"**Result {i+1}**")
                            
                            if "chunk" in item:
                                st.markdown(item["chunk"])
                            else:
                                display_json_preview(item)
                            
                            st.markdown("---")
                    
                    display_result(True, result)
                else:
                    display_result(False, response.json(), f"API returned status code {response.status_code}")
            except requests.exceptions.RequestException as e:
                display_result(False, None, f"API request failed: {str(e)}")

# --- Footer ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #777;">
    MCP Data Utility Tools Client • {0}
</div>
""".format(datetime.now().year), unsafe_allow_html=True)

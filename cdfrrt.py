import streamlit as st
import json
import pandas as pd
import plotly.express as px
import requests
import os
import time
from typing import Dict, List, Union, Any

st.set_page_config(
    page_title="EC2 MCP Analyzer Client", 
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 500;
        color: #333;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1E88E5;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #43A047;
    }
    .warning-box {
        background-color: #FFF8E1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #FFA000;
    }
    .error-box {
        background-color: #FFEBEE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #E53935;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Header
    st.markdown('<div class="main-header">EC2 MCP Analyzer Client</div>', unsafe_allow_html=True)
    st.markdown("Connect to your MCP server on EC2 and analyze data with the Analyze tool.")
    
    # Server configuration
    with st.sidebar:
        st.markdown('<div class="section-header">Server Configuration</div>', unsafe_allow_html=True)
        
        # EC2 connection settings
        ec2_url = st.text_input(
            "EC2 Server URL", 
            value="http://your-ec2-instance-ip:8000",
            help="The URL of your EC2 instance running the MCP server"
        )
        
        st.divider()
        
        # Analysis settings
        st.markdown('<div class="section-header">Analysis Settings</div>', unsafe_allow_html=True)
        
        operation = st.selectbox(
            "Select Operation", 
            options=["mean", "median", "sum", "min", "max", "average", "weighted_average"],
            format_func=lambda x: x.capitalize() if x != "weighted_average" else "Weighted Average",
            help="The statistical operation to perform on your data"
        )
        
        # Connection test button
        if st.button("Test Connection"):
            with st.spinner("Testing connection..."):
                try:
                    # Try to connect to the server's root endpoint
                    response = requests.get(f"{ec2_url}/")
                    if response.status_code == 200:
                        st.markdown('<div class="success-box">✅ Successfully connected to the server!</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="error-box">❌ Server returned status code: {response.status_code}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="error-box">❌ Failed to connect: {str(e)}</div>', unsafe_allow_html=True)
                    st.markdown("""
                    <div class="info-box">
                    <b>Troubleshooting tips:</b><br>
                    • Make sure your EC2 instance is running<br>
                    • Check that port 8000 is open in your security group<br>
                    • Verify the URL format (should be http://ip-address:8000)<br>
                    • Ensure your network allows the connection
                    </div>
                    """, unsafe_allow_html=True)
    
    # Create tabs for different data input methods
    tabs = st.tabs(["Upload JSON", "Example Data", "Manual Entry"])
    
    # Tab 1: Upload JSON
    with tabs[0]:
        st.markdown('<div class="section-header">Upload JSON Data</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Upload a JSON file containing your data for analysis.</div>', unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Choose a JSON file", type=["json"])
        
        if uploaded_file is not None:
            try:
                # Load and process the JSON data
                data = json.load(uploaded_file)
                process_data(data, ec2_url, operation)
            except json.JSONDecodeError:
                st.markdown('<div class="error-box">❌ Invalid JSON file. Please upload a valid JSON file.</div>', unsafe_allow_html=True)
    
    # Tab 2: Example Data
    with tabs[1]:
        st.markdown('<div class="section-header">Use Example Data</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Try the analyzer with our pre-defined example data.</div>', unsafe_allow_html=True)
        
        # Example type selection
        example_type = st.radio(
            "Select example data type:",
            ["Standard Data", "Weighted Average Data"]
        )
        
        if st.button("Load Example Data"):
            if example_type == "Standard Data":
                # Standard example data
                example_data = {
                    "sales_by_region": [120, 150, 80, 200, 95],
                    "temperatures": [22.5, 23.1, 21.8, 24.0, 22.7],
                    "website_traffic": [1520, 1845, 1350, 2100, 1750],
                    "conversion_rates": [0.12, 0.08, 0.15, 0.10, 0.11]
                }
            else:
                # Weighted average example data
                example_data = {
                    "values": [85, 90, 78, 92, 88],
                    "weights": [0.2, 0.3, 0.1, 0.25, 0.15]
                }
            
            # Process the example data
            process_data(example_data, ec2_url, operation)
    
    # Tab 3: Manual Entry
    with tabs[2]:
        st.markdown('<div class="section-header">Manual Data Entry</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">Enter your data manually for analysis.</div>', unsafe_allow_html=True)
        
        # Data structure selection
        data_structure = st.radio(
            "Select data structure:",
            ["Simple List", "Key-Value Pairs", "Weighted Average"]
        )
        
        if data_structure == "Simple List":
            # Simple list input
            values_input = st.text_area(
                "Enter values (comma-separated):",
                "10, 20, 30, 40, 50"
            )
            
            if st.button("Analyze List Data"):
                try:
                    # Parse the values
                    values = [float(v.strip()) for v in values_input.split(",") if v.strip()]
                    process_data(values, ec2_url, operation)
                except ValueError:
                    st.markdown('<div class="error-box">❌ Invalid input. Please enter comma-separated numbers.</div>', unsafe_allow_html=True)
                    
        elif data_structure == "Key-Value Pairs":
            # Dictionary input with multiple keys
            st.markdown("Enter each category and its values (comma-separated):")
            
            # Allow up to 5 categories
            categories = {}
            for i in range(5):
                col1, col2 = st.columns([1, 3])
                with col1:
                    key = st.text_input(f"Category name #{i+1}:", value="" if i > 0 else "Category 1")
                with col2:
                    values = st.text_input(f"Values for #{i+1}:", value="" if i > 0 else "10, 20, 30, 40, 50")
                
                if key and values:
                    try:
                        categories[key] = [float(v.strip()) for v in values.split(",") if v.strip()]
                    except ValueError:
                        st.markdown(f'<div class="error-box">❌ Invalid values for category "{key}".</div>', unsafe_allow_html=True)
            
            if st.button("Analyze Category Data"):
                if categories:
                    process_data(categories, ec2_url, operation)
                else:
                    st.markdown('<div class="error-box">❌ Please add at least one category with values.</div>', unsafe_allow_html=True)
                    
        else:  # Weighted Average
            # Weighted average input
            col1, col2 = st.columns(2)
            
            with col1:
                values_input = st.text_area(
                    "Values (comma-separated):",
                    "85, 90, 78, 92, 88"
                )
            
            with col2:
                weights_input = st.text_area(
                    "Weights (comma-separated):",
                    "0.2, 0.3, 0.1, 0.25, 0.15"
                )
                
            if st.button("Analyze Weighted Data"):
                try:
                    # Parse the inputs
                    values = [float(v.strip()) for v in values_input.split(",") if v.strip()]
                    weights = [float(w.strip()) for w in weights_input.split(",") if w.strip()]
                    
                    if len(values) != len(weights):
                        st.markdown('<div class="error-box">❌ Values and weights must have the same length.</div>', unsafe_allow_html=True)
                    else:
                        data = {
                            "values": values,
                            "weights": weights
                        }
                        process_data(data, ec2_url, operation)
                except ValueError:
                    st.markdown('<div class="error-box">❌ Invalid input. Please enter comma-separated numbers.</div>', unsafe_allow_html=True)

def process_data(data, server_url, operation):
    """Process the data and send it to the MCP server for analysis"""
    
    # Display the raw data
    with st.expander("Raw Data", expanded=False):
        st.json(data)
    
    # Check data type and format
    if isinstance(data, list):
        st.markdown(f'<div class="info-box">📊 Detected list data with {len(data)} elements</div>', unsafe_allow_html=True)
        data_to_analyze = data
    elif isinstance(data, dict):
        st.markdown(f'<div class="info-box">📊 Detected dictionary data with {len(data)} keys</div>', unsafe_allow_html=True)
        data_to_analyze = data
    else:
        st.markdown('<div class="error-box">❌ Invalid data format. Expected a list or dictionary.</div>', unsafe_allow_html=True)
        return
    
    # Analyze button
    analyze_btn = st.button("Run Analysis")
    
    if analyze_btn:
        with st.spinner(f"Performing {operation} analysis..."):
            try:
                # Prepare the request to the MCP server
                sse_url = f"{server_url}/sse"
                
                # Create the MCP request payload
                request_id = f"client-request-{int(time.time())}"
                payload = {
                    "id": request_id,
                    "name": "analyze",
                    "args": {
                        "data": data_to_analyze,
                        "operation": operation
                    }
                }
                
                # Log the request details for debugging
                with st.expander("Debug Information", expanded=False):
                    st.write("Request sent to:", sse_url)
                    st.write("Request payload:", payload)
                
                # Send the request to the MCP server
                response = requests.post(
                    sse_url,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                    stream=True,
                    timeout=10
                )
                
                if response.status_code != 200:
                    st.markdown(f'<div class="error-box">❌ HTTP Error: {response.status_code} - {response.text}</div>', unsafe_allow_html=True)
                    return
                
                # Process the SSE response
                result = None
                for line in response.iter_lines():
                    if not line:
                        continue
                    
                    line = line.decode('utf-8')
                    # Debug line in expander
                    with st.expander("Response Stream", expanded=False):
                        st.write(line)
                        
                    if not line.startswith("data: "):
                        continue
                    
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        response_data = json.loads(data_str)
                        if response_data.get("id") == request_id and "response" in response_data:
                            result = response_data["response"]
                            break
                    except json.JSONDecodeError:
                        continue
                
                if not result:
                    st.markdown('<div class="error-box">❌ No valid response received from server</div>', unsafe_allow_html=True)
                    return
                
                # Process the result
                if result.get("status") == "success":
                    st.markdown('<div class="success-box">✅ Analysis completed successfully!</div>', unsafe_allow_html=True)
                    
                    analysis_result = result["result"]
                    
                    # Display the results
                    st.markdown('<div class="section-header">Analysis Results</div>', unsafe_allow_html=True)
                    
                    # Create a container for the results
                    results_container = st.container()
                    
                    with results_container:
                        if isinstance(analysis_result, dict):
                            # Create a DataFrame for better visualization
                            df = pd.DataFrame({
                                "Category": list(analysis_result.keys()),
                                f"{operation.capitalize()} Value": list(analysis_result.values())
                            })
                            
                            # Display as table
                            st.dataframe(df, use_container_width=True)
                            
                            # Create a bar chart
                            fig = px.bar(
                                df, 
                                x="Category", 
                                y=f"{operation.capitalize()} Value",
                                title=f"{operation.capitalize()} Values by Category",
                                color=f"{operation.capitalize()} Value",
                                color_continuous_scale="Viridis"
                            )
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Add a download button for the results
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="Download Results as CSV",
                                data=csv,
                                file_name=f"{operation}_analysis_results.csv",
                                mime="text/csv"
                            )
                        else:
                            # Single value result
                            operation_display = "Weighted Average" if operation == "weighted_average" else operation.capitalize()
                            
                            # Create a metric display
                            st.metric(
                                label=f"{operation_display} of Data", 
                                value=f"{analysis_result:.4f}" if isinstance(analysis_result, float) else analysis_result
                            )
                            
                            # Create a simple visualization for single value
                            fig = px.bar(
                                x=["Result"], 
                                y=[analysis_result],
                                title=f"{operation_display} Analysis Result",
                                color=["Result"],
                                text=[f"{analysis_result:.4f}" if isinstance(analysis_result, float) else analysis_result]
                            )
                            fig.update_traces(textposition='outside')
                            fig.update_layout(showlegend=False, height=400)
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.markdown(f'<div class="error-box">❌ Analysis error: {result.get("error", "Unknown error")}</div>', unsafe_allow_html=True)
                    
            except requests.exceptions.Timeout:
                st.markdown('<div class="error-box">❌ Request timed out. The server took too long to respond.</div>', unsafe_allow_html=True)
                st.markdown("""
                <div class="info-box">
                <b>Timeout troubleshooting:</b><br>
                • Check if your EC2 instance is under heavy load<br>
                • Verify that the analyze tool is functioning correctly<br>
                • Try with a smaller dataset
                </div>
                """, unsafe_allow_html=True)
            except requests.exceptions.RequestException as e:
                st.markdown(f'<div class="error-box">❌ Connection error: {str(e)}</div>', unsafe_allow_html=True)
                st.markdown("""
                <div class="info-box">
                <b>Connection troubleshooting:</b><br>
                • Make sure the MCP server is running<br>
                • Check that your EC2 instance is accessible<br>
                • Verify the server URL format
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f'<div class="error-box">❌ Error: {str(e)}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()

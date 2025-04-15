#!/usr/bin/env python3
"""
LangChain Agent that uses:
1. MCP server for tools (running in AWS)
2. Fixed CortexWrapper for LLM access with proper imports
"""

import os
import sys
import math
import json
from typing import Dict, List, Any, Optional, Union

# Import the fixed CortexWrapper - this assumes it's in a file called cortex_wrapper.py
from cortex_wrapper import CortexWrapper

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# MCP Client import
from mcp.client.fastmcp import FastMCPClient

# For display
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# US State coordinates (a subset for testing)
US_STATES_SUBSET = {
    "Colorado": (39.059811, -105.311104),
    "Maine": (44.693947, -69.381927),
    "Michigan": (43.326618, -84.536095),
    "Minnesota": (45.694454, -93.900192),
    "Montana": (46.921925, -110.454353),
}

class MCPWeatherTool(BaseTool):
    name = "get_weather"
    description = "Fetches current weather forecast for a given location using the NWS API."
    
    def __init__(self, mcp_client):
        super().__init__()
        self.mcp_client = mcp_client
        
    def _run(self, input_str: str) -> str:
        """Get the weather for a location using MCP.
        
        Args:
            input_str: String in format "latitude,longitude" (e.g., "40.7128,-74.0060")
        """
        try:
            # Parse latitude and longitude from input
            lat_str, lon_str = input_str.split(',')
            latitude = float(lat_str.strip())
            longitude = float(lon_str.strip())
            
            # Call MCP server
            result = self.mcp_client.get_weather(latitude=latitude, longitude=longitude)
            return result
        except Exception as e:
            return f"Error getting weather: {str(e)}"

class MCPCalculatorTool(BaseTool):
    name = "calculator"
    description = "Useful for performing mathematical calculations."
    
    def _run(self, expression: str) -> str:
        """Calculate a mathematical expression."""
        try:
            # Create safe math environment with basic math functions
            safe_dict = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sum': sum, 'pow': pow, 'int': int, 'float': float
            }
            
            # Add common math module functions
            for name in dir(math):
                if not name.startswith('_'):
                    safe_dict[name] = getattr(math, name)
            
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return f"Result: {result}"
        except Exception as e:
            return f"Error calculating: {str(e)}"

def setup_mcp_client(aws_sse_url: str) -> FastMCPClient:
    """Connect to the MCP server running in AWS."""
    try:
        console.print(f"[bold blue]Connecting to MCP server at: {aws_sse_url}[/bold blue]")
        
        # Create MCP client
        client = FastMCPClient("langchain-client")
        
        # Connect to AWS server with SSE transport
        client.connect(aws_sse_url, transport="sse")
        
        console.print("[bold green]Successfully connected to MCP server![/bold green]")
        return client
    except Exception as e:
        console.print(f"[bold red]Failed to connect to MCP server: {str(e)}[/bold red]")
        sys.exit(1)

def create_langchain_agent(mcp_client: FastMCPClient):
    """Create a LangChain agent using CortexWrapper LLM and MCP tools."""
    
    # Create MCP tools
    tools = [
        MCPWeatherTool(mcp_client),
        MCPCalculatorTool()
    ]
    
    # Initialize the fixed CortexWrapper LLM
    llm = CortexWrapper(model="llama3.1-70b-elevance")
    
    # Create prompt template for the agent
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant with access to specialized tools.
        
        Available tools:
        - get_weather: Get weather information for a location using latitude and longitude coordinates
          - Input format: "latitude,longitude" (e.g., "40.7128,-74.0060")
        - calculator: Perform mathematical calculations
        
        Example tool usage:
        - To check weather in New York City: get_weather(40.7128,-74.0060)
        - To calculate a sum: calculator(23 + 45)
        
        Think step by step about which tool is most appropriate for the user's request.
        When analyzing US states for snow conditions, check each state's weather and compile the results.
        """),
        ("human", "{input}"),
        ("ai", "{agent_scratchpad}")
    ])
    
    # Create the agent
    agent = create_react_agent(llm, tools, prompt)
    
    # Create the agent executor
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )

def extract_temperature(weather_text: str) -> Optional[int]:
    """Extract temperature value from MCP weather response."""
    try:
        lines = weather_text.split('\n')
        for line in lines:
            if "Temperature:" in line:
                temp_part = line.split("Temperature:")[1].strip()
                temp_value = int(temp_part.split('°')[0].strip())
                return temp_value
        return None
    except Exception:
        return None

def is_snowing(weather_text: str) -> bool:
    """Check if weather text indicates snow."""
    return "snow" in weather_text.lower()

def analyze_us_states_subset(mcp_client: FastMCPClient):
    """Analyze a subset of US states for weather conditions."""
    console.print(Panel.fit(
        "Analyzing weather conditions for sample US states",
        title="🌦️ Weather Analysis",
        subtitle="Looking for snow conditions"
    ))
    
    weather_data = {}
    snowy_states = []
    temperatures = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Analyzing states...", total=len(US_STATES_SUBSET))
        
        for state, (lat, lon) in US_STATES_SUBSET.items():
            progress.update(task, description=f"[cyan]Checking {state}...")
            
            try:
                # Get weather from MCP
                weather_text = mcp_client.get_weather(latitude=lat, longitude=lon)
                weather_data[state] = weather_text
                
                # Check for snow
                if is_snowing(weather_text):
                    snowy_states.append(state)
                    console.print(f"[bold white on blue]{state}: SNOW DETECTED![/bold white on blue]")
                else:
                    console.print(f"{state}: No snow detected")
                
                # Extract temperature
                temp = extract_temperature(weather_text)
                if temp is not None:
                    temperatures.append(temp)
                    
                progress.advance(task)
            except Exception as e:
                console.print(f"[bold red]Error processing {state}: {str(e)}[/bold red]")
                progress.advance(task)
    
    # Calculate temperature sum
    temp_sum = sum(temperatures) if temperatures else 0
    
    # Display results
    console.print("\n[bold green]Analysis Complete![/bold green]")
    
    # Create results table
    table = Table(title="Weather Analysis Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("States Analyzed", str(len(US_STATES_SUBSET)))
    table.add_row("States with Snow", str(len(snowy_states)))
    table.add_row("Total Temperature Sum", f"{temp_sum}°F")
    table.add_row("Average Temperature", f"{(temp_sum / len(temperatures)):.1f}°F" if temperatures else "N/A")
    
    console.print(table)
    
    # Display snowy states
    if snowy_states:
        console.print("\n[bold blue]States with Snow:[/bold blue]")
        for state in sorted(snowy_states):
            console.print(f"- {state}")
    else:
        console.print("\n[bold yellow]No snow detected in the analyzed states.[/bold yellow]")

def run_interactive_session(agent_executor):
    """Run an interactive session with the agent."""
    console.print(Panel.fit(
        "Ask questions or give commands. Type 'exit' to quit.",
        title="🤖 LangChain Agent with MCP Tools",
        subtitle="Powered by Llama3.1-70b-elevance"
    ))
    
    # Store conversation history
    chat_history = []
    
    while True:
        user_input = console.input("[bold green]You:[/bold green] ")
        
        if user_input.lower() in ("exit", "quit", "bye"):
            console.print("[bold]Goodbye![/bold]")
            break
        
        try:
            # Show thinking indicator
            with console.status("[bold cyan]Thinking...[/bold cyan]"):
                # Execute agent with the input
                response = agent_executor.invoke({
                    "input": user_input,
                    "chat_history": chat_history
                })
            
            # Extract the output
            output = response["output"]
            
            # Display the response
            console.print("[bold blue]Assistant:[/bold blue]", style="blue")
            console.print(output)
            
            # Update chat history
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=output))
            
        except Exception as e:
            console.print(f"[bold red]Error: {str(e)}[/bold red]")

def main():
    console.print("[bold]🌟 LangChain Agent with MCP Tools & CortexWrapper[/bold]")
    
    # Get AWS SSE URL
    aws_sse_url = os.environ.get("MCP_SSE_URL")
    
    if not aws_sse_url:
        console.print("[yellow]MCP_SSE_URL environment variable not set.[/yellow]")
        aws_sse_url = console.input("[bold]Enter AWS SSE URL for MCP server:[/bold] ")
    
    # Connect to MCP server
    mcp_client = setup_mcp_client(aws_sse_url)
    
    # Create LangChain agent
    agent_executor = create_langchain_agent(mcp_client)
    
    # Menu options
    while True:
        console.print("\n[bold]Choose an option:[/bold]")
        console.print("1. Run quick weather analysis on sample states")
        console.print("2. Interactive mode")
        console.print("3. Exit")
        
        choice = console.input("[bold green]Selection:[/bold green] ")
        
        if choice == "1":
            analyze_us_states_subset(mcp_client)
        elif choice == "2":
            run_interactive_session(agent_executor)
        elif choice == "3":
            console.print("[bold]Exiting program.[/bold]")
            break
        else:
            console.print("[bold red]Invalid selection. Please try again.[/bold red]")
    
    # Disconnect from MCP when done
    try:
        mcp_client.disconnect()
        console.print("[green]Disconnected from MCP server.[/green]")
    except:
        pass

if __name__ == "__main__":
    main()

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from typing import Union, List, Dict
import statistics
import uvicorn

# Step 1: Create FastAPI app and wrap with FastMCP
app = FastAPI(title="Analyzer Tool Server")
mcp = FastMCP("Analyzer Tool Context", app=app)

# Step 2: Define tool using @mcp.tool
@mcp.tool(
    name="analyzserve",
    description="""
    Performs statistical operations (sum, mean, median, min, max) on list or dict of numbers.
    Ignores non-numeric entries like text.
    """
)
def analyzserve(data: Union[List, Dict[str, List]], operation: str) -> Dict:
    try:
        operation = operation.lower()
        valid_ops = ["sum", "mean", "median", "min", "max"]
        if operation not in valid_ops:
            return {"status": "error", "error": f"Invalid operation. Choose from {', '.join(valid_ops)}"}

        # Helper: safely extract numeric values
        def extract_numbers(raw):
            return [
                float(n) for n in raw
                if isinstance(n, (int, float)) or (isinstance(n, str) and n.replace('.', '', 1).isdigit())
            ]

        # If input is a list
        if isinstance(data, list):
            numbers = extract_numbers(data)
            if not numbers:
                return {"status": "error", "error": "No valid numeric values found in list."}
            result = {
                "sum": sum(numbers),
                "mean": statistics.mean(numbers),
                "median": statistics.median(numbers),
                "min": min(numbers),
                "max": max(numbers)
            }[operation]
            return {"status": "success", "result": result}

        # If input is a dict of columns
        elif isinstance(data, dict):
            result_dict = {}
            for key, values in data.items():
                if not isinstance(values, list):
                    continue
                numbers = extract_numbers(values)
                if numbers:
                    result_dict[key] = {
                        "sum": sum(numbers),
                        "mean": statistics.mean(numbers),
                        "median": statistics.median(numbers),
                        "min": min(numbers),
                        "max": max(numbers)
                    }[operation]
            if not result_dict:
                return {"status": "error", "error": "No valid numeric data in any columns."}
            return {"status": "success", "result": result_dict}

        # Not a valid structure
        return {"status": "error", "error": f"Invalid input type: {type(data).__name__}"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

# Step 3: Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

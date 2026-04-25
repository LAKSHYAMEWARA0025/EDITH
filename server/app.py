from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import Dict, Any
import sys
import os
import traceback

# Add parent directory to path to import wrapper modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper.edith_env import EDITHDroneEnv

app = FastAPI()

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return 200 with error message."""
    return JSONResponse(
        status_code=200,
        content={
            "error": f"Server error: {str(exc)}",
            "type": type(exc).__name__,
            "endpoint": str(request.url)
        }
    )

# Validation error handler
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=200,
        content={
            "error": "Invalid request format",
            "details": exc.errors()
        }
    )

# Instantiate global environment instance as requested
# GUI can be enabled via EDITH_GUI=true environment variable
try:
    gui_enabled = os.getenv("EDITH_GUI", "false").lower() in ("true", "1", "yes")
    task_type = os.getenv("EDITH_TASK", "task1")
    print(f"Initializing EDITH environment: task={task_type}, gui={gui_enabled}")
    env = EDITHDroneEnv(task_type=task_type, gui=gui_enabled)
except Exception as e:
    print(f"WARNING: Failed to initialize environment: {e}")
    env = None

class StepAction(BaseModel):
    tool: str
    args: Dict[str, Any]

@app.post("/reset")
def reset():
    """Reset the environment."""
    try:
        if env is None:
            return {"error": "Environment not initialized"}
        
        state, info = env.reset()
        return {"state": state, "info": info}
    except Exception as e:
        return {"error": f"Reset failed: {str(e)}"}

@app.post("/step")
def step(action: StepAction):
    """Execute one step in the environment."""
    try:
        if env is None:
            return {"error": "Environment not initialized"}
        
        # Validate action has required fields
        if not action.tool:
            return {"error": "Missing 'tool' field in action"}
        
        # Map back to action dict expected by edith_env step
        act_dict = {"name": action.tool, "arguments": action.args}
        state, reward, done, truncated, info = env.step(act_dict)
        return {
            "state": state,
            "reward": reward,
            "done": done,
            "truncated": truncated,
            "info": info
        }
    except Exception as e:
        return {
            "error": f"Step failed: {str(e)}",
            "state": {},
            "reward": 0.0,
            "done": False,
            "truncated": False,
            "info": {}
        }

@app.get("/tools")
def get_tools():
    """Return list of available tools."""
    try:
        # Return list of registered tools
        tools = [
            "get_drone_status",
            "get_obstacle_distances",
            "scan_area",
            "move_drone_to",
            "get_mission_status",
            "assign_drone_to_target",
            "return_drone_home",
            "get_camera_frame"
        ]
        return {"tools": tools}
    except Exception as e:
        return {"error": f"Failed to get tools: {str(e)}", "tools": []}

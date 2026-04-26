from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import Dict, Any, Optional
import sys
import os
import traceback
import uuid
import time

# Add parent directory to path to import wrapper modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper.edith_env import EDITHDroneEnv

app = FastAPI()

# --- SESSION STORAGE ---
# Maps session_id -> EDITHDroneEnv instance
environments: Dict[str, EDITHDroneEnv] = {}

# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "error": f"Server error: {str(exc)}",
            "type": type(exc).__name__,
            "endpoint": str(request.url)
        }
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=200,
        content={"error": "Invalid request format", "details": exc.errors()}
    )

class StepAction(BaseModel):
    tool: str
    args: Dict[str, Any]

class SessionRequest(BaseModel):
    session_id: str

def get_or_create_env(session_id: str, task_type: str = "task1") -> EDITHDroneEnv:
    """Retrieve an existing session or create a new PyBullet instance."""
    if session_id not in environments:
        gui_enabled = os.getenv("EDITH_GUI", "false").lower() in ("true", "1", "yes")
        # Ensure task type respects environment variable override if present
        env_task = os.getenv("EDITH_TASK", task_type)
        print(f"[SESSION {session_id}] Initializing EDITH environment: task={env_task}, gui={gui_enabled}")
        
        # This creates a completely isolated PyBullet physics server (p.DIRECT)
        environments[session_id] = EDITHDroneEnv(task_type=env_task, gui=gui_enabled)
        
    return environments[session_id]

@app.post("/reset")
def reset(x_session_id: Optional[str] = Header(None), task_type: str = "task1"):
    """Reset the environment. Generates a new session ID if none is provided."""
    try:
        # Generate a unique ID if the client didn't send one
        sid = x_session_id or str(uuid.uuid4())
        
        env_instance = get_or_create_env(sid, task_type)
        state, info = env_instance.reset()
        
        return {"state": state, "info": info, "session_id": sid}
    except Exception as e:
        return {"error": f"Reset failed: {str(e)}", "state": {}, "info": {}}

@app.post("/step")
def step(action: StepAction, x_session_id: str = Header(...)):
    """Execute one step in the specific session's environment."""
    try:
        if x_session_id not in environments:
            return {
                "error": "Session expired or not found. Please call /reset first.",
                "state": {}, "reward": 0.0, "done": True, "truncated": False, "info": {}
            }
        
        env_instance = environments[x_session_id]
        
        if not action.tool:
            return {"error": "Missing 'tool' field in action"}
        
        act_dict = {"name": action.tool, "arguments": action.args}
        state, reward, done, truncated, info = env_instance.step(act_dict)
        
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
            "state": {}, "reward": 0.0, "done": True, "truncated": False, "info": {}
        }

@app.post("/close")
def close_session(request: SessionRequest):
    """Explicitly clean up PyBullet resources when an episode finishes."""
    sid = request.session_id
    if sid in environments:
        print(f"[SESSION {sid}] Closing and freeing RAM...")
        environments[sid].close()
        del environments[sid]
        return {"status": "closed"}
    return {"status": "not_found"}

@app.get("/tools")
def get_tools():
    """Return list of available tools."""
    try:
        tools = [
            "get_drone_status", "get_obstacle_distances", "scan_area",
            "move_drone_to", "get_mission_status", "assign_drone_to_target",
            "return_drone_home"
        ]
        return {"tools": tools}
    except Exception as e:
        return {"error": f"Failed to get tools: {str(e)}", "tools": []}

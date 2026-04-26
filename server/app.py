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

class ResetRequest(BaseModel):
    seed: Optional[int] = None
    task_type: Optional[str] = "task1"

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
def reset(
    request: Optional[ResetRequest] = None,
    x_session_id: Optional[str] = Header(None),
    task_type: str = "task1",
    seed: Optional[int] = None
):
    """Reset the environment with optional seed for deterministic map generation.
    
    Args:
        request: Optional JSON body with seed and task_type
        x_session_id: Session ID from header
        task_type: Task type (query param, overridden by request body)
        seed: Random seed (query param, overridden by request body)
    """
    try:
        # Generate a unique ID if the client didn't send one
        sid = x_session_id or str(uuid.uuid4())
        
        # Priority: request body > query params > defaults
        if request:
            final_seed = request.seed if request.seed is not None else seed
            final_task = request.task_type or task_type
        else:
            final_seed = seed
            final_task = task_type
        
        env_instance = get_or_create_env(sid, final_task)
        
        # Pass seed to environment reset for deterministic map generation
        if final_seed is not None:
            print(f"[SESSION {sid}] Resetting with seed={final_seed}")
            state, info = env_instance.reset(seed=final_seed)
        else:
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

@app.get("/debug/scene")
def get_scene_debug(x_session_id: str = Header(...)):
    """Debug endpoint: Get raw obstacle and target positions from PyBullet."""
    try:
        if x_session_id not in environments:
            return {"error": "Session not found"}
        
        env_instance = environments[x_session_id]
        
        # Get obstacle positions directly from scene_manager
        import pybullet as p
        
        obstacle_positions = []
        for obs_id in env_instance.scene_manager.obstacle_ids:
            pos, _ = p.getBasePositionAndOrientation(obs_id, physicsClientId=env_instance.env.CLIENT)
            obstacle_positions.append(list(pos))
        
        target_positions = []
        for tgt_id in env_instance.scene_manager.target_ids:
            pos, _ = p.getBasePositionAndOrientation(tgt_id, physicsClientId=env_instance.env.CLIENT)
            target_positions.append(list(pos))
        
        return {
            "obstacles": obstacle_positions,
            "targets": target_positions,
            "obstacle_count": len(obstacle_positions),
            "target_count": len(target_positions)
        }
    except Exception as e:
        return {"error": f"Failed to get scene: {str(e)}"}

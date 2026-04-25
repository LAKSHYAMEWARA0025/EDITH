from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
import sys
import os

# Add parent directory to path to import wrapper modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper.edith_env import EDITHDroneEnv

app = FastAPI()

# Instantiate global environment instance as requested
env = EDITHDroneEnv(task_type="task1", gui=False)

class StepAction(BaseModel):
    tool: str
    args: Dict[str, Any]

@app.post("/reset")
def reset():
    state, info = env.reset()
    return {"state": state, "info": info}

@app.post("/step")
def step(action: StepAction):
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

@app.get("/tools")
def get_tools():
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

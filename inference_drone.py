"""
EDITH Drone Environment - Inference Script

Tests the environment with an LLM agent making decisions.
Similar to AEOM inference.py but for drone navigation tasks.

Usage:
    Terminal 1: Set EDITH_GUI=true and start server
        Windows: $env:EDITH_GUI="true"; uvicorn server.app:app --reload
        Linux: EDITH_GUI=true uvicorn server.app:app --reload
    
    Terminal 2: Run inference
        python inference_drone.py --task task1

Requirements:
    - HF_TOKEN environment variable (API token)
    - Server running on http://localhost:8000
"""

import os
import json
import argparse
import requests
from typing import Optional, List, Dict, Any
from openai import OpenAI

# Configuration (matches AEOM pattern)
API_KEY = os.getenv("HF_TOKEN", None)
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
if API_KEY is None:
    raise ValueError("HF_TOKEN environment variable is required")

MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

TEMPERATURE = 0.3
MAX_TOKENS = 512
MAX_STEPS = 20  # Maximum steps per episode

TASKS = ["task1", "task2", "task3"]

SYSTEM_PROMPT = """You are EDITH, an autonomous drone mission commander.

MISSION OBJECTIVE:
Navigate the drone to reach all green target markers. Return home after.
You have limited time and battery. Plan efficiently.

SCENE BOUNDARIES (never exceed these):
- X: -8.0 to +8.0 meters
- Y: -8.0 to +8.0 meters
- Z: 0.5 to 2.0 meters (safe flight altitude)
- Drone spawns at [0, 0, 0.1]
- Targets are within 5-8 meters of spawn
- Red cubes = obstacles (avoid) | Green cubes = targets (reach)

COORDINATE SYSTEM:
- X: negative=left, positive=right
- Y: negative=backward, positive=forward
- Z: negative=down, positive=up

DECISION FRAMEWORK — follow this priority each step:
1. No information yet → call get_mission_status to get target coordinates
2. Know where target is → call move_drone_to with coordinates toward target
3. Near obstacle → call get_obstacle_distances then reroute
4. Think you are close → call get_drone_status to verify position
5. Target reached → call return_drone_home ONCE only
   Then call get_drone_status ONCE to check position
   If distance to [0, 0, 0.1] is less than 0.5m — you are home, STOP
   Do not call get_drone_status repeatedly while returning

TARGET INFORMATION:
- Target coordinates are provided in mission_status["targets"]
- Each target has: {"id": 0, "position": [x, y, z], "reached": false}
- Navigate directly to target position using move_drone_to
- Use scan_area only for obstacle detection, not target finding

TOOL SIGNATURES (use exact parameter names):
1. get_mission_status: NO ARGUMENTS
   Example: {"tool": "get_mission_status", "args": {}}

2. move_drone_to: drone_id, x, y, z (separate coordinates, NOT "position")
   Example: {"tool": "move_drone_to", "args": {"drone_id": 0, "x": 5.0, "y": 0.0, "z": 1.0}}

3. get_drone_status: drone_id
   Example: {"tool": "get_drone_status", "args": {"drone_id": 0}}

4. scan_area: drone_id
   Example: {"tool": "scan_area", "args": {"drone_id": 0}}

5. return_drone_home: drone_id
   Example: {"tool": "return_drone_home", "args": {"drone_id": 0}}

MOVEMENT RULES:
- Move in steps of 2-4 meters at a time, not 10+ meters
- Keep Z between 0.8 and 1.5 for normal flight
- After each move_drone_to, verify new position with get_drone_status
- If target is "above" in scan, increase Z by 0.5m (e.g. from 1.0 to 1.5)
- If target is "left", decrease X. If "right", increase X. If "center", increase Y.

STRICT TOOL RULES (violations are penalized):
- NEVER call the same tool with identical arguments twice in a row
- return_drone_home: call ONCE only. Then switch to get_drone_status to monitor.
- move_drone_to: call ONCE per waypoint. Check position before issuing next waypoint.
- get_drone_status: call ONCE to check position, then act on what you learned
  Do not call it repeatedly without taking a movement action in between
- Do not scan repeatedly without moving in between.

TASK 1 SPECIFIC RULE:
- return_drone_home is INVALID until green target is reached
- Calling it before target reached will FAIL with error and -0.50 penalty
- Focus on finding and reaching the target first

BOUNDARY HANDLING:
- If you receive out_of_bounds penalty, reverse direction ONLY
- Do NOT call return_drone_home when hitting boundary
- You are still on mission — reroute and continue searching
- Boundaries are at X=±8, Y=±8, Z=2.0 (stay within these limits)

EXAMPLES OF GOOD SEQUENCES:
scan_area → move_drone_to → get_drone_status → move_drone_to → get_drone_status → return_drone_home → get_drone_status

EXAMPLES OF BAD SEQUENCES (penalized):
return_drone_home → return_drone_home → return_drone_home  (LOOP — never do this)
scan_area → scan_area → scan_area  (LOOP — never do this)
move_drone_to [0,0,50] (OUT OF BOUNDS — never exceed Z=2.0)

Respond with ONE JSON object only. No explanation. No markdown.
Format: {"tool": "tool_name", "args": {"drone_id": 0, ...}}
"""


def log_start(task: str, model: str) -> None:
    """Log episode start."""
    print(f"\n{'='*60}")
    print(f"[START] task={task} model={model}")
    print(f"{'='*60}\n")


def log_step(step: int, tool: str, result: Dict[Any, Any], reward: float, done: bool, action_args: Dict = None) -> None:
    """Log each step with per-step reward and action details."""
    error = result.get("error", None) if isinstance(result, dict) else None
    status = "ERROR" if error else "OK"
    
    # Show action arguments for move commands
    args_str = ""
    if action_args and tool == "move_drone_to":
        x = action_args.get("x", "?")
        y = action_args.get("y", "?")
        z = action_args.get("z", "?")
        args_str = f" → [{x}, {y}, {z}]"
    
    print(f"[STEP {step:2d}] tool={tool:25s}{args_str:20s} status={status:5s} step_reward={reward:+7.3f} done={done}")
    
    # Show scan results
    if tool == "scan_area" and not error:
        detections = result.get("detections", [])
        if detections:
            for det in detections[:3]:  # Show first 3
                print(f"          └─ {det['type']:8s}: dir={det.get('direction','?'):6s} alt={det.get('altitude','?'):6s} dist={det.get('estimated_distance',0):.1f}m")
        else:
            print(f"          └─ No detections")
    
    # Show mission status
    if tool == "get_mission_status" and not error:
        targets_info = ""
        if 'targets' in result and result['targets']:
            target = result['targets'][0]  # Show first target
            pos = target['position']
            targets_info = f" | Target: [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]"
        print(f"          └─ Targets: {result.get('targets_reached', 0)}/{result.get('total_targets', 0)} | Complete: {result.get('mission_complete', False)}{targets_info}")
    
    if error:
        print(f"          Error: {error}")


def log_end(done: bool, steps: int, total_reward: float, rewards: List[float]) -> None:
    """Log episode end."""
    print(f"\n{'='*60}")
    print(f"[END] done={done} steps={steps} total_reward={total_reward:.3f}")
    print(f"      rewards={[f'{r:.3f}' for r in rewards]}")
    print(f"{'='*60}\n")


def ask_llm(client: OpenAI, messages: List[Dict[str, str]]) -> str:
    """Query LLM for next action."""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[DEBUG] LLM error: {type(e).__name__}: {e}")
        raise


def parse_action(text: str) -> Optional[Dict[str, Any]]:
    """Parse LLM response into action dict."""
    try:
        # Strip markdown code fences if present
        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        
        data = json.loads(clean.strip())
        
        # Validate action has required fields
        if "tool" not in data:
            return None
        if "args" not in data:
            data["args"] = {}
        
        return data
    except Exception as e:
        print(f"[DEBUG] Parse error: {e}")
        print(f"[DEBUG] Raw text: {text[:200]}")
        return None


def reset_env(server_url: str) -> Dict[str, Any]:
    """Reset environment via server."""
    response = requests.post(f"{server_url}/reset")
    response.raise_for_status()
    return response.json()


def step_env(server_url: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """Step environment via server."""
    response = requests.post(f"{server_url}/step", json=action)
    response.raise_for_status()
    return response.json()


def run_episode(client: OpenAI, task: str, server_url: str, debug: bool = False) -> float:
    """Run one episode with LLM agent."""
    rewards: List[float] = []
    total_reward = 0.0
    steps_taken = 0
    
    log_start(task, MODEL_NAME)
    
    try:
        # Reset environment
        print("[INFO] Resetting environment...")
        reset_result = reset_env(server_url)
        state = reset_result["state"]
        
        print(f"[INFO] Initial state:")
        print(f"       Mission: {state['mission_status']['total_targets']} targets")
        print(f"       Time limit: {state['mission_status']['time_remaining']:.1f}s")
        print(f"       Drone position: {state['drones']['0']['position']}")
        
        # Show target positions
        if 'targets' in state['mission_status'] and state['mission_status']['targets']:
            for target in state['mission_status']['targets']:
                pos = target['position']
                print(f"       Target {target['id']}: [{pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}]")
        
        print(f"[DEBUG] Mission complete at reset: {state['mission_status']['mission_complete']}\n")
        
        # Initialize conversation
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Mission started. Initial state:\n{json.dumps(state, indent=2)}"}
        ]
        
        done = False
        truncated = False
        
        for step in range(1, MAX_STEPS + 1):
            if done or truncated:
                break
            
            # Get LLM decision
            raw_response = ask_llm(client, messages)
            action = parse_action(raw_response)
            
            # Debug: show what LLM is thinking
            if debug and step <= 5:
                print(f"\n[DEBUG] LLM Response (step {step}):")
                print(f"  {raw_response[:200]}...")
            
            # Fallback if parsing fails
            if action is None:
                print(f"[WARN] Failed to parse LLM response, using fallback action")
                action = {"tool": "get_mission_status", "args": {}}
            
            # Execute action
            step_result = step_env(server_url, action)
            
            # Guard against server error responses
            if "error" in step_result and "state" not in step_result:
                print(f"[ERROR] Server returned error: {step_result['error']}")
                break
            
            state = step_result.get("state", {})
            reward = step_result.get("reward", 0.0)
            done = step_result.get("done", False)
            truncated = step_result.get("truncated", False)
            tool_result = step_result.get("info", {}).get("tool_result", {})
            
            rewards.append(reward)
            total_reward += reward
            steps_taken = step
            
            log_step(step, action["tool"], tool_result, reward, done, action.get("args", {}))
            
            # Update conversation
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user", "content": json.dumps({
                "tool_result": tool_result,
                "state": state,
                "reward": reward,
                "done": done
            }, indent=2)})
            
            if done or truncated:
                break
        
        log_end(done, steps_taken, total_reward, rewards)
        
    except Exception as e:
        print(f"[ERROR] Episode failed: {e}")
        import traceback
        traceback.print_exc()
    
    return total_reward


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="EDITH Drone Inference Script")
    parser.add_argument("--task", choices=TASKS, default="task1", 
                       help="Task to run (task1=basic, task2=battery, task3=multi-target)")
    parser.add_argument("--server", default=SERVER_URL,
                       help="Server URL (default: http://localhost:8000)")
    parser.add_argument("--debug", action="store_true",
                       help="Show LLM reasoning and decisions")
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("EDITH DRONE ENVIRONMENT - INFERENCE TEST")
    print("="*60)
    print(f"Task: {args.task}")
    print(f"Model: {MODEL_NAME}")
    print(f"API: {API_BASE_URL}")
    print(f"Server: {args.server}")
    print(f"Max steps: {MAX_STEPS}")
    print("="*60 + "\n")
    
    # Check server is running
    try:
        response = requests.get(f"{args.server}/tools")
        tools = response.json()["tools"]
        print(f"[INFO] Server is running. Available tools: {len(tools)}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to server at {args.server}")
        print(f"        Make sure server is running with: EDITH_GUI=true uvicorn server.app:app")
        return
    
    # Initialize LLM client
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Run episode
    total_reward = run_episode(client, args.task, args.server, debug=args.debug)
    
    print(f"\n[FINAL] Total reward: {total_reward:.3f}")
    print("\nTest complete! Check the PyBullet GUI window for visualization.")


if __name__ == "__main__":
    main()

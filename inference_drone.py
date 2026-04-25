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
    - HF_TOKEN environment variable (Hugging Face API token) OR OPENAI_API_KEY
    - Server running on http://localhost:8000
"""

import os
import json
import argparse
import requests
from typing import Optional, List, Dict, Any

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN", None)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

# Determine which API to use
if OPENAI_API_KEY:
    USE_OPENAI = True
    API_KEY = OPENAI_API_KEY
    API_BASE_URL = "https://api.openai.com/v1"
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
    print("[INFO] Using OpenAI API")
elif HF_TOKEN:
    USE_OPENAI = False
    API_KEY = HF_TOKEN
    # Use HF Inference API directly (not OpenAI-compatible endpoint)
    HF_MODEL = os.getenv("MODEL_NAME", "meta-llama/Llama-3.2-3B-Instruct")
    HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    print(f"[INFO] Using Hugging Face Inference API: {HF_MODEL}")
else:
    raise ValueError("Either HF_TOKEN or OPENAI_API_KEY environment variable is required")

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

TEMPERATURE = 0.3
MAX_TOKENS = 512
MAX_STEPS = 20  # Maximum steps per episode

TASKS = ["task1", "task2", "task3"]

SYSTEM_PROMPT = """You are an autonomous drone navigation agent controlling a drone in a 3D environment.

Your goal: Navigate the drone to reach green target cubes while avoiding red obstacle cubes.

Available tools (respond with a single JSON object):
1. {"tool": "get_drone_status", "args": {"drone_id": 0}}
   - Returns: position [x,y,z], velocity, battery percentage

2. {"tool": "scan_area", "args": {"drone_id": 0}}
   - Returns: detected obstacles (red) and targets (green) with positions and distances

3. {"tool": "get_obstacle_distances", "args": {"drone_id": 0}}
   - Returns: distances to obstacles in 6 directions (north, south, east, west, up, down)

4. {"tool": "move_drone_to", "args": {"drone_id": 0, "x": 1.0, "y": 2.0, "z": 1.5, "timeout": 5.0}}
   - Moves drone to target coordinates
   - Returns: status (reached/interrupted/timeout/battery_low)

5. {"tool": "get_mission_status", "args": {}}
   - Returns: time remaining, targets reached, total targets, mission complete status

6. {"tool": "assign_drone_to_target", "args": {"drone_id": 0, "target_id": 0}}
   - Assigns drone to specific target, estimates battery cost

7. {"tool": "return_drone_home", "args": {"drone_id": 0}}
   - Commands drone to return to spawn position

8. {"tool": "get_camera_frame", "args": {"drone_id": 0, "width": 224, "height": 224}}
   - Gets raw camera image (large data, use sparingly)

Strategy tips:
- Start by scanning the area to find targets
- Check mission status to see how many targets remain
- Move towards targets while monitoring battery
- Avoid obstacles detected by scan_area
- Complete mission before time runs out

Respond with ONLY a valid JSON object, no explanation.
Example: {"tool": "scan_area", "args": {"drone_id": 0}}
"""


def log_start(task: str, model: str) -> None:
    """Log episode start."""
    print(f"\n{'='*60}")
    print(f"[START] task={task} model={model}")
    print(f"{'='*60}\n")


def log_step(step: int, tool: str, result: Dict[Any, Any], reward: float, done: bool) -> None:
    """Log each step."""
    error = result.get("error", None) if isinstance(result, dict) else None
    status = "ERROR" if error else "OK"
    print(f"[STEP {step:2d}] tool={tool:25s} status={status:5s} reward={reward:6.3f} done={done}")
    if error:
        print(f"          Error: {error}")


def log_end(done: bool, steps: int, total_reward: float, rewards: List[float]) -> None:
    """Log episode end."""
    print(f"\n{'='*60}")
    print(f"[END] done={done} steps={steps} total_reward={total_reward:.3f}")
    print(f"      rewards={[f'{r:.3f}' for r in rewards]}")
    print(f"{'='*60}\n")


def ask_llm(messages: List[Dict[str, str]]) -> str:
    """Query LLM for next action."""
    try:
        if USE_OPENAI:
            # Use OpenAI API
            from openai import OpenAI
            client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            return (resp.choices[0].message.content or "").strip()
        else:
            # Use Hugging Face Inference API
            # Convert messages to prompt format
            prompt = ""
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    prompt += f"<|system|>\n{content}\n"
                elif role == "user":
                    prompt += f"<|user|>\n{content}\n"
                elif role == "assistant":
                    prompt += f"<|assistant|>\n{content}\n"
            prompt += "<|assistant|>\n"
            
            headers = {"Authorization": f"Bearer {API_KEY}"}
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "return_full_text": False
                }
            }
            
            response = requests.post(HF_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "").strip()
            elif isinstance(result, dict):
                return result.get("generated_text", "").strip()
            else:
                raise ValueError(f"Unexpected HF API response format: {result}")
                
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


def run_episode(task: str, server_url: str) -> float:
    """Run one episode with LLM agent."""
    rewards: List[float] = []
    total_reward = 0.0
    steps_taken = 0
    
    log_start(task, MODEL_NAME if USE_OPENAI else HF_MODEL)
    
    try:
        # Reset environment
        print("[INFO] Resetting environment...")
        reset_result = reset_env(server_url)
        state = reset_result["state"]
        
        print(f"[INFO] Initial state:")
        print(f"       Mission: {state['mission_status']['total_targets']} targets")
        print(f"       Time limit: {state['mission_status']['time_remaining']:.1f}s")
        print(f"       Drone position: {state['drones']['0']['position']}\n")
        
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
            raw_response = ask_llm(messages)
            action = parse_action(raw_response)
            
            # Fallback if parsing fails
            if action is None:
                print(f"[WARN] Failed to parse LLM response, using fallback action")
                action = {"tool": "get_mission_status", "args": {}}
            
            # Execute action
            step_result = step_env(server_url, action)
            
            state = step_result["state"]
            reward = step_result["reward"]
            done = step_result["done"]
            truncated = step_result["truncated"]
            tool_result = step_result["info"]["tool_result"]
            
            rewards.append(reward)
            total_reward += reward
            steps_taken = step
            
            log_step(step, action["tool"], tool_result, reward, done)
            
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
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("EDITH DRONE ENVIRONMENT - INFERENCE TEST")
    print("="*60)
    print(f"Task: {args.task}")
    print(f"Model: {MODEL_NAME if USE_OPENAI else HF_MODEL}")
    print(f"API: {'OpenAI' if USE_OPENAI else 'Hugging Face'}")
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
    
    # Run episode
    total_reward = run_episode(args.task, args.server)
    
    print(f"\n[FINAL] Total reward: {total_reward:.3f}")
    print("\nTest complete! Check the PyBullet GUI window for visualization.")


if __name__ == "__main__":
    main()

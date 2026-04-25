# EDITH Inference Testing Guide

## Overview
Test the EDITH drone environment with an LLM agent making navigation decisions in real-time, visualized in PyBullet GUI.

## Setup

### 1. Get Hugging Face API Token
```bash
# Get token from: https://huggingface.co/settings/tokens
# Set environment variable
export HF_TOKEN="your_token_here"  # Linux/Mac
$env:HF_TOKEN="your_token_here"    # Windows PowerShell
```

### 2. Install Requirements
```bash
pip install openai requests
```

## Running the Test

### Terminal 1: Start Server with GUI

**Windows PowerShell:**
```powershell
cd EDITH/edith-env
$env:EDITH_GUI="true"
$env:EDITH_TASK="task1"
uvicorn server.app:app --reload
```

**Linux/Mac:**
```bash
cd EDITH/edith-env
EDITH_GUI=true EDITH_TASK=task1 uvicorn server.app:app --reload
```

You should see:
```
Initializing EDITH environment: task=task1, gui=True
[INFO] BaseAviary.__init__() loaded parameters...
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**PyBullet GUI window will open showing the 3D environment!**

### Terminal 2: Run Inference Script

**Windows PowerShell:**
```powershell
cd EDITH/edith-env
$env:HF_TOKEN="your_token_here"
python inference_drone.py --task task1
```

**Linux/Mac:**
```bash
cd EDITH/edith-env
HF_TOKEN="your_token_here" python inference_drone.py --task task1
```

## What Happens

1. **LLM Agent** (Llama-3.2-3B-Instruct) receives mission info
2. **Agent decides** which tool to call (scan_area, move_drone_to, etc.)
3. **Environment executes** the tool and returns results
4. **GUI shows** the drone moving in real-time
5. **Logs display** each step: tool called, result, reward
6. **Episode ends** when mission complete or time runs out

## Example Output

```
============================================================
EDITH DRONE ENVIRONMENT - INFERENCE TEST
============================================================
Task: task1
Model: meta-llama/Llama-3.2-3B-Instruct
Server: http://localhost:8000
Max steps: 20
============================================================

[INFO] Server is running. Available tools: 8

============================================================
[START] task=task1 model=meta-llama/Llama-3.2-3B-Instruct
============================================================

[INFO] Resetting environment...
[INFO] Initial state:
       Mission: 1 targets
       Time limit: 120.0s
       Drone position: [0.0, 0.0, 0.1125]

[STEP  1] tool=scan_area                status=OK    reward= 0.500 done=False
[STEP  2] tool=get_mission_status       status=OK    reward= 0.500 done=False
[STEP  3] tool=move_drone_to            status=OK    reward= 0.520 done=False
[STEP  4] tool=scan_area                status=OK    reward= 0.530 done=False
...
[STEP 12] tool=move_drone_to            status=OK    reward= 0.950 done=True

============================================================
[END] done=True steps=12 total_reward=7.850
      rewards=['0.500', '0.500', '0.520', ..., '0.950']
============================================================

[FINAL] Total reward: 7.850

Test complete! Check the PyBullet GUI window for visualization.
```

## Tasks Available

### Task 1: Basic Navigation (Recommended for first test)
- **Goal:** Navigate to 1 green target cube
- **Obstacles:** 5 red cubes (randomized positions)
- **Time limit:** 120 seconds
- **Battery:** 100% (no drain)
- **Difficulty:** Easy

### Task 2: Battery Management
- **Goal:** Navigate to 1 target with limited battery
- **Obstacles:** 5 red cubes
- **Time limit:** 120 seconds
- **Battery:** 30-70% (randomized start)
- **Difficulty:** Medium

### Task 3: Multi-Target
- **Goal:** Navigate to 3-5 targets
- **Obstacles:** 5-10 red cubes
- **Time limit:** 180 seconds
- **Battery:** 100%
- **Difficulty:** Hard

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EDITH_GUI` | `false` | Enable PyBullet GUI visualization |
| `EDITH_TASK` | `task1` | Task type (task1/task2/task3) |
| `HF_TOKEN` | (required) | Hugging Face API token |
| `MODEL_NAME` | `meta-llama/Llama-3.2-3B-Instruct` | LLM model to use |
| `API_BASE_URL` | `https://api-inference.huggingface.co/v1` | API endpoint |
| `SERVER_URL` | `http://localhost:8000` | EDITH server URL |

## Troubleshooting

### Server won't start
- Check PyBullet is installed: `pip install pybullet`
- Check gym-pybullet-drones is installed
- Try without GUI first: `EDITH_GUI=false`

### GUI doesn't show
- Make sure `EDITH_GUI=true` is set **before** starting server
- Check if PyBullet GUI window is hidden behind other windows
- Try restarting the server

### LLM errors
- Verify HF_TOKEN is valid
- Check internet connection
- Try different model: `MODEL_NAME=gpt-4o-mini` (requires OpenAI API key)

### Connection refused
- Make sure server is running on port 8000
- Check firewall settings
- Try: `SERVER_URL=http://127.0.0.1:8000`

## Advanced Usage

### Use Different LLM
```bash
# OpenAI GPT-4
export API_BASE_URL="https://api.openai.com/v1"
export HF_TOKEN="sk-..."  # OpenAI API key
export MODEL_NAME="gpt-4o-mini"
python inference_drone.py --task task1
```

### Run All Tasks
```bash
# Modify inference_drone.py to loop through all tasks
for task in task1 task2 task3; do
    python inference_drone.py --task $task
done
```

### Increase Max Steps
Edit `inference_drone.py`:
```python
MAX_STEPS = 50  # Allow more steps per episode
```

## What to Watch in GUI

- **Red cubes** = Obstacles (avoid these)
- **Green cubes** = Targets (reach these)
- **Small drone** = Your agent
- **Drone moves** when LLM calls `move_drone_to`
- **Target disappears** when reached
- **Episode ends** when mission complete

## Next Steps

After successful test:
1. Try different tasks (task2, task3)
2. Experiment with different LLMs
3. Analyze which tools the agent uses most
4. Check reward breakdown in logs
5. Optimize agent strategy based on observations

Happy testing! 🚁

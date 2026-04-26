# EDITH: Multi-Drone Mission Commander

**OpenEnv Hackathon Round 2 — India 2026**  
**Theme:** Multi-Agent Interactions + World Modeling

[![HuggingFace Space](https://img.shields.io/badge/🤗-Space-yellow)](https://huggingface.co/spaces/Invictus-Jai/edith-mission-commander)
[![Training Notebook](https://img.shields.io/badge/Colab-Training-orange)](https://colab.research.google.com/drive/1YEFLDpLOA14hsdkyqs4fQMd3qK-Pbnmt)

---

## Overview

EDITH (inspired by Tony Stark's AI from *Spider-Man: Far From Home*) is a reinforcement learning environment where an LLM agent learns to act as a **strategic mission commander** for autonomous drones. The agent operates at a high-level reasoning layer—issuing waypoint commands, monitoring telemetry, and replanning dynamically—while a PID controller handles low-level flight physics.

**Key Innovation:** The agent doesn't control motor speeds. It makes strategic decisions using tool calls, learning to navigate unknown obstacle layouts, manage battery constraints, and coordinate multi-drone swarms under uncertainty.

---

## Problem Statement

Modern drone swarms operate on **conditional automation scripts**—hardcoded rules that handle known situations. These scripts fail catastrophically when:

- Multiple drones need to coordinate dynamically
- Mission conditions change mid-flight (battery loss, obstacle movement)
- The agent must prioritize between competing objectives with no clear right answer
- The scenario is novel—never seen during the script's design

**What we built:** An RL environment where an LLM learns to reason about missions, allocate resources, and adapt to changing conditions—bridging the gap between rigid automation and genuine adaptive intelligence.

---

## Architecture

### System Layers

```
┌─────────────────────────────────────────────┐
│         LLM AGENT (Mission Commander)       │
│   Model: Qwen 1.5B / 3B (quantized)        │
│   Actions: Tool calls (8 tools)            │
│   Decisions: Every 1-2 seconds             │
└─────────────────┬───────────────────────────┘
                  │ High-level commands
                  ▼
┌─────────────────────────────────────────────┐
│         EDITH ENVIRONMENT WRAPPER           │
│   - Tool execution & validation             │
│   - Reward calculation (hybrid 2-layer)     │
│   - Episode tracking & termination          │
│   - Scene randomization per task            │
└─────────────────┬───────────────────────────┘
                  │ Waypoints
                  ▼
┌─────────────────────────────────────────────┐
│         PID CONTROLLER (DSLPIDControl)      │
│   Handles: smooth flight, stability         │
│   Output: RPM values per rotor              │
└─────────────────┬───────────────────────────┘
                  │ Motor commands
                  ▼
┌─────────────────────────────────────────────┐
│     GYM-PYBULLET-DRONES (Physics Engine)   │
│   Headless: DIRECT mode (no display)        │
│   Physics: 240Hz simulation                 │
│   Fully Dockerizable on Linux               │
└─────────────────────────────────────────────┘
```

### Why gym-pybullet-drones?

- **Headless by design:** Runs in `DIRECT` mode—no GUI, no virtual display, pure physics
- **Research-grade:** Used in MIT, ETH Zurich publications
- **Gym-compatible:** Standard `reset()`, `step()`, `observation_space` API
- **Lightweight:** Runs on 2-core CPU, 8GB RAM
- **Fully Dockerizable:** No Wine, no X11 dependencies

---

## Agent Tool Interface

The LLM interacts with the environment exclusively through **8 tool calls**. It never directly touches physics or motor commands.

| Tool | Description | Returns |
|------|-------------|---------|
| `get_drone_status(drone_id)` | Position, velocity, battery % | `{x, y, z, vx, vy, vz, battery}` |
| `get_obstacle_distances(drone_id)` | Raycasting in 6 directions (N/S/E/W/up/down) | `{north, south, east, west, up, down}` (meters) |
| `scan_area(drone_id)` | OpenCV color masking on camera frame | `{detections: [{type, distance, direction}]}` |
| `move_drone_to(drone_id, x, y, z)` | Move drone to absolute coordinates | `{status, current_pos, distance, eta}` |
| `get_mission_status()` | Targets remaining, time left, drone states | `{targets, time_remaining, drones}` |
| `assign_drone_to_target(drone_id, target_id)` | Assign drone to specific objective | `{status, estimated_battery_cost}` |
| `return_drone_home(drone_id)` | Send drone back to spawn point | `{status, eta_seconds}` |
| `get_camera_frame(drone_id)` | Raw camera frame (for debugging) | `{frame_data, shape, timestamp}` |

**Critical Design Principle — Proactive Sensing:**  
The environment never warns the agent about obstacles automatically. No data is pushed. The agent must decide when to call sensing tools, when to act, and when to recheck. This mirrors real-world drone operation—if the agent moves without scanning and hits an obstacle, that is the agent's failure, not the environment's.

---

## Vision System: Efficient Perception Pipeline

The `scan_area` tool uses a lightweight OpenCV-based vision pipeline that processes PyBullet's camera output in headless mode. Instead of sending raw pixel data to the LLM (computationally expensive and high latency), the system performs **color-based object detection** and returns structured text the agent can reason about.

### How It Works

1. **Camera Capture (Headless Mode)**  
   PyBullet's TinyRenderer captures RGB frames in DIRECT mode (no GUI required)

2. **Color Masking**  
   OpenCV HSV color space filtering detects:
   - **Red objects** → Obstacles (must avoid)
   - **Green objects** → Targets (must reach)

3. **Structured Output**  
   Returns: `{type, distance, direction, altitude}` for each detection

### Visual Pipeline

**Drone Camera Input (Headless Mode):**

![Drone Camera Input](assets/drone%20camera%20input.png)

*Raw RGB frame captured from drone's perspective using PyBullet TinyRenderer in headless mode.*

---

**Obstacle Mask (Red Color Detection):**

![Obstacle Mask](assets/obstacle%20mask.png)

*OpenCV HSV masking isolates red obstacles. Contour detection calculates position and distance.*

---

**Target Mask (Green Color Detection):**

![Target Mask](assets/target%20mask.png)

*OpenCV HSV masking isolates green targets. The agent uses this to verify target proximity.*

---

### Why This Approach?

**Advantages:**
- **Low latency:** Color masking is ~10ms vs 200ms+ for YOLO
- **Lightweight:** No 200MB+ model weights
- **Interpretable:** Agent receives structured data, not raw pixels
- **Headless-compatible:** Works in Docker without display server

**Scalability:**
For more complex environments, this pipeline can be extended with:
- **YOLO** for general object detection
- **Advanced OpenCV tracking** (KCF, CSRT) for moving obstacles
- **Depth estimation** from stereo cameras
- **Semantic segmentation** for scene understanding

**Current Implementation:**  
Color-based detection is sufficient for the hackathon scope and demonstrates the core concept without adding unnecessary complexity.

---

## Task Design

Tasks are organized into **3 tiers** with curriculum-based progression. Each task has randomized variants to prevent memorization.

### Task 1: Navigate & Reach (Single Drone)

**Objective:** Fly to a known target coordinate, avoid static obstacles, return home.

**Randomization per episode:**
- Target position: 5 zones, randomly selected
- Obstacle count: 2–5 boxes
- Obstacle placement: Strategic path-blocking with randomized lateral offsets

**What the agent learns:**
- When to scan vs when to move
- Spatial reasoning around obstacles
- That skipping sensing leads to collision

**Mastery threshold:** Mean reward ≥ 0.70 over 50 episodes

---

### Task 2: Constrained Delivery (Battery Pressure + Moving Obstacles)

**Objective:** Deliver to landing zone with limited battery, navigate through moving obstacles, handle mid-mission events.

**Randomization per episode:**
- Starting battery: 70–100%
- Moving obstacle speed: slow / medium / fast
- Mid-mission event: sudden battery drain OR new obstacle spawns

**What the agent learns:**
- Proactive battery checking before committing to routes
- Re-verification before acting (moving obstacles change position while LLM processes)
- Detecting state changes mid-mission and replanning

**Mastery threshold:** Mean reward ≥ 0.65 over 50 episodes

---

### Task 3: Two-Drone Coordination (Swarm Entry)

**Objective:** Allocate two drones to multiple targets efficiently, handle mid-mission drone degradation.

**Randomization per episode:**
- 2–3 targets in different zones
- Which drone starts with higher battery: randomized
- Which drone experiences speed reduction: randomized
- Timing of degradation: early / mid / late

**What the agent learns:**
- Parallel resource allocation across multiple agents
- Redundancy detection (both drones assigned to same target)
- Adapting swarm plan when one unit degrades

**Mastery threshold:** Mean reward ≥ 0.60 over 50 episodes

---

## Reward System: Two-Layer Hybrid Design

The reward function uses a **milestone-gated hybrid structure** to provide rich gradient signal without enabling reward hacking.

### Layer 1: Per-Step Rewards (Every Step)

Provides continuous feedback throughout the episode:

**1. Distance Progress Signal**
```python
delta = prev_distance_to_target - current_distance_to_target
signal = clip(delta / MAX_SCENE_DISTANCE, -0.10, +0.10)
```
- Moving closer → small positive reward
- Moving away → small negative reward
- Magnitude intentionally weak to prevent farming

**2. Milestone Bonuses (One-Time Per Episode)**

| Milestone | Trigger | Bonus |
|-----------|---------|-------|
| `first_scan_completed` | `scan_area()` returns detections | +0.05 |
| `target_located` | `assign_drone_to_target()` succeeds | +0.05 |
| `halfway_there` | Distance < 50% of initial | +0.10 |
| `close_approach` | Distance < 1.5m | +0.15 |
| `target_reached` | Distance < 0.5m | +0.20 |
| `return_initiated` | `return_drone_home()` called after target | +0.05 |
| `arrived_home` | Within 0.5m of spawn | +0.10 |

**Maximum milestone total:** +0.70 per episode

**3. Deviation Penalties (Per Occurrence)**

| Deviation | Trigger | Penalty |
|-----------|---------|---------|
| `collision` | Contact with obstacle | -0.20 |
| `out_of_bounds` | Position outside arena | -0.15 |
| `repeated_tool_call` | Identical tool + args as previous step | -0.05 |
| `battery_critical_ignored` | Battery < 10% and non-return tool called | -0.10 |
| `moving_away` | Distance increased > 2m in one step | -0.05 |
| `early_return_home` | Return before target reached (Task 1) | -0.50 |

---

### Layer 2: Episode-End Rewards (At Termination)

Comprehensive judgment across four weighted components:

**1. Mission Completion (40%)**
```python
mission_score = targets_reached / total_targets
```

**2. Safety (30%)**
```python
collisions == 0  →  safety_score = 1.0
collisions == 1  →  safety_score = 0.6
collisions == 2  →  safety_score = 0.2
collisions >= 3  →  safety_score = 0.0
```

**3. Efficiency (20%)**
```python
efficiency_score = clip(time_limit / time_elapsed, 0.0, 1.0)
```

**4. Battery (10%)**
```python
battery_score = mean(final_battery[i] for all drones) / 100.0
```

---

### Final Normalization

```python
per_step_total   = clip(sum(all per_step_rewards), -0.5, +0.5)
episode_end_norm = episode_end_score × 0.5  # scale [0,1] → [0, 0.5]
final_score      = clip(per_step_norm + episode_end_norm, -1.0, +1.0)
```

**Score Interpretation:**

| Range | Meaning |
|-------|---------|
| +0.8 to +1.0 | Excellent — mission complete, safe, efficient |
| +0.5 to +0.8 | Good — mission complete with minor issues |
| +0.2 to +0.5 | Partial — incomplete but meaningful progress |
| -0.2 to +0.2 | Poor — minimal progress, significant issues |
| -1.0 to -0.2 | Bad — looping, crashing, or complete failure |

---

## Training Architecture: Curriculum Learning

### Why Curriculum Learning?

Each task is like a level in a game. The agent **must** learn Task 1 before it can handle Task 2. Training all tasks simultaneously would make it impossible to isolate which task broke.

### Training Flow

```
┌─────────────────────────────────────────────┐
│  TASK 1: Navigate & Reach                   │
│  Train until mean reward ≥ 0.70 (50 eps)    │
│  Save weights → Gen 1 Model                 │
└─────────────────┬───────────────────────────┘
                  │ Load Gen 1 weights
                  ▼
┌─────────────────────────────────────────────┐
│  TASK 2: Constrained Delivery               │
│  Train until mean reward ≥ 0.65 (50 eps)    │
│  Save weights → Gen 2 Model                 │
│  (Contains Task 1 + Task 2 learnings)       │
└─────────────────┬───────────────────────────┘
                  │ Load Gen 2 weights
                  ▼
┌─────────────────────────────────────────────┐
│  TASK 3: Two-Drone Coordination             │
│  Train until mean reward ≥ 0.60 (50 eps)    │
│  Save weights → Gen 3 Model (Final)         │
│  (Contains Task 1 + Task 2 + Task 3)        │
└─────────────────────────────────────────────┘
```

### Advantages

1. **Validation per task:** Test each task in isolation on held-out scenes
2. **Extensibility:** Add Task 4 later by loading Gen 3 weights
3. **Interpretable learning:** Reward curves show clear progression across phases

### Training Configuration

- **Model:** Qwen2.5-1.5B-Instruct (4-bit quantized via bitsandbytes)
- **Algorithm:** GRPO (Group Relative Policy Optimization) via TRL
- **Episodes per task:** 50 (Gen 1), 50 (Gen 2)
- **Compute:** HuggingFace T4 Medium (8 vCPU, 30GB RAM, T4 16GB)
- **Parallel environments:** 2–4 (CPU simulation bottleneck)

---

## Project Structure

```
EDITH/
├── core/                          # Physics & simulation layer
│   ├── scene_manager.py           # Scene creation, obstacle placement, randomization
│   ├── battery_simulator.py       # Physics-based battery drain
│   ├── collision_detector.py      # Raycasting & collision detection
│   ├── vision_system.py           # Camera + OpenCV color masking
│   ├── pybullet_bridge.py         # PyBullet client management
│   └── tools.py                   # 8 tool functions for LLM
│
├── wrapper/                       # OpenEnv integration layer
│   ├── edith_env.py               # Main environment class (reset/step/state)
│   ├── reward_calculator_v2.py    # Two-layer hybrid reward system
│   ├── episode_tracker.py         # Episode data tracking & metrics
│   └── task_configs.py            # Task definitions & randomization params
│
├── server/                        # Deployment
│   └── app.py                     # FastAPI server (OpenEnv-compliant)
│
├── tests/                         # Testing suite
│   ├── test_environment_basic.py  # Basic reset/step/state tests
│   ├── test_core_logic.py         # Tool function tests
│   ├── test_integration.py        # End-to-end episode tests
│   ├── test_headless.py           # Headless mode verification
│   └── test_error_handling.py     # Edge case & error handling
│
├── openenv.yaml                   # OpenEnv manifest (rubric, tools)
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker configuration (headless mode)
├── inference_drone.py             # Inference script (LLM agent testing)
├── train_edith_grpo.py            # Training script (GRPO + curriculum)
└── README.md                      # This file
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Docker (for deployment)
- HuggingFace API token (for LLM inference)

### Local Development (Windows)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install PyBullet (from local wheel if needed)
pip install pybullet

# 3. Install dependencies
pip install -r requirements.txt

# 4. Clone and install gym-pybullet-drones
git clone https://github.com/utiasDSL/gym-pybullet-drones.git
cd gym-pybullet-drones
pip install -e .
cd ..

# 5. Test headless mode
python tests/test_headless.py
```

### Local Development (Linux/Mac)

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Clone and install gym-pybullet-drones
git clone https://github.com/utiasDSL/gym-pybullet-drones.git
cd gym-pybullet-drones
pip install -e .
cd ..

# 4. Test headless mode
python tests/test_headless.py
```

---

## Usage

### 1. Start FastAPI Server

```bash
# Headless mode (for training/deployment)
uvicorn server.app:app --host 0.0.0.0 --port 8000

# GUI mode (for debugging/visualization)
EDITH_GUI=true uvicorn server.app:app --reload
```

### 2. Run Inference Test

```bash
# Set HuggingFace API token
export HF_TOKEN="your_token_here"

# Run inference on Task 1
python inference_drone.py --task task1 --debug

# Run on Task 2
python inference_drone.py --task task2

# Run on Task 3
python inference_drone.py --task task3
```

### 3. Train Agent (Colab)

See training notebook: [Colab Link](https://colab.research.google.com/drive/1YEFLDpLOA14hsdkyqs4fQMd3qK-Pbnmt)

```python
# Training script structure
from wrapper.edith_env import EDITHDroneEnv
from trl import GRPOTrainer

# Initialize environment
env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)

# Train with GRPO
trainer = GRPOTrainer(
    model=model,
    tokenizer=tokenizer,
    config=grpo_config
)

# Curriculum: Task 1 → Task 2 → Task 3
# (See full training script in Colab)
```

---

## Docker Deployment

### Build Image

```bash
docker build -t edith-drone-env .
```

### Run Container

```bash
docker run -p 8000:8000 edith-drone-env
```

### Deploy to HuggingFace Space

```bash
# Push to HF Space repository
git remote add space https://huggingface.co/spaces/Invictus-Jai/edith-mission-commander
git push space main
```

---

## Results

### Generation 1 (50 episodes, Task 1)

- **Mean reward:** 0.05 / 1.0
- **Observations:** Agent learned to stop calling invalid tools, but struggled with tool sequencing
- **Issue:** Oscillating reward curve, no clear strategy emergence

![Gen 1 Rewards Chart](assets/Gen%201%20Rewards%20Chart.svg)

**Analysis:** The reward curve shows high volatility with frequent oscillations between positive and negative rewards. The agent is exploring randomly without discovering consistent patterns that lead to success. The flat mean reward around 0.05 indicates minimal learning progress.

---

### Generation 2 (50 episodes, Task 1, loaded Gen 1 weights)

- **Mean reward:** 0.35 / 1.0
- **Observations:** Agent started calling `get_obstacle_distances()` more consistently, began routing around obstacles
- **Improvement:** Reduced oscillation, upward trend in reward curve
- **Remaining gap:** Agent would scan but sometimes ignore the data

![Gen 2 Rewards Chart](assets/Gen%202%20Rewards%20Chart.svg)

**Analysis:** Clear improvement over Gen 1. The reward curve shows reduced volatility and an upward trend, especially in the latter half of training. The agent is discovering better tool sequencing patterns. Mean reward increased 7x (0.05 → 0.35), demonstrating that curriculum learning with weight transfer is effective.

---

### Key Learnings

1. **50 episodes is insufficient** for a 1.5B model learning drone navigation from scratch
2. **Curriculum learning works** — Gen 2 showed clear improvement over Gen 1 (7x reward increase)
3. **Reward shaping is critical** — milestone bonuses provided necessary gradient signal
4. **More training time needed** to reach Task 1 mastery threshold (0.70) and progress to Task 2/3

---

## Technical Challenges Solved

### 1. Camera Calibration
**Problem:** Camera facing perpendicular to ground, `scan_area` returned nothing  
**Solution:** Fixed camera orientation to face forward along drone's heading

### 2. Gimbal Lock
**Problem:** Drone's internal orientation representation hit singularities, causing coordinate frame flips  
**Solution:** Provided fixed world coordinate system in observation

### 3. Infinite Search
**Problem:** Agent kept moving away from target, convinced it would find it "just a bit farther"  
**Solution:** Hard boundary limits with instant penalty for crossing

### 4. Obstacle Placement
**Problem:** Random scattering created inconsistent difficulty—sometimes blocked, often not  
**Solution:** Strategic placement algorithm with randomized lateral offsets along path centerline

### 5. PySimverse Incompatibility
**Problem:** Unity engine only available for Mac/Windows, no Linux/Docker support  
**Solution:** Switched to gym-pybullet-drones (headless, Linux-native, Dockerizable)

---

## OpenEnv Compliance

| Requirement | Implementation |
|-------------|----------------|
| OpenEnv base class | Extends `MCPEnvironment` |
| Gym-style API | `reset()`, `step()`, `state()` |
| Reward in [0, 1] | Normalized to [-1, 1] (per OpenEnv rubric spec) |
| Composable reward dict | Returns `{total, mission_completion, safety, efficiency, battery, per_step_total}` |
| Tool calls as actions | 8 tools registered as MCP tools |
| `openenv.yaml` manifest | Includes rubric weights, tool list |
| HF Space deployment | Docker container, headless mode |
| Training script | TRL GRPO + Unsloth, curriculum-based |
| README with results | Reward curves, before/after comparison |

---

## Future Work

If we had more compute time:

1. **Train Gen 3+** until Task 1 mastery (0.70+ mean reward)
2. **Progress to Task 2** with battery pressure and moving obstacles
3. **Scale to Task 3** with two-drone coordination
4. **Generalization test** on held-out scene never seen during training
5. **Increase episode count** to 200–500 per task for better convergence

---

## Team

**Team Troopers**

- **Pulasari Jai:** Core mechanics (physics layer, tools, scene management)
- **Lakshya Mewara:** OpenEnv wrapper (API layer, reward system, episode tracking)

---

## Links

### Project Links
- **Environment:** https://huggingface.co/spaces/Invictus-Jai/edith-mission-commander
- **Training Code:** https://colab.research.google.com/drive/1YEFLDpLOA14hsdkyqs4fQMd3qK-Pbnmt

### Dependencies & Resources
- **gym-pybullet-drones (GPD):** https://github.com/utiasDSL/gym-pybullet-drones.git
- **PySimverse Website:** https://pysimverse.com
- **PySimverse Tutorial:** https://youtu.be/hedBZ_ViAGo?si=y2KjPuXtTts2pb4p

---

## Citation

```bibtex
@misc{edith2026,
  title={EDITH: Multi-Drone Mission Commander},
  author={Team Troopers},
  year={2026},
  howpublished={OpenEnv Hackathon Round 2 - India},
  url={https://huggingface.co/spaces/Invictus-Jai/edith-mission-commander}
}
```

---

## License

MIT License

---

*Built with chaos. Built with curiosity. Built to keep going.*

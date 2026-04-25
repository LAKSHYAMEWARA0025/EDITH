# EDITH: Multi-Drone Mission Commander

OpenEnv Hackathon - Round 2 Submission

## Project Structure

```
EDITH/
├── core/                      # Person A: Core mechanics (physics layer)
│   ├── scene_manager.py       # Scene creation and randomization
│   ├── battery_simulator.py   # Battery drain simulation
│   ├── collision_detector.py  # Collision detection
│   ├── vision_system.py       # Camera + OpenCV detection
│   └── tools.py               # 8 tool functions for LLM
│
├── wrapper/                   # Person B: OpenEnv wrapper (API layer)
│   ├── edith_env.py           # Main environment class
│   ├── reward_calculator.py   # Reward computation
│   ├── episode_tracker.py     # Episode data tracking
│   ├── task_configs.py        # Task definitions
│   └── mcp_tools.py           # MCP tool registration
│
├── server/                    # Deployment
│   ├── app.py                 # FastAPI server
│   └── requirements.txt       # Server dependencies
│
├── tests/                     # Testing
│   ├── test_scene.py
│   ├── test_battery.py
│   ├── test_collision.py
│   ├── test_vision.py
│   ├── test_tools.py
│   ├── test_reward.py
│   └── test_integration.py
│
├── openenv.yaml               # OpenEnv manifest
├── requirements.txt           # Python dependencies
├── setup_local.bat            # Local setup script (Windows)
├── test_gui.py                # GUI test script
├── Dockerfile                 # Docker configuration
└── README.md                  # This file
```

## Quick Start (Local Development - Windows)

### 1. Setup Virtual Environment

```bash
# Run setup script
setup_local.bat

# This will:
# - Create venv
# - Install PyBullet from local wheel
# - Install other dependencies
```

### 2. Install gym-pybullet-drones

```bash
# Activate venv (if not already active)
venv\Scripts\activate.bat

# Clone and install
git clone https://github.com/utiasDSL/gym-pybullet-drones.git
cd gym-pybullet-drones
git checkout main
pip install -e .
cd ..
```

### 3. Test GUI Mode

```bash
python test_gui.py
```

This will open a PyBullet GUI window and fly a drone in a simple pattern.

## Development Workflow

### Person A (Core Mechanics)

**Branch:** `person-a-core-mechanics`

**Tasks:**
1. Implement `core/scene_manager.py`
2. Implement `core/battery_simulator.py`
3. Implement `core/collision_detector.py`
4. Implement `core/vision_system.py`
5. Implement `core/tools.py`

**Testing:**
```bash
python -m pytest tests/test_scene.py
python -m pytest tests/test_battery.py
# etc.
```

### Person B (OpenEnv Wrapper)

**Branch:** `person-b-wrapper`

**Tasks:**
1. Implement `wrapper/edith_env.py`
2. Implement `wrapper/reward_calculator.py`
3. Implement `wrapper/episode_tracker.py`
4. Implement `wrapper/task_configs.py`
5. Implement `wrapper/mcp_tools.py`

**Testing:**
```bash
python -m pytest tests/test_reward.py
python -m pytest tests/test_integration.py
```

## Integration

**Merge both branches:**
```bash
git checkout main
git merge person-a-core-mechanics
git merge person-b-wrapper
```

## Deployment

### Docker

```bash
docker build -t edith-drone-env .
docker run -p 8000:8000 edith-drone-env
```

### HuggingFace Space

Push to HuggingFace Space repository (configured in `openenv.yaml`)

## Current Status

- [x] Verification tests complete (all passed)
- [x] Local setup scripts created
- [ ] Core mechanics implementation (Person A)
- [ ] OpenEnv wrapper implementation (Person B)
- [ ] Integration testing
- [ ] Deployment

## Team

- **Person A:** Core mechanics (physics layer)
- **Person B:** OpenEnv wrapper (API layer)

## Documentation

- `Docs/Drone/test_results_summary.md` - Verification test results
- `Docs/Drone/HIGH_LEVEL_IMPLEMENTATION_PLAN.md` - Implementation plan
- `Docs/Drone/drone_problem_statement.md` - Problem statement
- `Docs/Drone/GPD test.md` - gym-pybullet-drones testing guide

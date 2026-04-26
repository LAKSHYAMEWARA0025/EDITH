# Deploying EDITH to Hugging Face Spaces

## Overview

This guide walks you through deploying the EDITH environment to Hugging Face Spaces for the OpenEnv Hackathon. The deployment makes your environment publicly accessible and satisfies the hackathon requirement of hosting on HF Spaces.

## Prerequisites

- Hugging Face account ([Sign up here](https://huggingface.co/join))
- Git installed locally
- Docker tested locally (run `docker_build_test.bat` or `docker_build_test.sh` first)

## Step-by-Step Deployment

### 1. Create a New Space

1. Go to [https://huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in the details:
   - **Owner**: Your username or organization
   - **Space name**: `edith-mission-commander` (or your preferred name)
   - **License**: MIT
   - **Select the Space SDK**: **Docker**
   - **Space hardware**: CPU basic (free tier is sufficient)
   - **Visibility**: Public (required for hackathon)

4. Click **"Create Space"**

### 2. Clone the Space Repository

```bash
# Clone your new Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/edith-mission-commander
cd edith-mission-commander
```

### 3. Copy EDITH Files

Copy the necessary files from your EDITH directory:

**On Windows (PowerShell):**
```powershell
# From the edith-mission-commander directory
Copy-Item -Recurse ..\EDITH\core .
Copy-Item -Recurse ..\EDITH\wrapper .
Copy-Item -Recurse ..\EDITH\server .
Copy-Item ..\EDITH\Dockerfile .
Copy-Item ..\EDITH\requirements.txt .
Copy-Item ..\EDITH\openenv.yaml .
Copy-Item ..\EDITH\README.md .
Copy-Item ..\EDITH\.dockerignore .
```

**On Linux/Mac:**
```bash
# From the edith-mission-commander directory
cp -r ../EDITH/core .
cp -r ../EDITH/wrapper .
cp -r ../EDITH/server .
cp ../EDITH/Dockerfile .
cp ../EDITH/requirements.txt .
cp ../EDITH/openenv.yaml .
cp ../EDITH/README.md .
cp ../EDITH/.dockerignore .
```

### 4. Create Space README with Metadata

Replace the default README.md with this template:

```markdown
---
title: EDITH Mission Commander
emoji: 🚁
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
tags:
  - openenv
  - reinforcement-learning
  - drone-simulation
  - pybullet
  - hackathon
---

# EDITH: Emergency Drone Intelligence & Tactical Handler

**OpenEnv Hackathon 2026 Submission**

## Overview

EDITH is a reinforcement learning environment for training LLM agents to command autonomous drones in complex navigation scenarios. The environment simulates realistic drone physics using PyBullet and provides a rich reward structure for learning obstacle avoidance, mission planning, and resource management.

## Features

- **3 Task Types**: Basic navigation, battery management, multi-drone coordination
- **Realistic Physics**: PyBullet-based drone simulation with PID control
- **Rich Observations**: Vision system, proximity sensors, mission status
- **Comprehensive Rewards**: Multi-component reward system with milestone bonuses
- **OpenEnv Compliant**: Standard Gym-style API for RL training

## Quick Start

### Using the API

The environment exposes a FastAPI server with three main endpoints:

**1. Get Available Tools**
```bash
curl https://YOUR_USERNAME-edith-mission-commander.hf.space/tools
```

**2. Reset Environment**
```bash
curl -X POST https://YOUR_USERNAME-edith-mission-commander.hf.space/reset
```

**3. Execute Action**
```bash
curl -X POST https://YOUR_USERNAME-edith-mission-commander.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_mission_status", "args": {}}'
```

### Using Python Client

```python
import requests

BASE_URL = "https://YOUR_USERNAME-edith-mission-commander.hf.space"

# Reset environment
response = requests.post(f"{BASE_URL}/reset")
state = response.json()["state"]

# Execute action
action = {"tool": "move_drone_to", "args": {"drone_id": 0, "x": 2, "y": 2, "z": 1}}
response = requests.post(f"{BASE_URL}/step", json=action)
result = response.json()

print(f"Reward: {result['reward']}")
print(f"Done: {result['done']}")
```

## Available Tools

- `get_drone_status`: Get current drone position, velocity, battery
- `move_drone_to`: Command drone to move to coordinates
- `get_obstacle_distances`: Raycast distances to obstacles
- `scan_area`: Use camera to detect obstacles and targets
- `get_mission_status`: Get mission progress and target locations
- `assign_drone_to_target`: Assign drone to specific target (Task 3)
- `return_drone_home`: Command drone to return to spawn

## Task Types

### Task 1: Navigate & Reach
- **Objective**: Navigate to target, avoid obstacles, return home
- **Obstacles**: 2-5 strategically placed
- **Reward**: Mission completion (40%), safety (30%), efficiency (20%), battery (10%)

### Task 2: Constrained Delivery
- **Objective**: Same as Task 1 but with limited battery
- **Challenge**: Battery management, optimal path planning
- **Obstacles**: 3-5 with tighter placement

### Task 3: Two-Drone Coordination
- **Objective**: Coordinate two drones to reach multiple targets
- **Challenge**: Task allocation, collision avoidance between drones
- **Obstacles**: 4-6 distributed across paths

## Training

See the [training guide](./TRAINING.md) for examples using TRL and Unsloth.

## Architecture

- **Physics**: PyBullet with 240Hz simulation
- **Control**: PID controller for low-level flight control
- **Observation**: Position, velocity, battery, vision, proximity sensors
- **Reward**: Two-layer hybrid (per-step + episode-end)

## Repository

Full source code: [GitHub Link]

## Citation

```bibtex
@misc{edith2026,
  title={EDITH: Emergency Drone Intelligence & Tactical Handler},
  author={Your Name},
  year={2026},
  publisher={Hugging Face Spaces},
  howpublished={\url{https://huggingface.co/spaces/YOUR_USERNAME/edith-mission-commander}}
}
```

## License

MIT License - see LICENSE file for details
```

**Important**: Replace `YOUR_USERNAME` with your actual Hugging Face username!

### 5. Commit and Push

```bash
git add .
git commit -m "Initial deployment of EDITH environment"
git push
```

### 6. Wait for Build

- Hugging Face will automatically build your Docker image
- This takes **10-15 minutes** on first deployment
- Watch the build logs in the Space's "Logs" tab
- The Space will show "Building" → "Running" when ready

### 7. Verify Deployment

Once the Space shows "Running":

```bash
# Test the API
curl https://YOUR_USERNAME-edith-mission-commander.hf.space/tools

# Expected output:
# {"tools": ["get_drone_status", "move_drone_to", ...]}
```

## Troubleshooting

### Build Fails

**Check the logs** in the Space's "Logs" tab. Common issues:

1. **Missing files**: Ensure all files were copied correctly
2. **Dockerfile errors**: Test locally first with `docker build`
3. **Dependency conflicts**: Check requirements.txt

### Space Shows "Runtime Error"

1. Check if the health check is passing
2. Verify port 8000 is exposed in Dockerfile
3. Check server logs for Python errors

### API Returns Errors

1. Test locally first: `docker run -p 8000:8000 edith-mission-commander:latest`
2. Check if environment initializes correctly
3. Verify PyBullet can run in headless mode

## Updating Your Space

To update after making changes:

```bash
cd edith-mission-commander

# Copy updated files
cp -r ../EDITH/core .
cp -r ../EDITH/wrapper .
# ... etc

# Commit and push
git add .
git commit -m "Update: [describe changes]"
git push
```

The Space will automatically rebuild.

## Hardware Upgrades (Optional)

For faster inference during training:

1. Go to Space Settings
2. Select "Hardware"
3. Upgrade to:
   - **CPU Upgrade**: Faster episode rollouts
   - **GPU**: Not needed (PyBullet is CPU-based)

**Note**: Upgrades require payment. Free tier is sufficient for hackathon.

## Making Your Space Discoverable

### Add to OpenEnv Collection

1. Go to [OpenEnv Hub](https://huggingface.co/openenv)
2. Submit your Space to the collection
3. Tag with `openenv`, `hackathon`, `drone-simulation`

### Share Your Space

- **Direct link**: `https://huggingface.co/spaces/YOUR_USERNAME/edith-mission-commander`
- **Embed in blog**: Use HF's embed widget
- **Social media**: Share with #OpenEnvHackathon

## Hackathon Submission Checklist

- [ ] Space is public and running
- [ ] README includes problem statement and results
- [ ] Training script available (Colab notebook)
- [ ] Reward curves and metrics shown
- [ ] Video or blog post created (<2 minutes)
- [ ] All links work and are accessible
- [ ] Space URL submitted to hackathon form

## Additional Resources

- **OpenEnv Docs**: [https://openenv.dev](https://openenv.dev)
- **HF Spaces Docs**: [https://huggingface.co/docs/hub/spaces](https://huggingface.co/docs/hub/spaces)
- **Docker on Spaces**: [https://huggingface.co/docs/hub/spaces-sdks-docker](https://huggingface.co/docs/hub/spaces-sdks-docker)

## Support

- **Issues**: [GitHub Issues]
- **Discussions**: [HF Space Discussions]
- **Discord**: [OpenEnv Community]

Good luck with your hackathon submission! 🚁

# Target Coordinates Fix

## Problem

The agent was **flying blind** - it could only detect obstacles through `scan_area` but had no reliable way to find target locations. This led to:

1. **Random search behavior** - moving in arbitrary directions hoping to find targets
2. **Systematic failure** - agent would move away from targets due to obstacle avoidance with no way to recover
3. **Training impossibility** - no amount of GRPO training could fix this fundamental information gap

## Root Cause Analysis

### What Was Happening:
```
[STEP 1] scan_area → obstacle detected, NO target found
[STEP 2+] Agent moves blindly in +X direction
[REWARDS] Getting more negative each step (moving away from target)
[RESULT] Agent never finds target, episode times out
```

### Why Vision-Only Approach Failed:
1. **Camera FOV limitations** - Target at Z=1.0, drone scanning from Z=0.1
2. **Obstacle interference** - Obstacles block target visibility  
3. **Scene randomization** - Target could be anywhere in 8x8m area
4. **No systematic search** - Agent had no strategy to explore all areas

### Why Training Won't Fix This:
- Every episode has different obstacle/target layout
- Agent gets pushed away from targets by obstacles
- No reliable signal to indicate "search in opposite direction"
- This is a **navigation with known destination** problem, not **search and rescue**

## Solution: Operator-Provided Coordinates

In real drone operations, the operator provides target coordinates in the mission brief. The challenge is **navigation and obstacle avoidance**, not **target discovery**.

### Implementation

**1. Added target positions to `get_mission_status` in `core/tools.py`:**

```python
# Add target positions (operator provides coordinates in mission brief)
targets = []
for i, target_body_id in enumerate(env.scene_manager.target_ids):
    target_pos, _ = p.getBasePositionAndOrientation(
        target_body_id, physicsClientId=inner_env.CLIENT)
    targets.append({
        "id": i,
        "position": list(target_pos),
        "reached": False
    })
```

**2. Updated system prompt in `inference_drone.py`:**

```
DECISION FRAMEWORK:
1. No information yet → call get_mission_status to get target coordinates
2. Know where target is → call move_drone_to with coordinates toward target
3. Near obstacle → call get_obstacle_distances then reroute

TARGET INFORMATION:
- Target coordinates are provided in mission_status["targets"]
- Each target has: {"id": 0, "position": [x, y, z], "reached": false}
- Navigate directly to target position using move_drone_to
- Use scan_area only for obstacle detection, not target finding
```

**3. Enhanced logging to show target positions:**

```
[INFO] Initial state:
       Target 0: [5.0, 0.0, 1.0]
       Drone position: [0.0, 0.0, 0.1125]
```

## Expected Behavior After Fix

### Before:
```
[STEP 1] scan_area → obstacle found, no target
[STEP 2] move_drone_to → [random direction]
[STEP 3+] Continue moving randomly, getting negative rewards
[RESULT] Never finds target, times out
```

### After:
```
[STEP 1] get_mission_status → target at [5.0, 0.0, 1.0]
[STEP 2] move_drone_to → [5.0, 0.0, 1.0] (direct navigation)
[STEP 3] scan_area → check for obstacles on route
[STEP 4] move_drone_to → adjust path to avoid obstacles
[RESULT] Reaches target efficiently
```

## Why This Is The Right Approach

### Real-World Justification:
- **Military/Commercial drones**: Always given GPS coordinates
- **Search and rescue**: Operators provide search area coordinates  
- **Delivery drones**: Destination address converted to coordinates
- **Inspection drones**: Asset locations are known and provided

### Training Focus Shifts To:
- **Path planning** around obstacles
- **Efficient routing** (shortest safe path)
- **Obstacle avoidance** strategies
- **Battery management** (Task 2)
- **Multi-drone coordination** (Task 3)

### Not:
- Random exploration
- Blind search patterns
- Target discovery through vision

## Task Differentiation

- **Task 1**: Navigate to known coordinate, avoid obstacles
- **Task 2**: Same + battery constraint (strategic routing)  
- **Task 3**: Same + multi-drone coordination (task allocation)

Each task builds on navigation fundamentals while adding complexity layers.

---

*This fix transforms the environment from "search and rescue" to "navigation with obstacles" - the intended challenge for a drone mission commander.*
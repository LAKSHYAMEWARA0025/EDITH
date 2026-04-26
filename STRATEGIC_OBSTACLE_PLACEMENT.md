# Strategic Obstacle Placement System

## Problem Solved

**Before:** Obstacles placed randomly in zones, often far from the path. Agent could fly straight to target without encountering any obstacles. No navigation challenge.

**After:** Obstacles strategically placed ON the direct path between spawn and target, forcing the agent to detect, plan, and navigate around them.

---

## Algorithm Overview

### Core Principle: Path-Blocking Placement

1. **Calculate direct path** from spawn [0,0,1] to target
2. **Divide path into segments** (25-40%, 45-60%, 65-75% of distance)
3. **Place one obstacle per segment** along the path
4. **Add lateral offset** (±0.3m to ±1.2m) to create navigable gaps
5. **Alternate sides** (left, right, left) to create slalom pattern
6. **Enforce minimum separation** (0.8m) to prevent stacking/overlap

---

## Task 1: Navigate & Reach

### Placement Strategy
- **Segments:** 25-40%, 45-60%, 65-75% of path length
- **Lateral offset:** ±0.3m to ±1.2m (moderate difficulty)
- **Alternating sides:** Creates natural slalom pattern
- **Flanking obstacle:** 60% chance to add guard near target

### Safety Checks
- Minimum 1.0m from spawn
- Minimum 0.8m from target
- Minimum 0.8m between obstacles (prevents stacking)
- Clamped to arena bounds [-7.5, 7.5] x [-7.5, 7.5] x [0.5, 2.0]

### Navigation Challenge
Agent must:
1. Detect obstacle blocking direct path
2. Plan waypoint to go around (adjust X or Y by ±2m)
3. Continue toward target
4. Handle flanking obstacle on final approach

---

## Task 2: Constrained Delivery

### Placement Strategy
- **Segments:** 20-35%, 40-55%, 60-75% (tighter spacing)
- **Lateral offset:** ±0.2m to ±0.8m (TIGHTER than Task 1)
- **Midpoint obstacle:** Extra obstacle at 50% of path
- **Higher obstacle count:** 3-5 obstacles (vs 2-5 in Task 1)

### Why Tighter?
- Forces **longer detours** around obstacles
- Increases **battery cost** of navigation
- Tests battery management under navigation constraints
- Agent must balance "shortest path" vs "battery efficient path"

---

## Task 3: Two-Drone Coordination

### Placement Strategy
- **Multiple targets:** 2-3 targets placed
- **Distributed obstacles:** 4-6 obstacles split across paths
- **Per-target allocation:** Each target gets obstacles on its path
- **Path independence:** Obstacles for target A don't block path to target B

### Coordination Challenge
Agent must:
1. Identify which drone should go to which target
2. Plan independent paths for each drone
3. Avoid assigning both drones to same target
4. Navigate each drone around its path's obstacles

---

## Implementation Details

### Path Geometry Calculation
```python
spawn = np.array([0.0, 0.0, 1.0])
path_vec = target_pos - spawn
path_length = np.linalg.norm(path_vec)
path_dir = path_vec / path_length  # Unit vector toward target

# Perpendicular direction (for lateral offset)
perp_dir = np.array([-path_dir[1], path_dir[0], 0.0])
```

### Obstacle Placement
```python
# Position along path (within segment)
t = np.random.uniform(seg_min, seg_max)
base_pos = spawn + path_dir * path_length * t

# Lateral offset (alternating sides)
lateral_sign = 1 if i % 2 == 0 else -1
lateral_magnitude = np.random.uniform(0.3, 1.2)
lateral_offset = perp_dir * lateral_sign * lateral_magnitude

# Final position
obstacle_pos = base_pos + lateral_offset + vertical_offset
```

### Anti-Stacking Safety Check
```python
# Check distance to all previously placed obstacles
for prev_pos in placed_positions:
    distance = np.linalg.norm(obstacle_pos - np.array(prev_pos))
    if distance < 0.8:  # Minimum 0.8m separation
        too_close = True
        break

if too_close:
    attempts += 1
    continue  # Try different position
```

---

## What This Guarantees

### ✅ Path Blocking
Every obstacle is placed within defined segments along the direct path. Agent **cannot** fly straight to target.

### ✅ Navigability
Lateral offset ensures obstacles are NEAR centerline but not ON it. There's always a gap to navigate through.

### ✅ No Stacking
Minimum 0.8m separation between obstacles prevents overlapping or collapsed obstacles.

### ✅ Slalom Pattern
Alternating left/right placement creates natural navigation challenge requiring multiple waypoints.

### ✅ Randomization
Within constraints, positions randomize every episode. Agent cannot memorize fixed routes.

### ✅ Scalability
Works for any target position and any number of obstacles (2-6).

---

## Expected Agent Behavior

### Before Strategic Placement:
```
[STEP 1] get_mission_status → target at [5, 5, 1]
[STEP 2] move_drone_to(5, 5, 1) → direct flight
[STEP 3] Target reached
[RESULT] 3 steps, no obstacle avoidance needed
```

### After Strategic Placement:
```
[STEP 1] get_mission_status → target at [5, 5, 1]
[STEP 2] move_drone_to(2, 2, 1) → first waypoint
[WARN] Proximity: obstacle 1.2m ahead
[STEP 3] move_drone_to(2, 0, 1) → reroute right
[STEP 4] move_drone_to(4, 4, 1) → second waypoint
[WARN] Proximity: obstacle 0.8m ahead
[STEP 5] move_drone_to(4, 6, 1) → reroute left
[STEP 6] move_drone_to(5, 5, 1) → final approach
[STEP 7] Target reached
[RESULT] 7 steps, multiple reroutes, obstacle avoidance demonstrated
```

---

## Why This Matters for Training

### Without Strategic Placement:
- Agent learns: "fly forward, target is there"
- No obstacle avoidance learned
- Automation scripts sufficient
- LLM reasoning not required

### With Strategic Placement:
- Agent learns: "scan for obstacles, plan route around them, approach carefully"
- Obstacle avoidance is mandatory
- Automation scripts fail (can't handle dynamic obstacles)
- LLM reasoning required for path planning

This is what makes the environment a **genuine reasoning challenge** rather than a simple navigation task.

---

*Strategic placement transforms the environment from "fly to coordinates" to "plan and execute multi-step navigation under constraints."*

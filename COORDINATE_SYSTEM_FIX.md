# Coordinate System Fix

## Problem Identified

From the debug logs, we can see the agent was moving along the X-axis:
```
[DEBUG] Updated target for drone 0: [5.  0.  1.5]   # X=5, Y=0
[DEBUG] Updated target for drone 0: [10.  0.  1.5]  # X=10, Y=0
[DEBUG] Updated target for drone 0: [15.  0.  1.5]  # X=15, Y=0
```

But you observed: **"Target is forward, drone moved right side"**

This confirms a **coordinate system mismatch**.

## Root Cause

### PyBullet's Actual Coordinate System:
- **+X axis = RIGHT**
- **+Y axis = FORWARD**
- **+Z axis = UP**

### What the Code Assumed:
- **+X axis = FORWARD** ❌
- **+Y axis = RIGHT** ❌
- **+Z axis = UP** ✅

### Evidence:

**File:** `EDITH/core/vision_system.py` (line 32)
```python
# BEFORE (WRONG):
cameraTargetPosition=[pos[0] + 5.0, pos[1], pos[2]],  # Look forward (X direction)
```

The camera was looking in the +X direction (RIGHT), but the comment said "forward". This caused:
1. Camera to look right instead of forward
2. Vision system to report wrong directions
3. Agent to move right when trying to go forward

## Fixes Applied

### Fix 1: Camera Direction

**File:** `EDITH/core/vision_system.py`

```python
# AFTER (CORRECT):
cameraTargetPosition=[pos[0], pos[1] + 5.0, pos[2]],  # Look forward (+Y direction)
```

Now the camera looks in the **+Y direction (forward)**, matching PyBullet's coordinate system.

### Fix 2: System Prompt

**File:** `EDITH/inference_drone.py`

Added explicit coordinate system documentation:
```
COORDINATE SYSTEM (IMPORTANT):
- X-axis: left/right (positive X = right, negative X = left)
- Y-axis: forward/backward (positive Y = forward, negative Y = backward)
- Z-axis: up/down (positive Z = up, negative Z = down)
- Drone starts at [0, 0, 0.1] (origin, ground level)
- Camera looks in +Y direction (forward)
- When scan_area detects "left", target is at negative X
- When scan_area detects "right", target is at positive X
- When scan_area detects "center", target is straight ahead (+Y)
```

Also updated tool descriptions:
```
4. {"tool": "move_drone_to", "args": {"drone_id": 0, "x": 1.0, "y": 2.0, "z": 1.5}}
   - Plans movement to target coordinates (absolute position, not relative)
   - X: left(-) / right(+), Y: backward(-) / forward(+), Z: down(-) / up(+)
```

## Expected Behavior After Fix

### Before Fix:
```
Agent thinks: "Target is forward, move to X=5"
Drone moves: RIGHT (because +X = right in PyBullet)
Result: Wrong direction ❌
```

### After Fix:
```
Agent thinks: "Target is forward, move to Y=5"
Drone moves: FORWARD (because +Y = forward in PyBullet)
Result: Correct direction ✅
```

## Testing Instructions

### Step 1: Restart Server

The server needs to reload the fixed `vision_system.py`:

```bash
cd EDITH
# Stop the current server (Ctrl+C)
# Restart it
python server/app.py
```

### Step 2: Run Inference Test

```bash
python inference_drone.py --task task1
```

### Step 3: Watch Debug Output

Look for patterns like:
```
[DEBUG] Updated target for drone 0: [0.  5.  1.5]   # Y=5 (forward), not X=5
[DEBUG] Updated target for drone 0: [0. 10.  1.5]   # Y=10 (more forward)
```

**Key indicators of success:**
- Y coordinate should increase when moving forward
- X coordinate should change when moving left/right
- Drone should move towards target (not perpendicular)

### Step 4: Visual Verification

If GUI is enabled, you should see:
- Drone moves **towards** the green target
- Not perpendicular or away from it
- Smooth diagonal movement if target is at an angle

## Coordinate System Reference

For future development, here's the complete PyBullet coordinate system:

```
         +Z (UP)
          |
          |
          |
          +-------- +Y (FORWARD)
         /
        /
       +X (RIGHT)
```

**Drone spawn:** [0, 0, 0.1]
- X=0: centered left/right
- Y=0: at starting line
- Z=0.1: just above ground

**Example target positions:**
- [0, 10, 1.0]: 10m forward, 1m up
- [5, 10, 1.0]: 10m forward, 5m right, 1m up
- [-5, 10, 1.0]: 10m forward, 5m left, 1m up

**Movement examples:**
- `move_drone_to(0, 0, 10, 1.5)`: Move forward 10m
- `move_drone_to(0, 5, 0, 1.5)`: Move right 5m
- `move_drone_to(0, -5, 0, 1.5)`: Move left 5m
- `move_drone_to(0, 0, 0, 2.0)`: Move up to 2m altitude

## Impact on Other Components

### ✅ No Changes Needed:
- **PID Controller**: Works with absolute coordinates, doesn't care about axis names
- **Collision Detection**: Uses distances, not directions
- **Battery Simulator**: Independent of coordinates
- **Reward Calculator**: Uses distances, not directions

### ✅ Already Correct:
- **Scene Manager**: Places objects in PyBullet's coordinate system
- **Episode Tracker**: Tracks positions, doesn't interpret axes

### ✅ Now Fixed:
- **Vision System**: Camera now looks forward (+Y)
- **Inference Prompt**: Agent now understands coordinate system

## Why This Happened

This is a common issue when integrating different systems:

1. **Different conventions**: 
   - Game engines often use X=forward (Unity, Unreal)
   - Robotics often uses Y=forward (ROS, PyBullet)
   - Aviation uses X=forward (NED frame)

2. **Implicit assumptions**:
   - Code comment said "forward" but used X-axis
   - No explicit coordinate system documentation
   - Vision system and movement system assumed different conventions

3. **Testing gap**:
   - Tests verified "drone moves" but not "drone moves in correct direction"
   - Need directional tests: "move forward → Y increases"

## Prevention for Future

### 1. Document Coordinate System

Add to README and code comments:
```python
# PyBullet Coordinate System:
# +X = RIGHT, +Y = FORWARD, +Z = UP
# Drone spawn: [0, 0, 0.1]
```

### 2. Add Directional Tests

```python
def test_move_forward():
    env.reset()
    initial_y = env.get_drone_position()[1]
    env.step({"tool": "move_drone_to", "args": {"drone_id": 0, "x": 0, "y": 5, "z": 1}})
    final_y = env.get_drone_position()[1]
    assert final_y > initial_y, "Moving forward should increase Y"
```

### 3. Visual Debugging

Always test with GUI enabled first:
```python
env = EDITHDroneEnv(gui=True)  # See actual movement
```

## Summary

**Problem:** Coordinate system mismatch - camera and agent thought X=forward, but PyBullet uses Y=forward

**Fix:** 
1. Camera now looks in +Y direction (forward)
2. System prompt clarifies coordinate system
3. Agent now knows X=left/right, Y=forward/backward

**Result:** Drone should now move in the correct direction towards targets

**Next test:** Run inference and verify Y coordinate increases when moving forward

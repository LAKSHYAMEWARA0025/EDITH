# Mission Complete Bug Fix

## Problem Identified

The agent was calling `return_drone_home` repeatedly despite receiving errors because **`get_mission_status` was returning `mission_complete: true` from the very start of the episode**.

## Root Cause

In `core/tools.py`, the `get_mission_status` function had flawed logic:

```python
mission_complete = bool((targets_reached >= total_targets) and all(
    d["status"] != "crashed" for d in drones
))
```

### The Bug:

When `total_targets = 0` (uninitialized) or when both are 0:
- `targets_reached >= total_targets` → `0 >= 0` → `True`
- `mission_complete = True` ✗

The agent received contradictory signals:
1. `get_mission_status` → `mission_complete: true`
2. `return_drone_home` → ERROR: "Cannot return home. Reach the green target first."

The agent didn't know which to trust, so it alternated between:
- Trying to return home (because status says complete)
- Moving to [0, 0, 1] (because return fails)

## The Fix

### 1. Fixed `mission_complete` Logic in `core/tools.py`

```python
# Guard: mission cannot be complete if no targets exist or none reached
if total_targets == 0:
    mission_complete = False
else:
    mission_complete = bool(
        targets_reached >= total_targets and 
        targets_reached > 0 and  # must have actually reached something
        all(d["status"] != "crashed" for d in drones)
    )
```

**Key changes:**
- Explicit guard: `total_targets == 0` → `mission_complete = False`
- Added requirement: `targets_reached > 0` (must have actually reached something)
- Mission cannot be complete if no targets exist or none have been reached

### 2. Added Debug Logging

**In `core/tools.py` (get_mission_status):**
```python
print(f"[DEBUG] Mission status: total={total_targets}, reached={targets_reached}, complete={mission_complete}")
```

**In `wrapper/edith_env.py` (reset):**
```python
print(f"[DEBUG] Reset complete: {len(self.scene_manager.target_ids)} targets spawned")
print(f"[DEBUG] Episode tracker total_targets: {self.episode_tracker.total_targets}")
```

**In `inference_drone.py` (reset and step logging):**
```python
print(f"[DEBUG] Mission complete at reset: {state['mission_status']['mission_complete']}")
# And in log_step for get_mission_status calls:
print(f"          └─ Targets: {result.get('targets_reached', 0)}/{result.get('total_targets', 0)} | Complete: {result.get('mission_complete', False)}")
```

## Expected Behavior After Fix

### Before:
```
[RESET] total_targets=1, mission_complete=True  ✗ (BUG!)
[STEP 5] return_drone_home → ERROR (agent confused by contradictory signals)
[STEP 6-20] Alternates between return_home and move_to [0,0,1]
```

### After:
```
[RESET] total_targets=1, reached=0, mission_complete=False  ✓
[STEP 5] return_drone_home → ERROR (agent understands: mission not complete)
[STEP 6+] Agent continues searching (no contradictory signal)
```

## Why This Matters

The agent was receiving **contradictory signals**:
- Tool error: "Reach target first"
- Mission status: "Mission complete"

This created a logical impossibility. The agent couldn't learn because the environment was lying to it.

With the fix:
- Mission status is now **consistent** with tool gating
- Agent receives **clear, unambiguous feedback**
- GRPO can now learn proper exploration strategies

## Verification Steps

Run inference with debug mode and check logs:

```bash
python inference_drone.py --task task1 --debug
```

Look for:
1. `[DEBUG] Reset complete: 1 targets spawned` ✓
2. `[DEBUG] Mission complete at reset: False` ✓
3. `[DEBUG] Mission status: total=1, reached=0, complete=False` ✓
4. Agent should NOT call `return_drone_home` until target reached

---

*This fix ensures mission status accurately reflects episode state and eliminates contradictory signals to the agent.*

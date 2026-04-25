# Reward Normalization Fix

## Problem

**Massive unnormalized rewards:**
- Step 2: reward = -34
- Step 3-14: reward = -120 each
- Makes training impossible
- Can't compare episodes

## Root Cause

The old reward calculator didn't have proper bounds. Penalties could accumulate without limit.

## Solution: Redesigned Reward System

### Key Principles

1. **Per-step rewards in range [-1, +1]**
   - Prevents extreme values
   - Makes learning stable
   - Comparable across steps

2. **Weighted components (sum to 1.0)**
   - Progress: 60% (most important)
   - Safety: 20% (collisions)
   - Efficiency: 20% (time/movement)

3. **Episode-length independent**
   - Short episodes (10 steps) comparable to long ones (100 steps)
   - Average reward per step is meaningful
   - Total episode reward = sum of per-step rewards

### New Reward Structure

```python
# Per-step reward components:

Progress (60%):
  - Target reached: +1.0
  - Getting closer: 0.0 to +1.0 (based on distance)
  - Moving away: -0.2 to +0.5
  - Range: [-0.2, +1.0] → weighted: [-0.12, +0.6]

Safety (20%):
  - No collisions: +1.0
  - One collision: 0.0
  - Multiple: -1.0
  - Range: [-1.0, +1.0] → weighted: [-0.2, +0.2]

Efficiency (20%):
  - Moving well: +0.5
  - Some stagnation: 0.0
  - Mostly stuck: -0.5
  - Completely stuck: -1.0
  - Range: [-1.0, +0.5] → weighted: [-0.2, +0.1]

Total per-step: [-0.52, +0.9] ≈ [-1, +1]
```

### Distance Normalization

```python
MAX_EXPECTED_DISTANCE = 20.0  # Realistic max in scene

# Map distance to reward:
distance = 0m   → progress_score = 1.0 (at target)
distance = 10m  → progress_score = 0.5 (halfway)
distance = 20m+ → progress_score = 0.0 (far away)
```

### Episode Comparison

**Old system:**
- Episode A: 10 steps, total reward = -1200 ❌
- Episode B: 50 steps, total reward = +25 ❌
- Can't compare! Different scales!

**New system:**
- Episode A: 10 steps, avg reward = -0.3/step, total = -3.0 ✅
- Episode B: 50 steps, avg reward = +0.5/step, total = +25.0 ✅
- Episode B is clearly better (positive avg reward)

### Episode Score (0-100)

For final evaluation and comparison:

```python
Score = Target Completion (0-50)
      + Safety (0-25)
      + Efficiency (0-25)

Examples:
- Perfect run: 100 points
- Completed with 1 collision, slow: 70 points
- Failed, no collisions: 25 points
- Failed with crashes: 0 points
```

## Implementation

### Files Changed

1. **`wrapper/reward_calculator_v2.py`** (NEW)
   - Redesigned reward calculator
   - Proper normalization
   - Clear component weights

2. **`wrapper/edith_env.py`**
   - Import new calculator
   - Use RewardCalculatorV2

3. **`inference_drone.py`**
   - Display per-step reward clearly
   - Show `step_reward=+0.257` not cumulative

4. **`test_environment_basic.py`** (NEW)
   - Hardcoded action test
   - Verify rewards are reasonable
   - No LLM needed

## Testing

### Step 1: Test with Hardcoded Actions

```bash
cd EDITH
python test_environment_basic.py
```

**Expected output:**
```
[STEP 1] Scanning area...
  Reward: +0.257
  
[STEP 2] Moving to target area...
  Reward: +0.412
  
[STEP 3] Scanning again...
  Reward: +0.389
  
...

Total reward: +4.523
Average reward per step: +0.452
```

**Success criteria:**
- ✅ All rewards in range [-1, +1]
- ✅ Positive rewards when moving towards target
- ✅ Total reward reasonable (not -1000)
- ✅ Drone reaches target

### Step 2: Test with LLM

```bash
python inference_drone.py --task task1
```

**Expected output:**
```
[STEP  1] tool=scan_area      step_reward=+0.257 done=False
[STEP  2] tool=move_drone_to  step_reward=+0.412 done=False
[STEP  3] tool=scan_area      step_reward=+0.389 done=False
```

**Success criteria:**
- ✅ Rewards displayed as per-step (not cumulative)
- ✅ All rewards in reasonable range
- ✅ No -120 rewards

## Why This Matters for Training

### Problem with Unnormalized Rewards

```
Episode 1: rewards = [0.1, 0.2, -120, -120, -120]
Episode 2: rewards = [0.1, 0.2, 0.3, 0.4, 0.5]

Which is better? Episode 2!
But total: Episode 1 = -359.4, Episode 2 = 1.5

The -120 dominates everything. Agent learns:
"Avoid whatever caused -120" but can't learn what's actually good.
```

### With Normalized Rewards

```
Episode 1: rewards = [+0.2, +0.3, -0.5, -0.3, -0.2]
Episode 2: rewards = [+0.2, +0.3, +0.4, +0.5, +0.6]

Total: Episode 1 = -0.5, Episode 2 = +2.0

Clear signal: Episode 2 is better.
Agent learns: "Do more of what Episode 2 did"
```

### Gradient Signal

With normalized rewards:
- Small improvements → small reward increase (+0.1)
- Big improvements → big reward increase (+0.5)
- Small mistakes → small penalty (-0.1)
- Big mistakes → big penalty (-0.5)

**Proportional feedback = better learning**

## Comparison: Old vs New

### Old System

```
Step 1: scan_area → reward = 0.257
Step 2: move_drone_to → reward = -34.0  ❌ HUGE PENALTY
Step 3: return_home → reward = -120.0   ❌ CATASTROPHIC
```

**Problems:**
- Extreme values
- Dominates learning
- Can't compare episodes
- Unclear what's good/bad

### New System

```
Step 1: scan_area → reward = +0.26  ✅ Small positive
Step 2: move_drone_to → reward = +0.41  ✅ Good progress
Step 3: scan_area → reward = +0.39  ✅ Still good
```

**Benefits:**
- Bounded values
- Clear signal
- Comparable episodes
- Proportional feedback

## Next Steps

1. **Run test_environment_basic.py** - Verify rewards are normalized
2. **Run inference test** - Check LLM behavior with new rewards
3. **If good** - Proceed to training setup
4. **If issues** - Debug and adjust normalization constants

## Tuning Parameters

If rewards need adjustment, edit `reward_calculator_v2.py`:

```python
# Component weights (must sum to 1.0)
self.PROGRESS_WEIGHT = 0.6      # Increase if progress too weak
self.SAFETY_WEIGHT = 0.2        # Increase if collisions not penalized enough
self.EFFICIENCY_WEIGHT = 0.2    # Increase if time matters more

# Normalization
self.MAX_EXPECTED_DISTANCE = 20.0  # Adjust based on actual scene size
```

## Summary

**Problem:** Rewards were -120 per step, making training impossible

**Solution:** Redesigned reward calculator with proper normalization

**Result:** All rewards in range [-1, +1], comparable across episodes

**Test:** Run `test_environment_basic.py` to verify

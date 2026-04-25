# Diagnosing Agent Behavior

## Current Problem

Agent oscillates Z between 1.0 and 0.8, never moves in X or Y:

```
Step 2: move_drone_to [0, 0, 1.0]   # Up
Step 4: move_drone_to [0, 0, 0.8]   # Down
Step 6: move_drone_to [0, 0, 1.0]   # Up
Step 8: move_drone_to [0, 0, 0.8]   # Down
```

**Questions:**
1. What is the agent seeing in scan_area?
2. Why does it think moving up/down helps?
3. Why never move in X or Y?

## How to Diagnose

### Step 1: Run with Debug Mode

```bash
python inference_drone.py --task task1 --debug
```

This will show:
- What scan_area returns (detections)
- What coordinates agent chooses
- LLM's raw response (first 5 steps)

### Step 2: Check Scan Results

Look for patterns in the output:

```
[STEP 1] tool=scan_area
         └─ target: dir=center alt=above dist=5.2m
         
[STEP 2] tool=move_drone_to → [0, 0, 1.0]
```

**Questions to answer:**
- Does scan_area detect the target?
- What direction/altitude does it report?
- Does agent understand the coordinates?

### Step 3: Analyze Agent Logic

**Possible issues:**

#### Issue A: Agent Doesn't Understand Coordinates

**Symptom:** Always sets X=0, Y=0

**Cause:** Prompt unclear about how to use direction info

**Fix:** Improve prompt with examples:
```
If scan shows "direction: center, altitude: above":
→ Target is straight ahead (+Y) and up (+Z)
→ Move to: [0, 5, 1.0] (forward 5m, up to 1m)

If scan shows "direction: right, altitude: level":
→ Target is to the right (+X) at same height
→ Move to: [5, 0, 1.0] (right 5m, maintain height)
```

#### Issue B: Agent Sees No Detections

**Symptom:** scan_area returns empty

**Cause:** Camera not seeing target (wrong angle, too far, etc.)

**Fix:** Check camera setup, target placement

#### Issue C: Agent Confused by Altitude

**Symptom:** Oscillates Z, trying to find target

**Cause:** Thinks changing altitude will help see target

**Fix:** Clarify that altitude changes position, not view angle

#### Issue D: Agent Doesn't Trust Scan

**Symptom:** Scans repeatedly, doesn't commit to movement

**Cause:** Uncertain about information

**Fix:** Add confidence to prompt, encourage decisive action

## Detailed Diagnosis Steps

### 1. Check What Agent Sees

Run with debug and look at first scan:

```
[STEP 1] tool=scan_area
         └─ target: dir=center alt=above dist=5.2m
```

**If detections present:**
- Agent CAN see target
- Problem is in decision-making

**If no detections:**
- Agent CANNOT see target
- Problem is in vision/camera setup

### 2. Check Agent's Interpretation

Look at move command after scan:

```
[STEP 2] tool=move_drone_to → [0, 0, 1.0]
```

**Analysis:**
- X=0: Not moving left/right
- Y=0: Not moving forward/backward
- Z=1.0: Only moving up

**This means:**
- Agent saw "altitude: above"
- Interpreted as "move up"
- Ignored "direction: center" (should move forward)

### 3. Check Prompt Understanding

The prompt says:
```
- If target is "center", move forward in +Y direction
- If target is "above", increase Z to 1.0-1.5m
```

But agent only does Z, not Y!

**Root cause:** Agent interprets instructions as:
- "above" → ONLY change Z
- "center" → ONLY change Y

**Should be:**
- "above" AND "center" → change BOTH Y and Z

### 4. Test with Explicit Examples

Add to prompt:

```
EXAMPLES:

Scan result: {"direction": "center", "altitude": "above", "distance": 5.0}
Correct action: {"tool": "move_drone_to", "args": {"drone_id": 0, "x": 0, "y": 5, "z": 1.0}}
Explanation: Target is straight ahead (+Y) and above (+Z), so move forward AND up

Scan result: {"direction": "right", "altitude": "level", "distance": 3.0}
Correct action: {"tool": "move_drone_to", "args": {"drone_id": 0, "x": 3, "y": 0, "z": 1.0}}
Explanation: Target is to the right (+X) at same height, so move right

Scan result: {"direction": "left", "altitude": "below", "distance": 4.0}
Correct action: {"tool": "move_drone_to", "args": {"drone_id": 0, "x": -4, "y": 0, "z": 0.5}}
Explanation: Target is to the left (-X) and below (-Z), so move left AND down
```

## Quick Test

To verify if it's a prompt issue vs environment issue:

### Test 1: Hardcoded Action

```python
# In test script, force agent to move forward:
action = {"name": "move_drone_to", "arguments": {"drone_id": 0, "x": 0, "y": 5, "z": 1.0}}
```

**If drone moves correctly:**
- Environment works ✅
- Problem is LLM decision-making

**If drone doesn't move:**
- Environment issue ❌
- Check PID controller

### Test 2: Simple Prompt

Simplify prompt to bare minimum:

```
You control a drone. Target is ahead.
To move forward: set Y positive (e.g., y=5)
To move right: set X positive (e.g., x=5)
To move up: set Z to 1.0

Current position: [0, 0, 0.1]
Target position: [0, 5, 1.0]

What coordinates should you move to?
```

**If agent gives correct answer:**
- Agent CAN understand coordinates
- Original prompt too complex

**If agent still wrong:**
- Model too weak for task
- Need different model or training

## Summary

**The issue is likely:**

1. **Prompt ambiguity** - Agent doesn't understand it should change MULTIPLE coordinates
2. **Model weakness** - 7B model struggles with spatial reasoning
3. **Lack of examples** - No concrete examples in prompt

**Next steps:**

1. Run with `--debug` flag
2. Check what scan_area returns
3. Check what coordinates agent chooses
4. Add explicit examples to prompt
5. If still fails, model needs training (not just prompting)

**Remember:** Untrained models make mistakes. That's why we need RL training!

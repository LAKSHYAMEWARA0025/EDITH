# GRPO Seed Synchronization Fix

## The Problem: Map Desync in GRPO Training

### What Was Happening
GRPO (Group Relative Policy Optimization) requires comparing multiple LLM actions taken in **the exact same environment state**. The algorithm works by:

1. Taking 4 different action sequences in the same scenario
2. Ranking them by reward
3. Computing relative advantages (which action was better/worse)
4. Updating the policy based on these comparisons

**The Bug:** When requesting 4 parallel rollouts, each `/reset` call generated a **completely different random map**. This meant:
- Rollout 1: Easy map with 2 obstacles
- Rollout 2: Hard map with 5 obstacles  
- Rollout 3: Medium map with 3 obstacles
- Rollout 4: Easy map with 1 obstacle

GRPO was comparing apples to oranges, corrupting the advantage calculations and destroying learning gradients.

---

## The Solution: Seed Synchronization

### Backend Changes (FastAPI Server)

#### 1. Updated `/reset` Endpoint
```python
@app.post("/reset")
def reset(
    request: Optional[ResetRequest] = None,
    x_session_id: Optional[str] = Header(None),
    seed: Optional[int] = None
):
    """Reset with optional seed for deterministic map generation."""
    # ... 
    if seed is not None:
        state, info = env_instance.reset(seed=seed)
```

**New Parameters:**
- `seed` (optional): Integer seed for deterministic obstacle/target placement
- Can be passed via JSON body or query parameter

#### 2. Updated `EDITHDroneEnv.reset()`
```python
def reset(self, seed=None):
    """Reset with optional seed."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    # ... rest of reset logic
```

**Effect:** When seed is provided, all randomization becomes deterministic:
- Obstacle count selection
- Obstacle positions
- Target positions
- Battery levels (Task 2)

---

## Frontend Changes (Training Script)

### Update 1: Client Reset Method

```python
class EDITHClient:
    def reset(self, seed=None):
        """Reset environment with optional seed."""
        payload = {}
        if seed is not None:
            payload["seed"] = seed
        
        response = requests.post(
            f"{self.server_url}/reset",
            json=payload,
            headers={"x-session-id": self.session_id}
        )
        # ... handle response
```

### Update 2: GRPO Reward Function

```python
async def grpo_reward_function(prompts, **kwargs):
    """Collect 4 parallel rollouts with SAME seed for GRPO."""
    
    # Generate ONE seed per GRPO batch (all 4 rollouts use this)
    batch_seed = random.randint(0, 1_000_000)
    
    async def run_episode_with_seed(prompt, client):
        # All 4 clients reset with SAME seed
        state = await client.reset(seed=batch_seed)
        # ... run episode
        return reward, response, metrics
    
    # Create 4 parallel tasks with same seed
    tasks = [
        run_episode_with_seed(prompt, client)
        for prompt, client in zip(prompts, clients)
    ]
    
    results = await asyncio.gather(*tasks)
    # Now all 4 rollouts faced the SAME map!
```

---

## How It Works

### GRPO Training Flow (Fixed)

```
Batch 1:
  Generate seed: 42
  ├─ Rollout 1: reset(seed=42) → Map A → Action sequence 1 → Reward: 0.3
  ├─ Rollout 2: reset(seed=42) → Map A → Action sequence 2 → Reward: 0.7
  ├─ Rollout 3: reset(seed=42) → Map A → Action sequence 3 → Reward: 0.5
  └─ Rollout 4: reset(seed=42) → Map A → Action sequence 4 → Reward: 0.2
  
  GRPO compares: All faced Map A, so advantages are accurate!
  Best action: Sequence 2 (reward 0.7)
  Worst action: Sequence 4 (reward 0.2)

Batch 2:
  Generate seed: 1337
  ├─ Rollout 1: reset(seed=1337) → Map B → ...
  └─ ... (different map, but all 4 rollouts see Map B)
```

### Key Properties

✅ **Deterministic within batch**: All 4 rollouts see identical map  
✅ **Random across batches**: Each batch gets unique challenging scenario  
✅ **Accurate advantages**: GRPO can correctly identify which actions were better  
✅ **Curriculum learning preserved**: Still trains on diverse scenarios over time

---

## Testing

### Run Seed Sync Tests
```bash
# Start Docker container
cd EDITH
docker run -p 7860:7860 edith-mission-commander:latest

# Run test suite
python tests/test_seed_sync.py
```

### Expected Output
```
✅ Test 1: Same seed → identical maps (4/4 match)
✅ Test 2: Different seeds → varied maps
✅ Test 3: GRPO batch scenario → all rollouts identical
```

---

## Impact on Training

### Before Fix
- GRPO advantage calculations: **Corrupted** ❌
- Learning signal: **Noisy and unreliable** ❌
- Training progress: **Slow or divergent** ❌

### After Fix
- GRPO advantage calculations: **Accurate** ✅
- Learning signal: **Clean and consistent** ✅
- Training progress: **Stable and efficient** ✅

---

## Deployment Checklist

- [x] Backend: Add seed parameter to `/reset` endpoint
- [x] Backend: Update `EDITHDroneEnv.reset()` to accept seed
- [x] Backend: Set `random.seed()` and `np.random.seed()` when provided
- [x] Tests: Create `test_seed_sync.py` for validation
- [x] Docs: Document the fix and usage
- [ ] Frontend: Update `EDITHClient.reset()` in training script
- [ ] Frontend: Update `grpo_reward_function()` to use batch seeds
- [ ] Deploy: Push to HF Space
- [ ] Verify: Run seed sync tests on deployed server

---

## API Examples

### Without Seed (Random Map)
```bash
curl -X POST http://localhost:7860/reset \
  -H "x-session-id: session-1"
# Returns: Random map each time
```

### With Seed (Deterministic Map)
```bash
curl -X POST http://localhost:7860/reset \
  -H "x-session-id: session-1" \
  -H "Content-Type: application/json" \
  -d '{"seed": 42}'
# Returns: Same map every time with seed=42
```

### GRPO Batch (4 Parallel Sessions, Same Seed)
```python
import requests
import concurrent.futures

seed = 12345
sessions = [f"grpo-batch-{i}" for i in range(4)]

def reset_session(session_id):
    return requests.post(
        "http://localhost:7860/reset",
        json={"seed": seed},
        headers={"x-session-id": session_id}
    )

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(reset_session, sessions))

# All 4 sessions now have identical maps!
```

---

## Notes

- Seed only affects **environment randomization** (obstacles, targets, battery)
- Seed does **NOT** affect LLM generation (that's controlled by temperature)
- Each GRPO batch should use a **different seed** for curriculum diversity
- Seed range: Use `random.randint(0, 1_000_000)` for sufficient variety

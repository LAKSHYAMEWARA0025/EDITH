# EDITH - Local Setup Instructions (Person A)

## Current Status

✅ PyBullet wheel extracted: `Backup/pybullet-3.2.7-cp310-cp310-win_amd64.whl`  
✅ Folder structure created: `core/`, `wrapper/`, `server/`, `tests/`  
✅ Setup scripts created  
⏭️ Ready to install and test

---

## Step-by-Step Setup (Next 30 Minutes)

### Step 1: Run Setup Script (10 minutes)

```bash
cd EDITH
setup_local.bat
```

**What this does:**
1. Creates `venv` virtual environment
2. Activates it
3. Installs PyBullet from local wheel (no compiler needed!)
4. Installs other dependencies from `requirements.txt`

**Expected output:**
```
[1/6] Checking Python version...
Python 3.10.11
[2/6] Creating virtual environment...
+ Virtual environment created
[3/6] Activating virtual environment...
+ Activated
[4/6] Upgrading pip...
+ Pip upgraded
[5/6] Installing PyBullet from local wheel...
+ PyBullet installed
[6/6] Installing other dependencies...
+ Dependencies installed
```

---

### Step 2: Install gym-pybullet-drones (10 minutes)

```bash
# Make sure venv is active
venv\Scripts\activate.bat

# Clone the repo
git clone https://github.com/utiasDSL/gym-pybullet-drones.git
cd gym-pybullet-drones

# IMPORTANT: Use main branch
git checkout main

# Install in editable mode
pip install -e .

# Go back to EDITH folder
cd ..
```

**Expected output:**
```
Cloning into 'gym-pybullet-drones'...
...
Successfully installed gym-pybullet-drones-2.1.0
```

---

### Step 3: Test GUI Mode (5 minutes)

```bash
python test_gui.py
```

**What this does:**
- Opens PyBullet GUI window
- Spawns a drone at [0, 0, 1]
- Flies in a simple pattern:
  1. Hover at spawn (5 sec)
  2. Move to [2, 0, 1.5] (5 sec)
  3. Move to [2, 2, 1.5] (5 sec)
  4. Return to [0, 0, 1.0] (5 sec)

**Expected output:**
```
==========================================
EDITH - GUI Mode Test
==========================================

[1/4] Importing gym-pybullet-drones...
✓ Imports successful

[2/4] Creating environment with GUI...
✓ Environment created
  → PyBullet GUI window should be open now

[3/4] Resetting environment...
✓ Environment reset
  Drone spawned at: [0. 0. 1.]

[4/4] Flying drone in a simple pattern...
  → Flying to [0.0, 0.0, 1.0]...
  → Flying to [2.0, 0.0, 1.5]...
  → Flying to [2.0, 2.0, 1.5]...
  → Flying to [0.0, 0.0, 1.0]...

✓ Flight pattern complete!

==========================================
✓ GUI TEST PASSED
==========================================

Your local setup is working correctly!
You can now start building the environment.
```

**You should see:**
- A 3D window with a checkered ground
- A small quadrotor drone
- The drone flying in the pattern described

---

### Step 4: Organize Existing Files (5 minutes)

Person B already created some files in the root. Let's organize them:

```bash
# Move Person A files to core/
move scene_manager.py core\
move battery_simulator.py core\
move collision_detector.py core\
move vision_system.py core\
move pybullet_bridge.py core\

# Move Person B files to wrapper/
move edith_env.py wrapper\
move environment.py wrapper\
move reward_calculator.py wrapper\
move episode_tracker.py wrapper\

# Keep in root
# - openenv.yaml
# - requirements.txt
# - README.md
# - test_gui.py
# - setup_local.bat
```

---

## Troubleshooting

### Issue: "Python not found"
**Solution:** Make sure Python 3.10 is installed and in PATH

### Issue: "PyBullet wheel not found"
**Solution:** Check that `Backup/pybullet-3.2.7-cp310-cp310-win_amd64.whl` exists (not .zip)

### Issue: "gym-pybullet-drones import fails"
**Solution:** 
1. Make sure you're on `main` branch (not `master`)
2. Run `pip install -e .` inside gym-pybullet-drones folder

### Issue: "GUI window doesn't open"
**Solution:** This is expected on some systems. The test will still pass if imports work.

### Issue: "Drone falls through ground"
**Solution:** This is a physics issue, not a setup issue. The test should still complete.

---

## What's Next (After Setup)

### Person A Tasks (You):

1. **Review existing files in `core/`:**
   - Check what Person B already implemented
   - Identify what needs to be completed

2. **Start with `core/scene_manager.py`:**
   - Implement `create_colored_obstacle()` using exact HSV values
   - Implement `create_colored_target()`
   - Test in GUI mode

3. **Move to `core/battery_simulator.py`:**
   - Implement battery drain logic
   - Test drain rates

4. **Continue with remaining core modules**

### Testing Your Work:

```bash
# Test individual modules
python -c "from core.scene_manager import SceneManager; print('OK')"

# Test with GUI
python test_gui.py

# Later: Unit tests
python -m pytest tests/test_scene.py
```

---

## File Organization Summary

```
EDITH/
├── core/                          # Your work (Person A)
│   ├── scene_manager.py           # Scene creation
│   ├── battery_simulator.py       # Battery physics
│   ├── collision_detector.py      # Collision detection
│   ├── vision_system.py           # Camera + OpenCV
│   ├── pybullet_bridge.py         # PyBullet utilities
│   └── tools.py                   # 8 tool functions (to create)
│
├── wrapper/                       # Person B's work
│   ├── edith_env.py               # Main environment
│   ├── environment.py             # Base classes
│   ├── reward_calculator.py       # Rewards
│   └── episode_tracker.py         # Episode data
│
├── gym-pybullet-drones/           # External dependency (cloned)
├── venv/                          # Virtual environment
│
├── openenv.yaml                   # OpenEnv manifest
├── requirements.txt               # Dependencies
├── setup_local.bat                # Setup script
├── test_gui.py                    # GUI test
└── README.md                      # Documentation
```

---

## Ready to Start?

**Run these commands now:**

```bash
cd EDITH
setup_local.bat
# Wait for it to complete...

# Then:
git clone https://github.com/utiasDSL/gym-pybullet-drones.git
cd gym-pybullet-drones
git checkout main
pip install -e .
cd ..

# Test:
python test_gui.py
```

**If test passes → You're ready to code!** 🚁

**If test fails → Check troubleshooting section above**

---

**Estimated time:** 30 minutes  
**After this:** Start implementing `core/scene_manager.py`

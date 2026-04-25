"""
Integration test - Run on friend's laptop with PyBullet working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("EDITH Integration Test")
print("=" * 60)

# Test 1: Imports
print("\n[1/5] Testing imports...")
try:
    from wrapper.edith_env import EDITHDroneEnv
    print("✓ Imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    exit(1)

# Test 2: Environment creation
print("\n[2/5] Creating environment...")
try:
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=True)
    print("✓ Environment created")
except Exception as e:
    print(f"✗ Environment creation failed: {e}")
    exit(1)

# Test 3: Reset
print("\n[3/5] Testing reset...")
try:
    state = env.reset()
    print(f"✓ Reset successful")
    print(f"  Obstacles: {len(env.scene_manager.obstacle_ids)}")
    print(f"  Targets: {len(env.scene_manager.target_ids)}")
except Exception as e:
    print(f"✗ Reset failed: {e}")
    exit(1)

# Test 4: Tool functions
print("\n[4/5] Testing tools...")
try:
    from core.tools import get_drone_status, scan_area, get_mission_status
    
    status = get_drone_status(env.env, 0)
    print(f"✓ get_drone_status: {status['position']}")
    
    scan = scan_area(env.env, 0)
    print(f"✓ scan_area: {scan['total_found']} objects detected")
    
    mission = get_mission_status(env.env)
    print(f"✓ get_mission_status: {mission['total_targets']} targets")
except Exception as e:
    print(f"✗ Tools failed: {e}")
    exit(1)

# Test 5: Step
print("\n[5/5] Testing step...")
try:
    action = {"tool": "get_drone_status", "args": {"drone_id": 0}}
    result = env.step(action)
    print(f"✓ Step successful")
    print(f"  Reward: {result['reward']}")
except Exception as e:
    print(f"✗ Step failed: {e}")
    exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nClose the PyBullet GUI window to exit.")

input("Press Enter to close...")

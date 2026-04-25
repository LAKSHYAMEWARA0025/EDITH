"""
Verify scan_area works when drone is at proper height
Test hypothesis: scan_area returns 0 because drone is too low at spawn
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("SCAN_AREA VERIFICATION TEST")
print("=" * 60)

from wrapper.edith_env import EDITHDroneEnv
from core.tools import get_drone_status, scan_area
import time

# Create environment with GUI
print("\n[1/4] Creating environment with GUI...")
env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=True)
print("✓ Environment created")

# Reset
print("\n[2/4] Resetting environment...")
env.reset()
print(f"✓ Reset complete")
print(f"  Obstacles: {len(env.scene_manager.obstacle_ids)}")
print(f"  Targets: {len(env.scene_manager.target_ids)}")

# Test 1: Scan at spawn height (should see nothing)
print("\n[3/4] Test 1: Scan at spawn height...")
status = get_drone_status(env, 0)
if 'error' in status:
    print(f"  ERROR getting drone status: {status['error']}")
    print("  Trying to get position directly from env...")
    drone_pos = env.env._getDroneStateVector(0)[0:3]
    print(f"  Drone position: {drone_pos.tolist()}")
    print(f"  Drone height (z): {drone_pos[2]:.3f}m")
else:
    print(f"  Drone position: {status['position']}")
    print(f"  Drone height (z): {status['position'][2]:.3f}m")
    drone_pos = status['position']

scan1 = scan_area(env, 0)
print(f"  Objects detected: {scan1['total_found']}")
print(f"  → Hypothesis: Should see 0 objects (drone too low)")

# Test 2: Manually move drone UP and scan again
print("\n[4/4] Test 2: Move drone to 2m height and scan...")
print("  Manually setting drone to [0, 0, 2.0]...")

# Directly set drone position (bypass physics for test)
import pybullet as p
drone_id = env.env.DRONE_IDS[0]
p.resetBasePositionAndOrientation(
    drone_id,
    [0, 0, 2.0],  # 2 meters high
    [0, 0, 0, 1],  # orientation
    physicsClientId=env.env.CLIENT
)

# Wait a moment for physics to settle
time.sleep(0.1)

# Check new position
status2 = get_drone_status(env, 0)
if 'error' in status2:
    drone_pos2 = env.env._getDroneStateVector(0)[0:3]
    print(f"  New drone position: {drone_pos2.tolist()}")
    print(f"  New drone height (z): {drone_pos2[2]:.3f}m")
else:
    print(f"  New drone position: {status2['position']}")
    print(f"  New drone height (z): {status2['position'][2]:.3f}m")
    drone_pos2 = status2['position']

# Scan again
scan2 = scan_area(env, 0)
print(f"  Objects detected: {scan2['total_found']}")
print(f"  → Hypothesis: Should see {len(env.scene_manager.obstacle_ids) + len(env.scene_manager.target_ids)} objects (drone at good height)")

if scan2['total_found'] > 0:
    print("\n  Detections:")
    for det in scan2['detections']:
        print(f"    - {det['type']} ({det['color']}): area={det['area']} pixels")

# Summary
print("\n" + "=" * 60)
print("VERIFICATION RESULTS:")
print("=" * 60)
drone_z1 = drone_pos[2] if isinstance(drone_pos, list) else drone_pos[2]
print(f"At spawn height ({drone_z1:.3f}m): {scan1['total_found']} objects")
print(f"At 2.0m height: {scan2['total_found']} objects")

if scan1['total_found'] == 0 and scan2['total_found'] > 0:
    print("\n✅ HYPOTHESIS CONFIRMED!")
    print("   scan_area WORKS - drone just needs to be higher")
elif scan1['total_found'] > 0:
    print("\n⚠️  UNEXPECTED: Drone sees objects at spawn height")
elif scan2['total_found'] == 0:
    print("\n❌ ISSUE: Drone still sees nothing at 2m height")
    print("   Camera or vision system may have a problem")
else:
    print("\n❓ UNCLEAR RESULT")

print("\nClose the PyBullet GUI window to exit.")
input("Press Enter to close...")

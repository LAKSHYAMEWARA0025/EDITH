"""
Basic Environment Test - Hardcoded Actions

Tests the environment with simple hardcoded actions to verify:
1. Rewards are in reasonable range [-1, +1]
2. Drone can reach target
3. Physics works correctly
4. No crashes or errors
"""

import sys
sys.path.insert(0, '.')

from wrapper.edith_env import EDITHDroneEnv
import time

def test_basic_navigation():
    """Test basic navigation with hardcoded actions."""
    print("="*60)
    print("BASIC ENVIRONMENT TEST")
    print("="*60)
    
    # Create environment with GUI
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=True)
    
    # Reset
    state, _ = env.reset()
    print(f"\n[RESET] Initial state:")
    print(f"  Drone position: {state['drones']['0']['position']}")
    print(f"  Targets: {state['mission_status']['total_targets']}")
    print(f"  Time limit: {state['mission_status']['time_remaining']:.1f}s")
    
    # Get target location by scanning
    print(f"\n[STEP 1] Scanning area...")
    action1 = {"name": "scan_area", "arguments": {"drone_id": 0}}
    state, reward, done, _, info = env.step(action1)
    print(f"  Reward: {reward:+.3f}")
    print(f"  Detections: {info['tool_result'].get('total_found', 0)}")
    if info['tool_result'].get('detections'):
        for det in info['tool_result']['detections']:
            print(f"    - {det['type']}: direction={det.get('direction')}, altitude={det.get('altitude')}, distance={det.get('estimated_distance', 0):.1f}m")
    
    # Move to target (hardcoded reasonable position)
    print(f"\n[STEP 2] Moving to target area...")
    action2 = {"name": "move_drone_to", "arguments": {"drone_id": 0, "x": 0.0, "y": 5.0, "z": 1.0}}
    state, reward, done, _, info = env.step(action2)
    print(f"  Reward: {reward:+.3f}")
    print(f"  New position: {state['drones']['0']['position']}")
    print(f"  Tool result: {info['tool_result'].get('status')}")
    
    # Scan again
    print(f"\n[STEP 3] Scanning again...")
    action3 = {"name": "scan_area", "arguments": {"drone_id": 0}}
    state, reward, done, _, info = env.step(action3)
    print(f"  Reward: {reward:+.3f}")
    print(f"  Detections: {info['tool_result'].get('total_found', 0)}")
    
    # Move closer
    print(f"\n[STEP 4] Moving closer...")
    action4 = {"name": "move_drone_to", "arguments": {"drone_id": 0, "x": 0.0, "y": 8.0, "z": 1.0}}
    state, reward, done, _, info = env.step(action4)
    print(f"  Reward: {reward:+.3f}")
    print(f"  New position: {state['drones']['0']['position']}")
    
    # Continue for a few more steps
    total_reward = reward
    for step in range(5, 11):
        print(f"\n[STEP {step}] Moving forward...")
        y_pos = 8.0 + (step - 4) * 2.0
        action = {"name": "move_drone_to", "arguments": {"drone_id": 0, "x": 0.0, "y": y_pos, "z": 1.0}}
        state, reward, done, _, info = env.step(action)
        total_reward += reward
        print(f"  Reward: {reward:+.3f} (total: {total_reward:+.3f})")
        print(f"  Position: {state['drones']['0']['position']}")
        print(f"  Targets reached: {state['mission_status']['targets_reached']}/{state['mission_status']['total_targets']}")
        
        if done:
            print(f"\n[DONE] Episode finished!")
            print(f"  Total reward: {total_reward:+.3f}")
            print(f"  Targets reached: {state['mission_status']['targets_reached']}")
            break
    
    print(f"\n{'='*60}")
    print(f"TEST COMPLETE")
    print(f"{'='*60}")
    print(f"Total steps: {step}")
    print(f"Total reward: {total_reward:+.3f}")
    print(f"Average reward per step: {total_reward/step:+.3f}")
    print(f"Targets reached: {state['mission_status']['targets_reached']}/{state['mission_status']['total_targets']}")
    print(f"\nReward Analysis:")
    print(f"  ✓ Rewards should be in range [-1, +1] per step")
    print(f"  ✓ Total reward should be reasonable (not -1000)")
    print(f"  ✓ Drone should move towards target")
    print(f"  ✓ No crashes or errors")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    test_basic_navigation()

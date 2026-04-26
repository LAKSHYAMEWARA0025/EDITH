"""
Test return_drone_home functionality specifically
"""

import sys
sys.path.insert(0, '.')

from wrapper.edith_env import EDITHDroneEnv
import time

def test_return_home():
    """Test return_drone_home functionality."""
    print("="*60)
    print("RETURN HOME TEST")
    print("="*60)
    
    # Create environment with GUI
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=True)
    
    # Reset
    state, _ = env.reset()
    initial_pos = state['drones']['0']['position']
    print(f"\n[RESET] Initial position: {initial_pos}")
    
    # Move drone away from home
    print(f"\n[STEP 1] Moving drone away from home...")
    action1 = {"name": "move_drone_to", "arguments": {"drone_id": 0, "x": 5.0, "y": 5.0, "z": 1.5}}
    state, reward, done, _, info = env.step(action1)
    new_pos = state['drones']['0']['position']
    print(f"  Moved to: {new_pos}")
    print(f"  Tool result: {info['tool_result']}")
    
    # Wait a moment to see movement
    time.sleep(2)
    
    # Get current position after movement
    state = env.state()
    current_pos = state['drones']['0']['position']
    print(f"  Current position after movement: {current_pos}")
    
    # Now call return_drone_home
    print(f"\n[STEP 2] Calling return_drone_home...")
    action2 = {"name": "return_drone_home", "arguments": {"drone_id": 0}}
    state, reward, done, _, info = env.step(action2)
    print(f"  Tool result: {info['tool_result']}")
    print(f"  Home position: {info['tool_result'].get('home_position')}")
    print(f"  Current position: {info['tool_result'].get('current_position')}")
    print(f"  Distance to home: {info['tool_result'].get('distance_to_home')}")
    
    # Check position after return home command
    state = env.state()
    after_home_pos = state['drones']['0']['position']
    print(f"  Position after return_home: {after_home_pos}")
    
    # Wait to see if drone actually moves
    print(f"\n[WAITING] Letting drone move for 3 seconds...")
    time.sleep(3)
    
    # Check final position
    state = env.state()
    final_pos = state['drones']['0']['position']
    print(f"  Final position: {final_pos}")
    
    # Analysis
    print(f"\n{'='*60}")
    print(f"ANALYSIS")
    print(f"{'='*60}")
    print(f"Initial position:     {initial_pos}")
    print(f"After move away:      {current_pos}")
    print(f"After return_home:    {after_home_pos}")
    print(f"Final position:       {final_pos}")
    
    # Calculate distances
    import numpy as np
    home_pos = info['tool_result'].get('home_position', [0, 0, 0.1125])
    dist_to_home = np.linalg.norm(np.array(final_pos) - np.array(home_pos))
    print(f"Distance to home:     {dist_to_home:.3f}m")
    
    if dist_to_home < 0.5:
        print("✓ SUCCESS: Drone returned home!")
    else:
        print("✗ FAILED: Drone did not return home")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    test_return_home()
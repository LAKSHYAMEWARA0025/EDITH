"""
Quick test to debug drone movement issue
"""
import sys
sys.path.insert(0, '.')

from wrapper.edith_env import EDITHDroneEnv

# Create environment
env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=True)

# Reset
state, _ = env.reset()
print(f"Initial state: {state}")
print(f"Initial target positions: {env.target_positions}")

# Test move_drone_to
action1 = {
    "name": "move_drone_to",
    "arguments": {
        "drone_id": 0,
        "x": 5.0,
        "y": 3.0,
        "z": 1.5
    }
}

print("\n=== Executing move_drone_to(5.0, 3.0, 1.5) ===")
state, reward, done, _, info = env.step(action1)
print(f"Tool result: {info['tool_result']}")
print(f"Target positions after move: {env.target_positions}")
print(f"Drone position: {state['drones']['0']['position']}")
print(f"Reward: {reward}")

# Wait a bit
input("\nPress Enter to continue...")

# Try another move
action2 = {
    "name": "move_drone_to",
    "arguments": {
        "drone_id": 0,
        "x": 10.0,
        "y": 5.0,
        "z": 1.5
    }
}

print("\n=== Executing move_drone_to(10.0, 5.0, 1.5) ===")
state, reward, done, _, info = env.step(action2)
print(f"Tool result: {info['tool_result']}")
print(f"Target positions after move: {env.target_positions}")
print(f"Drone position: {state['drones']['0']['position']}")
print(f"Reward: {reward}")

input("\nPress Enter to exit...")

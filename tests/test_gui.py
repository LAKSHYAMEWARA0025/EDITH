#!/usr/bin/env python3
"""
Test script to verify gym-pybullet-drones works with GUI on local machine.
This tests that the installation is correct before building the environment.
"""

import numpy as np
import sys

def test_gui_mode():
    """Test PyBullet GUI mode with a simple drone flight."""
    print("=" * 60)
    print("EDITH - GUI Mode Test")
    print("=" * 60)
    print("\nThis will open a PyBullet GUI window.")
    print("Press Ctrl+C to stop the simulation.\n")
    
    try:
        # Import gym-pybullet-drones
        print("[1/4] Importing gym-pybullet-drones...")
        from gym_pybullet_drones.envs.HoverAviary import HoverAviary
        from gym_pybullet_drones.utils.enums import DroneModel, Physics
        from gym_pybullet_drones.control.DSLPIDControl import DSLPIDControl
        import pybullet as p
        print("✓ Imports successful")
        
        # Create environment with GUI
        print("\n[2/4] Creating environment with GUI...")
        env = HoverAviary(
            drone_model=DroneModel.CF2X,
            initial_xyzs=np.array([[0.0, 0.0, 1.0]]),
            physics=Physics.PYB,
            gui=True,  # Enable GUI
            record=False
        )
        print("✓ Environment created")
        print("  → PyBullet GUI window should be open now")
        
        # Reset environment
        print("\n[3/4] Resetting environment...")
        obs, info = env.reset()
        print("✓ Environment reset")
        print(f"  Drone spawned at: {obs[0, 0:3]}")
        
        # Initialize PID controller
        ctrl = DSLPIDControl(drone_model=DroneModel.CF2X)
        
        # Fly in a simple pattern
        print("\n[4/4] Flying drone in a simple pattern...")
        print("  Watch the GUI window - drone will:")
        print("  1. Hover at spawn (5 seconds)")
        print("  2. Move to [2, 0, 1.5] (5 seconds)")
        print("  3. Move to [2, 2, 1.5] (5 seconds)")
        print("  4. Return to [0, 0, 1.0] (5 seconds)")
        print("\n  Press Ctrl+C to stop early\n")
        
        waypoints = [
            ([0.0, 0.0, 1.0], 240),   # Hover at spawn (5 sec at 48Hz)
            ([2.0, 0.0, 1.5], 240),   # Move right
            ([2.0, 2.0, 1.5], 240),   # Move forward
            ([0.0, 0.0, 1.0], 240),   # Return home
        ]
        
        for target_pos, steps in waypoints:
            print(f"  → Flying to {target_pos}...")
            target = np.array(target_pos)
            
            for step in range(steps):
                # Get current state
                drone_pos, drone_orn = p.getBasePositionAndOrientation(
                    env.DRONE_IDS[0],
                    physicsClientId=env.CLIENT
                )
                drone_vel, drone_ang_vel = p.getBaseVelocity(
                    env.DRONE_IDS[0],
                    physicsClientId=env.CLIENT
                )
                
                # Compute PID control
                state = np.hstack([drone_pos, drone_orn, drone_vel, drone_ang_vel])
                rpm, _, _ = ctrl.computeControlFromState(
                    control_timestep=1.0/48.0,
                    state=state,
                    target_pos=target,
                    target_rpy=np.zeros(3)
                )
                
                # Apply action
                action = np.array([rpm])
                obs, reward, terminated, truncated, info = env.step(action)
                
                if terminated or truncated:
                    break
        
        print("\n✓ Flight pattern complete!")
        print("\nClosing environment...")
        env.close()
        
        print("\n" + "=" * 60)
        print("✓ GUI TEST PASSED")
        print("=" * 60)
        print("\nYour local setup is working correctly!")
        print("You can now start building the environment.\n")
        return True
        
    except ImportError as e:
        print(f"\n✗ Import failed: {e}")
        print("\nACTION REQUIRED:")
        print("  Install gym-pybullet-drones:")
        print("  1. git clone https://github.com/utiasDSL/gym-pybullet-drones.git")
        print("  2. cd gym-pybullet-drones")
        print("  3. git checkout main")
        print("  4. pip install -e .")
        return False
        
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user (Ctrl+C)")
        print("  Environment was working - you can proceed")
        if 'env' in locals():
            env.close()
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        if 'env' in locals():
            env.close()
        return False

if __name__ == "__main__":
    success = test_gui_mode()
    sys.exit(0 if success else 1)

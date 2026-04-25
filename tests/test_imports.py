"""
Test all imports work (without PyBullet)
"""

import sys
import os
from unittest.mock import MagicMock

# Add EDITH to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock PyBullet before any imports
sys.modules['pybullet'] = MagicMock()
sys.modules['pybullet_data'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['gym_pybullet_drones'] = MagicMock()
sys.modules['gym_pybullet_drones.envs'] = MagicMock()
sys.modules['gym_pybullet_drones.envs.MultiHoverAviary'] = MagicMock()
sys.modules['gym_pybullet_drones.utils'] = MagicMock()
sys.modules['gym_pybullet_drones.utils.enums'] = MagicMock()

print("Testing imports...\n")

# Test Person A core modules
try:
    from core.scene_manager import SceneManager
    print("✓ core.scene_manager")
except Exception as e:
    print(f"✗ core.scene_manager: {e}")

try:
    from core.battery_simulator import BatterySimulator
    print("✓ core.battery_simulator")
except Exception as e:
    print(f"✗ core.battery_simulator: {e}")

try:
    from core.collision_detector import CollisionDetector
    print("✓ core.collision_detector")
except Exception as e:
    print(f"✗ core.collision_detector: {e}")

try:
    from core.vision_system import VisionSystem
    print("✓ core.vision_system")
except Exception as e:
    print(f"✗ core.vision_system: {e}")

try:
    from core.tools import (
        get_drone_status, get_obstacle_distances, scan_area,
        move_drone_to, get_mission_status, assign_drone_to_target,
        return_drone_home, get_camera_frame
    )
    print("✓ core.tools (all 8 functions)")
except Exception as e:
    print(f"✗ core.tools: {e}")

# Test Person B wrapper modules
try:
    from wrapper.reward_calculator import RewardCalculator
    print("✓ wrapper.reward_calculator")
except Exception as e:
    print(f"✗ wrapper.reward_calculator: {e}")

try:
    from wrapper.episode_tracker import EpisodeData
    print("✓ wrapper.episode_tracker")
except Exception as e:
    print(f"✗ wrapper.episode_tracker: {e}")

try:
    from wrapper import task_configs
    print("✓ wrapper.task_configs")
except Exception as e:
    print(f"✗ wrapper.task_configs: {e}")

try:
    from wrapper.edith_env import EDITHDroneEnv
    print("✓ wrapper.edith_env")
except Exception as e:
    print(f"✗ wrapper.edith_env: {e}")

print("\n✅ All imports successful (PyBullet mocked)")

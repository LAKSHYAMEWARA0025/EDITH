"""
Unit tests for Person A core modules (no PyBullet required)
Tests logic using mocks
"""

import numpy as np
import sys
from unittest.mock import Mock, MagicMock, patch

# Mock pybullet before importing our modules
sys.modules['pybullet'] = MagicMock()
sys.modules['cv2'] = MagicMock()

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.scene_manager import SceneManager
from core.battery_simulator import BatterySimulator
from core.collision_detector import CollisionDetector


def test_scene_manager_constants():
    """Test SceneManager has correct constants"""
    assert SceneManager.RGBA_RED == [1.0, 0.0, 0.0, 1.0]
    assert SceneManager.RGBA_GREEN == [0.0, 1.0, 0.0, 1.0]
    assert SceneManager.OBSTACLE_SIZE == 0.3
    assert SceneManager.TARGET_SIZE == 0.2
    print("✓ SceneManager constants correct")


def test_battery_simulator_reset():
    """Test battery reset"""
    battery = BatterySimulator()
    battery.reset(num_drones=3)
    
    assert len(battery.battery_levels) == 3
    assert all(level == 100.0 for level in battery.battery_levels.values())
    print("✓ Battery reset works")


def test_battery_simulator_drain():
    """Test battery drains with velocity"""
    battery = BatterySimulator()
    battery.reset(num_drones=1)
    
    # Simulate movement
    velocities = {0: np.array([1.0, 0.0, 0.0])}  # 1 m/s
    battery.step(velocities)
    
    assert battery.get_battery(0) < 100.0
    print(f"✓ Battery drain works: {battery.get_battery(0):.2f}%")


def test_battery_simulator_no_negative():
    """Test battery doesn't go negative"""
    battery = BatterySimulator()
    battery.battery_levels = {0: 0.5}
    
    # Drain more than available
    velocities = {0: np.array([10.0, 10.0, 10.0])}
    battery.step(velocities)
    
    assert battery.get_battery(0) >= 0.0
    print("✓ Battery clamped to 0")


def test_collision_detector_init():
    """Test CollisionDetector initializes"""
    mock_client = 123
    detector = CollisionDetector(mock_client)
    assert detector.client_id == 123
    print("✓ CollisionDetector init works")


def test_scene_manager_tracking():
    """Test SceneManager tracks object IDs"""
    mock_client = 123
    scene = SceneManager(mock_client)
    
    assert scene.obstacle_ids == []
    assert scene.target_ids == []
    print("✓ SceneManager tracking works")


def test_randomization_methods_exist():
    """Test randomization methods exist"""
    mock_client = 123
    scene = SceneManager(mock_client)
    
    assert hasattr(scene, 'randomize_scene_task1')
    assert hasattr(scene, 'randomize_scene_task2')
    assert hasattr(scene, 'randomize_scene_task3')
    print("✓ Randomization methods exist")


if __name__ == "__main__":
    print("Testing Person A Core Modules (No PyBullet)\n")
    
    test_scene_manager_constants()
    test_battery_simulator_reset()
    test_battery_simulator_drain()
    test_battery_simulator_no_negative()
    test_collision_detector_init()
    test_scene_manager_tracking()
    test_randomization_methods_exist()
    
    print("\n✅ All logic tests passed!")

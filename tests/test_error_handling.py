"""
Test comprehensive error handling in EDITH environment.
Verifies that the environment never crashes and handles all invalid inputs gracefully.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wrapper.edith_env import EDITHDroneEnv

def test_invalid_tool_name():
    """Test that invalid tool names return error dict, not crash."""
    print("\n[TEST 1] Invalid tool name...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {"name": "invalid_tool_xyz", "arguments": {}}
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"], "Should return error for invalid tool"
    assert "Unknown tool" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_missing_tool_name():
    """Test that missing tool name is handled."""
    print("\n[TEST 2] Missing tool name...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {"arguments": {"drone_id": 0}}  # No 'name' or 'tool' key
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Missing tool name" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_action_type():
    """Test that non-dict action is handled."""
    print("\n[TEST 3] Invalid action type...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = "this is a string not a dict"
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid action type" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_drone_id():
    """Test that out-of-range drone_id is handled."""
    print("\n[TEST 4] Invalid drone_id...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    # Test drone_id >= num_drones
    action = {"name": "get_drone_status", "arguments": {"drone_id": 5}}
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid drone_id" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")
    
    # Test negative drone_id
    action = {"name": "get_drone_status", "arguments": {"drone_id": -1}}
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid drone_id" in info["tool_result"]["error"]
    print(f"  ✓ Returned error for negative ID: {info['tool_result']['error']}")


def test_invalid_drone_id_type():
    """Test that non-integer drone_id is handled."""
    print("\n[TEST 5] Invalid drone_id type...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {"name": "get_drone_status", "arguments": {"drone_id": "not_a_number"}}
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid drone_id type" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_missing_required_argument():
    """Test that missing required arguments are handled."""
    print("\n[TEST 6] Missing required argument...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    # get_drone_status requires drone_id
    action = {"name": "get_drone_status", "arguments": {}}
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_coordinate_types():
    """Test that non-numeric coordinates are handled in move_drone_to."""
    print("\n[TEST 7] Invalid coordinate types...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {
        "name": "move_drone_to",
        "arguments": {"drone_id": 0, "x": "not_a_number", "y": 0, "z": 1}
    }
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid coordinate types" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_timeout():
    """Test that negative timeout is handled."""
    print("\n[TEST 8] Invalid timeout...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {
        "name": "move_drone_to",
        "arguments": {"drone_id": 0, "x": 1, "y": 1, "z": 1, "timeout": -5}
    }
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid timeout" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_target_id():
    """Test that out-of-range target_id is handled."""
    print("\n[TEST 9] Invalid target_id...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {
        "name": "assign_drone_to_target",
        "arguments": {"drone_id": 0, "target_id": 999}
    }
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid target_id" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_target_id_type():
    """Test that non-integer target_id is handled."""
    print("\n[TEST 10] Invalid target_id type...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {
        "name": "assign_drone_to_target",
        "arguments": {"drone_id": 0, "target_id": "not_a_number"}
    }
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid target_id type" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_invalid_camera_dimensions():
    """Test that invalid camera dimensions are handled."""
    print("\n[TEST 11] Invalid camera dimensions...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    # Test negative dimensions
    action = {
        "name": "get_camera_frame",
        "arguments": {"drone_id": 0, "width": -100, "height": 224}
    }
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid dimensions" in info["tool_result"]["error"]
    print(f"  ✓ Returned error for negative: {info['tool_result']['error']}")
    
    # Test too large dimensions
    action = {
        "name": "get_camera_frame",
        "arguments": {"drone_id": 0, "width": 5000, "height": 5000}
    }
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "too large" in info["tool_result"]["error"]
    print(f"  ✓ Returned error for too large: {info['tool_result']['error']}")


def test_invalid_arguments_type():
    """Test that non-dict arguments are handled."""
    print("\n[TEST 12] Invalid arguments type...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {"name": "get_drone_status", "arguments": "not_a_dict"}
    state, reward, done, truncated, info = env.step(action)
    
    assert "error" in info["tool_result"]
    assert "Invalid arguments type" in info["tool_result"]["error"]
    print(f"  ✓ Returned error: {info['tool_result']['error']}")


def test_extra_arguments():
    """Test that extra unexpected arguments don't crash."""
    print("\n[TEST 13] Extra unexpected arguments...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {
        "name": "get_drone_status",
        "arguments": {"drone_id": 0, "unexpected_arg": "value", "another_arg": 123}
    }
    state, reward, done, truncated, info = env.step(action)
    
    # Should either work (ignoring extra args) or return error
    # Either way, should not crash
    print(f"  ✓ Handled gracefully: {info['tool_result']}")


def test_none_arguments():
    """Test that None arguments are handled."""
    print("\n[TEST 14] None arguments...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    action = {"name": "get_drone_status", "arguments": None}
    state, reward, done, truncated, info = env.step(action)
    
    # Should handle None gracefully (convert to empty dict or error)
    print(f"  ✓ Handled None: {info['tool_result']}")


def test_valid_operations_still_work():
    """Test that valid operations still work after error handling changes."""
    print("\n[TEST 15] Valid operations still work...")
    env = EDITHDroneEnv(num_drones=1, task_type="task1", gui=False)
    env.reset()
    
    # Test valid get_drone_status
    action = {"name": "get_drone_status", "arguments": {"drone_id": 0}}
    state, reward, done, truncated, info = env.step(action)
    
    result = info["tool_result"]
    assert "error" not in result, f"Valid operation returned error: {result}"
    assert "position" in result
    assert "velocity" in result
    assert "battery_percentage" in result
    print(f"  ✓ get_drone_status works: position={result['position']}")
    
    # Test valid scan_area
    action = {"name": "scan_area", "arguments": {"drone_id": 0}}
    state, reward, done, truncated, info = env.step(action)
    
    result = info["tool_result"]
    assert "error" not in result, f"Valid operation returned error: {result}"
    assert "detections" in result
    print(f"  ✓ scan_area works: {result['total_found']} objects detected")
    
    # Test valid get_mission_status
    action = {"name": "get_mission_status", "arguments": {}}
    state, reward, done, truncated, info = env.step(action)
    
    result = info["tool_result"]
    assert "error" not in result, f"Valid operation returned error: {result}"
    assert "time_remaining" in result
    print(f"  ✓ get_mission_status works: {result['total_targets']} targets")


if __name__ == "__main__":
    print("=" * 60)
    print("EDITH ERROR HANDLING TEST")
    print("=" * 60)
    
    try:
        test_invalid_tool_name()
        test_missing_tool_name()
        test_invalid_action_type()
        test_invalid_drone_id()
        test_invalid_drone_id_type()
        test_missing_required_argument()
        test_invalid_coordinate_types()
        test_invalid_timeout()
        test_invalid_target_id()
        test_invalid_target_id_type()
        test_invalid_camera_dimensions()
        test_invalid_arguments_type()
        test_extra_arguments()
        test_none_arguments()
        test_valid_operations_still_work()
        
        print("\n" + "=" * 60)
        print("✅ ALL ERROR HANDLING TESTS PASSED!")
        print("=" * 60)
        print("\nEnvironment never crashes - all errors handled gracefully.")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

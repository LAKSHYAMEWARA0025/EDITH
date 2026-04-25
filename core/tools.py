"""
EDITH Core Tool Functions (Person A)

8 tool functions that provide the interface between the LLM agent and the drone environment.
These functions will be wrapped by Person B in the OpenEnv MCP interface.
"""

import numpy as np
import pybullet as p
import time
from .vision_system import VisionSystem
from .collision_detector import CollisionDetector


def get_drone_status(env, drone_id):
    """
    Get current status of a specific drone.
    
    Args:
        env: Environment instance with PyBullet client
        drone_id: Integer ID of the drone
    
    Returns:
        dict: {
            "position": [x, y, z],
            "velocity": [vx, vy, vz],
            "battery_percentage": float (0-100)
        }
    """
    try:
        # Get drone state from environment
        state = env._getDroneStateVector(drone_id)
        
        position = state[0:3].tolist()
        velocity = state[10:13].tolist()
        
        # Get battery from battery simulator
        battery = env.batteries[drone_id].get_percentage() if hasattr(env, 'batteries') else 100.0
        
        return {
            "position": position,
            "velocity": velocity,
            "battery_percentage": battery,
            "drone_id": drone_id
        }
    except Exception as e:
        return {"error": f"Failed to get drone status: {str(e)}"}


def get_obstacle_distances(env, drone_id):
    """
    Get distances to nearest obstacles in 6 directions using raycasting.
    
    Args:
        env: Environment instance
        drone_id: Integer ID of the drone
    
    Returns:
        dict: {
            "north": float (meters),
            "south": float (meters),
            "east": float (meters),
            "west": float (meters),
            "up": float (meters),
            "down": float (meters)
        }
    """
    try:
        # Get drone position
        state = env._getDroneStateVector(drone_id)
        pos = state[0:3]
        
        # Use collision detector for raycasting
        collision_detector = CollisionDetector(env.CLIENT)
        
        # Cast rays in 6 cardinal directions
        ray_length = 5.0  # 5 meters
        
        directions = {
            "north": [0, ray_length, 0],
            "south": [0, -ray_length, 0],
            "east": [ray_length, 0, 0],
            "west": [-ray_length, 0, 0],
            "up": [0, 0, ray_length],
            "down": [0, 0, -ray_length]
        }
        
        distances = {}
        
        for direction_name, offset in directions.items():
            ray_from = pos.tolist()
            ray_to = (pos + np.array(offset)).tolist()
            
            result = p.rayTest(ray_from, ray_to, physicsClientId=env.CLIENT)
            
            if result and len(result) > 0:
                hit_fraction = result[0][2]
                distances[direction_name] = hit_fraction * ray_length
            else:
                distances[direction_name] = ray_length  # No obstacle detected
        
        return distances
        
    except Exception as e:
        return {"error": f"Failed to get obstacle distances: {str(e)}"}


def scan_area(env, drone_id):
    """
    Use drone camera to detect obstacles (red) and targets (green) using vision system.
    
    Args:
        env: Environment instance
        drone_id: Integer ID of the drone
    
    Returns:
        dict: {
            "detections": [
                {
                    "type": "obstacle" or "target",
                    "color": "red" or "green",
                    "area": int (pixels),
                    "bbox": [x, y, w, h],
                    "center": [x, y],
                    "estimated_distance": float (meters),
                    "direction": "left" or "center" or "right"
                },
                ...
            ],
            "total_found": int,
            "obstacles_count": int,
            "targets_count": int
        }
    """
    try:
        # Get drone position
        state = env._getDroneStateVector(drone_id)
        pos = state[0:3]
        
        # Initialize vision system
        vision = VisionSystem(env.CLIENT)
        
        # Capture camera frame
        frame = vision.get_camera_frame(pos, width=224, height=224)
        
        # Detect colored objects
        detections = vision.detect_colored_objects(frame)
        
        # Enhance detections with distance and direction
        for detection in detections:
            detection["estimated_distance"] = vision.estimate_distance(detection["area"])
            detection["direction"] = vision.get_direction(detection["center"], frame_width=224)
        
        # Count by type
        obstacles_count = sum(1 for d in detections if d["type"] == "obstacle")
        targets_count = sum(1 for d in detections if d["type"] == "target")
        
        return {
            "detections": detections,
            "total_found": len(detections),
            "obstacles_count": obstacles_count,
            "targets_count": targets_count,
            "drone_id": drone_id
        }
        
    except Exception as e:
        return {"error": f"Failed to scan area: {str(e)}"}


def move_drone_to(env, drone_id, x, y, z, timeout=10.0):
    """
    Move drone to specified coordinates using PID control.
    Checks for proximity warnings and interrupts if obstacle too close.
    
    Args:
        env: Environment instance
        drone_id: Integer ID of the drone
        x, y, z: Target coordinates (floats)
        timeout: Maximum time to attempt movement (seconds)
    
    Returns:
        dict: {
            "status": "reached" or "interrupted" or "timeout" or "battery_low",
            "current_position": [x, y, z],
            "reason": str (if interrupted),
            "time_elapsed": float (seconds)
        }
    """
    try:
        target = np.array([x, y, z])
        start_time = time.time()
        threshold = 0.3  # Consider "reached" if within 0.3m
        proximity_threshold = 0.5  # Interrupt if obstacle within 0.5m
        
        collision_detector = CollisionDetector(env.CLIENT)
        
        while time.time() - start_time < timeout:
            # Get current position
            state = env._getDroneStateVector(drone_id)
            current_pos = state[0:3]
            
            # Check battery
            if hasattr(env, 'batteries'):
                battery = env.batteries[drone_id].get_percentage()
                if battery < 10.0:
                    return {
                        "status": "battery_low",
                        "current_position": current_pos.tolist(),
                        "reason": f"Battery critically low: {battery:.1f}%",
                        "time_elapsed": time.time() - start_time
                    }
            
            # Check if target reached
            distance = np.linalg.norm(current_pos - target)
            if distance < threshold:
                return {
                    "status": "reached",
                    "current_position": current_pos.tolist(),
                    "time_elapsed": time.time() - start_time
                }
            
            # Check proximity warning (raycast for obstacles)
            distances = collision_detector.raycast(current_pos, num_rays=12, ray_length=3.0)
            min_distance = min(distances)
            
            if min_distance < proximity_threshold:
                return {
                    "status": "interrupted",
                    "current_position": current_pos.tolist(),
                    "reason": f"Proximity warning: obstacle at {min_distance:.2f}m",
                    "time_elapsed": time.time() - start_time
                }
            
            # Compute control action (simplified - actual PID would be in env.step)
            # This is a placeholder - Person B will integrate with actual control loop
            direction = target - current_pos
            direction_norm = direction / (np.linalg.norm(direction) + 1e-6)
            
            # Step the environment (Person B will implement actual control)
            # For now, just step with hover action
            action = {str(drone_id): np.array([0, 0, 0, 0])}
            env.step(action)
            
            # Small delay to prevent busy loop
            time.sleep(0.01)
        
        # Timeout
        state = env._getDroneStateVector(drone_id)
        return {
            "status": "timeout",
            "current_position": state[0:3].tolist(),
            "reason": f"Movement timeout after {timeout}s",
            "time_elapsed": timeout
        }
        
    except Exception as e:
        return {"error": f"Failed to move drone: {str(e)}"}


def get_mission_status(env):
    """
    Get overall mission status including all drones and targets.
    
    Args:
        env: Environment instance
    
    Returns:
        dict: {
            "time_remaining": float (seconds),
            "time_elapsed": float (seconds),
            "total_targets": int,
            "targets_reached": int,
            "drones": [
                {
                    "drone_id": int,
                    "position": [x, y, z],
                    "battery": float,
                    "status": "active" or "crashed" or "battery_dead"
                },
                ...
            ],
            "mission_complete": bool
        }
    """
    try:
        # Get time information
        time_limit = getattr(env, 'time_limit', 120.0)
        time_elapsed = getattr(env, 'step_counter', 0) * getattr(env, 'CTRL_TIMESTEP', 0.01)
        time_remaining = max(0.0, time_limit - time_elapsed)
        
        # Get target information - check both wrapper and inner env
        if hasattr(env, 'scene_manager'):
            total_targets = len(env.scene_manager.target_ids)
        elif hasattr(env, 'env') and hasattr(env.env, 'scene_manager'):
            total_targets = len(env.env.scene_manager.target_ids)
        else:
            total_targets = 0
        
        # Get targets reached from episode tracker if available
        if hasattr(env, 'episode_tracker'):
            targets_reached = env.episode_tracker.targets_reached
        elif hasattr(env, 'env') and hasattr(env.env, 'episode_tracker'):
            targets_reached = env.env.episode_tracker.targets_reached
        else:
            targets_reached = getattr(env, 'targets_reached', 0)
        
        # Get drone information
        num_drones = getattr(env, 'NUM_DRONES', 1)
        drones = []
        
        for drone_id in range(num_drones):
            state = env._getDroneStateVector(drone_id)
            position = state[0:3].tolist()
            
            battery = 100.0
            if hasattr(env, 'battery_simulator'):
                battery = env.battery_simulator.get_battery(drone_id)
            elif hasattr(env, 'batteries'):
                battery = env.batteries[drone_id].get_percentage()
            elif hasattr(env, 'env') and hasattr(env.env, 'battery_simulator'):
                battery = env.env.battery_simulator.get_battery(drone_id)
            
            # Determine status
            status = "active"
            if battery <= 0:
                status = "battery_dead"
            elif position[2] < 0.1:  # Crashed (z position near ground)
                status = "crashed"
            
            drones.append({
                "drone_id": drone_id,
                "position": position,
                "battery": battery,
                "status": status
            })
        
        # Check if mission complete
        mission_complete = (targets_reached >= total_targets) and all(
            d["status"] != "crashed" for d in drones
        )
        
        return {
            "time_remaining": time_remaining,
            "time_elapsed": time_elapsed,
            "total_targets": total_targets,
            "targets_reached": targets_reached,
            "drones": drones,
            "mission_complete": mission_complete
        }
        
    except Exception as e:
        return {"error": f"Failed to get mission status: {str(e)}"}


def assign_drone_to_target(env, drone_id, target_id):
    """
    Assign a drone to a specific target and estimate battery cost.
    
    Args:
        env: Environment instance
        drone_id: Integer ID of the drone
        target_id: Integer ID of the target (index in target_ids list)
    
    Returns:
        dict: {
            "status": "assigned" or "error",
            "drone_id": int,
            "target_id": int,
            "target_position": [x, y, z],
            "distance": float (meters),
            "estimated_battery_cost": float (percentage),
            "feasible": bool (can reach with current battery)
        }
    """
    try:
        # Get drone position and battery
        state = env._getDroneStateVector(drone_id)
        drone_pos = state[0:3]
        
        current_battery = 100.0
        if hasattr(env, 'batteries'):
            current_battery = env.batteries[drone_id].get_percentage()
        
        # Get target position
        if not hasattr(env, 'scene_manager') or target_id >= len(env.scene_manager.target_ids):
            return {"error": f"Invalid target_id: {target_id}"}
        
        target_body_id = env.scene_manager.target_ids[target_id]
        target_pos, _ = p.getBasePositionAndOrientation(target_body_id, physicsClientId=env.CLIENT)
        target_pos = np.array(target_pos)
        
        # Calculate distance
        distance = np.linalg.norm(drone_pos - target_pos)
        
        # Estimate battery cost (rough approximation)
        # Assume: 1% battery per meter traveled + 5% safety margin
        estimated_cost = (distance * 1.0) + 5.0
        
        # Check feasibility
        feasible = current_battery >= estimated_cost
        
        return {
            "status": "assigned",
            "drone_id": drone_id,
            "target_id": target_id,
            "target_position": target_pos.tolist(),
            "distance": distance,
            "estimated_battery_cost": estimated_cost,
            "current_battery": current_battery,
            "feasible": feasible
        }
        
    except Exception as e:
        return {"error": f"Failed to assign drone to target: {str(e)}"}


def return_drone_home(env, drone_id):
    """
    Command drone to return to home/spawn position.
    
    Args:
        env: Environment instance
        drone_id: Integer ID of the drone
    
    Returns:
        dict: {
            "status": "returning" or "error",
            "home_position": [x, y, z],
            "current_position": [x, y, z],
            "distance_to_home": float (meters),
            "estimated_time": float (seconds)
        }
    """
    try:
        # Get current position
        state = env._getDroneStateVector(drone_id)
        current_pos = state[0:3]
        
        # Get home position (spawn position)
        home_pos = getattr(env, 'INIT_XYZS', np.array([[0, 0, 1]]))[drone_id]
        
        # Calculate distance
        distance = np.linalg.norm(current_pos - home_pos)
        
        # Estimate time (assume 1 m/s average speed)
        estimated_time = distance / 1.0
        
        return {
            "status": "returning",
            "home_position": home_pos.tolist(),
            "current_position": current_pos.tolist(),
            "distance_to_home": distance,
            "estimated_time": estimated_time,
            "drone_id": drone_id
        }
        
    except Exception as e:
        return {"error": f"Failed to return drone home: {str(e)}"}


def get_camera_frame(env, drone_id, width=224, height=224):
    """
    Get raw camera frame from drone's perspective.
    
    Args:
        env: Environment instance
        drone_id: Integer ID of the drone
        width: Frame width in pixels
        height: Frame height in pixels
    
    Returns:
        dict: {
            "frame_shape": [height, width, channels],
            "frame_data": list (flattened RGB values),
            "drone_position": [x, y, z],
            "timestamp": float
        }
    """
    try:
        # Get drone position
        state = env._getDroneStateVector(drone_id)
        pos = state[0:3]
        
        # Initialize vision system
        vision = VisionSystem(env.CLIENT)
        
        # Capture frame
        frame = vision.get_camera_frame(pos, width=width, height=height)
        
        return {
            "frame_shape": list(frame.shape),
            "frame_data": frame.flatten().tolist(),  # Flatten for JSON serialization
            "drone_position": pos.tolist(),
            "timestamp": time.time(),
            "drone_id": drone_id
        }
        
    except Exception as e:
        return {"error": f"Failed to get camera frame: {str(e)}"}

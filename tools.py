import numpy as np
import pybullet as p
import cv2
import base64

def get_drone_status(env, drone_id):
    pos = env.env._getDroneStateVector(drone_id)[0:3]
    vel = env.env._getDroneStateVector(drone_id)[10:13]
    battery = env.battery_simulator.get_battery(drone_id)
    return {
        "position": pos.tolist(),
        "velocity": vel.tolist(),
        "battery_percentage": battery
    }

def get_obstacle_distances(env, drone_id):
    pos = env.env._getDroneStateVector(drone_id)[0:3]
    distances = env.collision_detector.raycast(pos)
    return {
        "distances": distances
    }

def scan_area(env, drone_id):
    pos = env.env._getDroneStateVector(drone_id)[0:3]
    vision_data = env.vision_system.get_camera_masking(pos)
    mask = vision_data["mask"]
    
    detected = []
    if np.sum(mask) > 0:
        detected.append("target_color_object")
        
    return {
        "status": "scan_complete",
        "detected_objects": detected
    }

def move_drone_to(env, drone_id, x, y, z):
    target_pos = np.array([x, y, z])
    max_steps = 1000
    steps = 0
    
    while steps < max_steps:
        pos = env.env._getDroneStateVector(drone_id)[0:3]
        
        if env.collision_detector.check_proximity_warning(pos):
            return {
                "status": "interrupted", 
                "reason": "proximity_warning", 
                "current_pos": pos.tolist()
            }
            
        dist_to_target = np.linalg.norm(target_pos - pos)
        if dist_to_target < 0.1:
            return {"status": "reached", "current_pos": pos.tolist()}
            
        # Move drone
        direction = (target_pos - pos) / dist_to_target
        new_pos = pos + direction * 0.05
        p.resetBasePositionAndOrientation(env.env.DRONE_IDS[drone_id], new_pos, [0, 0, 0, 1], physicsClientId=env.env.CLIENT)
        
        # Step physics
        action = np.zeros((env.num_drones, 4))
        env.env.step(action)
        steps += 1
        
    return {"status": "timeout", "current_pos": pos.tolist()}

def get_mission_status(env):
    # Approximation of time left
    time_elapsed = env.env.step_counter / env.env.SIM_FREQ
    time_left = max(0, 600 - time_elapsed) # Assuming 10 min max
    return {
        "remaining_targets": len(env.scene_manager.target_ids),
        "time_left": time_left
    }

def assign_drone_to_target(env, drone_id, target_id):
    pos = env.env._getDroneStateVector(drone_id)[0:3]
    target_pos, _ = p.getBasePositionAndOrientation(target_id, physicsClientId=env.env.CLIENT)
    
    dist = np.linalg.norm(np.array(target_pos) - np.array(pos))
    estimated_cost = dist * 0.5  # arbitrary factor
    
    return {
        "status": "assigned",
        "drone_id": drone_id,
        "target_id": target_id,
        "estimated_battery_cost": estimated_cost
    }

def return_drone_home(env, drone_id):
    home_pos = env.env.INIT_XYZS[drone_id]
    return move_drone_to(env, drone_id, home_pos[0], home_pos[1], home_pos[2])

def get_camera_frame(env, drone_id):
    pos = env.env._getDroneStateVector(drone_id)[0:3]
    vision_data = env.vision_system.get_camera_masking(pos)
    img = vision_data["image"]
    _, buffer = cv2.imencode('.jpg', img)
    b64 = base64.b64encode(buffer).decode('utf-8')
    return {
        "frame_base64": b64
    }

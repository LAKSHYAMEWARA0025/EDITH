import pybullet as p
import pybullet_data
import numpy as np
import cv2
import time
from gym_pybullet_drones.envs.MultiHoverAviary import MultiHoverAviary
from gym_pybullet_drones.utils.enums import Physics

class DronePhysicsManager:
    def __init__(self, num_drones=1):
        self.num_drones = num_drones
        # p.DIRECT for headless mode
        self.env = MultiHoverAviary(
            num_drones=self.num_drones,
            gui=False, 
            physics=Physics.PYB
        )
        self.battery_levels = {i: 100.0 for i in range(num_drones)}
        self.obstacle_ids = []
        self.target_ids = []

    def reset_world(self, target_positions, obstacle_positions):
        """Resets the simulation, spawns the drones, and places targets/obstacles."""
        self.env.reset()
        self.battery_levels = {i: 100.0 for i in range(self.num_drones)}
        
        # Remove old obstacles and targets
        for obs in self.obstacle_ids:
            p.removeBody(obs, physicsClientId=self.env.CLIENT)
        for tgt in self.target_ids:
            p.removeBody(tgt, physicsClientId=self.env.CLIENT)
            
        self.obstacle_ids = []
        self.target_ids = []
        
        # Place obstacles
        for pos in obstacle_positions:
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1], physicsClientId=self.env.CLIENT)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1], rgbaColor=[1, 0, 0, 1], physicsClientId=self.env.CLIENT)
            obs_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col_id, baseVisualShapeIndex=vis_id, basePosition=pos, physicsClientId=self.env.CLIENT)
            self.obstacle_ids.append(obs_id)

        # Place targets
        for pos in target_positions:
            vis_id = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=[0, 1, 0, 1], physicsClientId=self.env.CLIENT)
            tgt_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id, basePosition=pos, physicsClientId=self.env.CLIENT)
            self.target_ids.append(tgt_id)

    def get_drone_telemetry(self, drone_id):
        """Extracts [x, y, z] pos, velocity, and calculates battery percentage."""
        state = self.env._getDroneStateVector(drone_id)
        pos = state[0:3]
        vel = state[10:13] # linear velocity
        battery = self.battery_levels.get(drone_id, 0.0)
        return {
            "position": pos.tolist(),
            "velocity": vel.tolist(),
            "battery_percentage": battery
        }

    def min_obstacle_distance(self, drone_id):
        """Helper method: Calculate minimum distance to any obstacle for a drone."""
        pos = self.env._getDroneStateVector(drone_id)[0:3]
        min_dist = float('inf')
        for obs_id in self.obstacle_ids:
            obs_pos, _ = p.getBasePositionAndOrientation(obs_id, physicsClientId=self.env.CLIENT)
            dist = np.linalg.norm(np.array(pos) - np.array(obs_pos))
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def execute_move(self, drone_id, target_pos):
        """
        Steps the PyBullet simulation until drone reaches target_pos.
        Checks proximity warning every tick, interrupting if obstacle <= 0.3m.
        """
        target_pos = np.array(target_pos)
        threshold = 0.1
        max_steps = 1000
        steps = 0
        
        while steps < max_steps:
            current_pos = np.array(self.env._getDroneStateVector(drone_id)[0:3])
            
            # Check for proximity warning
            dist_to_obs = self.min_obstacle_distance(drone_id)
            if dist_to_obs <= 0.3:
                return {
                    "status": "interrupted",
                    "reason": f"proximity_warning ({dist_to_obs:.2f}m)",
                    "position": current_pos.tolist()
                }
                
            # Check if target reached
            if np.linalg.norm(current_pos - target_pos) < threshold:
                return {
                    "status": "success",
                    "position": current_pos.tolist()
                }
                
            # Placeholder for actual control: stepping the env
            # In a full implementation, we'd calculate RPMs to move towards target_pos
            action = {str(drone_id): np.array([0, 0, 0, 0])} 
            self.env.step(action)
            
            # Update simulated battery percentage
            if drone_id in self.battery_levels:
                self.battery_levels[drone_id] = max(0.0, self.battery_levels[drone_id] - 0.01)
                
            steps += 1
            
        return {"status": "timeout", "position": current_pos.tolist()}

    def get_camera_masking(self, drone_id):
        """
        Grabs p.getCameraImage() and sets up OpenCV scaffolding for HSV masking.
        """
        pos = self.env._getDroneStateVector(drone_id)[0:3]
        
        # Camera looks straight down from the drone
        view_matrix = p.computeViewMatrix(
            cameraEyePosition=pos,
            cameraTargetPosition=[pos[0], pos[1], pos[2]-1], 
            cameraUpVector=[0, 1, 0],
            physicsClientId=self.env.CLIENT
        )
        proj_matrix = p.computeProjectionMatrixFOV(
            fov=60.0,
            aspect=1.0,
            nearVal=0.1,
            farVal=100.0,
            physicsClientId=self.env.CLIENT
        )
        
        width, height, rgb_img, depth_img, seg_img = p.getCameraImage(
            width=320,
            height=240,
            viewMatrix=view_matrix,
            projectionMatrix=proj_matrix,
            renderer=p.ER_TINY_RENDERER, # headless DIRECT mode rendering
            physicsClientId=self.env.CLIENT
        )
        
        img = np.reshape(rgb_img, (height, width, 4))
        bgr_img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        # Setup OpenCV scaffolding
        hsv_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        
        # Placeholders for HSV thresholds (to be injected)
        lower_bound = np.array([0, 0, 0])
        upper_bound = np.array([255, 255, 255])
        
        mask = cv2.inRange(hsv_img, lower_bound, upper_bound)
        masked_img = cv2.bitwise_and(bgr_img, bgr_img, mask=mask)
        
        return {
            "image": bgr_img,
            "mask": mask,
            "masked_image": masked_img
        }

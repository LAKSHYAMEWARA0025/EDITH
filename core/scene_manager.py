import pybullet as p
import numpy as np

class SceneManager:
    """Manages scene objects (obstacles and targets) for EDITH drone environment."""
    
    # Exact RGBA colors from test_07
    RGBA_RED = [1.0, 0.0, 0.0, 1.0]
    RGBA_GREEN = [0.0, 1.0, 0.0, 1.0]
    
    # Object sizes
    OBSTACLE_SIZE = 0.3  # 0.3m cubes
    TARGET_SIZE = 0.2    # 0.2m cubes
    
    def __init__(self, client_id):
        self.client_id = client_id
        self.obstacle_ids = []
        self.target_ids = []

    def create_colored_obstacle(self, position, size=None):
        """Create red obstacle cube at specified position."""
        if size is None:
            size = self.OBSTACLE_SIZE
        
        col_id = p.createCollisionShape(
            p.GEOM_BOX, 
            halfExtents=[size, size, size], 
            physicsClientId=self.client_id
        )
        vis_id = p.createVisualShape(
            p.GEOM_BOX, 
            halfExtents=[size, size, size], 
            rgbaColor=self.RGBA_RED, 
            physicsClientId=self.client_id
        )
        obs_id = p.createMultiBody(
            baseMass=0, 
            baseCollisionShapeIndex=col_id, 
            baseVisualShapeIndex=vis_id, 
            basePosition=position, 
            physicsClientId=self.client_id
        )
        self.obstacle_ids.append(obs_id)
        return obs_id

    def create_colored_target(self, position, size=None):
        """Create green target cube at specified position (NO COLLISION - visual only)."""
        if size is None:
            size = self.TARGET_SIZE
        
        # Visual shape only - NO collision shape
        vis_id = p.createVisualShape(
            p.GEOM_BOX, 
            halfExtents=[size, size, size], 
            rgbaColor=self.RGBA_GREEN, 
            physicsClientId=self.client_id
        )
        tgt_id = p.createMultiBody(
            baseMass=0, 
            baseCollisionShapeIndex=-1,  # -1 = no collision
            baseVisualShapeIndex=vis_id, 
            basePosition=position, 
            physicsClientId=self.client_id
        )
        self.target_ids.append(tgt_id)
        return tgt_id

    def place_obstacles(self, obstacle_positions):
        """Place multiple obstacles at specified positions."""
        for pos in obstacle_positions:
            self.create_colored_obstacle(pos)

    def place_targets(self, target_positions):
        """Place multiple targets at specified positions."""
        for pos in target_positions:
            self.create_colored_target(pos)

    def randomize_scene_task1(self, num_obstacles=None):
        """
        Randomize scene for Task 1: Navigate & Reach
        - 1 target in one of 3 zones
        - 2-5 obstacles randomly placed
        """
        # Clear existing objects
        self.clear_scene()
        
        # Randomize number of obstacles
        if num_obstacles is None:
            num_obstacles = np.random.randint(2, 6)  # 2-5 obstacles
        
        # Target zones (one will be selected)
        target_zones = [
            [5.0, 0.0, 1.0],
            [0.0, 5.0, 1.0],
            [5.0, 5.0, 1.5]
        ]
        target_pos = target_zones[np.random.randint(0, len(target_zones))]
        self.create_colored_target(target_pos)
        
        # Obstacle placement zones
        obstacle_zones = [
            {"center": [2.5, 0.0, 0.5], "radius": 1.0},
            {"center": [0.0, 2.5, 0.5], "radius": 1.0},
            {"center": [2.5, 2.5, 0.5], "radius": 1.0}
        ]
        
        # Place obstacles randomly in zones
        for i in range(num_obstacles):
            zone = obstacle_zones[i % len(obstacle_zones)]
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(0, zone["radius"])
            x = zone["center"][0] + radius * np.cos(angle)
            y = zone["center"][1] + radius * np.sin(angle)
            z = zone["center"][2]
            self.create_colored_obstacle([x, y, z])

    def randomize_scene_task2(self, num_obstacles=None):
        """
        Randomize scene for Task 2: Constrained Delivery
        - 1 target (landing zone)
        - 3-5 obstacles
        - Similar to Task 1 but with battery pressure
        """
        if num_obstacles is None:
            num_obstacles = np.random.randint(3, 6)  # 3-5 obstacles
        
        self.randomize_scene_task1(num_obstacles)

    def randomize_scene_task3(self, num_obstacles=None, num_targets=None):
        """
        Randomize scene for Task 3: Two-Drone Coordination
        - 2-3 targets
        - 4-6 obstacles
        """
        self.clear_scene()
        
        if num_obstacles is None:
            num_obstacles = np.random.randint(4, 7)  # 4-6 obstacles
        if num_targets is None:
            num_targets = np.random.randint(2, 4)  # 2-3 targets
        
        # Place multiple targets
        target_zones = [
            [5.0, 0.0, 1.0],
            [0.0, 5.0, 1.0],
            [5.0, 5.0, 1.5],
            [-5.0, 0.0, 1.0],
            [0.0, -5.0, 1.0]
        ]
        selected_zones = np.random.choice(len(target_zones), num_targets, replace=False)
        for idx in selected_zones:
            self.create_colored_target(target_zones[idx])
        
        # Place obstacles
        obstacle_zones = [
            {"center": [2.5, 0.0, 0.5], "radius": 1.0},
            {"center": [0.0, 2.5, 0.5], "radius": 1.0},
            {"center": [2.5, 2.5, 0.5], "radius": 1.0},
            {"center": [-2.5, 0.0, 0.5], "radius": 1.0},
            {"center": [0.0, -2.5, 0.5], "radius": 1.0}
        ]
        
        for i in range(num_obstacles):
            zone = obstacle_zones[i % len(obstacle_zones)]
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(0, zone["radius"])
            x = zone["center"][0] + radius * np.cos(angle)
            y = zone["center"][1] + radius * np.sin(angle)
            z = zone["center"][2]
            self.create_colored_obstacle([x, y, z])

    def clear_scene(self):
        """Remove all obstacles and targets from the scene."""
        for obs in self.obstacle_ids:
            p.removeBody(obs, physicsClientId=self.client_id)
        for tgt in self.target_ids:
            p.removeBody(tgt, physicsClientId=self.client_id)
        self.obstacle_ids = []
        self.target_ids = []

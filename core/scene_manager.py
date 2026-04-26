import pybullet as p
import numpy as np

class SceneManager:
    """Manages scene objects (obstacles and targets) for EDITH drone environment."""
    
    # Exact RGBA colors from test_07
    RGBA_RED = [1.0, 0.0, 0.0, 1.0]
    RGBA_GREEN = [0.0, 1.0, 0.0, 1.0]
    
    # Object sizes
    OBSTACLE_WIDTH = 0.4   # 0.4m width (X/Y)
    OBSTACLE_HEIGHT = 1.2  # 1.2m height (Z) - tall enough to block flight paths
    TARGET_SIZE = 0.2      # 0.2m cubes
    
    def __init__(self, client_id):
        self.client_id = client_id
        self.obstacle_ids = []
        self.target_ids = []

    def create_colored_obstacle(self, position, size=None):
        """Create red obstacle cube at specified position with tall vertical extent."""
        width = self.OBSTACLE_WIDTH
        height = self.OBSTACLE_HEIGHT
        
        # Create tall rectangular obstacle (wider in Z to block vertical space)
        col_id = p.createCollisionShape(
            p.GEOM_BOX, 
            halfExtents=[width, width, height/2],  # Half-extents: X, Y, Z
            physicsClientId=self.client_id
        )
        vis_id = p.createVisualShape(
            p.GEOM_BOX, 
            halfExtents=[width, width, height/2], 
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
        - 1 target in one of 5 zones
        - 2-5 obstacles strategically placed to block direct path
        """
        self.clear_scene()
        
        if num_obstacles is None:
            num_obstacles = np.random.randint(2, 6)  # 2-5 obstacles
        
        # ── 1. Place target ──────────────────────────────────────────
        target_zones = [
            np.array([5.0, 0.0, 1.0]),
            np.array([0.0, 5.0, 1.0]),
            np.array([5.0, 5.0, 1.0]),
            np.array([-5.0, 5.0, 1.0]),
            np.array([3.0, 7.0, 1.0]),
        ]
        target_pos = target_zones[np.random.randint(0, len(target_zones))]
        self.create_colored_target(target_pos.tolist())
        
        # ── 2. Compute path geometry ─────────────────────────────────
        spawn = np.array([0.0, 0.0, 1.0])  # effective flight start altitude
        path_vec = target_pos - spawn
        path_length = np.linalg.norm(path_vec)
        path_dir = path_vec / path_length  # unit vector toward target
        
        # Perpendicular direction (horizontal plane only)
        perp_dir = np.array([-path_dir[1], path_dir[0], 0.0])
        
        # ── 3. Place obstacles strategically ─────────────────────────
        # Randomized blocking: each obstacle gets random lateral offset
        # Creates variable difficulty: sometimes blocked, sometimes open
        segment_ranges = [
            (0.25, 0.40),
            (0.45, 0.60),
            (0.65, 0.75),
            (0.30, 0.50),  # extra segments if more obstacles
            (0.55, 0.70),
        ]
        
        placed_positions = []
        attempts = 0
        max_attempts = 50
        
        for i in range(num_obstacles):
            if attempts > max_attempts:
                break
            
            seg_min, seg_max = segment_ranges[i % len(segment_ranges)]
            
            # Random position along path within segment
            t = np.random.uniform(seg_min, seg_max)
            base_pos = spawn + path_dir * path_length * t
            
            # RANDOMIZED lateral offset - varies per obstacle
            # 40% chance: fully blocked (0.0-0.3m)
            # 40% chance: partially blocked (0.5-1.2m)
            # 20% chance: open path (1.5-2.5m)
            rand_val = np.random.random()
            if rand_val < 0.4:
                lateral_magnitude = np.random.uniform(0.0, 0.3)  # Centerline block
            elif rand_val < 0.8:
                lateral_magnitude = np.random.uniform(0.5, 1.2)  # Partial block
            else:
                lateral_magnitude = np.random.uniform(1.5, 2.5)  # Open path
            
            lateral_sign = 1 if i % 2 == 0 else -1
            lateral_offset = perp_dir * lateral_sign * lateral_magnitude
            
            # Fixed Z position at flight altitude to force lateral navigation
            obstacle_pos = base_pos + lateral_offset
            obstacle_pos[2] = 1.0  # Center at typical flight altitude
            
            # ── 4. Safety checks ─────────────────────────────────────
            # Don't place too close to spawn
            if np.linalg.norm(obstacle_pos - spawn) < 1.0:
                attempts += 1
                continue
            
            # Don't place too close to target
            if np.linalg.norm(obstacle_pos - target_pos) < 0.8:
                attempts += 1
                continue
            
            # Don't place too close to another obstacle (prevents stacking/overlap)
            too_close = False
            for prev_pos in placed_positions:
                distance = np.linalg.norm(obstacle_pos - np.array(prev_pos))
                if distance < 0.8:  # Minimum 0.8m separation
                    too_close = True
                    break
            if too_close:
                attempts += 1
                continue
            
            # Clamp to arena bounds (no Z clamping - fixed at 1.0)
            obstacle_pos[0] = np.clip(obstacle_pos[0], -7.5, 7.5)
            obstacle_pos[1] = np.clip(obstacle_pos[1], -7.5, 7.5)
            
            self.create_colored_obstacle(obstacle_pos.tolist())
            placed_positions.append(obstacle_pos.tolist())
            attempts = 0  # Reset attempts counter on successful placement
        
        # ── 5. Optional: Add one flanking obstacle near target ───────
        # Forces final approach planning with lateral maneuver
        if len(placed_positions) >= 2 and np.random.random() > 0.4:
            flank_side = np.random.choice([-1, 1])
            flank_pos = target_pos + perp_dir * flank_side * np.random.uniform(0.5, 1.0)  # Closer to target
            flank_pos[2] = 1.0  # Fixed at flight altitude
            
            # Only place if not too close to target and other obstacles
            valid_flank = True
            if np.linalg.norm(flank_pos - target_pos) < 0.8:
                valid_flank = False
            for prev_pos in placed_positions:
                if np.linalg.norm(flank_pos - np.array(prev_pos)) < 0.8:
                    valid_flank = False
                    break
            
            if valid_flank:
                self.create_colored_obstacle(flank_pos.tolist())

    def randomize_scene_task2(self, num_obstacles=None):
        """
        Randomize scene for Task 2: Constrained Delivery
        - 1 target (landing zone)
        - 3-5 obstacles with tighter placement (higher battery cost)
        - Similar to Task 1 but obstacles closer to path
        """
        self.clear_scene()
        
        if num_obstacles is None:
            num_obstacles = np.random.randint(3, 6)  # 3-5 obstacles
        
        # ── 1. Place target ──────────────────────────────────────────
        target_zones = [
            np.array([5.0, 0.0, 1.0]),
            np.array([0.0, 5.0, 1.0]),
            np.array([5.0, 5.0, 1.0]),
            np.array([-5.0, 5.0, 1.0]),
            np.array([3.0, 7.0, 1.0]),
        ]
        target_pos = target_zones[np.random.randint(0, len(target_zones))]
        self.create_colored_target(target_pos.tolist())
        
        # ── 2. Compute path geometry ─────────────────────────────────
        spawn = np.array([0.0, 0.0, 1.0])
        path_vec = target_pos - spawn
        path_length = np.linalg.norm(path_vec)
        path_dir = path_vec / path_length
        perp_dir = np.array([-path_dir[1], path_dir[0], 0.0])
        
        # ── 3. Place obstacles with randomized blocking ──────────────────
        segment_ranges = [
            (0.20, 0.35),
            (0.40, 0.55),
            (0.60, 0.75),
            (0.30, 0.45),
            (0.65, 0.80),
        ]
        
        placed_positions = []
        attempts = 0
        max_attempts = 50
        
        for i in range(num_obstacles):
            if attempts > max_attempts:
                break
            
            seg_min, seg_max = segment_ranges[i % len(segment_ranges)]
            t = np.random.uniform(seg_min, seg_max)
            base_pos = spawn + path_dir * path_length * t
            
            # RANDOMIZED lateral offset for Task 2
            # 50% chance: fully blocked (0.0-0.2m) - higher battery cost
            # 30% chance: partially blocked (0.4-1.0m)
            # 20% chance: open path (1.2-2.0m)
            rand_val = np.random.random()
            if rand_val < 0.5:
                lateral_magnitude = np.random.uniform(0.0, 0.2)  # Tight block
            elif rand_val < 0.8:
                lateral_magnitude = np.random.uniform(0.4, 1.0)  # Partial block
            else:
                lateral_magnitude = np.random.uniform(1.2, 2.0)  # Open path
            
            lateral_sign = 1 if i % 2 == 0 else -1
            lateral_offset = perp_dir * lateral_sign * lateral_magnitude
            
            obstacle_pos = base_pos + lateral_offset
            obstacle_pos[2] = 1.0  # Fixed at flight altitude
            
            # Safety checks
            if np.linalg.norm(obstacle_pos - spawn) < 1.0:
                attempts += 1
                continue
            
            if np.linalg.norm(obstacle_pos - target_pos) < 0.8:
                attempts += 1
                continue
            
            too_close = False
            for prev_pos in placed_positions:
                if np.linalg.norm(obstacle_pos - np.array(prev_pos)) < 0.8:
                    too_close = True
                    break
            if too_close:
                attempts += 1
                continue
            
            # Clamp to bounds (no Z clamping)
            obstacle_pos[0] = np.clip(obstacle_pos[0], -7.5, 7.5)
            obstacle_pos[1] = np.clip(obstacle_pos[1], -7.5, 7.5)
            
            self.create_colored_obstacle(obstacle_pos.tolist())
            placed_positions.append(obstacle_pos.tolist())
            attempts = 0
        
        # Add midpoint obstacle to increase detour cost
        if len(placed_positions) >= 2:
            mid_pos = spawn + path_dir * path_length * 0.5
            mid_pos += perp_dir * np.random.choice([-1, 1]) * np.random.uniform(0.5, 1.0)
            mid_pos[2] = 1.0  # Fixed at flight altitude
            
            valid_mid = True
            for prev_pos in placed_positions:
                if np.linalg.norm(mid_pos - np.array(prev_pos)) < 0.8:
                    valid_mid = False
                    break
            
            if valid_mid:
                self.create_colored_obstacle(mid_pos.tolist())

    def randomize_scene_task3(self, num_obstacles=None, num_targets=None):
        """
        Randomize scene for Task 3: Two-Drone Coordination
        - 2-3 targets
        - 4-6 obstacles distributed across paths to each target
        """
        self.clear_scene()
        
        if num_obstacles is None:
            num_obstacles = np.random.randint(4, 7)  # 4-6 obstacles
        if num_targets is None:
            num_targets = np.random.randint(2, 4)  # 2-3 targets
        
        # ── 1. Place multiple targets ────────────────────────────────
        target_zones = [
            np.array([5.0, 0.0, 1.0]),
            np.array([0.0, 5.0, 1.0]),
            np.array([5.0, 5.0, 1.5]),
            np.array([-5.0, 0.0, 1.0]),
            np.array([0.0, -5.0, 1.0])
        ]
        selected_indices = np.random.choice(len(target_zones), num_targets, replace=False)
        target_positions = [target_zones[idx] for idx in selected_indices]
        
        for target_pos in target_positions:
            self.create_colored_target(target_pos.tolist())
        
        # ── 2. Distribute obstacles across paths ─────────────────────
        spawn = np.array([0.0, 0.0, 1.0])
        placed_positions = []
        obstacles_per_target = num_obstacles // num_targets
        remaining_obstacles = num_obstacles % num_targets
        
        for target_idx, target_pos in enumerate(target_positions):
            # Calculate path to this target
            path_vec = target_pos - spawn
            path_length = np.linalg.norm(path_vec)
            path_dir = path_vec / path_length
            perp_dir = np.array([-path_dir[1], path_dir[0], 0.0])
            
            # Number of obstacles for this target's path
            num_for_this_target = obstacles_per_target
            if target_idx < remaining_obstacles:
                num_for_this_target += 1
            
            # Place obstacles along this path
            for i in range(num_for_this_target):
                attempts = 0
                max_attempts = 30
                
                while attempts < max_attempts:
                    # Position along path
                    t = np.random.uniform(0.3, 0.7)
                    base_pos = spawn + path_dir * path_length * t
                    
                    # RANDOMIZED lateral offset for Task 3
                    # 35% chance: fully blocked (0.0-0.3m)
                    # 40% chance: partially blocked (0.5-1.2m)
                    # 25% chance: open path (1.5-2.5m)
                    rand_val = np.random.random()
                    if rand_val < 0.35:
                        lateral_magnitude = np.random.uniform(0.0, 0.3)
                    elif rand_val < 0.75:
                        lateral_magnitude = np.random.uniform(0.5, 1.2)
                    else:
                        lateral_magnitude = np.random.uniform(1.5, 2.5)
                    
                    lateral_sign = 1 if i % 2 == 0 else -1
                    lateral_offset = perp_dir * lateral_sign * lateral_magnitude
                    
                    obstacle_pos = base_pos + lateral_offset
                    obstacle_pos[2] = 1.0  # Fixed at flight altitude
                    
                    # Safety checks
                    if np.linalg.norm(obstacle_pos - spawn) < 1.0:
                        attempts += 1
                        continue
                    
                    # Check distance to all targets
                    too_close_to_target = False
                    for tgt_pos in target_positions:
                        if np.linalg.norm(obstacle_pos - tgt_pos) < 0.8:
                            too_close_to_target = True
                            break
                    if too_close_to_target:
                        attempts += 1
                        continue
                    
                    # Check distance to other obstacles
                    too_close = False
                    for prev_pos in placed_positions:
                        if np.linalg.norm(obstacle_pos - np.array(prev_pos)) < 0.8:
                            too_close = True
                            break
                    if too_close:
                        attempts += 1
                        continue
                    
                    # Clamp to bounds (no Z clamping)
                    obstacle_pos[0] = np.clip(obstacle_pos[0], -7.5, 7.5)
                    obstacle_pos[1] = np.clip(obstacle_pos[1], -7.5, 7.5)
                    
                    self.create_colored_obstacle(obstacle_pos.tolist())
                    placed_positions.append(obstacle_pos.tolist())
                    break  # Successfully placed

    def clear_scene(self):
        """Remove all obstacles and targets from the scene."""
        for obs in self.obstacle_ids:
            p.removeBody(obs, physicsClientId=self.client_id)
        for tgt in self.target_ids:
            p.removeBody(tgt, physicsClientId=self.client_id)
        self.obstacle_ids = []
        self.target_ids = []

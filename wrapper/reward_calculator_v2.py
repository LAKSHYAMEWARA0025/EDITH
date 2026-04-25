"""
Redesigned Reward Calculator with Proper Normalization

Key principles:
1. All rewards in range [-1, +1] per step
2. Episode rewards comparable across different episode lengths
3. Clear signal for what's good/bad
4. No extreme values that dominate learning
"""

class RewardCalculatorV2:
    def __init__(self):
        # Reward component weights (sum to 1.0)
        self.PROGRESS_WEIGHT = 0.6      # Most important
        self.SAFETY_WEIGHT = 0.2        # Collisions bad
        self.EFFICIENCY_WEIGHT = 0.2    # Time/battery management
        
        # Normalization constants
        self.MAX_EXPECTED_DISTANCE = 20.0  # Realistic max distance in scene
        self.COLLISION_PENALTY = -0.5      # Per collision
        self.TARGET_BONUS = 1.0            # Per target reached
        
    def compute_reward(self, episode_data):
        """
        Compute normalized per-step reward.
        
        Returns reward in range approximately [-1, +1] per step.
        """
        
        # Hard override for crashes
        if episode_data.all_drones_crashed:
            return {
                "total": -1.0,
                "progress": 0.0,
                "safety": -1.0,
                "efficiency": 0.0
            }
        
        # Compute weighted components
        progress = self._progress_reward(episode_data) * self.PROGRESS_WEIGHT
        safety = self._safety_reward(episode_data) * self.SAFETY_WEIGHT
        efficiency = self._efficiency_reward(episode_data) * self.EFFICIENCY_WEIGHT
        
        # Total is weighted sum (range: [-1, +1])
        total = progress + safety + efficiency
        
        # Clip to ensure bounds
        total = max(-1.0, min(1.0, total))
        
        return {
            "total": float(total),
            "progress": float(progress),
            "safety": float(safety),
            "efficiency": float(efficiency)
        }
    
    def _progress_reward(self, episode_data):
        """
        Progress towards target.
        Returns value in range [-1, +1].
        """
        # Target reached: maximum reward
        if episode_data.targets_reached > 0:
            return 1.0
        
        # No target info yet
        if episode_data.closest_distance_to_target == float('inf'):
            return 0.0
        
        # Distance-based reward
        # Closer = higher reward
        distance = episode_data.closest_distance_to_target
        normalized_distance = min(1.0, distance / self.MAX_EXPECTED_DISTANCE)
        
        # Map distance to reward:
        # 0m → +1.0
        # 10m → +0.5
        # 20m+ → 0.0
        progress_score = 1.0 - normalized_distance
        
        # Check if making progress (getting closer)
        if episode_data.is_making_progress():
            # Bonus for moving in right direction
            return progress_score
        else:
            # Penalty for moving away or stagnating
            # But not too harsh - exploration is okay
            return progress_score * 0.5 - 0.2
    
    def _safety_reward(self, episode_data):
        """
        Safety score based on collisions.
        Returns value in range [-1, +1].
        """
        if episode_data.collisions == 0:
            return 1.0  # Perfect safety
        elif episode_data.collisions == 1:
            return 0.0  # One collision, neutral
        else:
            return -1.0  # Multiple collisions, bad
    
    def _efficiency_reward(self, episode_data):
        """
        Efficiency score based on movement and time.
        Returns value in range [-1, +1].
        """
        # Penalize excessive stagnation
        if episode_data.stagnant_steps > 20:
            return -1.0  # Completely stuck
        elif episode_data.stagnant_steps > 10:
            return -0.5  # Mostly stuck
        elif episode_data.stagnant_steps > 5:
            return 0.0   # Some stagnation
        else:
            return 0.5   # Moving well
    
    def compute_episode_reward(self, episode_data):
        """
        Compute final episode reward (for logging/comparison).
        
        This is separate from per-step rewards and used for:
        - Comparing episodes of different lengths
        - Final evaluation metrics
        
        Returns normalized score in range [0, 100].
        """
        score = 0.0
        
        # Target completion (0-50 points)
        if episode_data.total_targets > 0:
            completion_rate = episode_data.targets_reached / episode_data.total_targets
            score += completion_rate * 50.0
        
        # Safety (0-25 points)
        if episode_data.collisions == 0:
            score += 25.0
        elif episode_data.collisions == 1:
            score += 15.0
        elif episode_data.collisions == 2:
            score += 5.0
        # else: 0 points
        
        # Efficiency (0-25 points)
        if episode_data.total_targets > 0 and episode_data.targets_reached > 0:
            # Time efficiency
            time_ratio = episode_data.get_time_elapsed() / episode_data.time_limit
            if time_ratio < 0.5:
                score += 15.0  # Very fast
            elif time_ratio < 0.75:
                score += 10.0  # Fast
            elif time_ratio < 1.0:
                score += 5.0   # On time
            # else: 0 points (timeout)
            
            # Step efficiency
            if episode_data.step_count < 20:
                score += 10.0  # Very efficient
            elif episode_data.step_count < 50:
                score += 5.0   # Efficient
            # else: 0 points
        
        return float(score)

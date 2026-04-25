class RewardCalculator:
    def __init__(self):
        pass

    def compute_reward(self, episode_data):
        """
        Compute per-step reward with progress tracking and anti-hacking.
        
        Reward structure:
        - Progress towards target (positive)
        - Safety (no collisions)
        - Penalties for stagnation, loops, wasted actions
        """
        
        # Hard override for crashes
        if episode_data.all_drones_crashed:
            return {
                "total": -1.0,  # Strong negative for crash
                "progress": 0.0,
                "safety": 0.0,
                "efficiency": 0.0,
                "penalties": 1.0
            }
        
        # Compute components
        progress = self._progress_reward(episode_data)
        safety = self._safety_penalty(episode_data)
        efficiency = self._efficiency_reward(episode_data)
        penalties = self._anti_hacking_penalties(episode_data)
        
        # Total (can be negative)
        total = progress + safety + efficiency - penalties
        
        return {
            "total": total,
            "progress": progress,
            "safety": safety,
            "efficiency": efficiency,
            "penalties": penalties
        }

    def _progress_reward(self, episode_data):
        """Reward for making progress towards target."""
        # Target reached: big reward
        if episode_data.targets_reached > 0:
            return 1.0
        
        # Getting closer: reward based on progress
        if episode_data.is_making_progress():
            # Reward based on how close we are
            if episode_data.closest_distance_to_target < float('inf'):
                # Normalize distance to [0, 1] assuming max distance ~50m
                max_expected_distance = 50.0
                normalized_distance = min(1.0, episode_data.closest_distance_to_target / max_expected_distance)
                # Closer = higher reward (inverse)
                closeness = 1.0 - normalized_distance
                return 0.3 * closeness  # Increased from 0.1 to 0.3 for better gradient
        
        # Small reward just for moving (not stagnant)
        if episode_data.stagnant_steps < 5:
            return 0.05
        
        return 0.0

    def _safety_penalty(self, episode_data):
        """Penalty for collisions."""
        if episode_data.collisions > 0:
            return -0.5 * episode_data.collisions
        return 0.0

    def _efficiency_reward(self, episode_data):
        """Small reward for not wasting time."""
        # Penalize stagnation
        if episode_data.stagnant_steps > 10:
            return -0.1
        return 0.0

    def _anti_hacking_penalties(self, episode_data):
        """Penalties for reward hacking behaviors."""
        penalty = 0.0
        
        # Penalty for action loops (repeating EXACT same action+args)
        # Increased threshold to 10 to allow scan/move patterns
        if episode_data.detect_action_loop():
            penalty += 0.1  # Reduced from 0.2
        
        # Penalty for excessive steps without ANY progress
        if episode_data.step_count > 30 and episode_data.targets_reached == 0:
            if not episode_data.is_making_progress():
                # Only penalize if truly stuck, not if exploring
                if episode_data.stagnant_steps > 15:
                    penalty += 0.1
        
        # Penalty for moving significantly away from target repeatedly
        if len(episode_data.distance_to_target_history) >= 5:
            recent_distances = episode_data.distance_to_target_history[-5:]
            # Check if consistently moving away (all 5 recent steps increased distance)
            if all(recent_distances[i] > recent_distances[i-1] + 1.0 for i in range(1, len(recent_distances))):
                penalty += 0.05
        
        return penalty

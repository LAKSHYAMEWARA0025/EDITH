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
        
        # Getting closer: small positive reward
        if episode_data.is_making_progress():
            # Reward based on how close we are
            if episode_data.closest_distance_to_target < float('inf'):
                # Closer = higher reward (inverse distance)
                closeness = 1.0 / (1.0 + episode_data.closest_distance_to_target)
                return 0.1 * closeness
        
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
        
        # Penalty for action loops (repeating same action)
        if episode_data.detect_action_loop():
            penalty += 0.2
        
        # Penalty for excessive tool calls without progress
        if episode_data.step_count > 20 and episode_data.targets_reached == 0:
            if not episode_data.is_making_progress():
                penalty += 0.1
        
        # Penalty for moving away from target
        if len(episode_data.distance_to_target_history) >= 2:
            recent_distance = episode_data.distance_to_target_history[-1]
            prev_distance = episode_data.distance_to_target_history[-2]
            if recent_distance > prev_distance + 0.5:  # Moving away significantly
                penalty += 0.05
        
        return penalty

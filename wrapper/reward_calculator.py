class RewardCalculator:
    def __init__(self):
        pass

    def compute_reward(self, episode_data):
        """
        Compute full reward dictionary.
        
        Reward structure from problem statement:
        - 35% mission completion
        - 25% safety
        - 15% efficiency
        - 10% battery management
        - 10% milestone bonuses
        - Penalties for format errors and timeouts
        """
        
        # Hard override for crashes
        if episode_data.all_drones_crashed:
            return {
                "total": 0.0,
                "mission": 0.0,
                "safety": 0.0,
                "efficiency": 0.0,
                "battery": 0.0,
                "milestones": 0.0,
                "penalties": 0.0
            }
        
        # Compute components
        mission = self._mission_completion_score(episode_data)
        safety = self._safety_score(episode_data)
        efficiency = self._efficiency_score(episode_data)
        battery = self._battery_management_score(episode_data)
        milestones = self._milestone_bonus(episode_data)
        penalties = self._penalties(episode_data)
        
        # Total (clamped to [0, 1])
        total = max(0.0, min(1.0, mission + safety + efficiency + battery + milestones - penalties))
        
        return {
            "total": total,
            "mission": mission,
            "safety": safety,
            "efficiency": efficiency,
            "battery": battery,
            "milestones": milestones,
            "penalties": penalties
        }

    def _mission_completion_score(self, episode_data):
        """35% weight - targets reached / total targets."""
        if episode_data.total_targets == 0:
            return 0.0
        ratio = episode_data.targets_reached / episode_data.total_targets
        return 0.35 * ratio

    def _safety_score(self, episode_data):
        """25% weight - collision penalty."""
        if episode_data.collisions == 0:
            return 0.25
        # Each collision reduces by 0.4 of the 0.25 max
        penalty = episode_data.collisions * 0.4
        return max(0.0, 0.25 * (1.0 - penalty))

    def _efficiency_score(self, episode_data):
        """15% weight - time efficiency."""
        time_elapsed = episode_data.get_time_elapsed()
        time_limit = episode_data.time_limit
        
        if time_elapsed >= time_limit:
            return 0.0  # Timeout
        
        # Reward faster completion
        ratio = min(1.0, time_limit / max(time_elapsed, 1.0))
        return 0.15 * ratio

    def _battery_management_score(self, episode_data):
        """10% weight - battery remaining."""
        if not episode_data.final_battery:
            return 0.0
        
        # Average battery remaining across all drones
        avg_battery = sum(episode_data.final_battery.values()) / max(len(episode_data.final_battery), 1)
        return 0.10 * (avg_battery / 100.0)

    def _milestone_bonus(self, episode_data):
        """10% weight - milestone bonuses (capped)."""
        # 0.02 per unique milestone, max 0.10
        bonus = len(episode_data.milestones) * 0.02
        return min(0.10, bonus)

    def _penalties(self, episode_data):
        """Penalties for format errors and timeouts."""
        penalty = 0.0
        
        # Count invalid tool calls (tools that returned errors)
        invalid_calls = sum(1 for call in episode_data.tool_calls 
                           if "error" in str(call))
        penalty += invalid_calls * 0.05
        
        # Timeout penalty
        if episode_data.timeout:
            penalty += 0.03
        
        return penalty

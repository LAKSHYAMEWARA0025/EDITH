class RewardCalculator:
    def __init__(self):
        pass

    def compute_reward(self, all_crashed=False, **kwargs):
        if all_crashed:
            return 0.0
            
        reward = 0.0
        reward += self._mission_completion_score(**kwargs)
        reward += self._safety_score(**kwargs)
        reward += self._efficiency_score(**kwargs)
        reward += self._battery_management_score(**kwargs)
        reward -= self._penalties(**kwargs)
        return reward

    def _mission_completion_score(self, **kwargs):
        return 0.0

    def _safety_score(self, **kwargs):
        return 0.0

    def _efficiency_score(self, **kwargs):
        return 0.0

    def _battery_management_score(self, **kwargs):
        return 0.0

    def _penalties(self, **kwargs):
        return 0.0

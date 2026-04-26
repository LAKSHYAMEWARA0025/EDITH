"""
EDITH Reward Calculator — Milestone-Based Hybrid Design

Two components:
1. Per-step: continuous distance progress signal + milestone bonuses + deviation penalties
2. Episode-end: comprehensive judgment across mission, safety, efficiency, battery

Final score normalized to [-1.0, 1.0]
"""

import numpy as np


class RewardCalculatorV2:
    def __init__(self):
        # Scene normalization constant
        self.MAX_SCENE_DISTANCE = 15.0

        # Per-step signal caps
        self.MAX_STEP_SIGNAL = 0.10
        self.MIN_STEP_SIGNAL = -0.10

        # Milestone bonuses (one-time per episode)
        self.MILESTONE_BONUSES = {
            "first_scan_completed":   0.05,
            "target_located":         0.05,
            "halfway_there":          0.10,
            "close_approach":         0.15,
            "target_reached":         0.20,
            "return_initiated":       0.05,
            "arrived_home":           0.10,
        }

        # Deviation penalties (per occurrence)
        self.DEVIATION_PENALTIES = {
            "collision":              0.20,
            "out_of_bounds":          0.15,
            "repeated_tool_call":     0.05,
            "battery_critical_ignored": 0.10,
            "moving_away":            0.05,
            "early_return_home":      0.50,  # Task 1: returning before target reached
        }

        # Episode-end weights (sum to 1.0)
        self.MISSION_WEIGHT    = 0.40
        self.SAFETY_WEIGHT     = 0.30
        self.EFFICIENCY_WEIGHT = 0.20
        self.BATTERY_WEIGHT    = 0.10

    # ------------------------------------------------------------------
    # PER-STEP REWARD
    # ------------------------------------------------------------------

    def compute_step_reward(self, episode_data, current_distance, prev_distance,
                            new_milestones=None, new_deviations=None):
        """
        Called every step. Returns per-step scalar reward.

        Args:
            episode_data: EpisodeData instance
            current_distance: float, distance to nearest target this step
            prev_distance: float, distance to nearest target last step
            new_milestones: list of milestone keys hit this step
            new_deviations: list of deviation keys triggered this step

        Returns:
            float: per-step reward signal
        """
        reward = 0.0

        # 1. Continuous distance progress signal
        if prev_distance is not None and prev_distance < float('inf'):
            delta = prev_distance - current_distance  # positive = getting closer
            signal = np.clip(delta / self.MAX_SCENE_DISTANCE, -0.10, 0.10)
            reward += float(signal)

        # 2. Milestone bonuses (one-time)
        if new_milestones:
            for milestone in new_milestones:
                if milestone in self.MILESTONE_BONUSES:
                    if milestone not in episode_data.milestones_hit:
                        reward += self.MILESTONE_BONUSES[milestone]
                        episode_data.milestones_hit.add(milestone)

        # 3. Deviation penalties
        if new_deviations:
            for deviation in new_deviations:
                if deviation in self.DEVIATION_PENALTIES:
                    reward -= self.DEVIATION_PENALTIES[deviation]

        return float(reward)

    # ------------------------------------------------------------------
    # EPISODE-END REWARD
    # ------------------------------------------------------------------

    def compute_episode_reward(self, episode_data):
        """
        Called once at episode termination.

        Returns:
            dict: rubric-compliant reward dictionary with keys matching openenv.yaml
        """

        # Hard override — all drones crashed
        if episode_data.all_drones_crashed:
            return {
                "total":              0.0,
                "mission_completion": 0.0,
                "safety":             0.0,
                "efficiency":         0.0,
                "battery":            0.0,
                "per_step_total":     float(np.clip(
                    sum(episode_data.per_step_rewards), -0.5, 0.5
                )),
            }

        # --- Mission Completion [0.0, 1.0] ---
        if episode_data.total_targets > 0:
            mission_score = episode_data.targets_reached / episode_data.total_targets
        else:
            mission_score = 0.0

        # --- Safety [0.0, 1.0] ---
        if episode_data.collisions == 0:
            safety_score = 1.0
        elif episode_data.collisions == 1:
            safety_score = 0.6
        elif episode_data.collisions == 2:
            safety_score = 0.2
        else:
            safety_score = 0.0

        # --- Efficiency [0.0, 1.0] ---
        time_elapsed = episode_data.get_time_elapsed()
        time_limit   = episode_data.time_limit
        if time_elapsed > 0 and time_limit > 0:
            efficiency_score = float(np.clip(time_limit / time_elapsed, 0.0, 1.0))
        else:
            efficiency_score = 0.0

        # --- Battery [0.0, 1.0] ---
        if episode_data.final_battery:
            avg_battery = np.mean(list(episode_data.final_battery.values()))
            battery_score = float(np.clip(avg_battery / 100.0, 0.0, 1.0))
        else:
            battery_score = 0.0

        # --- Weighted episode-end score [0.0, 1.0] ---
        episode_end = (
            self.MISSION_WEIGHT    * mission_score    +
            self.SAFETY_WEIGHT     * safety_score     +
            self.EFFICIENCY_WEIGHT * efficiency_score +
            self.BATTERY_WEIGHT    * battery_score
        )

        # --- Per-step total normalized to [-0.5, +0.5] ---
        per_step_total = float(np.clip(
            sum(episode_data.per_step_rewards), -0.5, 0.5
        ))

        # --- Final total [-1.0, +1.0] ---
        # episode_end scaled to [0.0, 0.5], per_step_total in [-0.5, +0.5]
        total = float(np.clip(
            (episode_end * 0.5) + per_step_total,
            -1.0, 1.0
        ))

        return {
            "total":              total,
            "mission_completion": float(round(mission_score, 4)),
            "safety":             float(round(safety_score, 4)),
            "efficiency":         float(round(efficiency_score, 4)),
            "battery":            float(round(battery_score, 4)),
            "per_step_total":     float(round(per_step_total, 4)),
        }

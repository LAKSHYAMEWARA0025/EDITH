from gym_pybullet_drones.envs.MultiHoverAviary import MultiHoverAviary
from gym_pybullet_drones.utils.enums import Physics
import random
import time
import numpy as np
import pybullet as p

from core.scene_manager import SceneManager
from core.vision_system import VisionSystem
from core.battery_simulator import BatterySimulator
from core.collision_detector import CollisionDetector
from wrapper.reward_calculator import RewardCalculator
from wrapper.episode_tracker import EpisodeData
from core.tools import (
    get_drone_status, get_obstacle_distances, scan_area,
    move_drone_to, get_mission_status, assign_drone_to_target,
    return_drone_home, get_camera_frame
)
from wrapper import task_configs

class EDITHDroneEnv:
    def __init__(self, num_drones=1, task_type="task1", gui=False):
        self.num_drones = num_drones
        self.task_type = task_type
        self.gui = gui
        self.env = MultiHoverAviary(
            num_drones=self.num_drones,
            gui=self.gui,
            physics=Physics.PYB
        )
        
        client_id = self.env.CLIENT
        self.scene_manager = SceneManager(client_id)
        self.vision_system = VisionSystem(client_id)
        self.battery_simulator = BatterySimulator()
        self.collision_detector = CollisionDetector(client_id)
        self.reward_calculator = RewardCalculator()
        self.episode_tracker = EpisodeData()

    def _execute_tool(self, tool_name, args):
        tool_map = {
            "get_drone_status": get_drone_status,
            "get_obstacle_distances": get_obstacle_distances,
            "scan_area": scan_area,
            "move_drone_to": move_drone_to,
            "get_mission_status": get_mission_status,
            "assign_drone_to_target": assign_drone_to_target,
            "return_drone_home": return_drone_home,
            "get_camera_frame": get_camera_frame
        }
        
        if tool_name in tool_map:
            return tool_map[tool_name](self, **args)
        return {"error": f"Unknown tool: {tool_name}"}

    def reset(self):
        self.env.reset()
        self.battery_simulator.reset(self.num_drones)
        self.episode_tracker = EpisodeData()
        
        # Get task config
        config = task_configs.get_task_config(self.task_type)
        
        # Use Person A's randomization methods
        if self.task_type == "task1":
            num_obstacles = random.choice(config["num_obstacles_range"])
            self.scene_manager.randomize_scene_task1(num_obstacles)
        elif self.task_type == "task2":
            num_obstacles = random.choice(config["num_obstacles_range"])
            battery_start = random.choice(config["battery_start_range"])
            self.battery_simulator.battery_levels[0] = battery_start
            self.scene_manager.randomize_scene_task2(num_obstacles)
        elif self.task_type == "task3":
            num_obstacles = random.choice(config["num_obstacles_range"])
            num_targets = random.choice(config["num_targets_range"])
            self.scene_manager.randomize_scene_task3(num_obstacles, num_targets)
        
        # Initialize episode tracking
        self.episode_tracker.total_targets = len(self.scene_manager.target_ids)
        self.episode_tracker.start_time = time.time()
        self.episode_tracker.time_limit = config["time_limit"]
        
        return self.state(), {}

    def step(self, action):
        # Record action
        self.episode_tracker.record_action(action)
        
        # Execute tool
        tool_name = action.get("name", action.get("tool"))
        args = action.get("arguments", action.get("args", {}))
        result = self._execute_tool(tool_name, args)
        
        # Check for target reached
        for i in range(self.num_drones):
            drone_pos = self.env._getDroneStateVector(i)[0:3]
            for target_idx, target_body_id in enumerate(self.scene_manager.target_ids):
                target_pos, _ = p.getBasePositionAndOrientation(target_body_id, 
                                                                physicsClientId=self.env.CLIENT)
                distance = np.linalg.norm(drone_pos - np.array(target_pos))
                if distance < 0.5:  # Within 0.5m = reached
                    self.episode_tracker.record_target_reached(target_idx)
                    # Remove target so it's not counted twice
                    p.removeBody(target_body_id, physicsClientId=self.env.CLIENT)
                    self.scene_manager.target_ids.pop(target_idx)
                    break
        
        # Finalize episode data
        final_battery = {i: self.battery_simulator.get_battery(i) 
                         for i in range(self.num_drones)}
        all_crashed = all(final_battery[i] <= 0 for i in range(self.num_drones))
        self.episode_tracker.finalize(final_battery, all_crashed)
        
        # Compute reward using episode tracker
        reward_dict = self.reward_calculator.compute_reward(self.episode_tracker)
        reward = reward_dict["total"]
        
        # Check termination
        time_left = self.episode_tracker.get_time_remaining()
        targets_left = self.episode_tracker.total_targets - self.episode_tracker.targets_reached
        batteries_dead = all_crashed
        
        done = bool(time_left <= 0 or targets_left <= 0 or batteries_dead)
        
        return self.state(), reward, done, False, {
            "tool_result": result,
            "reward_breakdown": reward_dict
        }

    def state(self):
        return {
            "mission_status": get_mission_status(self),
            "drones": {i: get_drone_status(self, i) for i in range(self.num_drones)}
        }
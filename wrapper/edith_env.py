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
        """Execute a tool with comprehensive error handling."""
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
        
        # Validate tool name
        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}
        
        # Validate args is a dict
        if not isinstance(args, dict):
            return {"error": f"Invalid arguments type: expected dict, got {type(args).__name__}"}
        
        # Validate drone_id if present
        if "drone_id" in args:
            try:
                drone_id = int(args["drone_id"])
                if drone_id < 0 or drone_id >= self.num_drones:
                    return {"error": f"Invalid drone_id: {drone_id}. Must be between 0 and {self.num_drones-1}"}
                args["drone_id"] = drone_id
            except (ValueError, TypeError):
                return {"error": f"Invalid drone_id type: expected int, got {type(args['drone_id']).__name__}"}
        
        # Execute tool with error handling
        try:
            result = tool_map[tool_name](self, **args)
            return result
        except TypeError as e:
            # Missing or extra arguments
            return {"error": f"Invalid arguments for {tool_name}: {str(e)}"}
        except Exception as e:
            # Catch any other unexpected errors
            return {"error": f"Tool execution failed: {str(e)}"}

    def reset(self):
        """Reset environment with error handling."""
        try:
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
            
        except Exception as e:
            # Return error state if reset fails
            return {"error": f"Reset failed: {str(e)}"}, {}

    def step(self, action):
        """Execute one step with comprehensive error handling."""
        try:
            # Validate action structure
            if not isinstance(action, dict):
                return self.state(), 0.0, False, False, {
                    "tool_result": {"error": f"Invalid action type: expected dict, got {type(action).__name__}"},
                    "reward_breakdown": {}
                }
            
            # Record action
            self.episode_tracker.record_action(action)
            
            # Extract tool name and args
            tool_name = action.get("name", action.get("tool"))
            if not tool_name:
                return self.state(), 0.0, False, False, {
                    "tool_result": {"error": "Missing tool name in action (expected 'name' or 'tool' key)"},
                    "reward_breakdown": {}
                }
            
            args = action.get("arguments", action.get("args", {}))
            if args is None:
                args = {}
            
            # Execute tool
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
            
        except Exception as e:
            # Catch any unexpected errors in step execution
            return self.state(), 0.0, False, False, {
                "tool_result": {"error": f"Step execution failed: {str(e)}"},
                "reward_breakdown": {}
            }

    def state(self):
        """Get current state with error handling."""
        try:
            return {
                "mission_status": get_mission_status(self),
                "drones": {i: get_drone_status(self, i) for i in range(self.num_drones)}
            }
        except Exception as e:
            return {"error": f"Failed to get state: {str(e)}"}
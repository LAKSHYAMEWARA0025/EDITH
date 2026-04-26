from gym_pybullet_drones.envs.MultiHoverAviary import MultiHoverAviary
from gym_pybullet_drones.utils.enums import Physics, ActionType
import random
import time
import numpy as np
import pybullet as p

from core.scene_manager import SceneManager
from core.vision_system import VisionSystem
from core.battery_simulator import BatterySimulator
from core.collision_detector import CollisionDetector
from wrapper.reward_calculator_v2 import RewardCalculatorV2
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
            physics=Physics.PYB,
            act=ActionType.PID  # Use PID control for waypoint following
        )
        
        client_id = self.env.CLIENT
        self.scene_manager = SceneManager(client_id)
        self.vision_system = VisionSystem(client_id)
        self.battery_simulator = BatterySimulator()
        self.collision_detector = CollisionDetector(client_id)
        self.reward_calculator = RewardCalculatorV2()
        self.episode_tracker = EpisodeData()
        
        # Store target positions for each drone (for PID controller)
        self.target_positions = {i: self.env.INIT_XYZS[i].copy() for i in range(self.num_drones)}

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
            # get_camera_frame removed - returns too much data for LLM context
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
            
            # Reset target positions to spawn positions
            self.target_positions = {i: self.env.INIT_XYZS[i].copy() for i in range(self.num_drones)}
            
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
            
            # Debug logging
            print(f"[DEBUG] Reset complete: {len(self.scene_manager.target_ids)} targets spawned")
            print(f"[DEBUG] Episode tracker total_targets: {self.episode_tracker.total_targets}")
            
            return self.state(), {}
            
        except Exception as e:
            # Return error state if reset fails
            return {"error": f"Reset failed: {str(e)}"}, {}

    def step(self, action):
        """Execute one step with comprehensive error handling."""
        try:
            # --- Validate action ---
            if not isinstance(action, dict):
                return self.state(), -0.1, False, False, {
                    "tool_result": {"error": f"Invalid action type: expected dict, got {type(action).__name__}"},
                    "reward_breakdown": {}
                }

            tool_name = action.get("name", action.get("tool"))
            if not tool_name:
                return self.state(), -0.1, False, False, {
                    "tool_result": {"error": "Missing tool name in action"},
                    "reward_breakdown": {}
                }

            args = action.get("arguments", action.get("args", {}))
            if args is None:
                args = {}

            # --- Detect deviations before executing ---
            deviations = []

            # Repeated tool call detection
            if self.episode_tracker.check_repeated_call(tool_name, args):
                deviations.append("repeated_tool_call")

            # Battery critical ignored
            if tool_name not in ("return_drone_home", "get_drone_status"):
                for i in range(self.num_drones):
                    if self.battery_simulator.get_battery(i) < 10.0:
                        deviations.append("battery_critical_ignored")
                        break
            
            # Early return home (Task 1 only)
            if tool_name == "return_drone_home" and self.task_type == "task1":
                if self.episode_tracker.targets_reached == 0:
                    deviations.append("early_return_home")

            # --- Record action ---
            self.episode_tracker.record_action(action)

            # --- Execute tool ---
            result = self._execute_tool(tool_name, args)

            # --- Update target position if move command ---
            if tool_name == "move_drone_to" and "error" not in result:
                drone_id = args.get("drone_id", 0)
                if "target_position" in result:
                    new_target = np.array(result["target_position"])
                    self.target_positions[drone_id] = new_target
                    print(f"[DEBUG] Updated target for drone {drone_id}: {new_target}")

            if tool_name == "return_drone_home" and "error" not in result:
                drone_id = args.get("drone_id", 0)
                if "home_position" in result:
                    new_target = np.array(result["home_position"])
                    self.target_positions[drone_id] = new_target
                    print(f"[DEBUG] Returning drone {drone_id} to home: {new_target}")

            # --- Run physics steps ---
            physics_steps = 240
            collision_detected = False
            
            for step_i in range(physics_steps):
                pid_action = np.zeros((self.num_drones, 3))
                for i in range(self.num_drones):
                    pid_action[i] = self.target_positions[i]
                
                if step_i == 0:
                    # Log initial position
                    initial_pos = self.env._getDroneStateVector(0)[0:3]
                    print(f"[DEBUG] PID action for step: {pid_action}")
                    print(f"[DEBUG] Drone position BEFORE physics: {initial_pos}")
                
                self.env.step(pid_action)
                
                # Check for collisions using PyBullet contact points
                for i in range(self.num_drones):
                    drone_body_id = self.env.DRONE_IDS[i]
                    contacts = p.getContactPoints(bodyA=drone_body_id, physicsClientId=self.env.CLIENT)
                    
                    if contacts:
                        collision_detected = True
                        if "collision" not in deviations:
                            deviations.append("collision")
                            print(f"[DEBUG] Collision detected for drone {i} at physics step {step_i}")
                    
                    # Also check ground crash
                    drone_pos = self.env._getDroneStateVector(i)[0:3]
                    if drone_pos[2] < 0.05:
                        self.episode_tracker.record_collision(i)
                        if "collision" not in deviations:
                            deviations.append("collision")
                
                if step_i == physics_steps - 1:
                    # Log final position
                    final_pos = self.env._getDroneStateVector(0)[0:3]
                    print(f"[DEBUG] Drone position AFTER physics: {final_pos}")
                    distance_moved = np.linalg.norm(final_pos - initial_pos)
                    print(f"[DEBUG] Distance moved: {distance_moved:.3f}m")

            # --- Compute current distance to nearest target ---
            current_distance = float('inf')
            for i in range(self.num_drones):
                drone_pos = self.env._getDroneStateVector(i)[0:3]
                for target_body_id in self.scene_manager.target_ids:
                    target_pos, _ = p.getBasePositionAndOrientation(
                        target_body_id, physicsClientId=self.env.CLIENT)
                    dist = np.linalg.norm(drone_pos - np.array(target_pos))
                    if dist < current_distance:
                        current_distance = dist

            # --- Out of bounds check ---
            for i in range(self.num_drones):
                pos = self.env._getDroneStateVector(i)[0:3]
                if abs(pos[0]) > 8.0 or abs(pos[1]) > 8.0 or pos[2] > 3.0:
                    deviations.append("out_of_bounds")

            # --- Moving away check ---
            prev_dist = self.episode_tracker.prev_distance_to_target
            if prev_dist is not None and current_distance > prev_dist + 2.0:
                deviations.append("moving_away")

            # --- Set initial distance ---
            if self.episode_tracker.initial_distance_to_target is None and current_distance < float('inf'):
                self.episode_tracker.initial_distance_to_target = current_distance

            # --- Detect milestones ---
            milestones = []
            initial_dist = self.episode_tracker.initial_distance_to_target

            if tool_name == "scan_area" and "error" not in result:
                if result.get("total_found", 0) > 0:
                    milestones.append("first_scan_completed")

            if tool_name == "assign_drone_to_target" and "error" not in result:
                milestones.append("target_located")

            if initial_dist and current_distance < initial_dist * 0.5:
                milestones.append("halfway_there")

            if current_distance < 1.5:
                milestones.append("close_approach")

            # --- Check targets reached ---
            for i in range(self.num_drones):
                drone_pos = self.env._getDroneStateVector(i)[0:3]
                for target_idx, target_body_id in enumerate(list(self.scene_manager.target_ids)):
                    target_pos, _ = p.getBasePositionAndOrientation(
                        target_body_id, physicsClientId=self.env.CLIENT)
                    distance = np.linalg.norm(drone_pos - np.array(target_pos))
                    if distance < 0.5:
                        self.episode_tracker.record_target_reached(target_idx)
                        milestones.append("target_reached")
                        p.removeBody(target_body_id, physicsClientId=self.env.CLIENT)
                        self.scene_manager.target_ids.remove(target_body_id)
                        break

            if tool_name == "return_drone_home" and "error" not in result:
                if result.get("status") == "command_sent":
                    milestones.append("return_initiated")
                elif result.get("status") == "arrived_home":
                    milestones.append("arrived_home")

            # --- Update position tracking ---
            self.episode_tracker.prev_distance_to_target = current_distance
            for i in range(self.num_drones):
                drone_pos = self.env._getDroneStateVector(i)[0:3].tolist()
                target_pos_list = [0, 0, 0]
                if self.scene_manager.target_ids:
                    tp, _ = p.getBasePositionAndOrientation(
                        self.scene_manager.target_ids[0], physicsClientId=self.env.CLIENT)
                    target_pos_list = list(tp)
                self.episode_tracker.update_position(i, drone_pos, target_pos_list)

            # --- Battery update ---
            for i in range(self.num_drones):
                vel = self.env._getDroneStateVector(i)[10:13]
                self.battery_simulator.step({i: vel})

            # --- Finalize episode data ---
            final_battery = {i: self.battery_simulator.get_battery(i)
                             for i in range(self.num_drones)}
            all_crashed = all(v <= 0 for v in final_battery.values())
            self.episode_tracker.finalize(final_battery, all_crashed)

            # --- Compute per-step reward ---
            step_reward = self.reward_calculator.compute_step_reward(
                episode_data=self.episode_tracker,
                current_distance=current_distance,
                prev_distance=prev_dist,
                new_milestones=milestones,
                new_deviations=deviations
            )
            self.episode_tracker.record_step_reward(step_reward)

            # --- Check termination ---
            time_left = self.episode_tracker.get_time_remaining()
            targets_left = self.episode_tracker.total_targets - self.episode_tracker.targets_reached
            step_limit = self.episode_tracker.step_count >= 100

            done = bool(
                targets_left <= 0 or
                time_left <= 0 or
                all_crashed or
                step_limit
            )

            # --- Episode-end reward on termination ---
            reward = step_reward
            reward_breakdown = {"step_reward": float(step_reward)}

            if done:
                episode_reward_dict = self.reward_calculator.compute_episode_reward(
                    self.episode_tracker)
                reward = episode_reward_dict["total"]
                reward_breakdown = episode_reward_dict

            return self._sanitize(self.state()), float(reward), bool(done), False, {
                "tool_result": self._sanitize(result),
                "reward_breakdown": reward_breakdown,
                "milestones_hit": list(milestones),
                "deviations": list(deviations)
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.state(), -0.5, False, False, {
                "tool_result": {"error": f"Step execution failed: {str(e)}"},
                "reward_breakdown": {}
            }

    def state(self):
        """Get current state with error handling."""
        try:
            return {
                "mission_status": get_mission_status(self),
                "drones": {str(i): get_drone_status(self, i) for i in range(self.num_drones)}
            }
        except Exception as e:
            return {"error": f"Failed to get state: {str(e)}"}

    def _sanitize(self, obj):
        """Recursively convert all numpy types to Python native types."""
        import numpy as np
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize(v) for v in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        return obj

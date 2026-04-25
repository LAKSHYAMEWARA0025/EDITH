from gym_pybullet_drones.envs.MultiHoverAviary import MultiHoverAviary
from gym_pybullet_drones.utils.enums import Physics

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
        
        config = task_configs.TASK1_CONFIG
        self.scene_manager.clear_scene()
        self.scene_manager.place_obstacles(config["obstacle_placement_zones"])
        self.scene_manager.place_targets(config["target_zones"])
        return self.state(), {}

    def step(self, action):
        self.episode_tracker.record_action(action)
        
        # Robust fallback: check for either 'name' or 'tool' keys in the JSON
        tool_name = action.get("name", action.get("tool"))
        args = action.get("arguments", action.get("args", {}))
        
        result = self._execute_tool(tool_name, args)

        reward = self.reward_calculator.compute_reward(self.episode_tracker)
        
        status = get_mission_status(self)
        time_left = status.get("time_left", 0)
        targets_left = status.get("remaining_targets", 0)
        
        try:
            batteries_dead = all(self.battery_simulator.get_battery(i) <= 0 for i in range(self.num_drones))
        except Exception:
            batteries_dead = False # Safety fallback in case battery logic isn't fully wired
        
        done = bool(time_left <= 0 or targets_left <= 0 or batteries_dead)
        
        return self.state(), reward, done, False, {"tool_result": result}

    def state(self):
        return {
            "mission_status": get_mission_status(self),
            "drones": {i: get_drone_status(self, i) for i in range(self.num_drones)}
        }
from openenv import MCPEnvironment
from gym_pybullet_drones.envs.MultiHoverAviary import MultiHoverAviary
from gym_pybullet_drones.utils.enums import Physics

from scene_manager import SceneManager
from vision_system import VisionSystem
from battery_simulator import BatterySimulator
from collision_detector import CollisionDetector
from reward_calculator import RewardCalculator
from episode_tracker import EpisodeData
from tools import (
    get_drone_status, get_obstacle_distances, scan_area,
    move_drone_to, get_mission_status, assign_drone_to_target,
    return_drone_home, get_camera_frame
)
import task_configs

class EDITHDroneEnv(MCPEnvironment):
    def __init__(self, num_drones=1, task_type="task1", gui=False):
        super().__init__()
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
        self._register_tools()

    def _register_tools(self):
        @self.tool(name="get_drone_status", description="Fetches position, velocity from physics, and current battery percentage for a given drone.")
        def _get_drone_status(drone_id: int):
            return get_drone_status(self, drone_id)

        @self.tool(name="get_obstacle_distances", description="Casts rays in all directions to return distances to nearby obstacles for a drone.")
        def _get_obstacle_distances(drone_id: int):
            return get_obstacle_distances(self, drone_id)

        @self.tool(name="scan_area", description="Uses the vision system to get the camera frame and run color masking detections, returning a list of detected objects.")
        def _scan_area(drone_id: int):
            return scan_area(self, drone_id)

        @self.tool(name="move_drone_to", description="Moves the drone to specific x, y, z coordinates. Checks for proximity warnings and interrupts if an obstacle is too close.")
        def _move_drone_to(drone_id: int, x: float, y: float, z: float):
            return move_drone_to(self, drone_id, x, y, z)

        @self.tool(name="get_mission_status", description="Returns the remaining targets and time left in the current mission.")
        def _get_mission_status():
            return get_mission_status(self)

        @self.tool(name="assign_drone_to_target", description="Logs the assignment of a drone to a target and calculates a rough estimated battery cost based on distance.")
        def _assign_drone_to_target(drone_id: int, target_id: int):
            return assign_drone_to_target(self, drone_id, target_id)

        @self.tool(name="return_drone_home", description="Commands the drone to return to its initial spawn point. Checks for proximity warnings.")
        def _return_drone_home(drone_id: int):
            return return_drone_home(self, drone_id)

        @self.tool(name="get_camera_frame", description="Returns the raw base64 string of the camera frame for direct inspection.")
        def _get_camera_frame(drone_id: int):
            return get_camera_frame(self, drone_id)

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
        
        tool_name = action.get("name")
        args = action.get("arguments", {})
        
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
        
        result = None
        if tool_name in tool_map:
            result = tool_map[tool_name](self, **args)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        reward = self.reward_calculator.compute_reward(self.episode_tracker)
        
        status = get_mission_status(self)
        time_left = status.get("time_left", 0)
        targets_left = status.get("remaining_targets", 0)
        batteries_dead = all(self.battery_simulator.get_battery(i) <= 0 for i in range(self.num_drones))
        
        done = bool(time_left <= 0 or targets_left == 0 or batteries_dead)
        
        return self.state(), reward, done, False, {"tool_result": result}

    def state(self):
        return {
            "mission_status": get_mission_status(self),
            "drones": {i: get_drone_status(self, i) for i in range(self.num_drones)}
        }

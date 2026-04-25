import random

TASK1_CONFIG = {
    "name": "Navigate & Reach",
    "num_drones": 1,
    "num_obstacles_range": [2, 3, 4, 5],  # Randomize
    "num_targets": 1,
    "time_limit": 120.0,
    "battery_start": 100.0,
    "mission_brief": "Fly to the green marker. Avoid all obstacles. Return home when done.",
    "spawn_positions": [
        [0.0, 0.0, 1.0],
        [0.5, 0.5, 1.0]
    ]
}

TASK2_CONFIG = {
    "name": "Constrained Delivery",
    "num_drones": 1,
    "num_obstacles_range": [3, 4, 5],
    "num_targets": 1,
    "battery_start_range": [70, 75, 80, 85, 90, 95, 100],  # Randomize
    "time_limit": 150.0,
    "mission_brief": "Deliver to the landing zone. Battery is limited. Return home after delivery.",
    "spawn_positions": [
        [0.0, 0.0, 1.0],
        [0.5, 0.5, 1.0]
    ]
}

TASK3_CONFIG = {
    "name": "Two-Drone Coordination",
    "num_drones": 2,
    "num_obstacles_range": [4, 5, 6],
    "num_targets_range": [2, 3],  # Randomize
    "time_limit": 180.0,
    "battery_start": 100.0,
    "mission_brief": "Two drones available. Multiple targets to reach. Allocate efficiently. All drones must return home.",
    "spawn_positions": [
        [0.0, 0.0, 1.0],
        [1.0, 1.0, 1.0]
    ]
}

def get_task_config(task_type):
    """Get task config with randomization applied."""
    configs = {
        "task1": TASK1_CONFIG,
        "task2": TASK2_CONFIG,
        "task3": TASK3_CONFIG
    }
    return configs.get(task_type, TASK1_CONFIG)

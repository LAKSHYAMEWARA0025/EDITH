import numpy as np

class BatterySimulator:
    def __init__(self):
        self.battery_levels = {}
        
    def reset(self, num_drones):
        """Reset batteries for a new episode."""
        self.battery_levels = {i: 100.0 for i in range(num_drones)}
        
    def step(self, velocities):
        """
        Updates battery levels based on drone velocities.
        velocities: dict mapping drone_id to velocity vector [vx, vy, vz]
        """
        for drone_id, vel in velocities.items():
            speed = np.linalg.norm(vel)
            # Battery drain formula: base idle drain + kinetic drain
            drain = 0.01 + (speed * 0.005)
            self.battery_levels[drone_id] = max(0.0, self.battery_levels[drone_id] - drain)
            
    def get_battery(self, drone_id):
        """Return the current battery percentage for a drone."""
        return self.battery_levels.get(drone_id, 0.0)

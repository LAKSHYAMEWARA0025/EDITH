import time

class EpisodeData:
    def __init__(self):
        # Tracking
        self.tool_calls = []
        self.collisions = 0
        self.targets_reached = 0
        self.total_targets = 0
        self.milestones = []
        
        # Timing
        self.start_time = time.time()
        self.end_time = None
        self.time_limit = 120.0
        
        # Battery
        self.initial_battery = {}
        self.final_battery = {}
        
        # Status
        self.all_drones_crashed = False
        self.timeout = False
        
    def record_action(self, action):
        """Log tool call."""
        self.tool_calls.append({
            "tool": action.get("name", action.get("tool")),
            "args": action.get("arguments", action.get("args", {})),
            "timestamp": time.time() - self.start_time
        })
    
    def record_collision(self, drone_id=None):
        """Log collision event."""
        self.collisions += 1
    
    def record_target_reached(self, target_id):
        """Log target completion."""
        self.targets_reached += 1
        self.milestones.append(f"target_{target_id}_reached")
    
    def record_milestone(self, milestone_name):
        """Log generic milestone."""
        if milestone_name not in self.milestones:
            self.milestones.append(milestone_name)
    
    def finalize(self, final_battery_dict, all_crashed=False):
        """Finalize episode data."""
        self.end_time = time.time()
        self.final_battery = final_battery_dict
        self.all_drones_crashed = all_crashed
    
    def get_time_elapsed(self):
        """Get elapsed time in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
    
    def get_time_remaining(self):
        """Get remaining time in seconds."""
        elapsed = self.get_time_elapsed()
        return max(0.0, self.time_limit - elapsed)
    
    def get_summary(self):
        """Return episode summary."""
        return {
            "targets_reached": self.targets_reached,
            "total_targets": self.total_targets,
            "collisions": self.collisions,
            "tool_calls": len(self.tool_calls),
            "time_elapsed": self.get_time_elapsed(),
            "milestones": len(self.milestones),
            "crashed": self.all_drones_crashed
        }

    def log_tool_call(self, tool_name, args):
        """Backward compatibility."""
        self.record_action({"tool": tool_name, "args": args})

    def log_collision(self):
        """Backward compatibility."""
        self.record_collision()

    def log_milestone(self, milestone_name):
        """Backward compatibility."""
        self.record_milestone(milestone_name)

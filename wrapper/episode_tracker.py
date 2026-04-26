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
        
        # Progress tracking (anti-hacking)
        self.step_count = 0
        self.previous_positions = {}  # Track drone positions
        self.distance_to_target_history = []  # Track if getting closer
        self.stagnant_steps = 0  # Steps without meaningful movement
        self.repeated_actions = {}  # Detect action loops
        self.closest_distance_to_target = float('inf')  # Best distance achieved
        
        # NEW fields for milestone-based reward system
        self.milestones_hit = set()              # prevents duplicate milestone rewards
        self.per_step_rewards = []               # accumulates per-step signals for normalization
        self.prev_distance_to_target = None      # for delta computation each step
        self.initial_distance_to_target = None   # for halfway milestone trigger
        self.last_tool_call = None               # for repeated call detection
        self.last_tool_args = None               # for repeated call detection
        self.deviation_penalties_accumulated = 0.0  # running total for logging
        
    def record_action(self, action):
        """Log tool call and detect loops."""
        self.step_count += 1
        
        tool_name = action.get("name", action.get("tool"))
        args_str = str(action.get("arguments", action.get("args", {})))
        
        self.tool_calls.append({
            "tool": tool_name,
            "args": action.get("arguments", action.get("args", {})),
            "timestamp": time.time() - self.start_time
        })
        
        # Detect repeated actions (reward hacking)
        action_signature = f"{tool_name}:{args_str}"
        self.repeated_actions[action_signature] = self.repeated_actions.get(action_signature, 0) + 1
    
    def update_position(self, drone_id, position, target_position):
        """Track drone movement and progress towards target."""
        import numpy as np
        
        # Calculate distance to target
        distance = np.linalg.norm(np.array(position) - np.array(target_position))
        self.distance_to_target_history.append(distance)
        
        # Update closest distance
        if distance < self.closest_distance_to_target:
            self.closest_distance_to_target = distance
        
        # Check if drone is stagnant
        # With 240 physics steps per agent step, drone should move significantly
        if drone_id in self.previous_positions:
            prev_pos = self.previous_positions[drone_id]
            movement = np.linalg.norm(np.array(position) - np.array(prev_pos))
            
            # Increased threshold from 0.05m to 0.5m since we now execute 240 physics steps
            # Drone should move at least 0.5m per agent action
            if movement < 0.5:
                self.stagnant_steps += 1
            else:
                self.stagnant_steps = 0  # Reset if moving
        
        self.previous_positions[drone_id] = position
    
    def is_making_progress(self):
        """Check if agent is making progress towards goal."""
        if len(self.distance_to_target_history) < 5:
            return True  # Too early to judge
        
        # Check if distance is decreasing over last 5 steps
        recent = self.distance_to_target_history[-5:]
        return recent[-1] < recent[0]  # Current < 5 steps ago
    
    def detect_action_loop(self):
        """Detect if agent is stuck in action loop (reward hacking)."""
        if not self.repeated_actions:
            return False
        
        # Allow scan/move alternation - this is correct behavior
        # Only penalize if EXACT same action+args repeated many times
        # Increased threshold from 5 to 10 to allow more exploration
        max_repeats = max(self.repeated_actions.values())
        return max_repeats > 10
    
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
    
    def record_step_reward(self, reward):
        """Accumulate per-step reward for episode-end normalization."""
        self.per_step_rewards.append(float(reward))
    
    def check_repeated_call(self, tool_name, args):
        """Returns True if this is identical to last tool call."""
        args_str = str(args)
        is_repeated = (
            self.last_tool_call == tool_name and
            self.last_tool_args == args_str
        )
        self.last_tool_call = tool_name
        self.last_tool_args = args_str
        return is_repeated

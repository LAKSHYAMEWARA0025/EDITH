class EpisodeData:
    def __init__(self):
        self.tool_calls = []
        self.collisions = 0
        self.milestones = []

    def log_tool_call(self, tool_name, args):
        self.tool_calls.append({"tool": tool_name, "args": args})

    def log_collision(self):
        self.collisions += 1

    def log_milestone(self, milestone_name):
        self.milestones.append(milestone_name)

    def record_action(self, action):
        self.tool_calls.append(action)

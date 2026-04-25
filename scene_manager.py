import pybullet as p

class SceneManager:
    def __init__(self, client_id):
        self.client_id = client_id
        self.obstacle_ids = []
        self.target_ids = []

    def place_obstacles(self, obstacle_positions):
        for pos in obstacle_positions:
            col_id = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1], physicsClientId=self.client_id)
            vis_id = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1], rgbaColor=[1, 0, 0, 1], physicsClientId=self.client_id)
            obs_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col_id, baseVisualShapeIndex=vis_id, basePosition=pos, physicsClientId=self.client_id)
            self.obstacle_ids.append(obs_id)

    def place_targets(self, target_positions):
        for pos in target_positions:
            vis_id = p.createVisualShape(p.GEOM_SPHERE, radius=0.1, rgbaColor=[0, 1, 0, 1], physicsClientId=self.client_id)
            tgt_id = p.createMultiBody(baseMass=0, baseVisualShapeIndex=vis_id, basePosition=pos, physicsClientId=self.client_id)
            self.target_ids.append(tgt_id)

    def clear_scene(self):
        for obs in self.obstacle_ids:
            p.removeBody(obs, physicsClientId=self.client_id)
        for tgt in self.target_ids:
            p.removeBody(tgt, physicsClientId=self.client_id)
        self.obstacle_ids = []
        self.target_ids = []

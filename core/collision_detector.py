import pybullet as p
import numpy as np

class CollisionDetector:
    def __init__(self, client_id):
        self.client_id = client_id
        
    def raycast(self, pos, num_rays=12, ray_length=3.0):
        """
        Casts rays radially around the position to detect nearby obstacles.
        Returns a list of distances to the nearest obstacle in each direction.
        """
        ray_from = []
        ray_to = []
        
        # Create rays in a horizontal circle around the drone
        for i in range(num_rays):
            angle = (2 * np.pi / num_rays) * i
            dx = ray_length * np.cos(angle)
            dy = ray_length * np.sin(angle)
            
            ray_from.append(pos)
            ray_to.append([pos[0] + dx, pos[1] + dy, pos[2]])
            
        results = p.rayTestBatch(ray_from, ray_to, physicsClientId=self.client_id)
        
        distances = []
        for res in results:
            hit_fraction = res[2] # fraction of ray length where collision occurred
            dist = hit_fraction * ray_length
            distances.append(dist)
            
        return distances

    def check_proximity_warning(self, pos, threshold=0.3):
        distances = self.raycast(pos)
        if min(distances) < threshold:
            return True
        return False


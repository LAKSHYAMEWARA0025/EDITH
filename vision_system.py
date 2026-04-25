import numpy as np
import cv2
import pybullet as p

class VisionSystem:
    def __init__(self, client_id):
        self.client_id = client_id
        self.lower_bound = np.array([0, 0, 0])
        self.upper_bound = np.array([255, 255, 255])

    def get_camera_masking(self, pos):
        view_matrix = p.computeViewMatrix(
            cameraEyePosition=pos,
            cameraTargetPosition=[pos[0], pos[1], pos[2]-1], 
            cameraUpVector=[0, 1, 0],
            physicsClientId=self.client_id
        )
        proj_matrix = p.computeProjectionMatrixFOV(
            fov=60.0,
            aspect=1.0,
            nearVal=0.1,
            farVal=100.0,
            physicsClientId=self.client_id
        )
        
        width, height, rgb_img, depth_img, seg_img = p.getCameraImage(
            width=320,
            height=240,
            viewMatrix=view_matrix,
            projectionMatrix=proj_matrix,
            renderer=p.ER_TINY_RENDERER, 
            physicsClientId=self.client_id
        )
        
        img = np.reshape(rgb_img, (height, width, 4))
        bgr_img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        hsv_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv_img, self.lower_bound, self.upper_bound)
        masked_img = cv2.bitwise_and(bgr_img, bgr_img, mask=mask)
        
        return {
            "image": bgr_img,
            "mask": mask,
            "masked_image": masked_img
        }

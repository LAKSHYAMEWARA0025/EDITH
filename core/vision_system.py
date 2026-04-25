import numpy as np
import cv2
import pybullet as p

class VisionSystem:
    """Vision system for detecting colored objects using OpenCV color masking."""
    
    # Exact HSV thresholds from test_07
    # Red obstacles (two ranges for red hue wrap-around)
    LOWER_RED1 = np.array([0, 100, 100])
    UPPER_RED1 = np.array([10, 255, 255])
    LOWER_RED2 = np.array([160, 100, 100])
    UPPER_RED2 = np.array([180, 255, 255])
    
    # Green targets
    LOWER_GREEN = np.array([40, 80, 80])
    UPPER_GREEN = np.array([80, 255, 255])
    
    def __init__(self, client_id):
        self.client_id = client_id

    def get_camera_frame(self, pos, width=224, height=224):
        """Capture camera frame from specified position looking down."""
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
        
        w, h, rgb_img, depth_img, seg_img = p.getCameraImage(
            width=width,
            height=height,
            viewMatrix=view_matrix,
            projectionMatrix=proj_matrix,
            renderer=p.ER_TINY_RENDERER, 
            physicsClientId=self.client_id
        )
        
        # Convert to numpy array
        img = np.reshape(rgb_img, (h, w, 4))
        rgb_frame = img[:, :, :3]  # Drop alpha channel
        
        return rgb_frame

    def detect_colored_objects(self, frame):
        """
        Detect red obstacles and green targets using HSV color masking.
        Returns list of detections with type, color, area, and bounding box.
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        
        detections = []
        
        # Detect red obstacles (two ranges for red hue wrap-around)
        mask_red1 = cv2.inRange(hsv, self.LOWER_RED1, self.UPPER_RED1)
        mask_red2 = cv2.inRange(hsv, self.LOWER_RED2, self.UPPER_RED2)
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        
        contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours_red:
            area = cv2.contourArea(cnt)
            if area > 200:  # Filter small noise
                x, y, w, h = cv2.boundingRect(cnt)
                detections.append({
                    "type": "obstacle",
                    "color": "red",
                    "area": area,
                    "bbox": [x, y, w, h],
                    "center": [x + w//2, y + h//2]
                })
        
        # Detect green targets
        mask_green = cv2.inRange(hsv, self.LOWER_GREEN, self.UPPER_GREEN)
        contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours_green:
            area = cv2.contourArea(cnt)
            if area > 200:  # Filter small noise
                x, y, w, h = cv2.boundingRect(cnt)
                detections.append({
                    "type": "target",
                    "color": "green",
                    "area": area,
                    "bbox": [x, y, w, h],
                    "center": [x + w//2, y + h//2]
                })
        
        return detections

    def estimate_distance(self, contour_area, frame_width=224):
        """
        Estimate distance to object based on contour area.
        Rough approximation: larger area = closer object.
        """
        # Calibration: 0.3m cube at 3m distance ≈ 1500 pixels
        # Distance ≈ sqrt(reference_area / contour_area) * reference_distance
        reference_area = 1500
        reference_distance = 3.0
        
        if contour_area < 50:
            return float('inf')  # Too small to estimate
        
        estimated_distance = np.sqrt(reference_area / contour_area) * reference_distance
        return estimated_distance

    def get_direction(self, bbox_center, frame_width=224):
        """
        Get direction of object relative to camera center.
        Returns: 'left', 'center', or 'right'
        """
        center_x = bbox_center[0]
        frame_center = frame_width // 2
        
        if center_x < frame_center - frame_width * 0.2:
            return "left"
        elif center_x > frame_center + frame_width * 0.2:
            return "right"
        else:
            return "center"

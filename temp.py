import pybullet as p
import pybullet_data
import time

# Connect to GUI to verify your friend's build works visually
client = p.connect(p.GUI) 
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

# Load the floor
planeId = p.loadURDF("plane.urdf")

# Load a sample box (This will be your red obstacle later)
boxId = p.loadURDF("cube_small.urdf", [0, 0, 1])

print("Environment Live! You should see a window with a floor and a cube.")
for _ in range(1000):
    p.stepSimulation()
    time.sleep(1./240.)

p.disconnect()
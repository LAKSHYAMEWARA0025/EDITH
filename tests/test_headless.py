#!/usr/bin/env python3
"""
Test script to verify EDITH works in headless mode.
Run this inside Docker container to verify PyBullet headless operation.

Usage:
    python test_headless.py
"""

import sys
import os

# Force headless mode
os.environ["EDITH_GUI"] = "false"
os.environ["DISPLAY"] = ""

print("=" * 60)
print("EDITH Headless Mode Test")
print("=" * 60)
print()

# Test 1: Import PyBullet
print("[1/5] Testing PyBullet import...")
try:
    import pybullet as p
    print("✓ PyBullet imported successfully")
except ImportError as e:
    print(f"✗ Failed to import PyBullet: {e}")
    sys.exit(1)

# Test 2: Connect in DIRECT mode (headless)
print("\n[2/5] Testing PyBullet DIRECT connection...")
try:
    client_id = p.connect(p.DIRECT)
    print(f"✓ Connected to PyBullet in DIRECT mode (client_id={client_id})")
except Exception as e:
    print(f"✗ Failed to connect: {e}")
    sys.exit(1)

# Test 3: Create simple physics simulation
print("\n[3/5] Testing physics simulation...")
try:
    p.setGravity(0, 0, -9.81, physicsClientId=client_id)
    
    # Create a simple sphere
    sphere_shape = p.createCollisionShape(p.GEOM_SPHERE, radius=0.5, physicsClientId=client_id)
    sphere_visual = p.createVisualShape(p.GEOM_SPHERE, radius=0.5, rgbaColor=[1, 0, 0, 1], physicsClientId=client_id)
    sphere_id = p.createMultiBody(
        baseMass=1.0,
        baseCollisionShapeIndex=sphere_shape,
        baseVisualShapeIndex=sphere_visual,
        basePosition=[0, 0, 2],
        physicsClientId=client_id
    )
    
    # Run simulation steps
    for _ in range(100):
        p.stepSimulation(physicsClientId=client_id)
    
    # Check position changed (fell due to gravity)
    pos, _ = p.getBasePositionAndOrientation(sphere_id, physicsClientId=client_id)
    if pos[2] < 2.0:
        print(f"✓ Physics simulation works (sphere fell from z=2.0 to z={pos[2]:.2f})")
    else:
        print(f"✗ Physics simulation may not be working (sphere at z={pos[2]:.2f})")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Physics simulation failed: {e}")
    sys.exit(1)

# Test 4: Test camera rendering (offscreen)
print("\n[4/5] Testing camera rendering (offscreen)...")
try:
    width, height = 128, 128
    view_matrix = p.computeViewMatrix(
        cameraEyePosition=[0, 0, 3],
        cameraTargetPosition=[0, 0, 0],
        cameraUpVector=[0, 0, 1],
        physicsClientId=client_id
    )
    proj_matrix = p.computeProjectionMatrixFOV(
        fov=60, aspect=1.0, nearVal=0.1, farVal=100,
        physicsClientId=client_id
    )
    
    img = p.getCameraImage(
        width, height,
        viewMatrix=view_matrix,
        projectionMatrix=proj_matrix,
        renderer=p.ER_TINY_RENDERER,  # Software renderer (no GPU)
        physicsClientId=client_id
    )
    
    if img and len(img) >= 3:
        rgb_array = img[2]  # RGB pixel data
        print(f"✓ Camera rendering works (captured {width}x{height} image)")
    else:
        print("✗ Camera rendering failed (no image data)")
        sys.exit(1)
        
except Exception as e:
    print(f"✗ Camera rendering failed: {e}")
    sys.exit(1)

# Test 5: Import and initialize EDITH environment
print("\n[5/5] Testing EDITH environment initialization...")
try:
    # Disconnect PyBullet test client
    p.disconnect(physicsClientId=client_id)
    
    # Import EDITH
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from wrapper.edith_env import EDITHDroneEnv
    
    # Initialize environment in headless mode
    env = EDITHDroneEnv(task_type="task1", gui=False)
    print("✓ EDITH environment initialized in headless mode")
    
    # Test reset
    state, info = env.reset()
    print("✓ Environment reset successful")
    
    # Test step
    action = {"name": "get_mission_status", "arguments": {}}
    state, reward, done, truncated, info = env.step(action)
    print(f"✓ Environment step successful (reward={reward:.3f})")
    
except Exception as e:
    print(f"✗ EDITH environment failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Success
print("\n" + "=" * 60)
print("✓ All headless mode tests passed!")
print("=" * 60)
print()
print("EDITH is ready for headless deployment:")
print("  • PyBullet DIRECT mode works")
print("  • Physics simulation works")
print("  • Camera rendering works (offscreen)")
print("  • EDITH environment works")
print()
print("Safe to deploy to Docker and Hugging Face Spaces!")
print()

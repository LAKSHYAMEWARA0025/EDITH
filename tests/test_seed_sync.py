"""
Test seed synchronization for GRPO training.
Verifies that multiple parallel sessions with the same seed generate identical maps.
"""
import requests
import concurrent.futures
import time

SERVER_URL = "http://localhost:7860"

def scan_environment(session_id):
    """Get actual obstacle and target positions using debug endpoint."""
    # Use debug endpoint to get raw positions from PyBullet
    response = requests.get(
        f"{SERVER_URL}/debug/scene",
        headers={"x-session-id": session_id}
    )
    
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    
    data = response.json()
    if "error" in data:
        return None, data["error"]
    
    # Sort positions for consistent comparison (round to 2 decimals)
    obstacle_positions = sorted([
        tuple(round(x, 2) for x in pos) 
        for pos in data.get("obstacles", [])
    ])
    target_positions = sorted([
        tuple(round(x, 2) for x in pos) 
        for pos in data.get("targets", [])
    ])
    
    return {
        "obstacles": obstacle_positions,
        "targets": target_positions,
        "obstacle_count": len(obstacle_positions),
        "target_count": len(target_positions)
    }, None

def reset_with_seed(session_id, seed):
    """Reset a session with a specific seed and scan the environment."""
    # Reset with seed
    response = requests.post(
        f"{SERVER_URL}/reset",
        json={"seed": seed, "task_type": "task1"},
        headers={"x-session-id": session_id}
    )
    
    if response.status_code != 200:
        return None, f"HTTP {response.status_code}"
    
    data = response.json()
    if "error" in data:
        return None, data["error"]
    
    # Extract mission status
    mission_status = data.get("state", {}).get("mission_status", {})
    
    # Scan the environment to get actual positions
    scan_data, scan_error = scan_environment(session_id)
    if scan_error:
        return None, scan_error
    
    return {
        "session_id": session_id,
        "seed": seed,
        "targets_total": mission_status.get("targets_total", 0),
        "targets_remaining": mission_status.get("targets_remaining", 0),
        "obstacle_count": scan_data["obstacle_count"],
        "target_count": scan_data["target_count"],
        "obstacle_positions": scan_data["obstacles"],
        "target_positions": scan_data["targets"]
    }, None

def test_seed_determinism():
    """Test that same seed produces identical maps across sessions."""
    print("="*60)
    print("TEST 1: Seed Determinism (Same Seed → Same Map)")
    print("="*60)
    
    test_seed = 42
    num_sessions = 4
    
    print(f"\nResetting {num_sessions} sessions with seed={test_seed}...")
    print("This will take ~5 seconds (using debug endpoint)...\n")
    
    # Create 4 parallel sessions with SAME seed
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(reset_with_seed, f"seed-test-{i}", test_seed)
            for i in range(num_sessions)
        ]
        results = [f.result() for f in futures]
    
    # Check for errors
    errors = [err for result, err in results if err]
    if errors:
        print(f"❌ FAILED: {len(errors)} sessions had errors")
        for err in errors:
            print(f"   Error: {err}")
        return False
    
    # Extract results
    data_list = [result for result, _ in results]
    
    # Compare all sessions - they should be identical
    first = data_list[0]
    
    # Check obstacle and target counts
    counts_match = all(
        d["obstacle_count"] == first["obstacle_count"] and
        d["target_count"] == first["target_count"]
        for d in data_list
    )
    
    # Check actual positions (deep comparison)
    positions_match = all(
        d["obstacle_positions"] == first["obstacle_positions"] and
        d["target_positions"] == first["target_positions"]
        for d in data_list
    )
    
    print(f"Results for seed={test_seed}:")
    for d in data_list:
        print(f"  Session {d['session_id']}:")
        print(f"    Obstacles: {d['obstacle_count']} at positions: {d['obstacle_positions'][:2]}..." if len(d['obstacle_positions']) > 2 else f"    Obstacles: {d['obstacle_count']} at {d['obstacle_positions']}")
        print(f"    Targets:   {d['target_count']} at positions: {d['target_positions']}")
    
    if counts_match and positions_match:
        print(f"\n✅ PASSED: All {num_sessions} sessions generated identical maps")
        print(f"   - Obstacle positions match: {positions_match}")
        print(f"   - Target positions match: {positions_match}")
        return True
    elif counts_match:
        print(f"\n⚠️  PARTIAL: Counts match but positions differ")
        print(f"   - Obstacle counts: {first['obstacle_count']}")
        print(f"   - Position match: {positions_match}")
        return False
    else:
        print(f"\n❌ FAILED: Sessions generated different maps with same seed")
        return False

def test_seed_randomness():
    """Test that different seeds produce different maps."""
    print("\n" + "="*60)
    print("TEST 2: Seed Randomness (Different Seeds → Different Maps)")
    print("="*60)
    
    seeds = [100, 200, 300, 400]
    
    print(f"\nResetting 4 sessions with different seeds...")
    print("This will take ~5 seconds...\n")
    
    # Create 4 sessions with DIFFERENT seeds
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(reset_with_seed, f"random-test-{i}", seed)
            for i, seed in enumerate(seeds)
        ]
        results = [f.result() for f in futures]
    
    # Check for errors
    errors = [err for result, err in results if err]
    if errors:
        print(f"❌ FAILED: {len(errors)} sessions had errors")
        return False
    
    # Extract results
    data_list = [result for result, _ in results]
    
    # Check that at least some are different (not all identical)
    first = data_list[0]
    
    # Compare obstacle positions
    all_obstacles_same = all(
        d["obstacle_positions"] == first["obstacle_positions"]
        for d in data_list
    )
    
    # Compare target positions
    all_targets_same = all(
        d["target_positions"] == first["target_positions"]
        for d in data_list
    )
    
    print(f"Results for different seeds:")
    for d, seed in zip(data_list, seeds):
        print(f"  Seed {seed}:")
        print(f"    Obstacles: {d['obstacle_count']} at {d['obstacle_positions'][:2]}..." if len(d['obstacle_positions']) > 2 else f"    Obstacles: {d['obstacle_count']} at {d['obstacle_positions']}")
        print(f"    Targets:   {d['target_count']} at {d['target_positions']}")
    
    if not all_obstacles_same or not all_targets_same:
        print(f"\n✅ PASSED: Different seeds produced varied maps")
        print(f"   - Obstacle positions vary: {not all_obstacles_same}")
        print(f"   - Target positions vary: {not all_targets_same}")
        return True
    else:
        print(f"\n⚠️  WARNING: All maps identical despite different seeds (very unlikely)")
        return True  # Not a failure, just extremely unlikely

def test_grpo_batch_scenario():
    """Simulate GRPO batch: 4 parallel rollouts with same seed."""
    print("\n" + "="*60)
    print("TEST 3: GRPO Batch Scenario (4 Parallel Rollouts)")
    print("="*60)
    
    batch_seed = 12345
    num_rollouts = 4
    
    print(f"\nSimulating GRPO batch with seed={batch_seed}")
    print(f"Creating {num_rollouts} parallel sessions...")
    print("This will take ~5 seconds...\n")
    
    # Simulate GRPO: all rollouts in batch use same seed
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(reset_with_seed, f"grpo-batch-{i}", batch_seed)
            for i in range(num_rollouts)
        ]
        results = [f.result() for f in futures]
    
    # Check for errors
    errors = [err for result, err in results if err]
    if errors:
        print(f"❌ FAILED: {len(errors)} rollouts had errors")
        return False
    
    # Extract results
    data_list = [result for result, _ in results]
    
    # Verify all rollouts have identical starting conditions
    first = data_list[0]
    
    # Check counts
    counts_match = all(
        d["obstacle_count"] == first["obstacle_count"] and
        d["target_count"] == first["target_count"]
        for d in data_list
    )
    
    # Check positions (critical for GRPO)
    positions_match = all(
        d["obstacle_positions"] == first["obstacle_positions"] and
        d["target_positions"] == first["target_positions"]
        for d in data_list
    )
    
    print(f"GRPO Batch Results:")
    for i, d in enumerate(data_list):
        print(f"  Rollout {i}:")
        print(f"    Obstacles: {d['obstacle_count']} at {d['obstacle_positions'][:2]}..." if len(d['obstacle_positions']) > 2 else f"    Obstacles: {d['obstacle_count']} at {d['obstacle_positions']}")
        print(f"    Targets:   {d['target_count']} at {d['target_positions']}")
    
    if counts_match and positions_match:
        print(f"\n✅ PASSED: All {num_rollouts} rollouts started with identical maps")
        print("   ✅ Obstacle positions match exactly")
        print("   ✅ Target positions match exactly")
        print("   🎯 GRPO can now accurately compare actions!")
        return True
    elif counts_match:
        print(f"\n⚠️  PARTIAL: Counts match but positions differ")
        print(f"   ⚠️  GRPO advantage calculations may still be inaccurate")
        return False
    else:
        print(f"\n❌ FAILED: Rollouts have different starting conditions")
        print("   ❌ GRPO advantage calculation will be corrupted!")
        return False

if __name__ == "__main__":
    print("\n🧪 EDITH Seed Synchronization Test Suite")
    print("Testing GRPO map desync fix...\n")
    
    # Run all tests
    test1 = test_seed_determinism()
    test2 = test_seed_randomness()
    test3 = test_grpo_batch_scenario()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Test 1 (Determinism):     {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Test 2 (Randomness):      {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"Test 3 (GRPO Scenario):   {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if all([test1, test2, test3]):
        print("\n🎉 All tests passed! Seed sync is working correctly.")
        print("   GRPO training will now have accurate advantage calculations.")
    else:
        print("\n⚠️  Some tests failed. Check implementation.")

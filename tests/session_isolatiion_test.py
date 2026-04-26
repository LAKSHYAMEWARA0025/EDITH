import requests
import concurrent.futures

def test_session(session_num):
    # Each session gets unique ID
    session_id = f"test-session-{session_num}"
    
    # Reset
    resp = requests.post(
        "http://localhost:7860/reset",
        headers={"x-session-id": session_id}
    )
    print(f"Session {session_num}: {resp.json().get('session_id')}")
    return resp.status_code == 200

# Test 4 parallel sessions
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(test_session, range(4)))
    print(f"Success: {sum(results)}/4")

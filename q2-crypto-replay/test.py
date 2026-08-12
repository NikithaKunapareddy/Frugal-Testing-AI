import requests
import time
import hmac
import hashlib
import json
import sys

BASE_URL = "http://localhost:3006/api/transaction"

def run_q2_automation():
    print("[*] Starting Q2: Cryptographic Replay Testing")
    
    # 1. Dynamic Sequence Chaining
    print("[automation] POST /api/transaction to generate initial wrapper...")
    try:
        post_res = requests.post(BASE_URL)
    except requests.exceptions.ConnectionError:
        print("[-] Connection failed. Is the Node.js server running on port 3006?")
        sys.exit(1)
        
    if post_res.status_code != 201:
        print(f"[-] Failed to generate transaction: {post_res.text}")
        sys.exit(1)
        
    tx_data = post_res.json()
    tx_id = tx_data["transaction_id"]
    challenge_token = post_res.headers.get("X-Challenge-Token")
    
    print(f"[+] Extracted Transaction ID: {tx_id}")
    print(f"[+] Extracted Challenge Token (Salt): {challenge_token}")

    # 2. Cryptographic Nonce Injection
    timestamp = str(int(time.time() * 1000000))
    
    update_payload = {"amount": 500, "currency": "USD", "action": "CONFIRM"}
    serialized_body = json.dumps(update_payload, separators=(',', ':'))
    
    payload_to_hash = challenge_token + timestamp + serialized_body
    mac = hmac.new(challenge_token.encode('utf-8'), payload_to_hash.encode('utf-8'), hashlib.sha512).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Frugal-Mac": mac
    }
    
    print(f"\n[automation] Generating Cryptographic Payload...")
    print(f"    - Timestamp: {timestamp}")
    print(f"    - Computed HMAC: {mac}")
    
    print(f"\n[automation] Submitting initial PUT request...")
    put_url = f"{BASE_URL}/{tx_id}"
    
    put_res = requests.put(put_url, headers=headers, data=serialized_body)
    
    print(f"[+] Initial PUT Response: {put_res.status_code} {put_res.text}")
    if put_res.status_code != 200:
        print("[-] Signature validation failed on backend. Test aborted.")
        sys.exit(1)

    # 3. The Replay Attack Vector
    print(f"\n[automation] Injecting Replay Attack Vector (Exact duplication within 150ms)...")
    replay_res = requests.put(put_url, headers=headers, data=serialized_body)
    
    print(f"[+] Replay PUT Response: {replay_res.status_code} {replay_res.text}")

    # 4. Assertion Layer
    print("\n================ Q2 RESULT SUMMARY ================")
    if replay_res.status_code == 409:
        print("  [PASS] Backend correctly identified and rejected the replay attack (409 Conflict).")
        print("  [PASS] Stateful Nonces & Hash-Chain API Chaining successful.")
    elif replay_res.status_code in [200, 201]:
        print("  [FAIL] HIGH-RISK DATA-MUTATION VULNERABILITY! Backend accepted duplicated payload.")
    else:
        print(f"  [WARN] Unexpected status code: {replay_res.status_code}")
    print("=====================================================")

if __name__ == "__main__":
    run_q2_automation()

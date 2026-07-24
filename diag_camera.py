"""Raw camera diagnostic — bypasses pytapo to show what the camera actually returns."""
import json
import hashlib
import requests
import urllib3
urllib3.disable_warnings()

CAMERAS = {
    "Jiu-Jitsu Room 1": "192.168.0.190",
    "Jiu-Jitsu Room 2": "192.168.0.24",
}

cam_pass = input("Camera account password: ").strip()

def check(ip, password):
    # 1. Basic HTTPS reachability
    try:
        r = requests.get(f"https://{ip}/", verify=False, timeout=5)
        print(f"  HTTPS GET /  → {r.status_code}")
    except Exception as e:
        print(f"  HTTPS GET /  → {type(e).__name__}: {e}")

    # 2. Raw login attempt (legacy protocol)
    try:
        payload = {
            "method": "login",
            "params": {
                "username": "admin",
                "password": hashlib.md5(password.encode()).hexdigest().upper(),
            }
        }
        r = requests.post(f"https://{ip}", json=payload, verify=False, timeout=5)
        print(f"  login (MD5)  → {r.status_code}  {r.text[:300]}")
    except Exception as e:
        print(f"  login (MD5)  → {type(e).__name__}: {e}")

    # 3. Secure passthrough (newer protocol)
    try:
        payload = {"method": "securePassthrough", "params": {"request": ""}}
        r = requests.post(f"https://{ip}", json=payload, verify=False, timeout=5)
        print(f"  securePass   → {r.status_code}  {r.text[:300]}")
    except Exception as e:
        print(f"  securePass   → {type(e).__name__}: {e}")

for name, ip in CAMERAS.items():
    print(f"\n{'─'*55}")
    print(f"  {name}  ({ip})")
    print(f"{'─'*55}")
    check(ip, cam_pass)

print()

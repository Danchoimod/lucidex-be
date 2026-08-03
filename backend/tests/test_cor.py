import json
import urllib.request
import urllib.error

url = "https://api-1027239076774.asia-southeast1.run.app/api/v1/admin/auth/login"
origin = "http://localhost:3000"

print("=== 1. PREFLIGHT TEST (OPTIONS) ===")
req_options = urllib.request.Request(
    url,
    headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type, authorization",
    },
    method="OPTIONS",
)

try:
    with urllib.request.urlopen(req_options) as response:
        print(f"Status Code: {response.status}")
        print("CORS Headers:")
        for k, v in response.headers.items():
            if "access-control" in k.lower():
                print(f"  {k}: {v}")
except urllib.error.HTTPError as e:
    print(f"Preflight Failed: HTTP {e.code}")

print("\n=== 2. ADMIN LOGIN TEST (POST) ===")
payload = json.dumps({"username": "admin", "password": "password"}).encode("utf-8")
req_post = urllib.request.Request(
    url,
    data=payload,
    headers={
        "Origin": origin,
        "Content-Type": "application/json",
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req_post) as response:
        print(f"Status Code: {response.status}")
        print("Body:", response.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"Status Code: {e.code}")
    print("CORS Headers:")
    for k, v in e.headers.items():
        if "access-control" in k.lower():
            print(f"  {k}: {v}")
    print("Body:", e.read().decode("utf-8"))

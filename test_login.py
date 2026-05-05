import requests
BASE_URL = "http://127.0.0.1:8001"
res = requests.post(f"{BASE_URL}/auth/login", json={"email": "e2e_test_1777946594@devforge.app", "password": "TestPassword123!"})
print(res.status_code)
print(res.text)

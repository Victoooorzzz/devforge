import os
import requests

token = os.getenv("VERCEL_TOKEN")
if not token:
    print("No VERCEL_TOKEN found")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}
r = requests.get("https://api.vercel.com/v9/projects", headers=headers)

if r.status_code == 200:
    projects = r.json().get("projects", [])
    for p in projects:
        print(f"Name: {p['name']}, ID: {p['id']}")
else:
    print(f"Error: {r.status_code}")
    print(r.text)

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = "https://api.cron-job.org"
BACKEND_URL = "https://devforge-universal-backend.onrender.com"
POST = 1
GET = 0


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def required_secret(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = values.get(name)
        if value:
            return value
    raise RuntimeError(f"Missing required env var. Tried: {', '.join(names)}")


def cron_api_key(values: dict[str, str]) -> str:
    return required_secret(values, "CRONJOB_API_KEY", "CRON_JOB_API_KEY", "CRONJOB_PK", "CRON_SECRET")


def cron_secret(values: dict[str, str]) -> str:
    return required_secret(values, "CRON_SECRET")


def api_request(api_key: str, path: str, method: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(f"{BASE_URL}{path}", headers=headers, data=body, method=method)
    with urllib.request.urlopen(request, context=ssl._create_unverified_context(), timeout=60) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def backend_request(url: str, method: str, authorization: str | None = None) -> tuple[int, str]:
    headers = {"Authorization": authorization} if authorization else {}
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.getcode(), response.read().decode("utf-8")[:1200]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")[:1200]


def job_specs(secret: str) -> list[dict[str, Any]]:
    auth_header = f"Bearer {secret}"
    common = {
        "enabled": True,
        "saveResponses": True,
        "requestMethod": POST,
        "requestTimeout": 300,
        "extendedData": {"headers": {"Authorization": auth_header}, "body": ""},
    }
    return [
        {
            **common,
            "title": "DevForge worker enqueue periodic",
            "url": f"{BACKEND_URL}/worker/enqueue-periodic",
            "schedule": {
                "timezone": "America/Lima",
                "expiresAt": 0,
                "hours": [-1],
                "minutes": [0],
                "mdays": [-1],
                "months": [-1],
                "wdays": [-1],
            },
        },
        {
            **common,
            "title": "DevForge worker process queue",
            "url": f"{BACKEND_URL}/worker/process",
            "schedule": {
                "timezone": "America/Lima",
                "expiresAt": 0,
                "hours": [-1],
                "minutes": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
                "mdays": [-1],
                "months": [-1],
                "wdays": [-1],
            },
        },
        {
            **common,
            "title": "DevForge worker cleanup",
            "url": f"{BACKEND_URL}/worker/cleanup",
            "schedule": {
                "timezone": "America/Lima",
                "expiresAt": 0,
                "hours": [3],
                "minutes": [0],
                "mdays": [-1],
                "months": [-1],
                "wdays": [-1],
            },
        },
    ]


def list_jobs(api_key: str) -> list[dict[str, Any]]:
    return api_request(api_key, "/jobs", "GET").get("jobs", [])


def job_details(api_key: str, job_id: int) -> dict[str, Any]:
    return api_request(api_key, f"/jobs/{job_id}", "GET").get("jobDetails", {})


def job_history(api_key: str, job_id: int) -> list[dict[str, Any]]:
    return api_request(api_key, f"/jobs/{job_id}/history", "GET").get("history", [])


def print_inventory(api_key: str) -> None:
    jobs = list_jobs(api_key)
    print(f"Found {len(jobs)} cron-job.org jobs.")
    for job in jobs:
        details = job_details(api_key, int(job["jobId"]))
        headers = (details.get("extendedData") or {}).get("headers") or {}
        history = job_history(api_key, int(job["jobId"]))
        last = history[0] if history else {}
        print(
            json.dumps(
                {
                    "jobId": details.get("jobId"),
                    "title": details.get("title"),
                    "enabled": details.get("enabled"),
                    "url": details.get("url"),
                    "method": "POST" if details.get("requestMethod") == POST else "GET",
                    "lastStatus": details.get("lastStatus"),
                    "lastHistory": {
                        "status": last.get("status"),
                        "statusText": last.get("statusText"),
                        "httpStatus": last.get("httpStatus"),
                    }
                    if last
                    else None,
                    "nextExecution": details.get("nextExecution"),
                    "hasAuthorizationHeader": "Authorization" in headers,
                    "schedule": details.get("schedule"),
                },
                ensure_ascii=False,
            )
        )
        time.sleep(0.25)


def sync_jobs(api_key: str, secret: str) -> None:
    existing = {job.get("url"): job for job in list_jobs(api_key)}
    for spec in job_specs(secret):
        payload = {"job": spec}
        existing_job = existing.get(spec["url"])
        if existing_job:
            job_id = int(existing_job["jobId"])
            api_request(api_key, f"/jobs/{job_id}", "PATCH", payload)
            print(f"updated jobId={job_id} title={spec['title']}")
        else:
            response = api_request(api_key, "/jobs", "PUT", payload)
            print(f"created jobId={response.get('jobId')} title={spec['title']}")
        time.sleep(1.1)


def test_backend_endpoints(secret: str) -> bool:
    ok = True
    checks = [
        ("GET", f"{BACKEND_URL}/health", None),
        ("POST", f"{BACKEND_URL}/worker/enqueue-periodic", f"Bearer {secret}"),
        ("POST", f"{BACKEND_URL}/worker/process", f"Bearer {secret}"),
        ("POST", f"{BACKEND_URL}/worker/cleanup", f"Bearer {secret}"),
    ]
    for method, url, auth in checks:
        status, body = backend_request(url, method, auth)
        expected = 200 if method == "GET" else None
        if url.endswith("/worker/process") or url.endswith("/worker/cleanup"):
            expected = 200
        if url.endswith("/worker/enqueue-periodic"):
            expected = 200
        passed = status == expected
        ok = ok and passed
        print(json.dumps({"url": url, "method": method, "status": status, "ok": passed, "body": body}, ensure_ascii=False))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="List, sync, and test DevForge cron-job.org jobs.")
    parser.add_argument("action", choices=["list", "sync", "test", "all"], nargs="?", default="list")
    args = parser.parse_args()

    values = load_env()
    api_key = cron_api_key(values)
    secret = cron_secret(values)

    if args.action in {"list", "all"}:
        print_inventory(api_key)
    if args.action in {"sync", "all"}:
        sync_jobs(api_key, secret)
    if args.action in {"test", "all"}:
        return 0 if test_backend_endpoints(secret) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

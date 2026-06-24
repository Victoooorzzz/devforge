from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


DEFAULT_API_URL = "https://feedbacklens.devforgeapp.pro"
CONFIG_DIR = Path(os.getenv("FEEDBACKLENS_CONFIG_DIR", Path.home() / ".feedbacklens"))
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_config() -> dict[str, str]:
    config = {"api_url": os.getenv("FEEDBACKLENS_API_URL", DEFAULT_API_URL), "api_key": os.getenv("FEEDBACKLENS_API_KEY", "")}
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            config.update({key: str(value) for key, value in saved.items() if value})
        except Exception:
            pass
    return config


def save_config(api_key: str, api_url: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"api_key": api_key, "api_url": api_url}, indent=2), encoding="utf-8")


def api_request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    config = load_config()
    api_key = config.get("api_key", "")
    if not api_key:
        raise SystemExit("Missing API key. Run `feedbacklens login --api-key KEY` or set FEEDBACKLENS_API_KEY.")

    base_url = config.get("api_url", DEFAULT_API_URL).rstrip("/")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        raise SystemExit(f"HTTP {exc.code}: {raw}") from exc
    return json.loads(raw) if raw else {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="feedbacklens")
    parser.add_argument("--api-url", default=None, help="Override API base URL for this command.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    login = subcommands.add_parser("login")
    login.add_argument("--api-key", required=True)

    sources = subcommands.add_parser("sources")
    source_commands = sources.add_subparsers(dest="source_command", required=True)
    source_add = source_commands.add_parser("add")
    source_add.add_argument("--type", required=True, choices=["twitter", "reddit", "github", "canny", "email", "manual"])
    source_add.add_argument("--handle", default="")
    source_add.add_argument("--repo", default="")
    source_add.add_argument("--token", default="")
    source_commands.add_parser("list")

    feedback = subcommands.add_parser("feedback")
    feedback_commands = feedback.add_subparsers(dest="feedback_command", required=True)
    feedback_list = feedback_commands.add_parser("list")
    feedback_list.add_argument("--priority", default="")
    feedback_list.add_argument("--source", default="")

    clusters = subcommands.add_parser("clusters")
    cluster_commands = clusters.add_subparsers(dest="cluster_command", required=True)
    cluster_list = cluster_commands.add_parser("list")
    cluster_list.add_argument("--days", default="30")
    cluster_issue = cluster_commands.add_parser("create-issue")
    cluster_issue.add_argument("--id", required=True)
    cluster_issue.add_argument("--repo", required=True)

    return parser


def run(argv: list[str] | None = None, request_func: Callable[[str, str, dict[str, Any] | None], Any] = api_request) -> Any:
    args = build_parser().parse_args(argv)
    if args.api_url:
        os.environ["FEEDBACKLENS_API_URL"] = args.api_url

    if args.command == "login":
        save_config(args.api_key, args.api_url or os.getenv("FEEDBACKLENS_API_URL", DEFAULT_API_URL))
        return {"status": "ok", "config_path": str(CONFIG_PATH)}

    if args.command == "sources":
        if args.source_command == "list":
            return request_func("GET", "/sources", None)
        if args.source_command == "add":
            label = args.handle or args.repo or args.type
            payload = {"source_type": args.type, "display_name": label}
            if args.handle:
                payload["handle"] = args.handle
            if args.repo:
                payload["repo"] = args.repo
            if args.token:
                payload["access_token"] = args.token
            return request_func("POST", "/sources", payload)

    if args.command == "feedback":
        if args.feedback_command == "list":
            params = []
            if args.priority:
                params.append(f"priority={args.priority}")
            if args.source:
                params.append(f"source={args.source}")
            suffix = f"?{'&'.join(params)}" if params else ""
            return request_func("GET", f"/feedback/list{suffix}", None)

    if args.command == "clusters":
        if args.cluster_command == "list":
            return request_func("GET", f"/clusters?days={args.days}", None)
        if args.cluster_command == "create-issue":
            return request_func("POST", f"/clusters/{args.id}/github-issue", {"repo": args.repo})

    raise SystemExit("Unsupported command")


def main() -> None:
    result = run(sys.argv[1:])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()


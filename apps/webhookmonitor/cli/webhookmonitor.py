from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


DEFAULT_API_URL = "https://webhookmonitor.devforgeapp.pro"
CONFIG_DIR = Path(os.getenv("WEBHOOKMONITOR_CONFIG_DIR", Path.home() / ".webhookmonitor"))
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_config() -> dict[str, str]:
    config = {"api_url": os.getenv("WEBHOOKMONITOR_API_URL", DEFAULT_API_URL), "api_key": os.getenv("WEBHOOKMONITOR_API_KEY", "")}
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
        raise SystemExit("Missing API key. Run `webhookmonitor login --api-key KEY` or set WEBHOOKMONITOR_API_KEY.")

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
    parser = argparse.ArgumentParser(prog="webhookmonitor")
    parser.add_argument("--api-url", default=None, help="Override API base URL for this command.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    login = subcommands.add_parser("login")
    login.add_argument("--api-key", required=True)

    endpoints = subcommands.add_parser("endpoints")
    endpoint_commands = endpoints.add_subparsers(dest="endpoint_command", required=True)
    endpoint_commands.add_parser("list")
    endpoint_create = endpoint_commands.add_parser("create")
    endpoint_create.add_argument("--name", required=True)
    endpoint_create.add_argument("--method", action="append", dest="methods", default=None)

    events = subcommands.add_parser("events")
    event_commands = events.add_subparsers(dest="event_command", required=True)
    event_list = event_commands.add_parser("list")
    event_list.add_argument("--endpoint", required=True, type=int)
    event_list.add_argument("--status", default="all")

    replay = event_commands.add_parser("replay")
    replay.add_argument("--id", required=True, type=int)
    replay.add_argument("--url", default="")
    replay.add_argument("--body-file", default="")
    replay.add_argument("--headers-json", default="")

    diff = event_commands.add_parser("diff")
    diff.add_argument("--id", required=True, type=int)
    diff.add_argument("--with", dest="base_id", required=True, type=int)

    search = event_commands.add_parser("search")
    search.add_argument("--json-path", default="")
    search.add_argument("--equals", default=None)
    search.add_argument("--status", default="all")
    search.add_argument("--method", default="")
    search.add_argument("--provider", default="")
    search.add_argument("--date-from", default=None)
    search.add_argument("--date-to", default=None)

    return parser


def run(argv: list[str] | None = None, request_func: Callable[[str, str, dict[str, Any] | None], Any] = api_request) -> Any:
    args = build_parser().parse_args(argv)
    if args.api_url:
        os.environ["WEBHOOKMONITOR_API_URL"] = args.api_url

    if args.command == "login":
        save_config(args.api_key, args.api_url or os.getenv("WEBHOOKMONITOR_API_URL", DEFAULT_API_URL))
        return {"status": "ok", "config_path": str(CONFIG_PATH)}

    if args.command == "endpoints":
        if args.endpoint_command == "list":
            return request_func("GET", "/webhooks/endpoints", None)
        if args.endpoint_command == "create":
            return request_func(
                "POST",
                "/webhooks/endpoints",
                {"name": args.name, "methods": args.methods or ["POST", "PUT", "PATCH", "DELETE"]},
            )

    if args.command == "events":
        if args.event_command == "list":
            return request_func("GET", f"/webhooks/endpoints/{args.endpoint}/events?status={args.status}", None)
        if args.event_command == "replay":
            body_override = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else None
            headers_override = json.loads(args.headers_json) if args.headers_json else None
            mode = "alternate" if args.url else ("modified" if body_override or headers_override else "exact")
            return request_func(
                "POST",
                f"/webhooks/events/{args.id}/replay",
                {
                    "mode": mode,
                    "target_url": args.url,
                    "body_override": body_override,
                    "headers_override": headers_override,
                },
            )
        if args.event_command == "diff":
            return request_func("GET", f"/webhooks/events/{args.id}/diff?base_request_id={args.base_id}", None)
        if args.event_command == "search":
            return request_func(
                "POST",
                "/webhooks/search",
                {
                    "json_path": args.json_path,
                    "equals": args.equals,
                    "status": args.status,
                    "method": args.method,
                    "provider": args.provider,
                    "date_from": args.date_from,
                    "date_to": args.date_to,
                },
            )

    raise SystemExit("Unsupported command")


def main() -> None:
    result = run(sys.argv[1:])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

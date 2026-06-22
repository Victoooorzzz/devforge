from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


"""
Examples:
  invoicefollow login --api-key KEY
  invoicefollow invoices list --status pending
  invoicefollow invoices create --client "Acme" --amount 4800 --currency USD --due 2024-07-15
  invoicefollow invoices mark-paid --id INV-001
  invoicefollow invoices pause --id INV-001
  invoicefollow templates list
  invoicefollow templates edit --id friendly --file template.txt
"""

DEFAULT_API_URL = "https://invoicefollow.devforgeapp.pro"
CONFIG_DIR = Path(os.getenv("INVOICEFOLLOW_CONFIG_DIR", Path.home() / ".invoicefollow"))
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_config() -> dict[str, str]:
    config = {"api_url": os.getenv("INVOICEFOLLOW_API_URL", DEFAULT_API_URL), "api_key": os.getenv("INVOICEFOLLOW_API_KEY", "")}
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
        raise SystemExit("Missing API key. Run `invoicefollow login --api-key KEY` or set INVOICEFOLLOW_API_KEY.")

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
    parser = argparse.ArgumentParser(prog="invoicefollow")
    parser.add_argument("--api-url", default=None, help="Override API base URL for this command.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    login = subcommands.add_parser("login")
    login.add_argument("--api-key", required=True)

    invoices = subcommands.add_parser("invoices")
    invoice_commands = invoices.add_subparsers(dest="invoice_command", required=True)
    invoice_list = invoice_commands.add_parser("list")
    invoice_list.add_argument("--status", default=None)
    invoice_create = invoice_commands.add_parser("create")
    invoice_create.add_argument("--client", required=True)
    invoice_create.add_argument("--email", required=True)
    invoice_create.add_argument("--amount", required=True, type=float)
    invoice_create.add_argument("--currency", required=True)
    invoice_create.add_argument("--due", required=True)
    invoice_create.add_argument("--number", default="")
    invoice_create.add_argument("--issued", default=None)
    invoice_create.add_argument("--notes", default="")
    invoice_mark_paid = invoice_commands.add_parser("mark-paid")
    invoice_mark_paid.add_argument("--id", required=True)
    invoice_pause = invoice_commands.add_parser("pause")
    invoice_pause.add_argument("--id", required=True)

    templates = subcommands.add_parser("templates")
    template_commands = templates.add_subparsers(dest="template_command", required=True)
    template_commands.add_parser("list")
    template_edit = template_commands.add_parser("edit")
    template_edit.add_argument("--id", required=True)
    template_edit.add_argument("--file", required=True)
    template_edit.add_argument("--subject", default=None)
    template_edit.add_argument("--disabled", action="store_true")

    return parser


def run(argv: list[str] | None = None, request_func: Callable[[str, str, dict[str, Any] | None], Any] = api_request) -> Any:
    args = build_parser().parse_args(argv)
    if args.api_url:
        os.environ["INVOICEFOLLOW_API_URL"] = args.api_url

    if args.command == "login":
        save_config(args.api_key, args.api_url or os.getenv("INVOICEFOLLOW_API_URL", DEFAULT_API_URL))
        return {"status": "ok", "config_path": str(CONFIG_PATH)}

    if args.command == "invoices":
        if args.invoice_command == "list":
            suffix = f"?status={args.status}" if args.status else ""
            return request_func("GET", f"/invoices{suffix}", None)
        if args.invoice_command == "create":
            return request_func(
                "POST",
                "/invoices",
                {
                    "client_name": args.client,
                    "client_email": args.email,
                    "amount": args.amount,
                    "currency": args.currency,
                    "due_date": args.due,
                    "issued_date": args.issued,
                    "invoice_number": args.number,
                    "notes": args.notes,
                },
            )
        if args.invoice_command == "mark-paid":
            return request_func("POST", f"/invoices/{args.id}/mark-paid", None)
        if args.invoice_command == "pause":
            return request_func("POST", f"/invoices/{args.id}/pause", None)

    if args.command == "templates":
        if args.template_command == "list":
            return request_func("GET", "/templates", None)
        if args.template_command == "edit":
            body = Path(args.file).read_text(encoding="utf-8")
            return request_func(
                "PUT",
                f"/templates/{args.id}",
                {"subject": args.subject, "body": body, "enabled": not args.disabled},
            )

    raise SystemExit("Unsupported command")


def main() -> None:
    result = run(sys.argv[1:])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

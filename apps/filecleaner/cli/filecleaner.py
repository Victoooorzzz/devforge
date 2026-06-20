#!/usr/bin/env python3
"""FileCleaner CLI for the production API workflow."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import uuid


CANCEL_ENDPOINT_TEMPLATE = "/files/{id}/cancel"


def _read_json(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _headers(token: str | None, *, content_type: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _multipart(fields: dict[str, str], files: dict[str, Path]) -> tuple[bytes, str]:
    boundary = f"----devforge-filecleaner-{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ])

    for name, path in files.items():
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {media_type}\r\n\r\n".encode(),
            path.read_bytes(),
            b"\r\n",
        ])

    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def _request(base_url: str, method: str, path: str, token: str | None, *, body: bytes | None = None, content_type: str | None = None) -> bytes:
    url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    request = Request(url, method=method, data=body, headers=_headers(token, content_type=content_type))
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {detail}") from exc


def _print_json(payload: bytes) -> None:
    try:
        print(json.dumps(json.loads(payload.decode("utf-8")), indent=2))
    except json.JSONDecodeError:
        print(payload.decode("utf-8", errors="replace"))


def cmd_analyze(args: argparse.Namespace) -> None:
    body, content_type = _multipart({}, {"file": Path(args.file)})
    _print_json(_request(args.base_url, "POST", "/files/analyze", args.token, body=body, content_type=content_type))


def cmd_upload(args: argparse.Namespace) -> None:
    config = _read_json(args.config)
    fields = {"config_json": json.dumps(config)}
    if args.notify_email:
        fields["notify_email"] = args.notify_email
    if args.notify_webhook_url:
        fields["notify_webhook_url"] = args.notify_webhook_url
    body, content_type = _multipart(fields, {"file": Path(args.file)})
    _print_json(_request(args.base_url, "POST", "/files/upload", args.token, body=body, content_type=content_type))


def cmd_status(args: argparse.Namespace) -> None:
    _print_json(_request(args.base_url, "GET", f"/files/{args.id}/status", args.token))


def cmd_report(args: argparse.Namespace) -> None:
    _print_json(_request(args.base_url, "GET", f"/files/{args.id}/report", args.token))


def cmd_cancel(args: argparse.Namespace) -> None:
    _print_json(_request(args.base_url, "POST", CANCEL_ENDPOINT_TEMPLATE.format(id=args.id), args.token))


def cmd_download(args: argparse.Namespace) -> None:
    payload = _request(args.base_url, "GET", f"/files/{args.id}/download", args.token)
    output = Path(args.output)
    output.write_bytes(payload)
    print(json.dumps({"downloaded": str(output), "bytes": output.stat().st_size}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FileCleaner API CLI")
    parser.add_argument("--base-url", default=os.getenv("FILECLEANER_API_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.getenv("FILECLEANER_TOKEN"))
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="POST /files/analyze")
    analyze.add_argument("file")
    analyze.set_defaults(func=cmd_analyze)

    upload = sub.add_parser("upload", help="POST /files/upload")
    upload.add_argument("file")
    upload.add_argument("--config", help="Path to config_json file")
    upload.add_argument("--notify-email")
    upload.add_argument("--notify-webhook-url")
    upload.set_defaults(func=cmd_upload)

    status = sub.add_parser("status", help="GET /files/{id}/status")
    status.add_argument("id")
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="GET /files/{id}/report")
    report.add_argument("id")
    report.set_defaults(func=cmd_report)

    cancel = sub.add_parser("cancel", help="POST /files/{id}/cancel")
    cancel.add_argument("id")
    cancel.set_defaults(func=cmd_cancel)

    download = sub.add_parser("download", help="GET /files/{id}/download")
    download.add_argument("id")
    download.add_argument("--output", required=True)
    download.set_defaults(func=cmd_download)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

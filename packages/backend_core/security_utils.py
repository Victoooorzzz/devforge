import ipaddress
import socket
from urllib.parse import urlparse


_BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_public_http_url(value: str | None) -> bool:
    if not value:
        return False

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    host = parsed.hostname.strip().lower().rstrip(".")
    if host in _BLOCKED_HOSTS or host.endswith(".localhost") or host.endswith(".local"):
        return False

    try:
        return _is_public_ip(host)
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    resolved_ips = {info[4][0] for info in resolved if info and info[4]}
    if not resolved_ips:
        return False

    return all(_is_public_ip(ip) for ip in resolved_ips)

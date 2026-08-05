"""Validation helpers for fetching user-supplied web URLs safely."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    """Raised when a URL could reach a non-public network destination."""


async def _resolve_host(hostname: str, port: int) -> set[str]:
    def resolve() -> set[str]:
        return {
            result[4][0]
            for result in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        }

    try:
        return await asyncio.to_thread(resolve)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve URL host: {hostname}") from exc


def _is_public_address(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False


async def validate_public_http_url(url: str) -> str:
    """Return a normalized public HTTP(S) URL or raise ``UnsafeURLError``."""
    candidate = url.strip()
    if len(candidate) > 2_048:
        raise UnsafeURLError("URL is too long")

    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeURLError("Only http:// and https:// URLs are supported")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeURLError("URL must include a valid host and no credentials")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise UnsafeURLError("Local network URLs are not allowed")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    addresses = await _resolve_host(hostname, port)
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise UnsafeURLError("Private, reserved, and link-local network URLs are not allowed")

    return candidate

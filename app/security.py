"""Local API access control for paired remote devices."""

import ipaddress
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from flask import current_app, request


def load_or_create_pairing_token() -> str:
    """Return a persistent random token stored in the user's private data folder."""
    data_dir = Path.home() / ".notes_workstation"
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_path = data_dir / "pairing_access_token"

    try:
        token = token_path.read_text(encoding="ascii").strip()
        if len(token) >= 40:
            return token
    except (OSError, UnicodeError):
        pass

    token = secrets.token_urlsafe(48)
    token_path.write_text(token, encoding="ascii")
    try:
        token_path.chmod(0o600)
    except OSError:
        # Windows uses the user's profile ACL; chmod is only meaningful on POSIX.
        pass
    return token


def is_loopback_request() -> bool:
    address = request.remote_addr
    if not address:
        return False
    try:
        parsed = ipaddress.ip_address(address.split("%", 1)[0])
        if getattr(parsed, "ipv4_mapped", None):
            parsed = parsed.ipv4_mapped
        return parsed.is_loopback
    except ValueError:
        return False


def is_trusted_local_origin(origin: str) -> bool:
    if origin in ("http://tauri.localhost", "tauri://localhost"):
        return True
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme in ("http", "https")
            and parsed.hostname in ("127.0.0.1", "localhost")
            and parsed.port is not None
            and 58850 <= parsed.port <= 58899
        )
    except ValueError:
        return False


def protect_remote_api() -> None:
    """Require the QR-paired token for API requests arriving over the network."""
    if request.method == "OPTIONS":
        return None

    if is_loopback_request():
        origin = request.headers.get("Origin")
        if origin and not is_trusted_local_origin(origin):
            return {"message": "Cross-origin access to the local workstation is blocked."}, 403
        fetch_site = request.headers.get("Sec-Fetch-Site", "").lower()
        if fetch_site in ("cross-site", "same-site") and not is_trusted_local_origin(origin or ""):
            return {"message": "Cross-origin access to the local workstation is blocked."}, 403
        return None

    protected_path = (
        request.path.startswith("/api/")
        or request.path == "/api"
        or request.path.startswith("/v1/")
        or request.path.startswith("/static/uploads/")
    )
    if not protected_path:
        return None

    expected = current_app.config["PAIRING_ACCESS_TOKEN"]
    supplied = request.headers.get("Authorization", "")
    prefix = "Bearer "
    if not supplied.startswith(prefix) or not secrets.compare_digest(supplied[len(prefix):], expected):
        return {"message": "This workstation requires a paired device credential."}, 401
    return None

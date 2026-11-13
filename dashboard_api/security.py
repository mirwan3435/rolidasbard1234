import os
import secrets

TOKEN = secrets.token_urlsafe(32)
ALLOWED_ORIGINS = {"http://127.0.0.1:5173", "http://localhost:5173"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def host_ok(host: str) -> bool:
    if not host:
        return False
    name = host.split(",")[0].strip().lower()
    if ":" in name:
        # IPv6 [::1]:port jarang dipakai di sini; cukup hostname:port
        host_only, _, port = name.rpartition(":")
        if port.isdigit():
            name = host_only
    if name in {"127.0.0.1", "localhost", "[::1]", "::1"}:
        return True
    if os.environ.get("DASHBOARD_TEST") == "1" and name == "testserver":
        return True
    return False


def origin_ok(origin: str, host: str = "", site: str = "") -> bool:
    if origin in ALLOWED_ORIGINS:
        return True
    cleaned = origin.rstrip("/")
    if cleaned in {item.rstrip("/") for item in ALLOWED_ORIGINS}:
        return True
    # Beberapa browser/webview tidak mengirim Origin pada GET same-origin.
    # Hanya izinkan jika Host sudah localhost (bukan testserver / host asing).
    if not origin and site.lower() in {"", "same-origin", "none"}:
        name = host.split(",")[0].strip().lower()
        if ":" in name:
            host_only, _, port = name.rpartition(":")
            if port.isdigit():
                name = host_only
        return name in {"127.0.0.1", "localhost", "[::1]", "::1"}
    return False

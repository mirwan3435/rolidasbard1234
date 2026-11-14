"""Tolak URL yang mengarah ke jaringan lokal atau alamat metadata."""
import ipaddress
import socket
from urllib.parse import urlparse


def public_url(url: str) -> bool:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname
    if host.lower() in {"localhost", "metadata.google.internal"}:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if any([
            ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_reserved,
            ip.is_multicast, ip.is_unspecified,
        ]):
            return False
    return True

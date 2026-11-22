"""Hashing and client-identity helpers. Raw IPs/UAs are NEVER stored (CLAUDE.md hard rule 7)."""

import hashlib
import hmac
import ipaddress

from django.conf import settings


def hmac_hash(value: str) -> str:
    """HMAC-SHA256 of a signal value (IP, UA) with SIGNALS_SALT (docs/voting.md).
    Deleting the salt at end of life makes these permanently unlinkable."""
    return hmac.new(
        settings.SIGNALS_SALT.encode(), (value or "").encode(), hashlib.sha256
    ).hexdigest()


def token_hash(value: str) -> str:
    """SHA-256 for high-entropy tokens (voter tokens, manage tokens). The tokens
    themselves are >=128-bit random, so no salt is needed."""
    return hashlib.sha256((value or "").encode()).hexdigest()


def secret_matches(sent: str, expected: str) -> bool:
    """Constant-time comparison of a secret header with its setting.

    Compares BYTES: hmac.compare_digest() raises TypeError for a str with non-ASCII
    characters, so a header such as "X-Origin-Token: \\xff" used to cause a 500 instead
    of a 403 (security assessment 2026-11-19, YV-40). "surrogatepass" lets any str
    encode, so no header value can make this raise. An empty setting never matches."""
    if not expected:
        return False
    return hmac.compare_digest(
        (sent or "").encode("utf-8", "surrogatepass"), expected.encode("utf-8")
    )


def came_through_cloudflare(request) -> bool:
    """True only when the origin shield is on (CF_ORIGIN_TOKEN set) AND this request
    carries the secret header the Cloudflare Transform Rule adds (docs/operations.md →
    Cloudflare checklist). Only then are Cloudflare's own headers (CF-Connecting-IP,
    X-Client-ASN) set by Cloudflare rather than by the client."""
    return secret_matches(request.headers.get("X-Origin-Token", ""), settings.CF_ORIGIN_TOKEN)


def client_ip(request) -> str:
    """Original client IP. CF-Connecting-IP is authoritative ONLY when the request came
    through Cloudflare (came_through_cloudflare; core/middleware.py rejects every other
    request while the shield is on); otherwise the header is attacker-controlled, so use
    the socket address."""
    if came_through_cloudflare(request):
        return request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
    return request.META.get("REMOTE_ADDR", "")


# NAT64 (RFC 6052 well-known prefix): the last 32 bits are the client's IPv4 address.
NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")


def network_key(ip: str) -> str:
    """The client NETWORK an address belongs to — what every per-IP limit counts by
    (security assessment 2026-11-19, YV-07; same rule as the platform's
    accounts.backends.network_of):

      IPv4                        the address itself          203.0.113.7/32
      IPv4-mapped IPv6            that IPv4 address           ::ffff:203.0.113.7 → .../32
      NAT64 (64:ff9b::/96)        the single address          (it carries one IPv4)
      any other IPv6              its /64                     2001:db8:1:2::/64

    One IPv6 customer line is normally a whole /64, so keying on the exact address let a
    single person rotate through millions of addresses and never hit a limit.
    Anything that is not an IP address is returned unchanged (it still hashes to a
    stable key). Use the RAW address only where an outside service needs it (Turnstile's
    remoteip)."""
    try:
        address = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return ip or ""
    if address.version == 6 and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if address.version == 4:
        prefix = 32
    elif address in NAT64_PREFIX:
        prefix = 128
    else:
        prefix = 64
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))


def network_hash(ip: str) -> str:
    """HMAC of network_key(ip): the stored and compared "ip_hash" of every limit."""
    return hmac_hash(network_key(ip))

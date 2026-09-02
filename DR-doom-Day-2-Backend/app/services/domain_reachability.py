import logging
from typing import TypedDict
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Known fallback mirror registries for high-availability sites and mirrors
KNOWN_MIRRORS_REGISTRY: dict[str, list[str]] = {
    "xhamster.com": [
        "https://xhamster.com",
        "https://xhamster1.com",
        "https://xhamster1.desi",
        "https://xhamster46.desi",
    ],
    "solarmoviez.tv": [
        "https://solarmoviez.tv",
        "https://solarmovie.to",
        "https://solarmovie.pe",
    ],
    "thepiratebay.org": [
        "https://thepiratebay.org",
        "https://tpb.party",
        "https://thepiratebay10.org",
    ],
    "1337x.to": [
        "https://1337x.to",
        "https://1337x.st",
        "https://1337x.ws",
    ],
    "reddit.com": [
        "https://www.reddit.com",
        "https://old.reddit.com",
    ],
    "wikipedia.org": [
        "https://www.wikipedia.org",
        "https://en.wikipedia.org",
    ],
}


class MirrorAttempt(TypedDict):
    url: str
    status_code: int | None
    success: bool
    error: str | None


class ReachabilityResult(TypedDict):
    target: str
    verified_url: str | None
    active: bool
    checked_mirrors: list[MirrorAttempt]
    message: str


def normalize_target_to_url(target: str) -> str:
    cleaned = target.strip()
    if not cleaned.startswith(("http://", "https://")):
        return f"https://{cleaned}"
    return cleaned


def extract_domain_key(target: str) -> str:
    url = normalize_target_to_url(target)
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def compile_verification_list(target: str, custom_mirrors: list[str] | None = None) -> list[str]:
    """
    Compile a target verification list consisting of the primary URL followed
    by known alternative domains, mirrors, or IP variants.
    """
    if custom_mirrors:
        return [normalize_target_to_url(m) for m in custom_mirrors]

    domain_key = extract_domain_key(target)
    primary_url = normalize_target_to_url(target)

    # Check pre-configured registry
    if domain_key in KNOWN_MIRRORS_REGISTRY:
        candidates = KNOWN_MIRRORS_REGISTRY[domain_key].copy()
        if primary_url not in candidates:
            candidates.insert(0, primary_url)
        return candidates

    # If not in registry, try primary URL plus standard common mirror heuristics
    candidates = [primary_url]
    
    # Generate common mirror variants if domain is simple
    parts = domain_key.split(".")
    if len(parts) == 2:
        name, tld = parts
        variants = [
            f"https://www.{domain_key}",
            f"https://{name}1.{tld}",
            f"https://{name}.to",
            f"https://{name}.is",
        ]
        for v in variants:
            if v not in candidates:
                candidates.append(v)

    return candidates


def ping_url(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> tuple[bool, int | None, str | None]:
    """
    Perform a lightweight HTTP HEAD (or fallback GET) request to evaluate URL reachability.
    Accepts 200 OK or 3xx redirects as ACTIVE.
    """
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        # First attempt HTTP HEAD for efficiency
        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        # Some servers return 405 Method Not Allowed or 403 on HEAD; fallback to lightweight GET stream
        if response.status_code in (405, 403, 501):
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)
            response.close()

        # 200 OK or 3xx redirect is acceptable and active
        if 200 <= response.status_code < 400:
            return True, response.status_code, None
        else:
            return False, response.status_code, f"HTTP status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, None, "Connection timeout"
    except requests.exceptions.ConnectionError as exc:
        return False, None, f"Connection error: {exc}"
    except requests.exceptions.RequestException as exc:
        return False, None, f"Request failed: {exc}"


def resolve_reachable_domain(
    target: str,
    custom_mirrors: list[str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> ReachabilityResult:
    """
    Health check (Ping Phase) and Fallback Logic:
    1. Sequentially pings each candidate URL in the verification list.
    2. If status is 200 OK (or acceptable 3xx redirect), mark as ACTIVE and select it.
    3. If failed (DNS error, timeout, 403, 404, 50x), log failed attempt and try next mirror.
    4. If all fail, return unreachable error.
    """
    candidates = compile_verification_list(target, custom_mirrors)
    checked_mirrors: list[MirrorAttempt] = []

    for candidate in candidates:
        domain_name = urlparse(candidate).netloc or candidate
        is_active, status_code, error = ping_url(candidate, timeout=timeout)

        checked_mirrors.append({
            "url": candidate,
            "status_code": status_code,
            "success": is_active,
            "error": error,
        })

        if is_active:
            msg = f"Operational URL verified: {candidate} (Status: {status_code})"
            logger.info(msg)
            return {
                "target": target,
                "verified_url": candidate,
                "active": True,
                "checked_mirrors": checked_mirrors,
                "message": msg,
            }
        else:
            logger.warning("Failed ping attempt for domain mirror %s: %s (Status: %s)", domain_name, error, status_code)

    error_msg = "Error: All requested domain mirrors are currently unreachable."
    logger.error(error_msg)
    return {
        "target": target,
        "verified_url": None,
        "active": False,
        "checked_mirrors": checked_mirrors,
        "message": error_msg,
    }

import json
import re
from typing import Literal
from urllib.parse import quote_plus, urlparse

import requests

from app.settings import settings

PlanKind = Literal["open_website", "web_search", "youtube_search", "spotify_search"]

PLANNER_PROMPT = """Classify a browser-navigation request. Return JSON only:
{"kind":"web_search|youtube_search|spotify_search","query":"short search text"}.
Use youtube_search for requests to find a YouTube video, song, audio, or channel.
Use spotify_search for requests to find music, an artist, album, podcast, or playlist on Spotify.
Use web_search for every other website/search request. Never return a URL, command,
file path, app name, or explanation."""

# Explicit mapping of common site shortcuts to URLs and labels
KNOWN_SHORTCUTS: dict[str, tuple[str, str]] = {
    "solarmoviez.tv": ("https://solarmoviez.tv", "solarmoviez.tv"),
    "solarmoviez": ("https://solarmoviez.tv", "solarmoviez.tv"),
    "solarmovie": ("https://solarmoviez.tv", "solarmoviez.tv"),
    "youtube.com": ("https://youtube.com", "youtube.com"),
    "newgrounds.com": ("https://newgrounds.com", "newgrounds.com"),
    "newgrounds": ("https://newgrounds.com", "newgrounds.com"),
    "rule34.xxx": ("https://rule34.xxx", "rule34.xxx"),
    "rule34": ("https://rule34.xxx", "rule34.xxx"),
    "reddit.com": ("https://www.reddit.com", "reddit.com"),
    "github.com": ("https://github.com", "github.com"),
    "wikipedia.org": ("https://www.wikipedia.org", "wikipedia.org"),
    "netflix.com": ("https://www.netflix.com", "netflix.com"),
    "amazon.com": ("https://www.amazon.com", "amazon.com"),
    "twitch.tv": ("https://www.twitch.tv", "twitch.tv"),
}

URL_REGEX = re.compile(r"https?://[^\s]+", re.IGNORECASE)
DOMAIN_REGEX = re.compile(
    r"\b(?:https?:\/\/)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:com|org|net|io|edu|gov|dev|app|co|ai|in|tv|xxx|to|is|cc|me|info|biz|uk|us|ca|de|jp|fr|au|ru|ch|it|nl|se|no|es|[a-zA-Z]{2,}))(?:\/[^\s]*)?",
    re.IGNORECASE,
)


def _model_classification(text: str) -> dict[str, str] | None:
    if not settings.groq_api_key or settings.groq_api_key.startswith("your_actual_groq_api_key"):
        return None
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_chat_model,
                "messages": [
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": text},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=5.0,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, dict) and "kind" in parsed and "query" in parsed:
            return parsed
    except Exception:
        pass
    return None


def _clean_query(text: str, platform_pattern: str | None = None) -> str:
    cleaned = text.strip()
    cleaned = re.sub(
        r"^(?:please\s+)?(?:can you\s+)?(?:play|search(?:\s+for)?|find|lookup|look up|listen to|watch|open|go to|visit|browse to)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    if platform_pattern:
        cleaned = re.sub(platform_pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


# ==============================================================================
# PHASE 4: THE HANDS (Safe Web Action Destination Planner)
# ==============================================================================
def make_web_action_plan(text: str) -> dict[str, str]:
    """
    Classify user navigation request and return safe destination plan {kind, label, url}.
    - Explicit URL -> open_website
    - YouTube search -> youtube_search
    - Spotify search -> spotify_search
    - Other search -> web_search
    """
    trimmed = text.strip()

    # 1. Check for explicit http(s) URL
    url_match = URL_REGEX.search(trimmed)
    if url_match:
        raw_url = url_match.group(0)
        parsed = urlparse(raw_url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            hostname = parsed.hostname or parsed.netloc
            return {
                "kind": "open_website",
                "label": hostname,
                "url": raw_url,
            }

    # 2. Check for known shortcuts / direct website keywords
    normalized = trimmed.lower()
    for shortcut, (target_url, label) in KNOWN_SHORTCUTS.items():
        pattern = rf"\b{re.escape(shortcut)}\b"
        if re.search(pattern, normalized):
            is_search_intent = bool(re.search(r"\b(play|listen to|search for|find)\b", normalized)) and not bool(re.search(r"\b(open|go to|visit)\b", normalized))
            if shortcut in ("youtube.com", "youtube") and is_search_intent:
                break
            return {
                "kind": "open_website",
                "label": label,
                "url": target_url,
            }

    # 3. Check for domain name patterns in user text (e.g. solarmoviez.tv, newgrounds.com, rule34.xxx)
    domain_match = DOMAIN_REGEX.search(trimmed)
    if domain_match:
        raw_domain = domain_match.group(1)
        full_match = domain_match.group(0)
        is_search_intent = bool(re.search(r"\b(play|listen to|search for|find)\b", normalized))
        is_platform_search = any(p in raw_domain.lower() for p in ("youtube", "spotify")) and is_search_intent
        if not is_platform_search:
            scheme = "https://" if not full_match.startswith(("http://", "https://")) else ""
            target_url = f"{scheme}{full_match}"
            parsed = urlparse(target_url)
            hostname = parsed.hostname or raw_domain
            return {
                "kind": "open_website",
                "label": hostname,
                "url": target_url,
            }

    # 4. Try LLM model classification if available
    classification = _model_classification(trimmed)
    if classification:
        kind = classification.get("kind")
        query = classification.get("query", "").strip()
        if kind == "youtube_search" and query:
            return {
                "kind": "youtube_search",
                "label": "YouTube",
                "url": f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            }
        elif kind == "spotify_search" and query:
            return {
                "kind": "spotify_search",
                "label": "Spotify",
                "url": f"https://open.spotify.com/search/{quote_plus(query)}",
            }
        elif kind == "web_search" and query:
            return {
                "kind": "web_search",
                "label": "Google Search",
                "url": f"https://www.google.com/search?q={quote_plus(query)}",
            }

    # 5. Fallback heuristic classification
    if re.search(r"\byoutube\b", normalized):
        query = _clean_query(trimmed, r"(?:\s+(?:on|in|from|at)\s+youtube.*$|\s+youtube$)")
        return {
            "kind": "youtube_search",
            "label": "YouTube",
            "url": f"https://www.youtube.com/results?search_query={quote_plus(query)}",
        }

    if re.search(r"\bspotify\b", normalized):
        query = _clean_query(trimmed, r"(?:\s+(?:on|in|from|at)\s+spotify.*$|\s+spotify$)")
        return {
            "kind": "spotify_search",
            "label": "Spotify",
            "url": f"https://open.spotify.com/search/{quote_plus(query)}",
        }

    # Default: web search
    query = _clean_query(trimmed)
    return {
        "kind": "web_search",
        "label": "Google Search",
        "url": f"https://www.google.com/search?q={quote_plus(query)}",
    }

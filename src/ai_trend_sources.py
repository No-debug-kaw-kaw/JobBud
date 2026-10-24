"""Independent, explicitly labelled fallback for unavailable GDELT topics."""
from datetime import datetime, timedelta, timezone

import requests

from gdelt_engine import MIN_SIGNAL, normalize_signals, save_gdelt_cache

HN_URL = "https://hn.algolia.com/api/v1/search"
HN_SOURCE = "Hacker News (Algolia)"
# These search terms are displayed alongside the results. In particular,
# "analytics" is broader than GDELT's exact "data analytics" phrase.
HN_QUERIES = {
    "Artificial Intelligence": "artificial intelligence",
    "Generative AI": "generative AI",
    "Machine Learning": "machine learning",
    "Data Analytics": "analytics",
    "Automation": "automation",
    "Cybersecurity": "cybersecurity",
}


def _story_count(query, start, end):
    response = requests.get(
        HN_URL,
        params={
            "query": query, "tags": "story", "hitsPerPage": 0,
            "typoTolerance": "false",
            "restrictSearchableAttributes": "title,story_text",
            "numericFilters": (
                f"created_at_i>={int(start.timestamp())},"
                f"created_at_i<{int(end.timestamp())}"
            ),
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Invalid backup response")
    count = data.get("nbHits")
    exhaustive = data.get("exhaustiveNbHits")
    if exhaustive is None and isinstance(data.get("exhaustive"), dict):
        exhaustive = data["exhaustive"].get("nbHits")
    if type(count) is not int or count < 0 or exhaustive is not True:
        raise ValueError("Backup count is missing, invalid or approximate")
    return count


def fetch_backup_signal(topic, now=None):
    now = now or datetime.now(timezone.utc)
    end = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    middle = end - timedelta(days=14)
    start = end - timedelta(days=28)
    query = HN_QUERIES[topic]
    # Both windows must succeed; never compare counts from different providers.
    recent = _story_count(query, middle, end)
    previous = _story_count(query, start, middle)
    result = {
        "skill": topic, "recent": recent, "previous": previous,
        "change": None, "score": None, "direction": "Insufficient signal",
        "source": HN_SOURCE, "source_url": "https://hn.algolia.com/api",
        "query": query, "fetched_at": now.timestamp(),
        "period_start": start.date().isoformat(),
        "period_end": (end - timedelta(days=1)).date().isoformat(),
    }
    if recent + previous >= MIN_SIGNAL:
        change = (recent - previous) / max(previous, 1) * 100
        result.update(
            change=round(change, 1),
            score=round(max(0, min(100, 50 + change / 2)), 1),
            direction="Rising" if change > 20 else "Declining" if change < -20 else "Stable",
        )
    return result


def add_backup_signals(primary_signals):
    """Keep valid primary evidence; replace only failed topics, then cache."""
    signals = normalize_signals(primary_signals)
    used_backup = False
    for topic, signal in list(signals.items()):
        if signal["direction"] != "Unavailable":
            continue
        try:
            signals[topic] = fetch_backup_signal(topic)
            used_backup = True
        except (requests.RequestException, ValueError, KeyError) as error:
            signals[topic] = {**signal, "backup_error": str(error)}
    if used_backup:
        save_gdelt_cache(signals)
    return signals

import requests
import pandas as pd
import time
import json
import os
import math
import tempfile

from datetime import datetime, timezone, timedelta

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

MIN_SIGNAL = 20

CACHE_FILE = "data/gdelt_cache.json"
CACHE_HOURS = 6
RETRY_COOLDOWN = 300
_retry_after = 0


def normalize_signals(signals):
    """Reject malformed records before either rendering or averaging scores."""
    if not isinstance(signals, dict):
        return {}
    clean = {}
    for topic, record in signals.items():
        if topic not in TECH_QUERIES or not isinstance(record, dict):
            continue
        direction = record.get("direction")
        if direction not in ("Rising", "Stable", "Declining", "Unavailable", "Insufficient signal"):
            continue
        record = dict(record)
        valid = True
        for field in ("recent", "previous", "change", "score"):
            value = record.get(field)
            if value is None and field in ("score", "change"):
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                valid = False
                break
            if field in ("recent", "previous", "score") and value < 0:
                valid = False
            if field == "score" and value > 100:
                valid = False
        if not valid:
            continue
        if direction in ("Unavailable", "Insufficient signal"):
            record["score"] = None
            record["change"] = None
        elif record.get("score") is None or record.get("change") is None:
            continue
        clean[topic] = record
    return clean


def unavailable_signal(name, error):
    return {"skill": name, "recent": 0, "previous": 0, "change": None,
            "direction": "Unavailable", "score": None, "error": str(error)}


TECH_QUERIES = {

    "Artificial Intelligence":
        '"artificial intelligence"',

    "Generative AI":
        '"generative AI"',

    "Machine Learning":
        '"machine learning"',

    "Data Analytics":
        '"data analytics"',

    "Automation":
        '(automation OR "workflow automation")',

    "Cybersecurity":
        'cybersecurity',
}


ROLE_TOPICS = {

    "Data Scientists": [
        "Artificial Intelligence",
        "Generative AI",
        "Machine Learning",
        "Data Analytics",
    ],

    "Business Intelligence Analysts": [
        "Artificial Intelligence",
        "Data Analytics",
        "Automation",
    ],

    "Statisticians": [
        "Machine Learning",
        "Data Analytics",
        "Artificial Intelligence",
    ],

    "Actuaries": [
        "Artificial Intelligence",
        "Data Analytics",
        "Automation",
    ],

    "Economists": [
        "Artificial Intelligence",
        "Generative AI",
        "Data Analytics",
    ],

    "Market Research Analysts and Marketing Specialists": [
        "Generative AI",
        "Data Analytics",
        "Automation",
    ],

    "Accountants and Auditors": [
        "Artificial Intelligence",
        "Generative AI",
        "Automation",
    ],

    "Management Analysts": [
        "Generative AI",
        "Data Analytics",
        "Automation",
    ],

    "Financial Quantitative Analysts": [
        "Artificial Intelligence",
        "Machine Learning",
        "Data Analytics",
    ],

    "Loan Officers": [
        "Artificial Intelligence",
        "Automation",
        "Generative AI",
    ],

    "Financial Examiners": [
        "Artificial Intelligence",
        "Data Analytics",
        "Automation",
    ],
}


def fetch_timeline(query):
    global _retry_after
    if time.monotonic() < _retry_after:
        raise RuntimeError("GDELT temporarily unavailable; retry after cooldown")

    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "timespan": "28d",
    }
    
    headers = {
        "User-Agent":
            "AI-Career-Navigator-University-Hackathon"
    }
    
    try:
        response = requests.get(
            GDELT_URL, params=params, timeout=10, headers=headers,
        )
        if response.status_code == 429:
            _retry_after = time.monotonic() + RETRY_COOLDOWN
            raise RuntimeError("GDELT rate-limited requests; retry in five minutes")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid GDELT response")
        timeline = data.get("timeline", [])
        if not timeline:
            return []
        if not isinstance(timeline, list) or not isinstance(timeline[0], dict):
            raise ValueError("Invalid GDELT timeline")
        points = timeline[0].get("data", [])
        if not isinstance(points, list):
            raise ValueError("Invalid GDELT timeline data")
        return points
    except (requests.exceptions.RequestException, ValueError):
        _retry_after = time.monotonic() + RETRY_COOLDOWN
        raise

def _parse_timeline_rows(data):
    """Reject malformed observations rather than scoring a partial timeline."""
    if not isinstance(data, list):
        raise ValueError("Malformed GDELT timeline: expected a list")

    rows = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Malformed GDELT timeline observation")

        raw_date = item.get("date")
        if not isinstance(raw_date, str):
            continue
        date = pd.to_datetime(raw_date, utc=True, errors="coerce")
        if pd.isna(date):
            continue

        if isinstance(item.get("value"), bool):
            raise ValueError("GDELT timeline count cannot be boolean")
        if "value" not in item:
            raise ValueError("GDELT timeline observation is missing its count")
        value = float(item["value"])
        if not math.isfinite(value) or value < 0:
            raise ValueError("GDELT timeline values must be finite and non-negative")
        rows.append({"date": date, "value": value})
    return rows


def analyse_topic(name, query):

    try:
        data = fetch_timeline(query)
        rows = _parse_timeline_rows(data)

    except Exception as error:

        return {
            "skill": name,
            "recent": 0,
            "previous": 0,
            "change": None,
            "direction": "Unavailable",
            "score": None,
            "error": str(error),
        }

    if not rows:

        return {
            "skill": name,
            "recent": 0,
            "previous": 0,
            "change": None,
            "direction": "Insufficient signal",
            "score": None,
        }

    df = pd.DataFrame(rows)

    latest = df["date"].max()

    recent_start = (
        latest - timedelta(days=14)
    )

    previous_start = (
        latest - timedelta(days=28)
    )

    recent = df[
        df["date"] > recent_start
    ]["value"].sum()

    previous = df[
        (df["date"] > previous_start)
        &
        (df["date"] <= recent_start)
    ]["value"].sum()

    total_signal = recent + previous

    if total_signal < MIN_SIGNAL:

        return {
            "skill": name,
            "recent": round(recent),
            "previous": round(previous),
            "change": None,
            "direction": "Insufficient signal",
            "score": None,
        }

    change = (
        (recent - previous)
        / max(previous, 1)
        * 100
    )

    if change > 20:
        direction = "Rising"

    elif change < -20:
        direction = "Declining"

    else:
        direction = "Stable"

    # Convert momentum into 0-100 score.
    # Team-defined prototype method.
    score = max(
        0,
        min(
            100,
            50 + change / 2,
        ),
    )

    return {
        "skill": name,
        "recent": round(recent),
        "previous": round(previous),
        "change": round(change, 1),
        "direction": direction,
        "score": round(score, 1),
    }

def load_gdelt_cache():

    if not os.path.exists(CACHE_FILE):
        return None

    try:

        modified_time = os.path.getmtime(
            CACHE_FILE
        )

        age = (
            datetime.now().timestamp()
            - modified_time
        )

        max_age = CACHE_HOURS * 3600

        if age > max_age:
            return None

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            records = normalize_signals(json.load(file))
            # Per-topic timestamps prevent a partial refresh from extending the
            # lifetime of old signals when the file's modification time changes.
            now = datetime.now(timezone.utc).timestamp()
            fresh = {}
            for topic, record in records.items():
                stamp = record.get("fetched_at", modified_time)
                if isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and 0 <= now - stamp <= max_age:
                    fresh[topic] = {**record, "fetched_at": stamp}
            return fresh

    except Exception:
        return None


def save_gdelt_cache(results):
    directory = os.path.dirname(CACHE_FILE) or "."
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=directory, delete=False) as file:
            temp_path = file.name
            json.dump(normalize_signals(results), file, indent=2, allow_nan=False)
        os.replace(temp_path, CACHE_FILE)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

def get_ai_skill_signals():

    cached = normalize_signals(load_gdelt_cache())
    
    if cached is None:
        cached = {}
    
    results = {}
    
    for skill, query in TECH_QUERIES.items():
    
        cached_result = cached.get(skill)
    
        # Reuse good cached data
        if (
            cached_result
            and cached_result.get("direction")
            not in ["Unavailable", None]
        ):
    
            print(
                f"Using cached {skill}"
            )
    
            results[skill] = cached_result
    
            continue
    
        # Retry only missing / unavailable topics
        if time.monotonic() < _retry_after:
            results[skill] = unavailable_signal(skill, "GDELT provider cooldown")
            continue
        print(
            f"Checking {skill}..."
        )
    
        result = analyse_topic(
            skill,
            query
        )
    
        results[skill] = result
        result["fetched_at"] = datetime.now(timezone.utc).timestamp()

        # Save each completed topic so an interruption does not lose the batch.
        save_gdelt_cache({**cached, **results})
    
        print(
            f"{skill} -> "
            f"{result['direction']}"
        )
    
        if result.get("error"):
    
            print(
                "Error:",
                result["error"]
            )
    
        # Be gentle with GDELT
        if time.monotonic() >= _retry_after and skill != next(reversed(TECH_QUERIES)):
            time.sleep(8)
    
    save_gdelt_cache(
        results
    )
    
    return results
   
    
def get_role_ai_signal(
    role,
    skill_signals,
):
    skill_signals = normalize_signals(skill_signals)

    topics = ROLE_TOPICS.get(
        role,
        [],
    )

    available_scores = []

    used_topics = []

    for topic in topics:

        signal = skill_signals.get(
            topic
        )

        if (
            signal
            and signal.get("score")
            is not None
        ):

            available_scores.append(
                signal["score"]
            )

            used_topics.append(topic)

    if not available_scores:

        return {
            "score": None,
            "direction":
                "Insufficient signal",
            "topics": [],
        }

    score = sum(
        available_scores
    ) / len(available_scores)

    if score > 60:
        direction = "Rising"

    elif score < 40:
        direction = "Declining"

    else:
        direction = "Stable"

    return {
        "score": round(score, 1),
        "direction": direction,
        "topics": used_topics,
    }


if __name__ == "__main__":

    print("GDELT AI trend test started")
    
    signals = get_ai_skill_signals()
    
    print("\n" + "=" * 30)
    print("AI / TECHNOLOGY SIGNALS")
    print("=" * 30)
    
    for skill, result in signals.items():
    
        print(
            f"\n{skill}"
        )
    
        print(
            f"Direction: "
            f"{result['direction']}"
        )
    
        print(
            f"Recent 14 days: "
            f"{result['recent']}"
        )
    
        print(
            f"Previous 14 days: "
            f"{result['previous']}"
        )
    
        print(
            f"Change: "
            f"{result['change']}"
        )
    
        print(
            f"Trend Score: "
            f"{result['score']}"
        )
    
    print("\n" + "=" * 30)
    print("ROLE AI SIGNAL EXAMPLE")
    print("=" * 30)
    
    example = get_role_ai_signal(
        "Data Scientists",
        signals
    )
    
    print(example)

    

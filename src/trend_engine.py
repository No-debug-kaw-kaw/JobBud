"""Cached, evidence-gated labour-market signals from Himalayas with Remotive fallback."""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent

HIMALAYAS_SEARCH_URL = "https://himalayas.app/jobs/api/search"
REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"

CACHE_FILE = BASE_DIR / "data" / "job_market_cache.json"
CACHE_HOURS = 24
MIN_SIGNAL_COUNT = 6
MAX_CACHED_JOBS = 2500

# One recent search is made for each role family. Results are merged and
# deduplicated, so the trend engine sees a broader sample than a single feed.
# Himalayas refreshes its public API approximately every 24 hours, so the
# local cache uses the same cadence.
HIMALAYAS_SEARCH_QUERIES: tuple[str, ...] = (
    "business intelligence",
    "data scientist",
    "statistician",
    "actuary",
    "economist",
    "marketing analyst",
    "accountant",
    "business analyst",
    "quantitative analyst",
    "credit analyst",
    "risk analyst",
)

ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Business Intelligence Analysts": (
        "business intelligence",
        "bi analyst",
        "business analytics",
        "analytics engineer",
    ),
    "Data Scientists": (
        "data scientist",
        "machine learning scientist",
        "applied scientist",
        "data science",
    ),
    "Statisticians": (
        "statistician",
        "statistical analyst",
        "biostatistician",
        "statistics",
    ),
    "Actuaries": ("actuary", "actuarial"),
    "Economists": ("economist", "economic analyst", "economics"),
    "Market Research Analysts and Marketing Specialists": (
        "market research",
        "marketing analyst",
        "consumer insights",
        "growth analyst",
        "marketing specialist",
    ),
    "Accountants and Auditors": ("accountant", "accounting", "auditor", "audit"),
    "Management Analysts": (
        "management analyst",
        "business analyst",
        "strategy analyst",
        "operations analyst",
    ),
    "Financial Quantitative Analysts": (
        "quantitative analyst",
        "quant analyst",
        "quantitative researcher",
        "financial modeling",
    ),
    "Loan Officers": ("loan officer", "credit analyst", "lending", "credit risk"),
    "Financial Examiners": (
        "financial examiner",
        "risk analyst",
        "compliance analyst",
        "financial risk",
    ),
}

SKILL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Artificial Intelligence": (
        "artificial intelligence",
        "generative ai",
        "genai",
        "large language model",
        "llm",
    ),
    "Machine Learning": ("machine learning", "deep learning"),
    "Python": ("python",),
    "SQL": ("sql", "structured query language"),
    "Data Analysis": ("data analysis", "data analytics", "analytics"),
    "Cloud Computing": ("cloud computing", "aws", "azure", "google cloud", "gcp"),
    "Automation": ("automation", "automated"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Cybersecurity": ("cybersecurity", "cyber security", "information security"),
}


def _now_utc(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_date(value: Any) -> datetime | None:
    """Parse ISO timestamps and Unix timestamps into UTC datetimes."""
    if value is None or value == "":
        return None

    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)

        text = str(value).strip()

        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            return datetime.fromtimestamp(float(text), tz=timezone.utc)

        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    except (TypeError, ValueError, OSError):
        return None

def load_cache(cache_file: Path | None = None) -> dict[str, Any] | None:
    path = cache_file or CACHE_FILE
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            return None
        return payload
    except (OSError, json.JSONDecodeError):
        return None


def _cache_age(cache: dict[str, Any], now: datetime) -> timedelta | None:
    fetched_at = parse_date(cache.get("fetched_at"))
    return now - fetched_at if fetched_at else None


def _dedupe_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_identity: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        identity = job.get("id") or job.get("url")
        if not identity:
            identity = "|".join(
                str(job.get(field, "")).strip().lower()
                for field in ("title", "company_name", "publication_date")
            )
        if identity and identity != "||":
            by_identity[str(identity)] = job
    return list(by_identity.values())


def _job_age_days(job: dict[str, Any], now: datetime) -> float | None:
    published = parse_date(job.get("publication_date"))
    if published is None:
        return None
    return (now - published).total_seconds() / 86400


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)



def _normalise_himalayas_job(job: dict[str, Any]) -> dict[str, Any]:
    published = parse_date(job.get("pubDate"))

    categories = job.get("categories") or []
    parent_categories = job.get("parentCategories") or []

    if not isinstance(categories, list):
        categories = [categories]

    if not isinstance(parent_categories, list):
        parent_categories = [parent_categories]

    return {
        "id": job.get("guid"),
        "url": job.get("applicationLink") or job.get("guid"),
        "title": job.get("title", ""),
        "company_name": job.get("companyName", ""),
        "publication_date": published.isoformat() if published else None,
        "category": " ".join(
            str(value)
            for value in [*categories, *parent_categories]
            if value
        ),
        "description": " ".join(
            str(value)
            for value in (
                job.get("excerpt", ""),
                job.get("description", ""),
            )
            if value
        ),
        "source": "Himalayas Remote Jobs API",
    }


def _normalise_remotive_job(job: dict[str, Any]) -> dict[str, Any]:
    result = dict(job)
    result["source"] = "Remotive Public Jobs API"
    return result


def _cache_response(
    cache: dict[str, Any] | None,
    *,
    stale: bool,
    error: str | None = None,
) -> dict[str, Any]:
    cached = cache or {}
    jobs = cached.get("jobs", [])

    return {
        "jobs": jobs if isinstance(jobs, list) else [],
        "fetched_at": cached.get("fetched_at"),
        "source": cached.get("source") or "Cached job-market sample",
        "from_cache": True,
        "stale": stale,
        "error": error,
        "query": None,
        "listings_analysed": len(jobs) if isinstance(jobs, list) else 0,
        "api_calls_today": cached.get("api_calls_today", 0),
        "next_refresh_at": cached.get("next_refresh_at"),
    }


def _fetch_himalayas_jobs(
    session: Any,
) -> tuple[list[dict[str, Any]], list[str]]:
    jobs: list[dict[str, Any]] = []
    errors: list[str] = []

    for query in HIMALAYAS_SEARCH_QUERIES:
        try:
            response = session.get(
                HIMALAYAS_SEARCH_URL,
                params={
                    "q": query,
                    "sort": "recent",
                    "page": 1,
                },
                timeout=20,
                headers={"User-Agent": "AI-Career-Navigator/1.0"},
            )
            response.raise_for_status()

            payload = response.json()
            rows = payload.get("jobs", [])

            if not isinstance(rows, list):
                raise ValueError(
                    "Himalayas returned an unexpected jobs payload."
                )

            jobs.extend(
                _normalise_himalayas_job(job)
                for job in rows
                if isinstance(job, dict)
            )

        except Exception as error:
            errors.append(
                f"{query}: {type(error).__name__}"
            )

    return jobs, errors


def _fetch_remotive_fallback(
    session: Any,
) -> list[dict[str, Any]]:
    try:
        response = session.get(
            REMOTIVE_API_URL,
            timeout=20,
            headers={"User-Agent": "AI-Career-Navigator/1.0"},
        )
        response.raise_for_status()

        payload = response.json()
        rows = payload.get("jobs", [])

        if not isinstance(rows, list):
            return []

        return [
            _normalise_remotive_job(job)
            for job in rows
            if isinstance(job, dict)
        ]

    except Exception:
        return []


def cached_job_data():
    """Read the existing sample without starting any HTTP requests."""
    cache = load_cache()
    age = _cache_age(cache, _now_utc()) if cache else None
    return _cache_response(
        cache, stale=age is None or age >= timedelta(hours=CACHE_HOURS),
    )


def fetch_job_data(
    force_refresh: bool = False,
    *,
    session: Any = requests,
    cache_file: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch a broader remote-job sample and cache it for 24 hours.

    Himalayas is the primary source. One recent page is requested for each
    role-family query, then results are merged and deduplicated. Remotive is
    added as a small secondary/fallback source when available.

    The downstream trend functions continue to apply the same evidence
    threshold, so small niche samples may still correctly show
    "Insufficient signal".
    """

    current_time = _now_utc(now)
    path = cache_file or CACHE_FILE
    cache = load_cache(path)
    age = _cache_age(cache, current_time) if cache else None

    if (
        cache
        and age is not None
        and age < timedelta(hours=CACHE_HOURS)
        and not force_refresh
    ):
        return _cache_response(
            cache,
            stale=False,
        )

    himalayas_jobs, himalayas_errors = _fetch_himalayas_jobs(
        session
    )

    remotive_jobs = _fetch_remotive_fallback(
        session
    )

    combined = _dedupe_jobs(
        [
            *himalayas_jobs,
            *remotive_jobs,
        ]
    )

    recent_jobs = [
        job
        for job in combined
        if (
            _job_age_days(job, current_time) is None
            or _job_age_days(job, current_time) <= 35
        )
    ]

    recent_jobs.sort(
        key=lambda job: (
            parse_date(job.get("publication_date"))
            or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )

    recent_jobs = recent_jobs[:MAX_CACHED_JOBS]

    if not recent_jobs and cache:
        return _cache_response(
            cache,
            stale=True,
            error=(
                "Live job-market refresh failed; "
                "using the latest cached sample."
            ),
        )

    if not recent_jobs:
        return {
            "jobs": [],
            "fetched_at": None,
            "source": "Job-market APIs unavailable",
            "from_cache": False,
            "stale": True,
            "error": (
                "No usable job listings were returned "
                "from the live market sources."
            ),
            "query": None,
            "listings_analysed": 0,
            "api_calls_today": len(HIMALAYAS_SEARCH_QUERIES) + 1,
            "next_refresh_at": None,
        }

    sources = []

    if himalayas_jobs:
        sources.append(
            "Himalayas Remote Jobs API"
        )

    if remotive_jobs:
        sources.append(
            "Remotive Public Jobs API"
        )

    source_label = " + ".join(sources)

    fetched_at = current_time.isoformat()
    next_refresh = (
        current_time
        + timedelta(hours=CACHE_HOURS)
    ).isoformat()

    warning = None

    if himalayas_errors and himalayas_jobs:
        warning = (
            "Some Himalayas role-family searches were unavailable; "
            "the trend engine used the successful searches."
        )

    saved = {
        "source": source_label,
        "fetched_at": fetched_at,
        "next_refresh_at": next_refresh,
        "jobs": recent_jobs,
        "api_calls_today": (
            len(HIMALAYAS_SEARCH_QUERIES) + 1
        ),
        "himalayas_queries_requested": len(
            HIMALAYAS_SEARCH_QUERIES
        ),
        "himalayas_query_errors": himalayas_errors,
    }

    _write_cache(
        path,
        saved,
    )

    return {
        "jobs": recent_jobs,
        "fetched_at": fetched_at,
        "source": source_label,
        "from_cache": False,
        "stale": False,
        "error": warning,
        "query": None,
        "listings_analysed": len(recent_jobs),
        "api_calls_today": len(HIMALAYAS_SEARCH_QUERIES) + 1,
        "next_refresh_at": next_refresh,
    }

def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", text).lower()


def _contains_keyword(text: str, keyword: str) -> bool:
    # Word boundaries prevent short terms such as "AI" and "R" matching
    # inside unrelated words (for example, "email" or "credit").
    pattern = rf"(?<!\w){re.escape(keyword.lower())}(?!\w)"
    return re.search(pattern, text) is not None


def _job_matches(job: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    text = " ".join(
        clean_text(job.get(field))
        for field in ("title", "category", "description")
    )
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def get_time_bucket(
    publication_date: Any,
    now: datetime | None = None,
) -> str | None:
    published = parse_date(publication_date)
    if published is None:
        return None
    age_days = (_now_utc(now) - published).total_seconds() / 86400
    if age_days < 0:
        return None
    if age_days < 14:
        return "recent"
    if age_days < 28:
        return "previous"
    return "older"


def _count_signals(
    jobs: list[dict[str, Any]],
    keywords: tuple[str, ...],
    now: datetime | None,
) -> tuple[int, int]:
    recent = previous = 0
    for job in jobs:
        if not _job_matches(job, keywords):
            continue
        bucket = get_time_bucket(job.get("publication_date"), now)
        if bucket == "recent":
            recent += 1
        elif bucket == "previous":
            previous += 1
    return recent, previous


def _direction_and_score(
    recent: int,
    previous: int,
    max_recent: int,
) -> dict[str, Any]:
    """
    Convert recent posting frequency into a current-market signal.

    The job feed is heavily weighted toward recent listings, so
    recent-vs-previous counts are not interpreted as a time trend.
    GDELT is used separately for temporal AI/technology momentum.
    """

    sample_count = recent + previous

    demand_index = (
        recent / max_recent * 100.0
        if max_recent
        else 0.0
    )

    # Require enough current evidence before assigning a signal.
    if recent < MIN_SIGNAL_COUNT:
        return {
            "recent_signal": recent,
            "previous_signal": previous,
            "sample_count": sample_count,
            "demand_index": demand_index,
            "momentum": None,
            "direction": "Insufficient signal",
            "trend_score": None,
        }

    if demand_index >= 60:
        direction = "Strong current signal"

    elif demand_index >= 30:
        direction = "Moderate current signal"

    else:
        direction = "Limited current signal"

    return {
        "recent_signal": recent,
        "previous_signal": previous,
        "sample_count": sample_count,
        "demand_index": demand_index,

        # Do not infer momentum from this recency-biased feed.
        "momentum": None,

        "direction": direction,

        # Existing downstream code can continue using trend_score,
        # but it now represents relative current posting demand.
        "trend_score": demand_index,
    }

def analyse_role_trends(
    jobs: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    counts = {
        role: _count_signals(jobs, keywords, now)
        for role, keywords in ROLE_KEYWORDS.items()
    }
    max_recent = max((recent for recent, _ in counts.values()), default=0)
    return {
        role: _direction_and_score(recent, previous, max_recent)
        for role, (recent, previous) in counts.items()
    }


def analyse_skill_radar(
    jobs: list[dict[str, Any]],
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    counts = {
        skill: _count_signals(jobs, keywords, now)
        for skill, keywords in SKILL_KEYWORDS.items()
    }
    max_recent = max((recent for recent, _ in counts.values()), default=0)
    radar = []
    for skill, (recent, previous) in counts.items():
        signal = _direction_and_score(recent, previous, max_recent)
        radar.append(
            {
                "skill": skill,
                "recent": recent,
                "previous": previous,
                "sample_count": signal["sample_count"],
                "demand_index": signal["demand_index"],
                "change": signal["momentum"],
                "direction": signal["direction"],
            }
        )
    return sorted(radar, key=lambda item: (-item["recent"], item["skill"]))


def apply_trends_to_matches(
    base_matches: list[dict[str, Any]],
    role_trends: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Apply only a small positive market-demand bonus.

    Career fit remains primarily determined by the user's assessed
    O*NET skills, knowledge and technologies.

    The remote-job sample must not dominate the recommendation because
    some occupations are naturally less represented in remote-job feeds.
    """
    MAX_MARKET_BONUS = 3.0

    adjusted = []

    for match in base_matches:
        result = match.copy()

        base_score = float(
            match.get("overall") or 0.0
        )

        trend = role_trends.get(
            match.get("role", ""),
            {},
        )

        demand_score = trend.get("demand_index")

        # Compatibility with older engine/cache versions.
        if demand_score is None:
            demand_score = trend.get("trend_score")

        direction = trend.get(
            "direction",
            "Insufficient signal",
        )

        has_evidence = (
            direction != "Insufficient signal"
            and demand_score is not None
        )

        market_bonus = 0.0

        if has_evidence:
            demand_score = float(demand_score)

            # A demand score of 50/100 or below gives no bonus.
            # A demand score of 100/100 gives the maximum +3 points.
            market_bonus = max(
                0.0,
                min(
                    MAX_MARKET_BONUS,
                    ((demand_score - 50.0) / 50.0)
                    * MAX_MARKET_BONUS,
                ),
            )

        future_match = max(
            0.0,
            min(
                100.0,
                base_score + market_bonus,
            ),
        )

        result.update(
            {
                "base_match": round(base_score, 1),

                # Keep the existing field name for compatibility with
                # app.py and scenario_engine.py. It now represents
                # relative current posting demand, not time momentum.
                "trend_score": (
                    float(demand_score)
                    if has_evidence
                    else None
                ),

                "market_bonus": round(
                    market_bonus,
                    1,
                ),

                "future_match": round(
                    future_match,
                    1,
                ),

                "trend_direction": direction,

                "market_demand_index": trend.get(
                    "demand_index"
                ),

                "trend_momentum": trend.get(
                    "momentum"
                ),

                "recent_signal": trend.get(
                    "recent_signal",
                    0,
                ),

                "previous_signal": trend.get(
                    "previous_signal",
                    0,
                ),

                "trend_sample_count": trend.get(
                    "sample_count",
                    0,
                ),

                "trend_adjusted": has_evidence,
            }
        )

        adjusted.append(result)

    return sorted(
        adjusted,
        key=lambda item: (
            item.get("future_match", 0),
            item.get("confidence", 0),
            item.get("base_match", 0),
        ),
        reverse=True,
    )



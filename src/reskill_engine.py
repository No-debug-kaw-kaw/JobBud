"""Learning paths generated from scored, role-specific O*NET skill gaps."""

import json
import math
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
RESOURCE_FILE = BASE_DIR / "config" / "learning_resources.json"

OFFICIAL_FALLBACKS = [
    {
        "keywords": ["microsoft"],
        "title": "Microsoft Learn",
        "provider": "Microsoft",
        "url": "https://learn.microsoft.com/training/",
        "cost": "Free self-paced learning available",
        "description": "Official Microsoft training catalog."
    },
    {
        "keywords": ["ibm"],
        "title": "IBM SkillsBuild",
        "provider": "IBM",
        "url": "https://skillsbuild.org/learning-catalog",
        "cost": "Free",
        "description": "Official IBM learning catalog for technology and professional skills."
    },
    {
        "keywords": ["sap"],
        "title": "SAP Learning",
        "provider": "SAP",
        "url": "https://learning.sap.com/",
        "cost": "Free self-paced courses available",
        "description": "Official SAP learning platform with free self-paced courses."
    },
    {
        "keywords": ["oracle"],
        "title": "Oracle Career and Learning Resources",
        "provider": "Oracle Academy",
        "url": "https://academy.oracle.com/en/resources-summary.html",
        "cost": "Free learning resources available",
        "description": "Official Oracle learning and career resources."
    }
]


def load_learning_resources(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or RESOURCE_FILE
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        resources = payload.get("resources", [])
        return resources if isinstance(resources, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _resource_for_skill(
    skill: str,
    resources: list[dict[str, Any]],
) -> dict[str, Any] | None:

    normalized = skill.lower()

    # 1. Prefer exact / specific resource mapping
    for resource in resources:

        for keyword in resource.get(
            "keywords",
            []
        ):

            pattern = (
                rf"(?<!\w)"
                rf"{re.escape(str(keyword).lower())}"
                rf"(?!\w)"
            )

            if re.search(
                pattern,
                normalized
            ):
                return resource

    # 2. If no specific course exists,
    # use a verified official learning platform
    for fallback in OFFICIAL_FALLBACKS:

        for keyword in fallback.get(
            "keywords",
            []
        ):

            if keyword.lower() in normalized:

                return {
                    "title":
                        fallback["title"],

                    "provider":
                        fallback["provider"],

                    "url":
                        fallback["url"],

                    "cost":
                        fallback["cost"],

                    "description":
                        fallback["description"],
                }

    # 3. No verified resource available
    return None

def select_diverse_gaps(
    gaps: list[dict],
    limit: int = 5,
) -> list[dict]:
    """
    Select only genuine assessed gaps while trying
    to represent different development categories.

    If a category has no real gap, it is skipped.
    Remaining places are filled by the strongest
    available genuine gaps.
    """

    valid_gaps = []

    for item in gaps:

        gap = item.get("gap")

        try:
            gap_value = float(gap)
        except (TypeError, ValueError):
            continue

        # Never recommend something that is not
        # actually an assessed gap.
        if gap_value <= 0:
            continue

        copy = dict(item)
        copy["_gap_value"] = gap_value

        try:
            importance = float(
                item.get("importance", 1)
            )
        except (TypeError, ValueError):
            importance = 1.0

        copy["_importance_value"] = importance

        # Larger gap + higher O*NET importance
        # receives higher priority.
        copy["_priority_score"] = (
            gap_value * importance
        )

        valid_gaps.append(copy)

    if not valid_gaps:
        return []

    valid_gaps.sort(
        key=lambda x: (
            x["_priority_score"],
            x["_gap_value"],
        ),
        reverse=True,
    )

    selected = []
    used_ids = set()

    # Try to include several kinds of development,
    # but ONLY when a genuine gap exists.
    preferred_categories = [
        "Essential",
        "Transferable",
        "Knowledge",
        "Technology",
    ]

    for category in preferred_categories:

        candidate = next(
            (
                item
                for item in valid_gaps
                if str(
                    item.get("group", "")
                ).strip().lower()
                == category.lower()
                and id(item) not in used_ids
            ),
            None,
        )

        if candidate is not None:

            selected.append(candidate)
            used_ids.add(id(candidate))

        if len(selected) >= limit:
            break

    # Fill remaining places with the strongest
    # genuine gaps, regardless of category.
    for item in valid_gaps:

        if len(selected) >= limit:
            break

        if id(item) in used_ids:
            continue

        selected.append(item)
        used_ids.add(id(item))

    # Remove temporary ranking fields.
    cleaned = []

    for item in selected:

        item = dict(item)

        item.pop(
            "_gap_value",
            None,
        )

        item.pop(
            "_importance_value",
            None,
        )

        item.pop(
            "_priority_score",
            None,
        )

        cleaned.append(item)

    return cleaned

def build_learning_path(
    match: dict[str, Any],
    *,
    resources: list[dict[str, Any]] | None = None,
    max_steps: int = 5,
) -> list[dict[str, Any]]:
    """
    Build a personalised learning pathway from genuine
    assessed gaps.

    The pathway tries to include different categories
    when real gaps exist, without inventing gaps.
    """

    resource_catalog = (
        resources
        if resources is not None
        else load_learning_resources()
    )

    # Step 1: keep only genuine assessed gaps
    gaps = [
        gap
        for gap in match.get("gaps", [])
        if (
            gap.get("skill")
            and float(gap.get("gap", 0) or 0) > 0
        )
    ]

    # Step 2: choose a diverse set of genuine gaps
    selected_gaps = select_diverse_gaps(
        gaps,
        limit=max_steps,
    )

    path = []

    # Step 3: build learning pathway
    for position, gap in enumerate(
        selected_gaps,
        start=1,
    ):

        gap_size = float(
            gap.get("gap", 0)
        )

        importance = float(
            gap.get("importance", 0)
        )

        is_technology = (
            gap.get("group") == "Technology"
        )

        estimated_weeks = max(
            1,
            min(
                8,
                math.ceil(gap_size * 1.4)
            )
        )

        resource = _resource_for_skill(
            str(gap["skill"]),
            resource_catalog,
        )

        if is_technology:

            current_level = (
                "Not self-reported"
            )

            target_level = (
                "Technology listed for this "
                "O*NET occupation"
            )

        else:

            current_level = (
                f"{float(gap.get('user', 0)):.1f}/5"
            )

            target_level = (
                f"{float(gap.get('target', 0)):.1f}/5"
            )

        path.append(
            {
                "step": position,

                "skill":
                    str(gap["skill"]),

                "group":
                    str(
                        gap.get(
                            "group",
                            "O*NET skill"
                        )
                    ),

                "current_level":
                    current_level,

                "target_level":
                    target_level,

                "gap":
                    gap_size,

                "importance":
                    importance,

                "priority":
                    gap_size * importance,

                "estimated_weeks":
                    estimated_weeks,

                "time_basis":
                    (
                        "Team planning estimate "
                        "based on assessed gap size"
                    ),

                "why_it_matters":
                    (
                        f"O*NET lists this for "
                        f"{match.get('role', 'the selected role')}; "
                        f"the assessed gap is "
                        f"{gap_size:.1f} points and its O*NET "
                        f"importance is {importance:.2f}/5."
                    ),

                "resource_title":
                    (
                        resource.get("title")
                        if resource
                        else
                        "Learning resource not yet mapped"
                    ),

                "provider":
                    (
                        resource.get("provider")
                        if resource
                        else None
                    ),

                "source_url":
                    (
                        resource.get("url")
                        if resource
                        else None
                    ),

                "resource_cost":
                    (
                        resource.get("cost")
                        if resource
                        else None
                    ),
            }
        )

    return path
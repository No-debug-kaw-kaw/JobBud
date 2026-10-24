"""Interpretive, role-based contribution mappings to official UN SDGs."""

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
MAPPING_FILE = BASE_DIR / "config" / "sdg_mapping.json"


def load_sdg_mapping(path: Path | None = None) -> dict[str, Any]:
    source = path or MAPPING_FILE
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_role_sdg_mappings(role: str) -> list[dict[str, Any]]:
    return load_sdg_mapping().get("careers", {}).get(role, [])


def get_skill_category_sdg_mappings(category: str) -> list[dict[str, Any]]:
    key = category.strip().lower()
    return load_sdg_mapping().get("skill_categories", {}).get(key, [])


def get_match_sdg_impact(match: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": match.get("role", ""),
        "label": load_sdg_mapping().get("label", ""),
        "career_mappings": get_role_sdg_mappings(match.get("role", "")),
        "skill_categories": {
            group: get_skill_category_sdg_mappings(group)
            for group in ("essential", "transferable", "knowledge", "technology")
        },
    }

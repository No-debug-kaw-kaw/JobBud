"""Optional RunPod explanation layer with a deterministic local fallback."""

import json
import os
from typing import Any

import requests
from i18n import t, tf, term_label, role_label, signal_label


RUNPOD_BASE_URL = "https://api.runpod.ai/v2"


def _format_top_items(items: list[dict[str, Any]], limit: int = 3, language: str = "en") -> str:
    if not items:
        return t("explanation_empty", language)
    return "; ".join(
        tf("explanation_item", language,
           skill=term_label(item.get("skill", ""), language),
           user=f"{float(item.get('user', 0)):.1f}",
           target=f"{float(item.get('target', 0)):.1f}")
        for item in items[:limit]
    )


def _technology_items(match: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = [
        item
        for item in [*match.get("strengths", []), *match.get("gaps", [])]
        if item.get("group") == "Technology"
    ]
    selected = list(
        {item.get("skill"): item for item in items if float(item.get("user", 0)) > 0}
        .values()
    )
    not_selected = list(
        {item.get("skill"): item for item in items if float(item.get("user", 0)) <= 0}
        .values()
    )
    return selected, not_selected


def fallback_explanation(match: dict[str, Any], language: str = "en") -> str:
    strengths = _format_top_items(
        [item for item in match.get("strengths", []) if item.get("group") != "Technology"],
        language=language,
    )
    gaps = _format_top_items(
        [item for item in match.get("gaps", []) if item.get("group") != "Technology"],
        language=language,
    )
    selected_tools, not_selected_tools = _technology_items(match)
    if selected_tools:
        tool_note = tf("explanation_tools", language,
                       tools=", ".join(item.get("skill", "") for item in selected_tools[:3]))
    elif not_selected_tools:
        tool_note = t("explanation_no_tools", language)
    else:
        tool_note = ""
    trend = match.get("trend_direction", "Insufficient signal")
    if trend == "Insufficient signal":
        trend_note = t("explanation_insufficient", language)
    else:
        trend_note = tf("explanation_signal", language, signal=signal_label(trend, language))
    return " ".join([
        tf("explanation_intro", language, role=role_label(match.get("role", ""), language)),
        tf("explanation_strengths", language, items=strengths),
        tf("explanation_gaps", language, items=gaps),
        tool_note, trend_note,
    ])


def _extract_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = [text for item in value if (text := _extract_text(item))]
        return "\n".join(parts) if parts else None
    if isinstance(value, dict):
        for key in (
            "output",
            "text",
            "generated_text",
            "response",
            "content",
            "result",
            "choices",
            "message",
        ):
            if key in value:
                text = _extract_text(value[key])
                if text:
                    return text
    return None


def explain_recommendation(
    profile: dict[str, Any],
    match: dict[str, Any],
    *,
    learning_path: list[dict[str, Any]] | None = None,
    sdg_impact: dict[str, Any] | None = None,
    language: str = "en",
    session: Any = requests,
    timeout: int = 30,
) -> dict[str, str]:
    """Ask the configured endpoint to explain existing results, never score them."""
    api_key = os.getenv("RUNPOD_API_KEY")
    endpoint_id = os.getenv("RUNPOD_ENDPOINT_ID")
    fallback = fallback_explanation(match, language)
    if not api_key or not endpoint_id:
        return {"text": fallback, "source": "Rule-based fallback"}

    structured_results = {
        "profile_context_not_used_for_scoring": {
            "user_type": profile.get("user_type"),
            "background": profile.get("background"),
            "experience": profile.get("experience"),
            "interests": profile.get("interests", []),
        },
        "match": {
            "role": match.get("role"),
            "base_match": match.get("base_match", match.get("overall")),
            "future_match": match.get("future_match"),
            "confidence": match.get("confidence"),
            "component_scores": match.get("component_scores"),
            "trend_direction": match.get("trend_direction"),
            "trend_score": match.get("trend_score"),
            "strengths": [
                item
                for item in match.get("strengths", [])
                if item.get("group") != "Technology"
            ][:5],
            "gaps": [
                item
                for item in match.get("gaps", [])
                if item.get("group") != "Technology"
            ][:5],
            "technology_self_report": {
                "selected_tools": [
                    item.get("skill") for item in _technology_items(match)[0][:10]
                ],
                "not_selected_tools": [
                    item.get("skill") for item in _technology_items(match)[1][:10]
                ],
                "not_a_1_to_5_skill_rating": True,
            },
        },
        "learning_path": (learning_path or [])[:5],
        "sdg_impact": sdg_impact or {},
    }
    prompt = (
        f"Write entirely in { {'en': 'English', 'ms': 'Bahasa Melayu (Malay)', 'zh': 'Simplified Chinese'}.get(language, 'English') }. "
        "Write a concise, supportive career explanation using only the JSON "
        "facts below. Do not invent jobs, statistics, course names, trend "
        "claims, or credentials. Explain why the role fits, the most important "
        "assessed gaps, what to learn first if a verified resource is present, "
        "and how to interpret uncertainty. Treat match values and scenarios as "
        "estimates, not predictions or hiring decisions. If trend direction is "
        "'Insufficient signal', say so and do not imply a trend adjustment. "
        "Technology selection is self-reported tool usage, not a 1-5 rating. "
        "The profile context is not part of the scoring formula.\n\n"
        f"RESULTS_JSON:\n{json.dumps(structured_results, ensure_ascii=False)}"
    )
    try:
        response = session.post(
            f"{RUNPOD_BASE_URL}/{endpoint_id}/runsync",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": {
                    "prompt": prompt,
                    "max_new_tokens": 400,
                    "temperature": 0.2,
                }
            },
            timeout=timeout,
        )
        response.raise_for_status()
        generated = _extract_text(response.json())
        if generated:
            return {"text": generated, "source": "RunPod"}
    except (requests.RequestException, ValueError, TypeError):
        pass
    return {"text": fallback, "source": "Rule-based fallback"}

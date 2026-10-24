"""Malaysia industry salary context from DOSM wages by industry."""

import csv
import io
from typing import Any

import requests


DATA_URL = "https://storage.dosm.gov.my/labour/wages_industry.csv"

DATASET_NAME = "Annual Salaries & Wages by Industry & Sex"

SOURCE_NAME = "Department of Statistics Malaysia (DOSM)"


INDUSTRY_LABELS = {
    "J": "Information and communication",
    "K": "Financial and insurance/takaful activities",
    "M": "Professional, scientific and technical activities",
}


ROLE_TO_INDUSTRY = {
    "Business Intelligence Analysts": "J",

    "Data Scientists": "J",

    "Statisticians": "M",

    "Actuaries": "K",

    "Economists": "M",

    "Market Research Analysts and Marketing Specialists": "M",

    "Accountants and Auditors": "M",

    "Management Analysts": "M",

    "Financial Quantitative Analysts": "K",

    "Loan Officers": "K",

    "Financial Examiners": "K",
}


def _to_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def get_salary_benchmark(
    role: str,
) -> dict[str, Any]:

    section = ROLE_TO_INDUSTRY.get(role)

    if not section:
        return {
            "available": False,
            "role": role,
            "error": "No industry mapping is available for this role.",
        }

    try:
        response = requests.get(
            DATA_URL,
            timeout=20,
            headers={
                "User-Agent": "AI-Career-Navigator/1.0",
            },
        )

        response.raise_for_status()

        reader = csv.DictReader(
            io.StringIO(response.text)
        )

        matching_rows = []

        for row in reader:

            if (
                str(row.get("sex", "")).strip().lower()
                != "both"
            ):
                continue

            if (
                str(row.get("section", "")).strip().upper()
                != section
            ):
                continue

            matching_rows.append(row)

        if not matching_rows:
            return {
                "available": False,
                "role": role,
                "section": section,
                "error": "No DOSM salary row found for this industry.",
            }

        matching_rows.sort(
            key=lambda row: str(
                row.get("date", "")
            ),
            reverse=True,
        )

        latest = matching_rows[0]

        date_value = str(
            latest.get("date", "")
        )

        year = (
            date_value[:4]
            if len(date_value) >= 4
            else "Unknown"
        )

        median = _to_int(
            latest.get("wages_median")
        )

        mean = _to_int(
            latest.get("wages_mean")
        )

        if median is None or mean is None:
            return {
                "available": False,
                "role": role,
                "section": section,
                "error": "DOSM wage values are unavailable.",
            }

        industry_label = INDUSTRY_LABELS.get(
            section,
            f"MSIC section {section}",
        )

        return {
            "available": True,

            "role": role,

            "industry_section": section,

            "industry_label": industry_label,

            "median": median,

            "mean": mean,

            "year": year,

            "source": SOURCE_NAME,

            "dataset": DATASET_NAME,

            "source_url":
                "https://data.gov.my/data-catalogue/wages_industry",

            "note": (
                "This is an industry-level Malaysian salary context "
                "rather than an exact salary for this specific job title."
            ),
        }

    except Exception as error:

        return {
            "available": False,

            "role": role,

            "section": section,

            "error":
                f"Salary data unavailable "
                f"({type(error).__name__}).",
        }
        
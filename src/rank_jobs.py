"""Rank and classify jobs by score, type, and country."""

import json
import os
import sys

import pandas as pd

JOBS_SCORED_PATH = os.path.join("data", "jobs_scored.json")


def rank_jobs(jobs_scored_path: str = JOBS_SCORED_PATH) -> dict:
    """Load scored jobs, sort by score, classify, and group by country.

    Returns a dict with keys:
        - all_jobs: list of all jobs sorted by score descending
        - by_classification: dict mapping 'research'/'industry' to job lists
        - by_country: dict mapping country name to job lists
    """
    if not os.path.exists(jobs_scored_path):
        raise FileNotFoundError(f"Scored jobs file not found: {jobs_scored_path}")

    with open(jobs_scored_path, encoding="utf-8") as fh:
        jobs = json.load(fh)

    if not jobs:
        print("[rank_jobs] No scored jobs to rank.")
        return {"all_jobs": [], "by_classification": {}, "by_country": {}}

    df = pd.DataFrame(jobs)

    # Ensure required columns exist with sensible defaults
    if "score" not in df.columns:
        df["score"] = 0
    if "classification" not in df.columns:
        df["classification"] = "industry"
    if "country" not in df.columns:
        df["country"] = "Unknown"

    # Coerce score to numeric, replacing bad values with 0
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)

    # Sort by score descending
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    all_jobs = df.to_dict(orient="records")

    # Group by classification
    by_classification: dict[str, list[dict]] = {}
    for classification, group in df.groupby("classification"):
        by_classification[str(classification)] = group.to_dict(orient="records")

    # Group by country
    by_country: dict[str, list[dict]] = {}
    for country, group in df.groupby("country"):
        by_country[str(country)] = group.to_dict(orient="records")

    result = {
        "all_jobs": all_jobs,
        "by_classification": by_classification,
        "by_country": by_country,
    }

    print(
        f"[rank_jobs] Ranked {len(all_jobs)} jobs. "
        f"Classifications: {list(by_classification.keys())}. "
        f"Countries: {len(by_country)}"
    )
    return result


if __name__ == "__main__":
    try:
        result = rank_jobs()
        print(json.dumps(result, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

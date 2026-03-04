"""Main pipeline orchestrator for the CV-automation job search system.

Pipeline steps
--------------
1. parse_cv      – Extract skills from CV.pdf → data/profile.json
2. job_search    – Search job sites           → data/jobs_raw.json
3. evaluate_jobs – Score jobs via LLM         → data/jobs_scored.json
4. rank_jobs     – Rank & classify jobs
5. report_builder– Build HTML report          → output/report.html
6. email_sender  – Send report via Gmail
"""

import sys

from src.parse_cv import parse_cv
from src.job_search import run as search_jobs
from src.evaluate_jobs import evaluate_jobs
from src.rank_jobs import rank_jobs
from src.report_builder import build_report
from src.email_sender import send_email


def run_pipeline() -> None:
    """Execute the full job search pipeline end-to-end."""

    # Step 1: Parse CV and extract profile
    print("\n=== Step 1/6: Parsing CV ===")
    try:
        profile = parse_cv()
        print(f"  → Extracted {len(profile.get('skills', []))} skills")
    except Exception as exc:
        print(f"[main] FATAL – parse_cv failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Search for jobs
    print("\n=== Step 2/6: Searching jobs ===")
    try:
        raw_jobs = search_jobs()
        print(f"  → Found {len(raw_jobs)} raw job listings")
    except Exception as exc:
        print(f"[main] FATAL – job_search failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if not raw_jobs:
        print("[main] No jobs found – exiting early.")
        sys.exit(0)

    # Step 3: Evaluate jobs with LLM
    print("\n=== Step 3/6: Evaluating jobs ===")
    try:
        scored_jobs = evaluate_jobs()
        print(f"  → Scored {len(scored_jobs)} jobs")
    except Exception as exc:
        print(f"[main] FATAL – evaluate_jobs failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Step 4: Rank and classify
    print("\n=== Step 4/6: Ranking jobs ===")
    try:
        ranked = rank_jobs()
        all_jobs = ranked.get("all_jobs", [])
        print(
            f"  → Top job: {all_jobs[0].get('title', 'N/A')} "
            f"(score {all_jobs[0].get('score', 0)}/10)"
            if all_jobs
            else "  → No ranked jobs"
        )
    except Exception as exc:
        print(f"[main] FATAL – rank_jobs failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Step 5: Build HTML report
    print("\n=== Step 5/6: Building report ===")
    try:
        build_report()
        print("  → Report generated at output/report.html")
    except Exception as exc:
        print(f"[main] FATAL – report_builder failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Step 6: Send email
    print("\n=== Step 6/6: Sending email ===")
    try:
        send_email()
        print("  → Email sent successfully")
    except Exception as exc:
        # Email failure is non-fatal; report has already been created
        print(f"[main] WARNING – email_sender failed: {exc}", file=sys.stderr)

    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    run_pipeline()

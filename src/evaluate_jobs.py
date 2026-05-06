"""Evaluate job descriptions against a candidate profile using an LLM."""

import json
import os
import sys
import time

import config
from src.llm_client import OpenAI, validate_llm_configuration
from src.matching import evaluate_and_enrich_job

PROFILE_PATH = os.path.join("data", "profile.json")
JOBS_RAW_PATH = os.path.join("data", "jobs_raw.json")
JOBS_SCORED_PATH = os.path.join("data", "jobs_scored.json")

_DELAY_BETWEEN_CALLS = 1  # seconds – respect rate limits
_MAX_DESC_CHARS = 3000  # truncate long descriptions to save tokens


def _config_value(name: str, default):
    """Read a config attribute while staying compatible with mocked config modules."""
    if hasattr(config, "__dict__") and name in config.__dict__:
        return getattr(config, name)
    return default


def _build_evaluation_prompt(profile: dict, job: dict) -> str:
    """Build the LLM prompt for evaluating a single job."""
    skills = ", ".join(profile.get("skills", []))
    summary = profile.get("summary", "")
    description = job.get("description", "")[:_MAX_DESC_CHARS]
    title = job.get("title", "N/A")
    company = job.get("company", "N/A")

    return (
        "You are an expert job-fit evaluator.\n"
        "Given a candidate profile and a job description, respond with a JSON object "
        "containing:\n"
        "  - score (integer 1-10, where 10 is a perfect fit)\n"
        "  - classification (one of: 'research', 'industry')\n"
        "  - reasoning (string, 1-2 sentences explaining the score)\n\n"
        "Return ONLY valid JSON with no markdown fences.\n\n"
        f"Candidate skills: {skills}\n"
        f"Candidate summary: {summary}\n\n"
        f"Job title: {title}\n"
        f"Company: {company}\n"
        f"Job description:\n{description}"
    )


def evaluate_job(profile: dict, job: dict, client: OpenAI) -> dict:
    """Evaluate a single job and return the job dict enriched with LLM scores."""
    prompt = _build_evaluation_prompt(profile, job)

    try:
        evaluation = client.generate_json(prompt, temperature=0.1)
    except ValueError as exc:
        print(
            f"[evaluate_jobs] JSON parse error for '{job.get('title')}': {exc}",
            file=sys.stderr,
        )
        evaluation = {"score": 0, "classification": "unknown", "reasoning": "Parse error"}
    except Exception as exc:  # noqa: BLE001
        print(
            f"[evaluate_jobs] LLM error for '{job.get('title')}': {exc}",
            file=sys.stderr,
        )
        evaluation = {"score": 0, "classification": "unknown", "reasoning": str(exc)}

    # Combine LLM evaluation with deterministic signals (keywords, embeddings)
    enriched = evaluate_and_enrich_job(profile, job, evaluation)
    return enriched


def evaluate_jobs(
    profile_path: str = PROFILE_PATH,
    jobs_raw_path: str = JOBS_RAW_PATH,
) -> list[dict]:
    """Load profile and raw jobs, evaluate each, save scored jobs, and return them."""
    provider = str(_config_value("LLM_PROVIDER", "openai"))
    api_key = _config_value("LLM_API_KEY", "") or _config_value("OPENAI_API_KEY", "")
    model = str(_config_value("LLM_MODEL", "gpt-4o-mini"))
    base_url = _config_value("LLM_BASE_URL", "") or None
    timeout = float(_config_value("LLM_TIMEOUT", 60))
    max_retries = int(_config_value("LLM_MAX_RETRIES", 3))
    temperature = float(_config_value("LLM_TEMPERATURE", 0.2))

    validate_llm_configuration(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        temperature=temperature,
    )

    for path in (profile_path, jobs_raw_path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required file not found: {path}")

    with open(profile_path, encoding="utf-8") as fh:
        profile = json.load(fh)

    with open(jobs_raw_path, encoding="utf-8") as fh:
        jobs = json.load(fh)

    if not jobs:
        print("[evaluate_jobs] No jobs to evaluate.")
        return []

    client = OpenAI(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        temperature=temperature,
    )
    scored_jobs: list[dict] = []

    print(f"[evaluate_jobs] Evaluating {len(jobs)} jobs …")
    for i, job in enumerate(jobs, start=1):
        print(
            f"[evaluate_jobs] ({i}/{len(jobs)}) Evaluating: {job.get('title', 'N/A')} "
            f"@ {job.get('company', 'N/A')}"
        )
        scored = evaluate_job(profile, job, client)
        scored_jobs.append(scored)
        time.sleep(_DELAY_BETWEEN_CALLS)

    os.makedirs("data", exist_ok=True)
    with open(JOBS_SCORED_PATH, "w", encoding="utf-8") as fh:
        json.dump(scored_jobs, fh, indent=2, ensure_ascii=False)

    print(f"[evaluate_jobs] Scored jobs saved to {JOBS_SCORED_PATH}")
    return scored_jobs


if __name__ == "__main__":
    try:
        result = evaluate_jobs()
        print(f"Evaluated {len(result)} jobs")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

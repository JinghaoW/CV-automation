"""Parse CV.pdf and extract skills using an LLM.

Refactored for better testability and typing while preserving the original
`parse_cv` behavior and file-based outputs.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pdfplumber

import config
from src.llm_client import OpenAI, validate_llm_configuration

PROFILE_PATH = os.path.join("data", "profile.json")


@dataclass
class Profile:
    name: str = ""
    skills: List[str] = field(default_factory=list)
    experience_years: int | float = 0
    education: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        return cls(
            name=data.get("name", ""),
            skills=list(data.get("skills", [])) if data.get("skills") is not None else [],
            experience_years=data.get("experience_years", 0) or 0,
            education=list(data.get("education", [])) if data.get("education") is not None else [],
            languages=list(data.get("languages", [])) if data.get("languages") is not None else [],
            summary=data.get("summary", "") or "",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "skills": self.skills,
            "experience_years": self.experience_years,
            "education": self.education,
            "languages": self.languages,
            "summary": self.summary,
        }


def _config_value(name: str, default):
    if hasattr(config, "__dict__") and name in config.__dict__:
        return getattr(config, name)
    return default


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using pdfplumber."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"CV file not found: {pdf_path}")

    text_parts: List[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    if not text_parts:
        raise ValueError(f"No text could be extracted from {pdf_path}")

    return "\n".join(text_parts)


def parse_text_to_profile(cv_text: str, client: OpenAI) -> Profile:
    """Parse CV text via an LLM client and return a typed Profile."""
    prompt = (
        "You are a professional CV analyzer. "
        "Given the following CV text, extract a structured profile as JSON with these fields:\n"
        "  - name (string)\n"
        "  - skills (list of strings)\n"
        "  - experience_years (number, your best estimate)\n"
        "  - education (list of strings)\n"
        "  - languages (list of strings)\n"
        "  - summary (string, 2-3 sentences)\n\n"
        "Return ONLY valid JSON with no markdown fences.\n\n"
        f"CV text:\n{cv_text}"
    )

    data = client.generate_json(prompt, temperature=0.2)
    return Profile.from_dict(data)


def extract_skills_with_llm(cv_text: str, client: OpenAI) -> dict:
    """Backward-compatible wrapper that returns a dict (keeps existing API)."""
    profile = parse_text_to_profile(cv_text, client)
    return profile.to_dict()


def save_profile(profile: Profile, path: str = PROFILE_PATH) -> None:
    os.makedirs(os.path.dirname(path) or "data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile.to_dict(), fh, indent=2, ensure_ascii=False)


def save_cv_file(content_bytes: bytes, dest_path: str) -> None:
    os.makedirs(os.path.dirname(dest_path) or "cv", exist_ok=True)
    with open(dest_path, "wb") as fh:
        fh.write(content_bytes)


def parse_cv(cv_path: str = config.CV_PATH) -> dict:
    """Full parse pipeline: read PDF → extract skills via LLM → save profile.

    Returns the profile dict for backwards compatibility.
    """
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

    client = OpenAI(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        temperature=temperature,
    )

    print(f"[parse_cv] Extracting text from {cv_path} …")
    cv_text = extract_text_from_pdf(cv_path)

    print("[parse_cv] Extracting skills with LLM …")
    profile = parse_text_to_profile(cv_text, client)

    save_profile(profile, PROFILE_PATH)

    print(f"[parse_cv] Profile saved to {PROFILE_PATH}")
    return profile.to_dict()


if __name__ == "__main__":
    try:
        result = parse_cv()
        print(json.dumps(result, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

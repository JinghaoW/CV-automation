"""Parse CV.pdf and extract skills using an LLM."""

import json
import os
import sys

import pdfplumber
from openai import OpenAI

CV_PATH = os.environ.get("CV_PATH", "CV.pdf")
PROFILE_PATH = os.path.join("data", "profile.json")


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF file using pdfplumber."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"CV file not found: {pdf_path}")

    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    if not text_parts:
        raise ValueError(f"No text could be extracted from {pdf_path}")

    return "\n".join(text_parts)


def extract_skills_with_llm(cv_text: str, client: OpenAI) -> dict:
    """Use an LLM to extract structured skills and profile from CV text."""
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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("LLM returned no content (content was None)")
    raw = content.strip()

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {raw}") from exc

    return profile


def parse_cv(cv_path: str = CV_PATH) -> dict:
    """Full parse pipeline: read PDF → extract skills via LLM → save profile.

    Returns the profile dict.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)

    print(f"[parse_cv] Extracting text from {cv_path} …")
    cv_text = extract_text_from_pdf(cv_path)

    print("[parse_cv] Extracting skills with LLM …")
    profile = extract_skills_with_llm(cv_text, client)

    os.makedirs("data", exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2, ensure_ascii=False)

    print(f"[parse_cv] Profile saved to {PROFILE_PATH}")
    return profile


if __name__ == "__main__":
    try:
        result = parse_cv()
        print(json.dumps(result, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

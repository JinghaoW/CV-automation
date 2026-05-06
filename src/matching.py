"""Recommendation matching engine.

Provides a modular scoring pipeline with:
- keyword scoring
- embedding-style (bag-of-words cosine) similarity
- LLM evaluation layer (score 1-10 expected)
- configurable weights to combine components into a final score (1-10)

Design notes:
- keep LLM-dominant default weights so existing behavior is preserved
- embedding and keyword scoring are deterministic and lightweight (no external deps)
- functions operate on plain dicts so they can be composed easily
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Optional

_WORD_RE = re.compile(r"\b\w+\b")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def _term_counts(tokens: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    return counts


def cosine_similarity_counts(a: Dict[str, int], b: Dict[str, int]) -> float:
    # deterministic cosine similarity between term-count maps; returns 0.0-1.0
    if not a or not b:
        return 0.0
    intersection = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in intersection)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def keyword_score(profile: Dict, job: Dict) -> float:
    """Score based on exact keyword overlap between profile.skills and job text.

    Returns a 0.0-1.0 score.
    """
    skills = profile.get("skills") or []
    if not skills:
        return 0.0
    skill_tokens = set(t.lower() for s in skills for t in _tokenize(s))
    text = " ".join([str(job.get("title", "")), str(job.get("company", "")), str(job.get("description", ""))])
    tokens = set(_tokenize(text))
    if not skill_tokens:
        return 0.0
    matches = skill_tokens & tokens
    return float(len(matches) / len(skill_tokens))


def embedding_similarity(profile: Dict, job: Dict) -> float:
    """Lightweight embedding-style similarity: cosine over bag-of-words counts.

    Returns a 0.0-1.0 score.
    """
    profile_text = " ".join([
        " ".join(profile.get("skills") or []),
        str(profile.get("summary", "")),
    ])
    job_text = " ".join([str(job.get("title", "")), str(job.get("description", "")), str(job.get("company", ""))])
    a = _term_counts(_tokenize(profile_text))
    b = _term_counts(_tokenize(job_text))
    return cosine_similarity_counts(a, b)


def llm_component_score(llm_evaluation: Optional[Dict]) -> float:
    """Normalize an LLM-provided score (1-10) to 0.0-1.0.

    If the LLM evaluation is missing or malformed, returns 0.0.
    """
    if not llm_evaluation:
        return 0.0
    score = llm_evaluation.get("score")
    try:
        s = float(score)
    except Exception:
        return 0.0
    # clamp and normalize
    s = max(0.0, min(s, 10.0))
    return (s - 1.0) / 9.0 if s >= 1.0 else 0.0


def combine_scores(
    *,
    llm_score_norm: float = 0.0,
    keyword_score_val: float = 0.0,
    embedding_score_val: float = 0.0,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Combine normalized component scores into a final 1-10 score.

    Component inputs are expected to be in 0.0-1.0 range. Default weights favor
    the LLM component to preserve existing behavior unless overridden.
    """
    if weights is None:
        weights = {"llm": 1.0, "keyword": 0.0, "embedding": 0.0}
    w_llm = float(weights.get("llm", 0.0))
    w_kw = float(weights.get("keyword", 0.0))
    w_emb = float(weights.get("embedding", 0.0))
    total_w = w_llm + w_kw + w_emb
    if total_w == 0:
        # avoid division by zero; default to LLM-only
        total_w = 1.0
        w_llm = 1.0
    combined_norm = (w_llm * llm_score_norm + w_kw * keyword_score_val + w_emb * embedding_score_val) / total_w
    # Map normalized 0.0-1.0 back to 1-10 integer score
    final = 1 + combined_norm * 9.0
    return round(final, 3)


def evaluate_and_enrich_job(profile: Dict, job: Dict, llm_evaluation: Optional[Dict], weights: Optional[Dict[str, float]] = None) -> Dict:
    """Produce an enriched job dict with combined score and maintain classification/reasoning.

    `llm_evaluation` is the structured output from the LLM (if available) so the
    caller can avoid re-calling the model. This function is deterministic when
    `llm_evaluation` is provided and weights are fixed.
    """
    # Preserve backward-compatible behavior: if the LLM explicitly returned a
    # zero score (used as an error sentinel in the previous pipeline), keep
    # the score at 0 rather than mapping to the 1-10 scale.
    if llm_evaluation and llm_evaluation.get("score") in (0, "0", 0.0):
        enriched = dict(job)
        enriched["score"] = 0
        if "classification" in llm_evaluation:
            enriched["classification"] = llm_evaluation.get("classification")
        if "reasoning" in llm_evaluation:
            enriched["reasoning"] = llm_evaluation.get("reasoning")
        return enriched

    kw = keyword_score(profile, job)
    emb = embedding_similarity(profile, job)
    lnorm = llm_component_score(llm_evaluation)
    combined = combine_scores(llm_score_norm=lnorm, keyword_score_val=kw, embedding_score_val=emb, weights=weights)

    enriched = dict(job)
    # Ensure score is an int-like 1-10 for compatibility
    enriched["score"] = int(round(combined))
    # Preserve LLM classification/reasoning when present
    if llm_evaluation:
        if "classification" in llm_evaluation:
            enriched["classification"] = llm_evaluation.get("classification")
        if "reasoning" in llm_evaluation:
            enriched["reasoning"] = llm_evaluation.get("reasoning")
    return enriched


__all__ = [
    "keyword_score",
    "embedding_similarity",
    "llm_component_score",
    "combine_scores",
    "evaluate_and_enrich_job",
]


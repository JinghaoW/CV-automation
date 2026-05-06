"""Unit tests for src/matching.py."""

from src.matching import (
    keyword_score,
    embedding_similarity,
    llm_component_score,
    combine_scores,
    evaluate_and_enrich_job,
)


def test_keyword_score_simple():
    profile = {"skills": ["Python", "Machine Learning"]}
    job = {"title": "ML Engineer", "description": "We use Python and ML for models."}
    s = keyword_score(profile, job)
    assert s > 0
    assert s <= 1.0


def test_embedding_similarity_deterministic():
    profile = {"skills": ["Python"], "summary": "Experienced dev"}
    job_a = {"title": "Python dev", "description": "Work with Python"}
    job_b = {"title": "Go dev", "description": "Work with Go"}
    sa = embedding_similarity(profile, job_a)
    sb = embedding_similarity(profile, job_b)
    assert sa > sb
    assert 0.0 <= sa <= 1.0


def test_llm_component_score_normalization():
    assert llm_component_score({"score": 1}) == 0.0
    assert llm_component_score({"score": 10}) == 1.0
    assert llm_component_score({"score": 5}) == (5 - 1) / 9


def test_combine_scores_defaults_to_llm():
    # LLM-only default behavior
    final = combine_scores(llm_score_norm=0.777, keyword_score_val=0.0, embedding_score_val=0.0)
    assert round(final) == 8


def test_evaluate_and_enrich_job_includes_llm_fields():
    profile = {"skills": ["Python"], "summary": "Dev"}
    job = {"title": "Engineer", "description": "Python role", "company": "Co"}
    llm_eval = {"score": 9, "classification": "industry", "reasoning": "Great fit"}
    enriched = evaluate_and_enrich_job(profile, job, llm_eval)
    assert enriched["score"] == 9
    assert enriched["classification"] == "industry"
    assert "reasoning" in enriched


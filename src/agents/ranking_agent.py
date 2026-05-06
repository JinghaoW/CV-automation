"""RankingAgent: rank jobs with typed output asynchronously."""
from __future__ import annotations

import asyncio
from typing import Dict, List

import pandas as pd


class RankingAgent:
    async def rank(self, scored_jobs: List[Dict]) -> Dict:
        # run the in-memory ranking similar to src.rank_jobs.rank_jobs
        def _rank_sync(jobs: List[Dict]) -> Dict:
            if not jobs:
                return {"all_jobs": [], "by_classification": {}, "by_country": {}}
            df = pd.DataFrame(jobs)
            if "score" not in df.columns:
                df["score"] = 0
            if "classification" not in df.columns:
                df["classification"] = "industry"
            if "country" not in df.columns:
                df["country"] = "Unknown"
            df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
            df = df.sort_values("score", ascending=False).reset_index(drop=True)
            all_jobs = df.to_dict(orient="records")
            by_class = {str(k): g.to_dict(orient="records") for k, g in df.groupby("classification")}
            by_country = {str(k): g.to_dict(orient="records") for k, g in df.groupby("country")}
            return {"all_jobs": all_jobs, "by_classification": by_class, "by_country": by_country}

        return await asyncio.to_thread(_rank_sync, scored_jobs)


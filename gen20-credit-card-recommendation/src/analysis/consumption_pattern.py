from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from ..logging_utils import get_logger, safe_mkdir


@dataclass(frozen=True)
class ConsumptionOutputs:
    tfidf_keywords_csv: Path
    monthly_trend_csv: Path


class ConsumptionPatternAnalyzer:
    """20대 소비 트렌드(유튜브 영상) 기반 키워드/월별 추이 분석(경량)."""

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        self.logger = get_logger()

    def run(
        self,
        *,
        youtube_consumption: pd.DataFrame,
        reports_dir: Path,
        top_k: int = 50,
    ) -> ConsumptionOutputs:
        safe_mkdir(reports_dir)

        tfidf_df = self._tfidf_keywords(youtube_consumption, top_k=top_k)
        tfidf_path = reports_dir / "yt_tfidf_keywords.csv"
        tfidf_df.to_csv(tfidf_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", tfidf_path)

        monthly = self._monthly_trend(youtube_consumption)
        monthly_path = reports_dir / "yt_monthly_trend.csv"
        monthly.to_csv(monthly_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", monthly_path)

        return ConsumptionOutputs(tfidf_keywords_csv=tfidf_path, monthly_trend_csv=monthly_path)

    def _tfidf_keywords(self, youtube_consumption: pd.DataFrame, top_k: int) -> pd.DataFrame:
        df = youtube_consumption.copy()
        title = df.get("video_title", pd.Series([""] * len(df)))
        summary = df.get("content_summary", pd.Series([""] * len(df)))
        text = (title.fillna("").astype(str) + " " + summary.fillna("").astype(str)).str.strip()

        if text.str.len().sum() == 0:
            return pd.DataFrame({"keyword": [], "tfidf": []})

        # 한국어 형태소 분석 없이도 동작하는 최소 설정(공백 기준)
        vec = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
        )
        X = vec.fit_transform(text.tolist())
        scores = X.mean(axis=0).A1
        terms = vec.get_feature_names_out()

        out = (
            pd.DataFrame({"keyword": terms, "tfidf": scores})
            .sort_values("tfidf", ascending=False)
            .head(top_k)
            .reset_index(drop=True)
        )
        return out

    def _monthly_trend(self, youtube_consumption: pd.DataFrame) -> pd.DataFrame:
        df = youtube_consumption.copy()
        if "publish_date" in df.columns:
            dt = pd.to_datetime(df["publish_date"], errors="coerce")
        else:
            dt = pd.NaT
        df["publish_month"] = dt.dt.to_period("M").dt.to_timestamp()

        # 월별 영상 수 + 평균 조회수/좋아요/댓글(있으면)
        agg = {"video_count": ("publish_month", "size")}
        for col in ["view_count", "like_count", "comment_count"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                agg[f"{col}_mean"] = (col, "mean")

        out = df.groupby("publish_month", dropna=False).agg(**agg).reset_index()
        out = out.sort_values("publish_month")
        return out


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .logging_utils import get_logger, safe_mkdir


@dataclass(frozen=True)
class PreprocessOutputs:
    """전처리 산출물 경로 모음."""

    cards_merged_csv: Path
    sentiment_csv: Path
    spending_pattern_csv: Path


class Preprocessor:
    """데이터 전처리 + 표준 processed CSV 생성."""

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        self.logger = get_logger()
        np.random.seed(random_seed)

    def run(
        self,
        *,
        processed_dir: Path,
        cards_info: pd.DataFrame,
        cards_benefits: pd.DataFrame,
        youtube_consumption: pd.DataFrame,
        youtube_comments: pd.DataFrame,
    ) -> PreprocessOutputs:
        """전처리 실행 후 processed CSV 저장."""

        safe_mkdir(processed_dir)

        cards_merged = self._merge_cards(cards_info, cards_benefits)
        cards_merged_csv = processed_dir / "cards_merged.csv"
        cards_merged.to_csv(cards_merged_csv, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", cards_merged_csv)

        spending_pattern = self._build_spending_pattern_20s(youtube_consumption)
        spending_pattern_csv = processed_dir / "spending_pattern_20s.csv"
        spending_pattern.to_csv(spending_pattern_csv, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", spending_pattern_csv)

        sentiment_df = self._init_sentiment_frame(youtube_comments)
        sentiment_csv = processed_dir / "sentiment_analysis.csv"
        sentiment_df.to_csv(sentiment_csv, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", sentiment_csv)

        return PreprocessOutputs(
            cards_merged_csv=cards_merged_csv,
            sentiment_csv=sentiment_csv,
            spending_pattern_csv=spending_pattern_csv,
        )

    def _merge_cards(self, cards_info: pd.DataFrame, cards_benefits: pd.DataFrame) -> pd.DataFrame:
        """cards_info + cards_benefits를 (카드-혜택) 레벨로 병합."""

        if "card_id" not in cards_info.columns or "card_id" not in cards_benefits.columns:
            raise ValueError("cards_info/cards_benefits에 card_id 컬럼이 필요합니다.")

        merged = cards_benefits.merge(cards_info, on="card_id", how="left", suffixes=("", "_info"))

        # 최소 컬럼 정렬(없으면 그대로 둠)
        preferred = [
            "card_id",
            "card_name",
            "issuer",
            "annual_fee_domestic",
            "annual_fee_overseas",
            "min_usage_requirement",
            "benefit_order",
            "benefit_category",
            "discount_type",
            "discount_rate",
            "is_optional",
            "benefit_summary",
            "benefit_detail",
            "card_image_url",
            "detail_page_url",
        ]
        cols = [c for c in preferred if c in merged.columns] + [c for c in merged.columns if c not in preferred]
        return merged[cols]

    def _build_spending_pattern_20s(self, youtube_consumption: pd.DataFrame) -> pd.DataFrame:
        """유튜브 소비 영상에서 월별/키워드 기반 '소비 패턴' 요약 테이블 생성(가벼운 버전)."""

        df = youtube_consumption.copy()
        if "publish_date" in df.columns:
            df["publish_month"] = pd.to_datetime(df["publish_date"], errors="coerce").dt.to_period("M").dt.to_timestamp()
        else:
            df["publish_month"] = pd.NaT

        # 키워드(related_keywords)가 쉼표 구분 텍스트라고 가정하고 빈도 집계
        kw_col = "related_keywords" if "related_keywords" in df.columns else None
        if kw_col is None:
            return pd.DataFrame({"publish_month": [], "top_keywords": [], "video_count": []})

        def _explode_keywords(s: object) -> list[str]:
            if not isinstance(s, str) or not s.strip():
                return []
            return [k.strip() for k in s.split(",") if k.strip()]

        df["__kw"] = df[kw_col].apply(_explode_keywords)
        exploded = df.explode("__kw")
        exploded = exploded.dropna(subset=["__kw"])

        kw_counts = (
            exploded.groupby(["publish_month", "__kw"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(["publish_month", "count"], ascending=[True, False])
        )

        top = kw_counts.groupby("publish_month").head(10)
        summary = (
            top.groupby("publish_month")
            .agg(top_keywords=("__kw", lambda x: ", ".join(list(x))), video_count=("count", "sum"))
            .reset_index()
        )
        return summary

    def _init_sentiment_frame(self, youtube_comments: pd.DataFrame) -> pd.DataFrame:
        """감성 분석 전용 테이블 스키마로 초기화(실제 점수는 분석 모듈에서 채움)."""

        df = youtube_comments.copy()
        if "comment_text" not in df.columns:
            # 표준화가 안 되어 있을 때를 대비
            text_candidates = [c for c in df.columns if "댓글" in c or "comment" in c.lower()]
            if text_candidates:
                df = df.rename(columns={text_candidates[0]: "comment_text"})
            else:
                df["comment_text"] = ""

        if "sentiment_score" not in df.columns:
            df["sentiment_score"] = np.nan
        if "dining_mention" not in df.columns:
            df["dining_mention"] = df["comment_text"].fillna("").astype(str).apply(self._is_dining_mention)

        keep = [c for c in ["video_publish_date", "video_title", "comment_text", "sentiment_score", "dining_mention"] if c in df.columns]
        return df[keep]

    def _is_dining_mention(self, text: str) -> bool:
        keywords = ["외식", "식비", "맛집", "예약", "웨이팅", "캐치테이블", "테이블링", "식신", "망고플레이트", "배달"]
        t = text.replace(" ", "")
        return any(k in t for k in keywords)


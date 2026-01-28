from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..logging_utils import get_logger, safe_mkdir


@dataclass(frozen=True)
class BenefitMatchingOutputs:
    dining_benefit_scores_csv: Path
    weighted_match_scores_csv: Path


class CardBenefitMatcher:
    """카드 혜택을 카테고리별로 집계하고, 20대 가중치 기반 매칭 점수를 계산합니다."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def run(
        self,
        *,
        cards_merged: pd.DataFrame,
        processed_dir: Path,
        pattern_weights: dict[str, float] | None = None,
    ) -> BenefitMatchingOutputs:
        safe_mkdir(processed_dir)

        dining_scores = self._compute_dining_scores(cards_merged)
        dining_path = processed_dir / "dining_benefit_scores.csv"
        dining_scores.to_csv(dining_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", dining_path)

        weights = pattern_weights or {
            "외식": 0.4,
            "카페": 0.2,
            "디지털콘텐츠": 0.15,
            "생활편의": 0.15,
            "교통": 0.1,
        }
        weighted = self._compute_weighted_match(cards_merged, weights)
        weighted_path = processed_dir / "weighted_match_scores.csv"
        weighted.to_csv(weighted_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", weighted_path)

        return BenefitMatchingOutputs(
            dining_benefit_scores_csv=dining_path,
            weighted_match_scores_csv=weighted_path,
        )

    def _compute_dining_scores(self, cards_merged: pd.DataFrame) -> pd.DataFrame:
        df = cards_merged.copy()
        if "benefit_category" not in df.columns:
            raise ValueError("cards_merged에 benefit_category 컬럼이 필요합니다.")

        df["benefit_category_norm"] = df["benefit_category"].astype(str).apply(self._normalize_category)
        df["discount_rate"] = pd.to_numeric(df.get("discount_rate"), errors="coerce")
        dining_mask = df["benefit_category_norm"].isin(["외식", "카페"])
        dining = df.loc[dining_mask].copy()

        # 카드별: (평균 할인율) * (혜택 개수) 를 단순 점수로 사용
        grouped = dining.groupby(["card_id", "card_name", "issuer"], dropna=False).agg(
            dining_benefit_count=("benefit_category_norm", "size"),
            dining_discount_rate_mean=("discount_rate", "mean"),
        )
        grouped["dining_benefit_score"] = (
            grouped["dining_benefit_count"] * grouped["dining_discount_rate_mean"].fillna(0.0)
        )
        out = grouped.reset_index().sort_values("dining_benefit_score", ascending=False)
        return out

    def _compute_weighted_match(self, cards_merged: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
        df = cards_merged.copy()
        df["discount_rate"] = pd.to_numeric(df.get("discount_rate"), errors="coerce").fillna(0.0)
        df["benefit_category_norm"] = df["benefit_category"].astype(str).apply(self._normalize_category)

        # 카테고리별 평균 할인율을 카드 단위로 만들고, weights로 가중합
        pivot = (
            df.pivot_table(
                index=["card_id", "card_name", "issuer"],
                columns="benefit_category_norm",
                values="discount_rate",
                aggfunc="mean",
                fill_value=0.0,
            )
            .reset_index()
        )

        score = 0.0
        for cat, w in weights.items():
            if cat in pivot.columns:
                score = score + pivot[cat] * float(w)
            else:
                score = score + 0.0
        pivot["weighted_match_score"] = score
        return pivot.sort_values("weighted_match_score", ascending=False)

    def _normalize_category(self, category: str) -> str:
        """원본 카테고리를 AGENT.md의 표준 카테고리로 최대한 매핑."""
        c = (category or "").strip()
        mapping = {
            "푸드": "외식",
            "음식점": "외식",
            "카페": "카페",
            "마트/편의점": "생활편의",
            "쇼핑": "생활편의",
            "공과금": "생활편의",
            "통신": "디지털콘텐츠",
            "문화": "디지털콘텐츠",
            "여행/항공": "여행",
        }
        return mapping.get(c, c)


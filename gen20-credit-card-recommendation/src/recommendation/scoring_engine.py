from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..logging_utils import get_logger, safe_mkdir


@dataclass(frozen=True)
class ScoringOutputs:
    top_cards_csv: Path
    scenario_csv: Path


class ScoringEngine:
    """가중치 기반 카드 추천 스코어링 엔진(AGENT.md 초안 반영)."""

    def __init__(self, random_seed: int = 42) -> None:
        self.random_seed = random_seed
        self.logger = get_logger()
        np.random.seed(random_seed)

    def run(
        self,
        *,
        cards_info: pd.DataFrame,
        dining_benefit_scores: pd.DataFrame,
        weighted_match_scores: pd.DataFrame,
        processed_dir: Path,
        top_n: int = 3,
    ) -> ScoringOutputs:
        safe_mkdir(processed_dir)

        scored = self._score(cards_info, dining_benefit_scores, weighted_match_scores)
        top = scored.sort_values("final_score", ascending=False).head(top_n).reset_index(drop=True)
        top_path = processed_dir / "top_cards.csv"
        top.to_csv(top_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", top_path)

        scenario = self._scenario_simulation(scored)
        scenario_path = processed_dir / "scenario_recommendations.csv"
        scenario.to_csv(scenario_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", scenario_path)

        return ScoringOutputs(top_cards_csv=top_path, scenario_csv=scenario_path)

    def _score(
        self,
        cards_info: pd.DataFrame,
        dining_benefit_scores: pd.DataFrame,
        weighted_match_scores: pd.DataFrame,
    ) -> pd.DataFrame:
        # 기본 키
        base_cols = [c for c in ["card_id", "card_name", "issuer", "annual_fee_domestic"] if c in cards_info.columns]
        base = cards_info[base_cols].drop_duplicates(subset=["card_id"]).copy()

        # 외식 혜택 점수(정규화)
        dining = dining_benefit_scores[["card_id", "dining_benefit_score"]].copy()
        base = base.merge(dining, on="card_id", how="left")
        base["dining_benefit_score"] = pd.to_numeric(base["dining_benefit_score"], errors="coerce").fillna(0.0)
        base["dining_score_norm"] = self._minmax(base["dining_benefit_score"])

        # 카테고리 매칭 점수(정규화)
        w = weighted_match_scores[["card_id", "weighted_match_score"]].copy()
        base = base.merge(w, on="card_id", how="left")
        base["weighted_match_score"] = pd.to_numeric(base["weighted_match_score"], errors="coerce").fillna(0.0)
        base["match_score_norm"] = self._minmax(base["weighted_match_score"])

        # 연회비 효율(낮을수록 좋음) → 역정규화
        if "annual_fee_domestic" in base.columns:
            fee_num = pd.to_numeric(base["annual_fee_domestic"], errors="coerce")
            med = float(fee_num.median(skipna=True)) if fee_num.notna().any() else 0.0
            fee = fee_num.fillna(med)
            base["annual_fee_domestic"] = fee
            base["fee_efficiency_norm"] = 1.0 - self._minmax(fee)
        else:
            base["fee_efficiency_norm"] = 0.5

        # 20대 선호도(현재는 데이터 부족 → issuer 빈도 기반 더미) : 추후 유튜브 언급으로 교체 가능
        issuer_pref = base["issuer"].fillna("").astype(str).value_counts(normalize=True).to_dict()
        base["issuer_pref_norm"] = base["issuer"].fillna("").astype(str).map(issuer_pref).fillna(0.0)
        base["issuer_pref_norm"] = self._minmax(base["issuer_pref_norm"])

        # 최종 점수(AGENT.md 가중치)
        base["final_score"] = (
            base["dining_score_norm"] * 0.40
            + base["fee_efficiency_norm"] * 0.25
            + base["issuer_pref_norm"] * 0.20
            + base["match_score_norm"] * 0.15
        )

        # 설명(한줄)
        base["reason"] = base.apply(self._build_reason, axis=1)
        return base

    def _scenario_simulation(self, scored: pd.DataFrame) -> pd.DataFrame:
        """외식비 시나리오별 손익분기점 기반 간단 추천."""

        df = scored.copy()
        df["annual_fee_domestic"] = pd.to_numeric(df.get("annual_fee_domestic"), errors="coerce").fillna(0.0)

        scenarios = [200_000, 300_000, 400_000]  # 월 외식비
        rows: list[dict[str, object]] = []
        for spend in scenarios:
            # 임의로 '외식 평균 할인율'을 dining_score_norm로 근사(0~1) → 5~15%로 매핑
            avg_rate = (df["dining_score_norm"].fillna(0.0) * 0.10) + 0.05
            # 손익분기점(월): 연회비 / (월 할인액)
            monthly_saving = spend * avg_rate
            breakeven_months = np.where(monthly_saving > 0, df["annual_fee_domestic"] / monthly_saving, np.inf)

            tmp = df.copy()
            tmp["scenario_monthly_dining_spend"] = spend
            tmp["assumed_avg_dining_discount_rate"] = avg_rate
            tmp["breakeven_months"] = breakeven_months
            # breakeven이 짧고 final_score가 높은 카드 선호
            tmp["scenario_score"] = (1.0 - self._minmax(tmp["breakeven_months"].replace([np.inf], np.nan).fillna(tmp["breakeven_months"].max()))) * 0.5 + tmp["final_score"] * 0.5
            top3 = tmp.sort_values("scenario_score", ascending=False).head(3)
            for rank, r in enumerate(top3.itertuples(index=False), start=1):
                rows.append(
                    {
                        "scenario_monthly_dining_spend": spend,
                        "rank": rank,
                        "card_id": getattr(r, "card_id"),
                        "card_name": getattr(r, "card_name", ""),
                        "issuer": getattr(r, "issuer", ""),
                        "final_score": float(getattr(r, "final_score")),
                        "breakeven_months": float(getattr(r, "breakeven_months")),
                    }
                )
        return pd.DataFrame(rows)

    def _build_reason(self, row: pd.Series) -> str:
        parts: list[str] = []
        parts.append(f"외식점수 {row.get('dining_score_norm', 0):.2f}")
        parts.append(f"연회비효율 {row.get('fee_efficiency_norm', 0):.2f}")
        parts.append(f"매칭 {row.get('match_score_norm', 0):.2f}")
        return ", ".join(parts)

    def _minmax(self, s: pd.Series) -> pd.Series:
        s = pd.to_numeric(s, errors="coerce").fillna(0.0)
        mn = float(s.min())
        mx = float(s.max())
        if mx - mn < 1e-12:
            return pd.Series([0.0] * len(s), index=s.index)
        return (s - mn) / (mx - mn)


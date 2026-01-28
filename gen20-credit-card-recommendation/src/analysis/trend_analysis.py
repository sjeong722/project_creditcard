from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from ..logging_utils import get_logger, safe_mkdir


@dataclass(frozen=True)
class TrendOutputs:
    correlation_csv: Path


class TrendAnalyzer:
    """네이버 데이터랩 트렌드의 상관관계(피어슨) 및 간단 리포팅."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def run(self, *, naver_trend: pd.DataFrame, reports_dir: Path) -> TrendOutputs:
        safe_mkdir(reports_dir)

        corr = self._pearson_correlation(naver_trend)
        out_path = reports_dir / "trend_correlations.csv"
        corr.to_csv(out_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", out_path)

        return TrendOutputs(correlation_csv=out_path)

    def _pearson_correlation(self, naver_trend: pd.DataFrame) -> pd.DataFrame:
        df = naver_trend.copy()
        required = ["catchtable_index", "culinary_class_wars_index"]
        for c in required:
            if c not in df.columns:
                raise ValueError(f"naver_trend에 {c} 컬럼이 필요합니다.")

        x = pd.to_numeric(df["catchtable_index"], errors="coerce")
        y = pd.to_numeric(df["culinary_class_wars_index"], errors="coerce")
        mask = x.notna() & y.notna()
        x = x[mask]
        y = y[mask]

        if len(x) < 3:
            r, p = np.nan, np.nan
        else:
            r, p = stats.pearsonr(x, y)

        self.logger.info("피어슨 상관계수: r=%.4f, p-value=%.4f", r, p)
        return pd.DataFrame(
            [
                {
                    "metric": "pearson",
                    "x": "catchtable_index",
                    "y": "culinary_class_wars_index",
                    "r": r,
                    "p_value": p,
                    "n": int(len(x)),
                }
            ]
        )


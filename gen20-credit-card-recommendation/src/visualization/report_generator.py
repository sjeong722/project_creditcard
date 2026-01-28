from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..logging_utils import get_logger, maybe_write_text, safe_mkdir


@dataclass(frozen=True)
class ReportOutputs:
    report_md: Path


class ReportGenerator:
    """산출물(테이블/요약)을 모아 단일 마크다운 리포트 생성."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def run(
        self,
        *,
        reports_dir: Path,
        top_cards: pd.DataFrame | None = None,
        scenario: pd.DataFrame | None = None,
        trend_correlations: pd.DataFrame | None = None,
        tfidf_keywords: pd.DataFrame | None = None,
    ) -> ReportOutputs:
        safe_mkdir(reports_dir)

        md = self._render(
            top_cards=top_cards,
            scenario=scenario,
            trend_correlations=trend_correlations,
            tfidf_keywords=tfidf_keywords,
        )
        out_path = reports_dir / "final_report.md"
        maybe_write_text(out_path, md)
        self.logger.info("저장 완료: %s", out_path)
        return ReportOutputs(report_md=out_path)

    def _render(
        self,
        *,
        top_cards: pd.DataFrame | None,
        scenario: pd.DataFrame | None,
        trend_correlations: pd.DataFrame | None,
        tfidf_keywords: pd.DataFrame | None,
    ) -> str:
        def _md_table(df: pd.DataFrame | None, head: int = 10) -> str:
            if df is None or df.empty:
                return "(데이터 없음)\n"
            return self._df_to_markdown(df.head(head))

        return f"""# 20대 맞춤형 신용카드 추천 리포트(자동 생성)

## 카드 TOP3 추천
{_md_table(top_cards, head=3)}

## 외식비 시나리오(월 20/30/40만원) 추천 TOP3
{_md_table(scenario, head=20)}

## 흑백요리사 × 캐치테이블 트렌드 상관관계(네이버 데이터랩)
{_md_table(trend_correlations, head=5)}

## 유튜브 콘텐츠 TF-IDF 상위 키워드
{_md_table(tfidf_keywords, head=30)}
"""

    def _df_to_markdown(self, df: pd.DataFrame) -> str:
        """tabulate 없이 동작하는 간단 마크다운 테이블 렌더러."""
        if df.empty:
            return "(데이터 없음)\n"
        cols = [str(c) for c in df.columns]
        lines = [
            "| " + " | ".join(cols) + " |",
            "| " + " | ".join(["---"] * len(cols)) + " |",
        ]
        for row in df.itertuples(index=False):
            lines.append("| " + " | ".join(str(v) for v in row) + " |")
        return "\n".join(lines)


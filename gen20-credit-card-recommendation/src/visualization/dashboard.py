from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..logging_utils import get_logger, maybe_write_text, safe_mkdir


@dataclass(frozen=True)
class DashboardOutputs:
    dashboard_html: Path


class DashboardBuilder:
    """간단한 정적 HTML 대시보드(표 위주)."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def run(
        self,
        *,
        reports_dir: Path,
        top_cards: pd.DataFrame | None = None,
        scenario: pd.DataFrame | None = None,
    ) -> DashboardOutputs:
        safe_mkdir(reports_dir)
        html = self._render(top_cards=top_cards, scenario=scenario)
        out_path = reports_dir / "dashboard.html"
        maybe_write_text(out_path, html)
        self.logger.info("저장 완료: %s", out_path)
        return DashboardOutputs(dashboard_html=out_path)

    def _render(self, *, top_cards: pd.DataFrame | None, scenario: pd.DataFrame | None) -> str:
        def _html_table(df: pd.DataFrame | None, head: int = 10) -> str:
            if df is None or df.empty:
                return "<p>(데이터 없음)</p>"
            return df.head(head).to_html(index=False, escape=False)

        return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gen20 Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; margin: 24px; }}
    h1, h2 {{ margin: 0 0 12px 0; }}
    .card {{ padding: 16px; border: 1px solid #eee; border-radius: 12px; margin: 16px 0; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #eee; padding: 8px; text-align: left; font-size: 14px; }}
    th {{ background: #fafafa; }}
  </style>
</head>
<body>
  <h1>20대 신용카드 추천 대시보드(자동 생성)</h1>
  <div class="card">
    <h2>TOP3 추천</h2>
    {_html_table(top_cards, head=3)}
  </div>
  <div class="card">
    <h2>외식비 시나리오 추천</h2>
    {_html_table(scenario, head=30)}
  </div>
</body>
</html>
"""


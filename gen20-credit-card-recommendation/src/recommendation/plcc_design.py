from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..logging_utils import get_logger, maybe_write_text, safe_mkdir


@dataclass(frozen=True)
class PLCCOutputs:
    proposal_md: Path


class PLCCDesigner:
    """캐치테이블 PLCC 제안서(마크다운) 자동 생성기(프로토타입)."""

    def __init__(self) -> None:
        self.logger = get_logger()

    def run(
        self,
        *,
        reports_dir: Path,
        trend_correlations: pd.DataFrame | None = None,
        top_cards: pd.DataFrame | None = None,
    ) -> PLCCOutputs:
        safe_mkdir(reports_dir)

        md = self._render_md(trend_correlations=trend_correlations, top_cards=top_cards)
        out_path = reports_dir / "plcc_proposal.md"
        maybe_write_text(out_path, md)
        self.logger.info("저장 완료: %s", out_path)
        return PLCCOutputs(proposal_md=out_path)

    def _render_md(
        self, *, trend_correlations: pd.DataFrame | None, top_cards: pd.DataFrame | None
    ) -> str:
        r_line = ""
        if trend_correlations is not None and not trend_correlations.empty:
            row = trend_correlations.iloc[0].to_dict()
            r_line = f"- 피어슨 상관: r={row.get('r'):.4f}, p-value={row.get('p_value'):.4f} (n={row.get('n')})\n"

        top_table = ""
        if top_cards is not None and not top_cards.empty:
            cols = [
                c
                for c in ["card_name", "issuer", "annual_fee_domestic", "final_score", "reason"]
                if c in top_cards.columns
            ]
            top_view = top_cards[cols].head(3).copy()
            top_table = self._df_to_markdown(top_view)

        return f"""# 캐치테이블 PLCC 제안서(프로토타입)

## 핵심 가치 제안(Value Proposition)
- **"흑백요리사 맛집, 기념일에 예약 걱정 없이"**
- 문제: 예약 실패/웨이팅 스트레스
- 해결: PLCC 보유자 **우선 예약/좌석 할당/추가 할인**

## 데이터 기반 근거(자동 생성)
### 흑백요리사 × 캐치테이블 상관관계(네이버 트렌드)
{r_line if r_line else "- (트렌드 데이터가 비어 있어 상관관계를 계산하지 못했습니다)\n"}

### 20대 추천 카드 TOP3(참고)
{top_table if top_table else "(TOP3 추천 결과가 아직 없습니다)\n"}

## 혜택 구조(초안)
| 혜택 항목 | 상세 내용 | 비고 |
|---|---|---|
| 연회비 | 국내전용 1만원, 해외겸용 1.5만원 | 20대 저항 최소화 |
| 전월 실적 | 30만원 이상 | 외식 2~3회면 달성 가능 |
| 핵심 혜택 1 | 흑백요리사 맛집 전용 좌석 예약 보장(월 1회) | 레스토랑 협의 |
| 핵심 혜택 2 | 캐치테이블 제휴 레스토랑 10% 할인(월 5만원 한도) | 비용 분담 |
| 핵심 혜택 3 | 기념일 7일 전 우선 예약 권한(분기 1회) |  |
| 추가 혜택 | 카페/배달앱/OTT 할인 |  |

## 협의 필요 사항
- 좌석 할당 비율(20% vs 30%)
- 할인 비용 분담(카드사 vs 캐치테이블 vs 가맹점)
- 최소 가맹점 수/런칭 로드맵
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


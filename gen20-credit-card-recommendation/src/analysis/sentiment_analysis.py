from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..logging_utils import get_logger, safe_mkdir


@dataclass(frozen=True)
class SentimentOutputs:
    sentiment_csv: Path


class SentimentAnalyzer:
    """댓글 감성 분석(경량 규칙 기반).

    -1~1 범위의 sentiment_score를 생성합니다.
    (향후 transformers/KoBERT로 교체 가능하도록 인터페이스만 고정)
    """

    def __init__(self) -> None:
        self.logger = get_logger()

        # 매우 단순한 한국어 키워드 기반 룰(프로토타입)
        self.pos_words = [
            "좋다",
            "만족",
            "추천",
            "최고",
            "행복",
            "가성비",
            "꿀",
            "혜자",
            "할인",
            "적립",
            "성공",
        ]
        self.neg_words = [
            "별로",
            "후회",
            "최악",
            "비싸",
            "실패",
            "짜증",
            "불만",
            "손해",
            "어렵",
            "막힘",
        ]

    def run(self, *, youtube_comments: pd.DataFrame, processed_dir: Path) -> SentimentOutputs:
        safe_mkdir(processed_dir)
        df = youtube_comments.copy()

        if "comment_text" not in df.columns:
            raise ValueError("youtube_comments에 comment_text 컬럼이 필요합니다.")

        df["sentiment_score"] = df["comment_text"].fillna("").astype(str).apply(self._score_text)

        out_cols = [c for c in ["video_publish_date", "video_title", "comment_text", "sentiment_score", "dining_mention"] if c in df.columns]
        out = df[out_cols]

        out_path = processed_dir / "sentiment_analysis.csv"
        out.to_csv(out_path, index=False, encoding="utf-8-sig")
        self.logger.info("저장 완료: %s", out_path)

        # 간단 통계 로그
        s = pd.to_numeric(out["sentiment_score"], errors="coerce")
        self.logger.info("sentiment_score mean=%.4f, std=%.4f", float(s.mean()), float(s.std()))

        return SentimentOutputs(sentiment_csv=out_path)

    def _score_text(self, text: str) -> float:
        t = text.replace(" ", "")
        pos = sum(1 for w in self.pos_words if w in t)
        neg = sum(1 for w in self.neg_words if w in t)
        raw = pos - neg

        # 0이면 중립
        if raw == 0:
            return 0.0

        # 스케일링: 키워드 개수에 따라 -1~1로 압축
        score = raw / max(3, (pos + neg))
        return float(np.clip(score, -1.0, 1.0))


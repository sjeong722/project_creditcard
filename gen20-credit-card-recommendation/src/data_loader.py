from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import re

from .logging_utils import get_logger, log_df_info


@dataclass(frozen=True)
class LoadedData:
    """파이프라인에서 사용하는 표준 DataFrame 묶음."""

    cards_info: pd.DataFrame
    cards_benefits: pd.DataFrame
    youtube_consumption: pd.DataFrame
    youtube_comments: pd.DataFrame
    youtube_dining_search: pd.DataFrame
    naver_trend: pd.DataFrame


class DataLoader:
    """CSV 로딩 + 기본 스키마 정리."""

    def __init__(self, encoding: str = "utf-8") -> None:
        self.encoding = encoding
        self.logger = get_logger()

    def _read_csv(self, path: Path, encoding: Optional[str] = None) -> pd.DataFrame:
        try:
            df = pd.read_csv(path, encoding=encoding or self.encoding)
            log_df_info(self.logger, path.name, df.shape[0], df.shape[1])
            return df
        except FileNotFoundError:
            self.logger.exception("파일을 찾을 수 없습니다: %s", path)
            raise
        except Exception:
            self.logger.exception("CSV 로딩 실패: %s", path)
            raise

    def load_all(
        self,
        cards_info_csv: Path,
        cards_benefits_csv: Path,
        youtube_consumption_csv: Path,
        youtube_comments_csv: Path,
        youtube_dining_search_csv: Path,
        naver_trend_csv: Path,
    ) -> LoadedData:
        """필수 CSV 전부 로딩."""

        cards_info = self._read_csv(cards_info_csv)
        cards_benefits = self._read_csv(cards_benefits_csv)
        yt_cons = self._read_csv(youtube_consumption_csv)
        yt_comments = self._read_csv(youtube_comments_csv)
        yt_dining = self._read_csv(youtube_dining_search_csv)
        naver_trend = self._read_csv(naver_trend_csv)

        return LoadedData(
            cards_info=self._standardize_cards_info(cards_info),
            cards_benefits=self._standardize_cards_benefits(cards_benefits),
            youtube_consumption=self._standardize_youtube_consumption(yt_cons),
            youtube_comments=self._standardize_youtube_comments(yt_comments),
            youtube_dining_search=self._standardize_youtube_dining_search(yt_dining),
            naver_trend=self._standardize_naver_trend(naver_trend),
        )

    def _standardize_cards_info(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "company": "issuer",
            "image_url": "card_image_url",
            "url": "detail_page_url",
        }
        out = df.rename(columns=rename_map).copy()
        # annual_fee가 단일 컬럼이면 국내/해외로 복제(AGENT.md 스키마 호환)
        if "annual_fee" in out.columns and "annual_fee_domestic" not in out.columns:
            out["annual_fee_raw"] = out["annual_fee"]
            parsed = out["annual_fee"].apply(self._parse_annual_fee)
            out["annual_fee_domestic"] = parsed.apply(lambda x: x[0])
            out["annual_fee_overseas"] = parsed.apply(lambda x: x[1])
        if "performance" in out.columns and "min_usage_requirement" not in out.columns:
            out["min_usage_requirement"] = out["performance"]
        return out

    def _parse_annual_fee(self, v: object) -> tuple[float, float]:
        """연회비 문자열을 국내/해외 숫자(원)로 파싱.

        예)
        - '국내전용20,000원해외겸용20,000원'
        - '해외겸용15,000원'
        - '국내전용15,000원해외겸용15,000원 |20,000원'
        """

        if v is None or (isinstance(v, float) and pd.isna(v)):
            return (float("nan"), float("nan"))
        if isinstance(v, (int, float)) and not pd.isna(v):
            return (float(v), float(v))

        s = str(v).replace(" ", "")

        dom = re.search(r"국내전용([0-9,]+)원", s)
        ov = re.search(r"해외겸용([0-9,]+)원", s)

        def _to_num(m: Optional[re.Match[str]]) -> float:
            if m is None:
                return float("nan")
            return float(m.group(1).replace(",", ""))

        d = _to_num(dom)
        o = _to_num(ov)

        # 둘 다 없으면, 문자열 내 첫 숫자를 사용(단일 표기 케이스)
        if pd.isna(d) and pd.isna(o):
            any_num = re.search(r"([0-9,]+)원", s)
            if any_num:
                n = float(any_num.group(1).replace(",", ""))
                return (n, n)
            return (float("nan"), float("nan"))

        # 한쪽만 있으면 동일 값으로 채움(해외겸용만 있는 경우 등)
        if pd.isna(d) and not pd.isna(o):
            d = o
        if pd.isna(o) and not pd.isna(d):
            o = d
        return (d, o)

    def _standardize_cards_benefits(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "benefit_seq": "benefit_order",
            "category": "benefit_category",
            "benefit_type": "discount_type",
            "rate": "discount_rate",
            "is_selectable": "is_optional",
            "summary": "benefit_summary",
            "detail": "benefit_detail",
        }
        out = df.rename(columns=rename_map).copy()

        # discount_rate: '5%' 같은 문자열을 숫자(퍼센트)로 파싱
        if "discount_rate" in out.columns:
            out["discount_rate_raw"] = out["discount_rate"]
            out["discount_rate"] = out["discount_rate"].apply(self._parse_rate_percent)
            out["discount_amount_won"] = out["discount_rate_raw"].apply(self._parse_amount_won)

        return out

    def _parse_rate_percent(self, v: object) -> float:
        """'10%' -> 10.0, 숫자면 그대로, 그 외 NaN."""
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return float("nan")
        if isinstance(v, (int, float)) and not pd.isna(v):
            return float(v)
        s = str(v).strip()
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
        if not m:
            return float("nan")
        return float(m.group(1))

    def _parse_amount_won(self, v: object) -> float:
        """'1,000원' -> 1000.0, 그 외 NaN."""
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return float("nan")
        s = str(v).strip().replace(" ", "")
        m = re.search(r"([0-9,]+)원", s)
        if not m:
            return float("nan")
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return float("nan")

    def _standardize_youtube_consumption(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "게시날짜": "publish_date",
            "제목": "video_title",
            "조회수": "view_count",
            "좋아요수": "like_count",
            "댓글수": "comment_count",
            "연관키워드": "related_keywords",
            "영상내용요약": "content_summary",
        }
        out = df.rename(columns=rename_map).copy()
        if "publish_date" in out.columns:
            out["publish_date"] = pd.to_datetime(out["publish_date"], errors="coerce")
        return out

    def _standardize_youtube_comments(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "게시날짜": "video_publish_date",
            "제목": "video_title",
            "댓글내용": "comment_text",
        }
        out = df.rename(columns=rename_map).copy()
        if "video_publish_date" in out.columns:
            out["video_publish_date"] = pd.to_datetime(out["video_publish_date"], errors="coerce")
        return out

    def _standardize_youtube_dining_search(self, df: pd.DataFrame) -> pd.DataFrame:
        # 파일 구조가 명확치 않으므로, 최소한 날짜 파싱만 시도
        out = df.copy()
        for col in ("Date", "date", "publish_date", "month"):
            if col in out.columns:
                out[col] = pd.to_datetime(out[col], errors="coerce")
        return out

    def _standardize_naver_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {
            "Date": "trend_month",
            "미슐랭": "michelin_index",
            "블루리본": "blueribbon_index",
            "캐치테이블": "catchtable_index",
            "흑백요리사": "culinary_class_wars_index",
        }
        out = df.rename(columns=rename_map).copy()
        if "trend_month" in out.columns:
            out["trend_month"] = pd.to_datetime(out["trend_month"], errors="coerce")
        return out


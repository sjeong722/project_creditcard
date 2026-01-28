from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import Config
from src.data_loader import DataLoader
from src.logging_utils import setup_logging
from src.preprocessing import Preprocessor
from src.analysis.consumption_pattern import ConsumptionPatternAnalyzer
from src.analysis.sentiment_analysis import SentimentAnalyzer
from src.analysis.trend_analysis import TrendAnalyzer
from src.analysis.card_benefit_matching import CardBenefitMatcher
from src.recommendation.scoring_engine import ScoringEngine
from src.recommendation.plcc_design import PLCCDesigner
from src.visualization.report_generator import ReportGenerator
from src.visualization.dashboard import DashboardBuilder


def main() -> None:
    project_root = Path(__file__).resolve().parent
    # workspace_root: 이 레포의 상위 폴더(원본 CSV들이 있는 위치)
    workspace_root = project_root.parent

    cfg = Config.load(project_root=project_root, workspace_root=workspace_root, random_seed=42)
    logger = setup_logging(cfg.paths.outputs_dir / "logs")
    logger.info("프로젝트 루트: %s", cfg.paths.project_root)
    logger.info("워크스페이스 루트: %s", workspace_root)

    # 디렉토리 보장
    cfg.paths.raw_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.processed_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.figures_dir.mkdir(parents=True, exist_ok=True)
    cfg.paths.reports_dir.mkdir(parents=True, exist_ok=True)

    # 1) Load
    loader = DataLoader()
    data = loader.load_all(
        cards_info_csv=cfg.raw_sources.cards_info_csv,
        cards_benefits_csv=cfg.raw_sources.cards_benefits_csv,
        youtube_consumption_csv=cfg.raw_sources.youtube_consumption_csv,
        youtube_comments_csv=cfg.raw_sources.youtube_comments_csv,
        youtube_dining_search_csv=cfg.raw_sources.youtube_dining_search_csv,
        naver_trend_csv=cfg.raw_sources.naver_trend_csv,
    )

    # 2) Preprocess
    pre = Preprocessor(random_seed=cfg.random_seed)
    pre_out = pre.run(
        processed_dir=cfg.paths.processed_dir,
        cards_info=data.cards_info,
        cards_benefits=data.cards_benefits,
        youtube_consumption=data.youtube_consumption,
        youtube_comments=data.youtube_comments,
    )

    # 3) Analysis
    cons = ConsumptionPatternAnalyzer(random_seed=cfg.random_seed)
    cons_out = cons.run(youtube_consumption=data.youtube_consumption, reports_dir=cfg.paths.reports_dir)
    senti = SentimentAnalyzer()
    senti_out = senti.run(youtube_comments=data.youtube_comments, processed_dir=cfg.paths.processed_dir)
    trend = TrendAnalyzer()
    trend_out = trend.run(naver_trend=data.naver_trend, reports_dir=cfg.paths.reports_dir)

    cards_merged = pd.read_csv(pre_out.cards_merged_csv)
    matcher = CardBenefitMatcher()
    match_out = matcher.run(cards_merged=cards_merged, processed_dir=cfg.paths.processed_dir)

    dining_scores = pd.read_csv(match_out.dining_benefit_scores_csv)
    weighted_scores = pd.read_csv(match_out.weighted_match_scores_csv)

    # 4) Recommendation
    engine = ScoringEngine(random_seed=cfg.random_seed)
    score_out = engine.run(
        cards_info=data.cards_info,
        dining_benefit_scores=dining_scores,
        weighted_match_scores=weighted_scores,
        processed_dir=cfg.paths.processed_dir,
        top_n=3,
    )

    top_cards = pd.read_csv(score_out.top_cards_csv)
    scenario = pd.read_csv(score_out.scenario_csv)
    trend_corr = pd.read_csv(trend_out.correlation_csv)
    tfidf_kw = pd.read_csv(cons_out.tfidf_keywords_csv)

    # 5) PLCC + Report
    plcc = PLCCDesigner()
    plcc.run(reports_dir=cfg.paths.reports_dir, trend_correlations=trend_corr, top_cards=top_cards)

    report = ReportGenerator()
    report.run(
        reports_dir=cfg.paths.reports_dir,
        top_cards=top_cards,
        scenario=scenario,
        trend_correlations=trend_corr,
        tfidf_keywords=tfidf_kw,
    )

    dash = DashboardBuilder()
    dash.run(reports_dir=cfg.paths.reports_dir, top_cards=top_cards, scenario=scenario)

    logger.info("파이프라인 완료. outputs/reports 확인하세요.")


if __name__ == "__main__":
    main()


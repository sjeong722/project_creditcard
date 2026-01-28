from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """프로젝트 경로 모음.

    기본값은 레포 내 `gen20-credit-card-recommendation/` 구조를 기준으로 합니다.
    """

    project_root: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    outputs_dir: Path
    figures_dir: Path
    reports_dir: Path

    @staticmethod
    def from_project_root(project_root: Path) -> "ProjectPaths":
        data_dir = project_root / "data"
        outputs_dir = project_root / "outputs"
        return ProjectPaths(
            project_root=project_root,
            data_dir=data_dir,
            raw_dir=data_dir / "raw",
            processed_dir=data_dir / "processed",
            outputs_dir=outputs_dir,
            figures_dir=outputs_dir / "figures",
            reports_dir=outputs_dir / "reports",
        )


@dataclass(frozen=True)
class RawDataSources:
    """원본 데이터 소스 경로.

    이 레포에서는 CSV들이 루트 폴더 하위에 흩어져 있으므로, 기본값을 해당 경로로 지정합니다.
    필요 시 환경변수로 덮어쓸 수 있습니다.
    """

    cards_info_csv: Path
    cards_benefits_csv: Path
    youtube_consumption_csv: Path
    youtube_comments_csv: Path
    youtube_dining_search_csv: Path
    naver_trend_csv: Path

    @staticmethod
    def default(workspace_root: Path) -> "RawDataSources":
        # NOTE: 사용자 레포 구조에 맞춘 기본 경로
        return RawDataSources(
            cards_info_csv=workspace_root / "card" / "cards_info.csv",
            cards_benefits_csv=workspace_root / "card" / "cards_benefits_fixed.csv",
            youtube_consumption_csv=workspace_root / "20대" / "youtube_20_consumption.csv.csv",
            youtube_comments_csv=workspace_root / "20대" / "youtube_comments_700.csv",
            youtube_dining_search_csv=workspace_root / "20대" / "youtube_dining_search_100.csv",
            naver_trend_csv=workspace_root / "20대" / "naverlab_dining_trend_comparison.csv",
        )

    @staticmethod
    def from_env(workspace_root: Path) -> "RawDataSources":
        """환경변수로 원본 CSV 경로를 덮어씁니다(없으면 default 사용)."""

        d = RawDataSources.default(workspace_root)
        return RawDataSources(
            cards_info_csv=Path(os.getenv("GEN20_CARDS_INFO_CSV", str(d.cards_info_csv))),
            cards_benefits_csv=Path(
                os.getenv("GEN20_CARDS_BENEFITS_CSV", str(d.cards_benefits_csv))
            ),
            youtube_consumption_csv=Path(
                os.getenv("GEN20_YT_CONSUMPTION_CSV", str(d.youtube_consumption_csv))
            ),
            youtube_comments_csv=Path(
                os.getenv("GEN20_YT_COMMENTS_CSV", str(d.youtube_comments_csv))
            ),
            youtube_dining_search_csv=Path(
                os.getenv("GEN20_YT_DINING_SEARCH_CSV", str(d.youtube_dining_search_csv))
            ),
            naver_trend_csv=Path(os.getenv("GEN20_NAVER_TREND_CSV", str(d.naver_trend_csv))),
        )


@dataclass(frozen=True)
class Config:
    """파이프라인 실행 설정."""

    random_seed: int
    paths: ProjectPaths
    raw_sources: RawDataSources

    @staticmethod
    def load(project_root: Path, workspace_root: Path, random_seed: int = 42) -> "Config":
        return Config(
            random_seed=random_seed,
            paths=ProjectPaths.from_project_root(project_root),
            raw_sources=RawDataSources.from_env(workspace_root),
        )


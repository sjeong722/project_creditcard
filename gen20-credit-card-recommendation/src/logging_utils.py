from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


def setup_logging(log_dir: Path, name: str = "gen20", level: int = logging.INFO) -> logging.Logger:
    """로깅 설정(콘솔 + 파일).

    Args:
        log_dir: 로그 파일을 저장할 디렉토리
        name: 로거 이름
        level: 로그 레벨

    Returns:
        설정 완료된 Logger
    """

    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 중복 핸들러 방지(노트북/재실행 고려)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


def get_logger(name: str = "gen20") -> logging.Logger:
    """기본 로거를 반환합니다(설정이 안 되어 있으면 root 로거로 동작)."""

    return logging.getLogger(name)


def log_df_info(logger: logging.Logger, df_name: str, n_rows: int, n_cols: int) -> None:
    logger.info("%s shape=%s x %s", df_name, n_rows, n_cols)


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def maybe_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)


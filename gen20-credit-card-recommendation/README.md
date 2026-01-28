# gen20-credit-card-recommendation

20대(특히 외식/맛집 지출 비중이 높은 사용자)를 위한 **데이터 기반 신용카드 추천** 및 **캐치테이블 PLCC 제안서** 자동 생성 프로젝트입니다.

## 빠른 시작

### 1) (선택) 가상환경

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) 의존성 설치

```bash
pip install -r requirements.txt
```

### 3) 파이프라인 실행

```bash
python run_pipeline.py
```

## 산출물 경로

- `outputs/reports/final_report.md`: 최종 요약 리포트(마크다운)
- `outputs/reports/plcc_proposal.md`: 캐치테이블 PLCC 제안서(프로토타입)
- `outputs/reports/dashboard.html`: 간단 대시보드(정적 HTML)
- `data/processed/`: 전처리 및 추천 결과 CSV

## 원본 데이터 경로(현재 레포 기준)

기본값은 이 레포 구조를 가정합니다:

- `../card/cards_info.csv`
- `../card/cards_benefits_fixed.csv`
- `../20대/youtube_20_consumption.csv.csv`
- `../20대/youtube_comments_700.csv`
- `../20대/youtube_dining_search_100.csv`
- `../20대/naverlab_dining_trend_comparison.csv`

필요 시 환경변수로 덮어쓸 수 있습니다:

- `GEN20_CARDS_INFO_CSV`
- `GEN20_CARDS_BENEFITS_CSV`
- `GEN20_YT_CONSUMPTION_CSV`
- `GEN20_YT_COMMENTS_CSV`
- `GEN20_YT_DINING_SEARCH_CSV`
- `GEN20_NAVER_TREND_CSV`


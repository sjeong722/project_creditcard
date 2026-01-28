import pandas as pd
import matplotlib.pyplot as plt

# 한글 폰트 설정 (Mac: AppleGothic)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

# 데이터 로드 (절대 경로 사용)
csv_path = '/Users/t2024-m0246/Documents/GitHub/project_sojeong/card/cards_info.csv'
try:
    cards_df = pd.read_csv(csv_path)
except FileNotFoundError:
    # 혹시 경로가 다를 경우를 대비해 예비 경로 확인 (현재 스크립트 위치 기준 상위 등)
    # 하지만 절대 경로가 가장 안전함.
    print(f"Error: 파일 {csv_path}을 찾을 수 없습니다.")
    exit(1)

# 카드사별 개수 집계
company_counts = cards_df['company'].value_counts()

# 상위 5개 + 기타로 재분류
# 카드사가 5개 미만일 수도 있으므로 체크
n_largest = 5
if len(company_counts) <= n_largest:
    plot_data = company_counts
else:
    top5 = company_counts.nlargest(n_largest)
    others_sum = company_counts[~company_counts.index.isin(top5.index)].sum()
    if others_sum > 0:
        plot_data = pd.concat([top5, pd.Series({'기타': others_sum})])
    else:
        plot_data = top5

# 색상 설정
colors = ['#4A90E2', '#50C878', '#F5A623', '#E94B3C', '#9013FE', '#8E8E93']
if len(plot_data) > len(colors):
    # 색상이 모자라면 반복 사용
    colors = colors * (int(len(plot_data)/len(colors)) + 1)
colors = colors[:len(plot_data)]

# 도넛차트 그리기
fig, ax = plt.subplots(figsize=(10, 8))

# wedgeprops의 width를 0.7로 설정하여 도넛 두께를 늘리고(구멍을 줄임)
wedges, texts, autotexts = ax.pie(
    plot_data.values,
    labels=plot_data.index,
    autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100.*plot_data.sum())}개)',
    startangle=90,
    colors=colors,
    wedgeprops={'width': 0.7, 'edgecolor': 'white', 'linewidth': 2},
    textprops={'fontsize': 11, 'weight': 'bold'}
)

# 중앙 텍스트
ax.text(0, 0, f'인기 TOP\n{plot_data.sum()}개', 
        ha='center', va='center', 
        fontsize=16, weight='bold', color='#333333')

# 제목
plt.title('인기 순위 30개 카드의 카드사별 구성 비율', 
          fontsize=15, weight='bold', pad=20)

plt.tight_layout()
output_file = 'card_issuer_donut.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"Saved donut chart to {output_file}")

# 결과 출력
print("카드사별 구성:")
print(plot_data)
print(f"\n전체: {plot_data.sum()}개")
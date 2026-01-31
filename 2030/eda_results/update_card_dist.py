
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def main():
    # 데이터 로드
    # 프로젝트 루트 기준 경로 설정
    base_path = '/Users/t2024-m0246/Documents/GitHub/project_sojeong'
    csv_path = os.path.join(base_path, 'card/cards_info.csv')
    output_dir = os.path.join(base_path, '2030/eda_results')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"Error: {csv_path} not found.")
        return

    # 카드사별 개수 집계 및 정렬
    company_counts = df['company'].value_counts()
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x=company_counts.index, y=company_counts.values, palette='viridis')
    
    # 레이블 및 타이틀 한글화
    plt.title('상위 30개 카드사별 분포', fontsize=15, weight='bold')
    plt.xlabel('카드사', fontsize=12)
    plt.ylabel('카드 개수 (개)', fontsize=12)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'card_top30_dist.png')
    plt.savefig(output_file, dpi=300)
    print(f"Saved plot to {output_file}")

if __name__ == "__main__":
    main()

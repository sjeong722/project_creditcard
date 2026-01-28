
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import re

# 한글 폰트 설정 (Mac: AppleGothic)
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def clean_amount(amt_str):
    if pd.isna(amt_str):
        return 0
    # Remove commas and quotes
    clean_str = str(amt_str).replace(',', '').replace('"', '')
    try:
        return int(clean_str)
    except ValueError:
        return 0

def main():
    # 데이터 로드 (Header는 6번째 줄, index 5)
    file_path = '/Users/t2024-m0246/Documents/GitHub/project_sojeong/30대윤모양/카드이용내역__2025.csv'
    
    # 30대 폴더 확인
    output_dir = '/Users/t2024-m0246/Documents/GitHub/project_sojeong/30대윤모양/eda_images'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # skiprows=5 because header is on line 6 (0-indexed 5)
        df = pd.read_csv(file_path, skiprows=5)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # 컬럼 정리
    # '이용금액', '이용일자', '업종', '취소여부' 확인
    if '이용금액' not in df.columns or '이용일자' not in df.columns:
        print("Required columns not found. Columns are:", df.columns)
        return

    # 데이터 전처리
    df['이용금액_clean'] = df['이용금액'].apply(clean_amount)
    
    # 취소된 거래 제외 (취소여부 == 'Y' 인 경우 제외하거나, 마이너스 금액 처리)
    # 데이터를 보면 취소 매출도 따로 잡히는 것 같음 (취소금액 컬럼 등)
    # 하지만 간단히 '취소여부'가 'N'인 것만 보거나, 
    # 혹은 취소 전표가 마이너스 금액으로 들어오는지 확인 필요.
    # 본문 예시: line 55 취소여부 Y, 취소금액 "-7,960".
    # 따라서 취소여부 Y인 행은 통계에서 제외하는 것이 깔끔할 수 있음 (이중 계산 방지)
    # 다만 부분 취소 등 복잡한 케이스가 있을 수 있으나, 여기선 단순화하여 'N'만 분석
    
    df_valid = df[df['취소여부'] != 'Y'].copy()

    # 날짜 형식 변환
    df_valid['이용일자'] = pd.to_datetime(df_valid['이용일자'], errors='coerce')
    df_valid['Month'] = df_valid['이용일자'].dt.month
    
    # 1. 월별 이용 금액 추이
    monthly_sum = df_valid.groupby('Month')['이용금액_clean'].sum()
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x=monthly_sum.index, y=monthly_sum.values, palette='viridis')
    plt.title('2025년 월별 카드 이용 금액')
    plt.xlabel('월')
    plt.ylabel('이용 금액 (원)')
    plt.ticklabel_format(style='plain', axis='y') # 과학적 표기법 방지
    plt.tight_layout()
    plt.savefig(f'{output_dir}/monthly_usage_2025.png')
    plt.close()

    # 2. 업종별 이용 비중 (Top 10)
    category_sum = df_valid.groupby('업종')['이용금액_clean'].sum().sort_values(ascending=False)
    top_categories = category_sum.head(10)
    
    plt.figure(figsize=(12, 8))
    sns.barplot(y=top_categories.index, x=top_categories.values, palette='rocket')
    plt.title('업종별 이용 금액 Top 10')
    plt.xlabel('이용 금액 (원)')
    plt.ylabel('업종')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/category_usage_top10.png')
    plt.close()

    # 3. 도넛 차트 (업종별 비율)
    plt.figure(figsize=(10, 10))
    # Top 5 + Others
    top5_cat = category_sum.head(5)
    others_cat_sum = category_sum.iloc[5:].sum()
    if others_cat_sum > 0:
        top5_cat['기타'] = others_cat_sum
    
    plt.pie(top5_cat, labels=top5_cat.index, autopct='%1.1f%%', startangle=140, 
            wedgeprops={'width': 0.6, 'edgecolor': 'w'})
    plt.title('상위 5개 업종별 소비 비율')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/category_doughnut.png')
    plt.close()

    # 4. 가맹점별 이용 빈도 Top 15
    top_stores = df_valid['이용가맹점'].value_counts().head(15)
    
    # 지역명 마스킹 함수
    def anonymize_store_name(name):
        # 주요 지역명 마스킹 처리
        name = str(name)
        if '고척' in name:
            name = name.replace('고척', 'ㅇㅇ')
        if '신도림' in name:
            name = name.replace('신도림', 'ㅇㅇㅇ')
        if '경기' in name: # 경기마트 등
            name = name.replace('경기', 'ㅇㅇ')
        if '디큐브시티' in name:
            name = name.replace('디큐브시티', 'ㅇㅇㅇㅇㅇ')
        return name

    # 인덱스(가맹점명)에 마스킹 적용
    top_stores.index = top_stores.index.map(anonymize_store_name)

    plt.figure(figsize=(12, 6))
    sns.barplot(x=top_stores.values, y=top_stores.index, palette='cubehelix')
    plt.title('가맹점별 이용 건수 Top 15')
    plt.xlabel('건수')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/store_frequency_top15.png')
    plt.close()

    print(f"EDA Completed. Images saved to {output_dir}")

if __name__ == "__main__":
    main()

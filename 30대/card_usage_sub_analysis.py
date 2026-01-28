
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def clean_amount(amt_str):
    if pd.isna(amt_str):
        return 0
    clean_str = str(amt_str).replace(',', '').replace('"', '')
    try:
        return int(clean_str)
    except ValueError:
        return 0

def main():
    file_path = '/Users/t2024-m0246/Documents/GitHub/project_sojeong/30대/카드이용내역__2025.csv'
    output_dir = '/Users/t2024-m0246/Documents/GitHub/project_sojeong/30대/eda_images'
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        df = pd.read_csv(file_path, skiprows=5)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    df['이용금액_clean'] = df['이용금액'].apply(clean_amount)
    df_valid = df[df['취소여부'] != 'Y'].copy()

    # 1. 'PG(온라인)' 세부 분석 (가맹점별)
    df_pg = df_valid[df_valid['업종'] == 'PG(온라인)']
    pg_vendor_sum = df_pg.groupby('이용가맹점')['이용금액_clean'].sum().sort_values(ascending=False)
    
    # 상위 10개 PG 가맹점 시각화
    top_pg_vendors = pg_vendor_sum.head(10)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_pg_vendors.values, y=top_pg_vendors.index, palette='Blues_r')
    plt.title("'PG(온라인)' 업종 내 상위 이용 가맹점 (Top 10)")
    plt.xlabel('이용 금액 (원)')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/pg_online_details.png')
    plt.close()
    
    print("Saved PG(Online) analysis to pg_online_details.png")

    # 2. '기타' (Top 5 제외한 업종들) 세부 분석
    # 전체 업종 순위
    category_sum = df_valid.groupby('업종')['이용금액_clean'].sum().sort_values(ascending=False)
    
    # 앞서 도넛 차트에서 Top 5를 제외한 나머지를 '기타'로 묶었으므로,
    # 여기서는 6위부터의 업종들을 상세 분석
    others_categories = category_sum.iloc[5:]
    top_others = others_categories.head(15) # 그 중 상위 15개만
    
    plt.figure(figsize=(10, 8))
    sns.barplot(x=top_others.values, y=top_others.index, palette='Greys_r')
    plt.title("'기타' 항목(Top 5 제외 업종) 상세 구성 (Top 15)")
    plt.xlabel('이용 금액 (원)')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/others_category_details.png')
    plt.close()

    print("Saved Others analysis to others_category_details.png")

if __name__ == "__main__":
    main()

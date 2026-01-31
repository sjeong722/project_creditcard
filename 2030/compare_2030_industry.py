
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
import numpy as np

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def load_env_key():
    load_dotenv()
    key = os.getenv("Public_shinhan_API")
    return key.strip() if key else None

def fetch_citydata(api_key, place):
    base_url = f"http://openapi.seoul.go.kr:8088/{api_key}/json/citydata/1/5/{place}/"
    try:
        response = requests.get(base_url)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def main():
    api_key = load_env_key()
    if not api_key:
        print("Error: .env key missing")
        return

    places = [
        "강남 MICE 관광특구", "홍대 관광특구", "명동 관광특구", "성수카페거리", 
        "가로수길", "이태원 관광특구", "잠실 관광특구", "종로·청계 관광특구", 
        "여의도", "북촌한옥마을", "동대문 관광특구"
    ]
    
    data_points = []
    
    print("Fetching data for comparison...")
    
    for place in places:
        data = fetch_citydata(api_key, place)
        if data and "CITYDATA" in data:
            root = data["CITYDATA"]
            cmrcl_stts = root.get("LIVE_CMRCL_STTS", [])
            
            # Extract list items
            stat = None
            if isinstance(cmrcl_stts, list) and len(cmrcl_stts) > 0:
                stat = cmrcl_stts[0]
            elif isinstance(cmrcl_stts, dict):
                stat = cmrcl_stts
                
            if stat:
                rate_20s = float(stat.get('CMRCL_20_RATE', 0))
                rate_30s = float(stat.get('CMRCL_30_RATE', 0))
                
                rsb_list = stat.get('CMRCL_RSB', [])
                if rsb_list:
                    for item in rsb_list:
                        cat_mid = item.get('RSB_MID_CTGR', 'Unknown')
                        # cat_lrg = item.get('RSB_LRG_CTGR', 'Unknown')
                        
                        amin = float(item.get('RSB_SH_PAYMENT_AMT_MIN', 0) or 0)
                        amax = float(item.get('RSB_SH_PAYMENT_AMT_MAX', 0) or 0)
                        avg_amt = (amin + amax) / 2
                        
                        if avg_amt > 0:
                            # 20대/30대 각각 추정
                            est_20s = avg_amt * (rate_20s / 100)
                            est_30s = avg_amt * (rate_30s / 100)
                            
                            data_points.append({
                                'category': cat_mid,
                                '20대': est_20s,
                                '30대': est_30s
                            })

    if not data_points:
        print("No data collected.")
        return
        
    df = pd.DataFrame(data_points)
    
    # Group by category and sum
    df_grouped = df.groupby('category')[['20대', '30대']].sum()
    
    # Sort by Total (20s + 30s) to find Top 15 common categories
    df_grouped['Total'] = df_grouped['20대'] + df_grouped['30대']
    df_top = df_grouped.sort_values(by='Total', ascending=False).head(15)
    
    # Melt for plotting
    df_plot = df_top[['20대', '30대']].reset_index().melt(id_vars='category', var_name='Age Group', value_name='Estimated Sales')
    
    # Plotting
    output_dir = '2030/eda_images'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    plt.figure(figsize=(12, 8))
    sns.barplot(data=df_plot, y='category', x='Estimated Sales', hue='Age Group', palette={'20대': 'skyblue', '30대': 'orange'})
    plt.title('20대 vs 30대 업종별 추정 매출액 비교 (Top 15)')
    plt.xlabel('추정 매출액 (원)')
    plt.ylabel('업종')
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/comparison_2030_industry.png')
    plt.close()
    
    print(f"Comparison chart saved to {output_dir}/comparison_2030_industry.png")
    
    # 추가: 비율 차이 분석 도표
    # 30대 비중이 특히 높은 업종 vs 20대 비중이 상대적으로 높은 업종 찾기
    df_grouped['Ratio_30_to_20'] = df_grouped['30대'] / df_grouped['20대'].replace(0, 1)
    
    # 30대 선호도 순 (20대 대비)
    df_preference = df_grouped[df_grouped['Total'] > 0].sort_values(by='Ratio_30_to_20', ascending=False)
    
    print("\n[Analysis] 20대 대비 30대 매출 비율이 높은 상위 5개 업종:")
    print(df_preference[['20대', '30대', 'Ratio_30_to_20']].head(5))

if __name__ == "__main__":
    main()

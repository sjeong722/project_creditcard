
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
    # Try multiple keys if needed, but here use the same one
    key = os.getenv("Public_shinhan_API")
    return key.strip() if key else None

def fetch_shinhan_data(api_key, service_name, start=1, end=5, extra_arg=""):
    """
    서울 열린데이터 광장 API 호출 (20대 분석과 동일한 로직)
    """
    base_url = f"http://openapi.seoul.go.kr:8088/{api_key}/json/{service_name}/{start}/{end}/"
    if extra_arg:
        base_url += f"{extra_arg}/"
        
    try:
        response = requests.get(base_url)
        if response.status_code != 200:
             print(f"Server returned status {response.status_code}")
             return None
             
        data = response.json()
        if "RESULT" in data and "CODE" in data["RESULT"]:
             code = data["RESULT"]["CODE"]
             if code != "INFO-000":
                  if code.startswith("ERROR"):
                       return None
        return data
    except Exception as e:
        print(f"API Request Failed for {service_name} ({extra_arg}): {e}")
        return None

def analyze_commercial_data(place_df, cat_df, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. 지역별 30대 매출 비중
    plt.figure(figsize=(12, 6))
    if not place_df.empty:
        place_df['sales_30s_rate'] = pd.to_numeric(place_df['sales_30s_rate'], errors='coerce')
        sns.barplot(data=place_df, x='place_name', y='sales_30s_rate', palette='viridis')
    plt.title('주요 핫플레이스 30대 신한카드 매출 비중 (%)')
    plt.xlabel('장소')
    plt.ylabel('30대 매출 비중 (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/place_30s_sales_rate.png')
    plt.close()
    
    # 2. 업종별 30대 추정 카드 매출 (가로 막대 그래프)
    if not cat_df.empty:
        # 30대 추정 매출액 합계 (weighted_amount 사용)
        cat_sum = cat_df.groupby('category')['weighted_amount'].sum().sort_values(ascending=True)
        
        plt.figure(figsize=(10, 8))
        cat_sum_top = cat_sum.tail(15)
        
        bars = plt.barh(cat_sum_top.index, cat_sum_top.values, color=sns.color_palette('rocket', len(cat_sum_top)))
        
        plt.title('주요 핫플레이스 30대 업종별 추정 매출액 (Top 15)')
        plt.xlabel('추정 매출액 (원, 30대 비중 반영)')
        plt.ylabel('업종 (중분류)')
        plt.ticklabel_format(style='plain', axis='x')
        plt.grid(axis='x', linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(f'{output_dir}/category_sales_distribution_30s.png')
        plt.close()
        print(f"Category analysis saved to {output_dir}/category_sales_distribution_30s.png")

    print(f"Analysis saved to {output_dir}")

def main():
    api_key = load_env_key()
    if not api_key:
        print("Error: Public_shinhan_API key not found in .env")
        return

    # 20대 분석과 동일한 장소 목록 사용
    places = [
        "강남 MICE 관광특구", 
        "홍대 관광특구", 
        "명동 관광특구", 
        "성수카페거리", 
        "가로수길", 
        "이태원 관광특구",
        "잠실 관광특구",
        "종로·청계 관광특구",
        "여의도",
        "북촌한옥마을",
        "동대문 관광특구" 
    ]
    
    collected_place_data = []
    collected_category_data = []
    
    print("API 호출 시작 (30대 분석)...")
    
    for place in places:
        api_data = fetch_shinhan_data(api_key, 'citydata', 1, 5, place)
        
        if api_data and "CITYDATA" in api_data:
            data_root = api_data["CITYDATA"]
            cmrcl_stts = data_root.get("LIVE_CMRCL_STTS", [])
            
            stat = None
            if isinstance(cmrcl_stts, list) and len(cmrcl_stts) > 0:
                stat = cmrcl_stts[0]
            elif isinstance(cmrcl_stts, dict):
                stat = cmrcl_stts
                
            if stat:
                # 30대 데이터 추출 (CMRCL_30_RATE)
                rate_30s = stat.get('CMRCL_30_RATE', 0)
                collected_place_data.append({
                    'place_name': place,
                    'sales_30s_rate': rate_30s
                })
                print(f"  -> {place}: 30s Sales Rate {rate_30s}%")
                
                # 업종별 데이터
                rsb_list = stat.get('CMRCL_RSB', [])
                if rsb_list:
                    for item in rsb_list:
                        cat_mid = item.get('RSB_MID_CTGR', 'Unknown')
                        cat_lrg = item.get('RSB_LRG_CTGR', 'Unknown')
                        
                        amin = float(item.get('RSB_SH_PAYMENT_AMT_MIN', 0) or 0)
                        amax = float(item.get('RSB_SH_PAYMENT_AMT_MAX', 0) or 0)
                        avg_amt = (amin + amax) / 2
                        
                        # 30대 추정 매출: 전체 매출 * (30대 비중 / 100)
                        # *주의: 이는 해당 지역 전체의 30대 비중을 각 업종에 일괄 적용하는 추정치임.
                        # 업종별 연령 비중 데이터가 없으므로 이 방식을 사용.
                        weighted_amt = avg_amt * (float(rate_30s) / 100)
                        
                        period = item.get('RSB_MCT_TIME', 'Unknown')
                        
                        if weighted_amt > 0:
                            collected_category_data.append({
                                'place': place,
                                'category': cat_mid,
                                'amount': avg_amt,
                                'weighted_amount': weighted_amt,
                                'period': period
                            })
            else:
                print(f"  -> {place}: No Commercial Data")
        else:
             print(f"  -> {place}: API Request Failed or No Data")

    if not collected_place_data:
        print("\n[Error] 데이터 수집 실패.")
        return

    place_df = pd.DataFrame(collected_place_data)
    cat_df = pd.DataFrame(collected_category_data)
    
    print(f"\n[Notice] 데이터 집계 완료. (장소 {len(place_df)}개, 업종세부데이터 {len(cat_df)}건)")
    analyze_commercial_data(place_df, cat_df, '30대/eda_images')

if __name__ == "__main__":
    main()

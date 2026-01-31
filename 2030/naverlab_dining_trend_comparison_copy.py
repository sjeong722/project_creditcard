import os
import urllib.request
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from dotenv import load_dotenv

# 1. .env 파일에서 키 로드
load_dotenv()

client_id = os.getenv("NAVER_CLIENT_ID")
client_secret = os.getenv("NAVER_CLIENT_SECRET")

if not client_id or not client_secret or "your_client_id" in client_id:
    print("ERROR: .env 파일에 올바른 Client ID와 Secret을 입력해주세요.")
    exit(1)
else:
    print("Client ID & Secret 로드 완료.")

# 2. API 요청 함수 정의
def get_datalab_trend(keywords_groups, start_date="2025-01-01", end_date="2025-12-31", ages=["3", "4"]):
    """
    네이버 데이터랩 API 요청 함수
    ages: 
        '1': 0-12
        '2': 13-18
        '3': 19-24
        '4': 25-29
        '5': 30-34
        ...
    """
    url = "https://openapi.naver.com/v1/datalab/search"
    
    body = json.dumps({
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "month",
        "keywordGroups": keywords_groups,
        "ages": ages  # 20대 (19-24, 25-29)
    })

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    request.add_header("Content-Type", "application/json")

    try:
        response = urllib.request.urlopen(request, data=body.encode("utf-8"))
        res_code = response.getcode()
        if res_code == 200:
            response_body = response.read()
            return json.loads(response_body.decode('utf-8'))
        else:
            print("Error Code:" + res_code)
            return None
    except Exception as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None

# 3. 데이터 정의 
keywords_groups = [
    {"groupName": "흑백요리사", "keywords": ["흑백요리사", "흑백요리사1", "흑백요리사2", "흑백요리사3"]},
    {"groupName": "블루리본", "keywords": ["블루리본", "블루리본맛집", "블루리본서베이", "블루리본예약"]},
    {"groupName": "미슐랭", "keywords": ["미슐랭", "미슐랭가이드", "미슐랭맛집", "미슐랭스타"]},
    {"groupName": "캐치테이블", "keywords": ["캐치테이블", "캐치테이블예약", "캐치테이블웨이팅", "캐치테이블오픈런"]},
    {"groupName": "테이블링", "keywords": ["테이블링", "테이블링예약", "테이블링웨이팅", "원격줄서기"]},
]

print("데이터 요청 중...")
data_json = get_datalab_trend(keywords_groups)

if data_json:
    print("API 데이터 수신 성공!")
    
    # 4. 데이터 가공 및 저장
    results = []
    for group in data_json['results']:
        title = group['title']
        for period in group['data']:
            results.append({
                'Category': title,
                'Date': period['period'],
                'Ratio': period['ratio']
            })

    df = pd.DataFrame(results)
    df['Date'] = pd.to_datetime(df['Date'])
    df_pivot = df.pivot(index='Date', columns='Category', values='Ratio')

    # CSV 저장
    output_filename = "20대/naverlab_dining_trend_comparison.csv"
    df_pivot.to_csv(output_filename)
    print(f"csv 저장 완료: {output_filename}")
    
    # Optional: Display head
    print(df_pivot.head())

else:
    print("데이터를 가져오지 못했습니다.")
    

plt.figure(figsize=(12, 6))

for col in df_pivot.columns:
    plt.plot(df_pivot.index, df_pivot[col], marker='o', label=col)

plt.title("20대 검색 트렌드 변화 (네이버 데이터랩)", fontsize=14)
plt.xlabel("Date")
plt.ylabel("Search Trend Index")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
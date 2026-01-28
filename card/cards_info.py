
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 2026년 1월 23일 업데이트 목록
urls_gorilla = [
    "https://www.card-gorilla.com/card/detail/2885",
    "https://www.card-gorilla.com/card/detail/13",
    "https://www.card-gorilla.com/card/detail/49",
    "https://www.card-gorilla.com/card/detail/2441",
    "https://www.card-gorilla.com/card/detail/51",
    "https://www.card-gorilla.com/card/detail/2687",
    "https://www.card-gorilla.com/card/detail/2663",
    "https://www.card-gorilla.com/card/detail/2719",
    "https://www.card-gorilla.com/card/detail/2669",
    "https://www.card-gorilla.com/card/detail/2330",
    "https://www.card-gorilla.com/card/detail/2609", 
    "https://www.card-gorilla.com/card/detail/2886",
    "https://www.card-gorilla.com/card/detail/2376",
    "https://www.card-gorilla.com/card/detail/2835",
    "https://www.card-gorilla.com/card/detail/106",
    "https://www.card-gorilla.com/card/detail/2759",
    "https://www.card-gorilla.com/card/detail/769",
    "https://www.card-gorilla.com/card/detail/2261",
    "https://www.card-gorilla.com/card/detail/657",
    "https://www.card-gorilla.com/card/detail/2915",
    "https://www.card-gorilla.com/card/detail/1909",
    "https://www.card-gorilla.com/card/detail/2553",
    "https://www.card-gorilla.com/card/detail/39",
    "https://www.card-gorilla.com/card/detail/2676",
    "https://www.card-gorilla.com/card/detail/2657",
    "https://www.card-gorilla.com/card/detail/2685",
    "https://www.card-gorilla.com/card/detail/2898",
    "https://www.card-gorilla.com/card/detail/2591",
    "https://www.card-gorilla.com/card/detail/2844",
    "https://www.card-gorilla.com/card/detail/666"
]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # 봇 탐지를 피하기 위한 사용자 에이전트 추가
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

data = []
driver = get_driver()

print("Starting scraping with ID extraction...")
try:
    for url in urls_gorilla:
        print(f"Processing: {url}")
        
        # ID 추출
        card_id = url.split("detail/")[1].split("?")[0] if "detail/" in url else "N/A"
        
        driver.get(url)
        time.sleep(2) # 약간 줄였지만 안전함
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 1. 카드 이름
        og_title = soup.find('meta', property='og:title')
        name = og_title['content'].split('|')[0].strip() if og_title else "N/A"
        
        # 2. 카드 이미지
        og_image = soup.find('meta', property='og:image')
        image_url = og_image['content'] if og_image else "N/A"
        
        # 3. 혜택 (최종 CSV에는 사용되지 않지만 디버그나 확장을 위해 유지)
        og_desc = soup.find('meta', property='og:description')
        benefits = og_desc['content'] if og_desc else "N/A"
        
        # 4. 데이터 목록 추출 (실적, 연회비, 카드사)
        performance = "N/A"
        annual_fee = "N/A"
        company = "N/A"

        # 표준 정의 목록 항목 찾기 시도
        
        # 실적
        perf_dt = soup.find(lambda tag: tag.name == "dt" and "전월실적" in tag.text)
        if perf_dt:
            perf_dd = perf_dt.find_next_sibling('dd')
            if perf_dd:
                performance = perf_dd.get_text(strip=True)

        # 연회비
        fee_dt = soup.find(lambda tag: tag.name == "dt" and "연회비" in tag.text)
        if fee_dt:
            fee_dd = fee_dt.find_next_sibling('dd')
            if fee_dd:
                annual_fee = fee_dd.get_text(strip=True)
                
        # 카드사
        # 전략: 카드사는 특정 클래스에 나타나거나 추론됨.
        # 일반적인 카드고릴라 페이지를 보면 'brand' 클래스나 유사한 것이 있음.
        # 또는 "카드사"가 DL에 명시적으로 표시되지 않는 경우가 많음.
        # 그러나 종종 'card_img' alt 텍스트나 유사한 메타데이터에 포함됨.
        # 특정 요소를 찾아보겠음.
        # 쉽지 않다면 제목에 "삼성" 등이 있는 경우 추출할 수 있지만 신뢰할 수 없음.
        # 기존 데이터와 일치시켜 보겠음: "삼성", "신한카드".
        # 때때로 일반적인 <p class="brand">나 유사한 것이 있음.
        # 'brand' 클래스를 찾아보겠음.
        brand_tag = soup.find(class_="brand")
        if brand_tag:
            company = brand_tag.get_text(strip=True)
        else:
            # 대체: 상단 영역에 있을 수 있음
            pass

        data.append({
            "card_id": card_id,
            "card_name": name,
            "company": company,
            "annual_fee": annual_fee,
            "performance": performance,
            "image_url": image_url,
            "url": url
        })
        
finally:
    driver.quit()

df = pd.DataFrame(data)

# 타겟 CSV 스키마에 맞춰 열 순서 변경
# card_id,card_name,company,annual_fee,performance,image_url,url
cols = ["card_id", "card_name", "company", "annual_fee", "performance", "image_url", "url"]
df = df[cols]

output_file = "cards_info.csv"
df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(f"Saved {len(df)} records to {output_file}")
print(df[["card_id", "card_name", "company"]].head())

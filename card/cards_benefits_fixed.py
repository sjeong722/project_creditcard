
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import os

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Add User-Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def normalize(text):
    if not isinstance(text, str):
        return ""
    # Remove spaces, lowercase
    return re.sub(r'\s+', '', text).lower()

def get_tokens(text):
    if not isinstance(text, str):
        return set()
    tokens = re.split(r'[\s\(\)\[\]\/,]+', text)
    return {t.lower() for t in tokens if len(t) >= 1}

def calculate_score(csv_row, dt_text):
    category = str(csv_row.get('category', ''))
    summary = str(csv_row.get('summary', ''))
    dt_norm = normalize(dt_text)
    
    score = 0
    if normalize(summary) in dt_norm and len(summary) > 3:
        score += 20
        
    summary_tokens = get_tokens(summary)
    category_tokens = get_tokens(category)
    
    common_words = {'할인', '적립', '제공', '서비스', '기타', '카드'}
    
    for token in summary_tokens:
        if token in dt_norm:
            if token not in common_words:
                score += 3
            else:
                score += 1

    for token in category_tokens:
        if token in dt_norm:
            if token not in common_words:
                score += 4
            else:
                score += 1

    synonyms = [('마일', '마일리지'), ('mr', '멤버십리워즈'), ('라운지', '공항라운지')]
    for s1, s2 in synonyms:
        if (s1 in summary or s2 in summary) and (s1 in dt_text or s2 in dt_text):
            score += 5

    return score

def infer_benefit_metadata(summary, detail):
    # Simple heuristics to fill potential columns
    summary = str(summary)
    detail = str(detail)
    combined = summary + " " + detail
    
    benefit_type = "기타"
    if "할인" in combined:
        benefit_type = "할인"
    elif "적립" in combined or "마일리지" in combined or "캐시백" in combined:
        benefit_type = "적립"
        
    rate = ""
    # Extract percentage if exists, e.g. "10%"
    # Look for number followed by %
    rate_match = re.search(r'(\d+(?:\.\d+)?)%', combined)
    if rate_match:
        rate = rate_match.group(0)
    else:
        # Check for currency "원" amount if looks like a rate/limit
        pass
        
    return benefit_type, rate

def scrape_card_benefits(driver, card_id, url):
    print(f"Scraping NEW card ID: {card_id} from {url}")
    try:
        driver.get(url)
        # Wait for content
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "dl"))
            )
        except:
            print(f"  Warning: No DLs found for {card_id}")
            return []
            
        dls = driver.find_elements(By.TAG_NAME, "dl")
        new_rows = []
        seq = 1
        
        for dl in dls:
            try:
                dt = dl.find_element(By.TAG_NAME, "dt")
                # Sometimes there's a button to expand detail, but if we just get text, usually Selenium gets visible text.
                # If detail is hidden, we might need to click.
                # Let's try clicking just in case, or just get text first. 
                # The 'fix' script clicked.
                
                # Check if DD is visible?
                # Usually DD text exists but might be hidden. 
                # Let's try to get innerText directly.
                
                # Try to click to ensure expansion if it's an accordion
                driver.execute_script("arguments[0].click();", dt)
                time.sleep(0.1)
                
                dd = dl.find_element(By.TAG_NAME, "dd")
                summary = dt.text
                detail = dd.text
                
                if not summary:
                    continue
                    
                # Infer Metadata
                benefit_type, rate = infer_benefit_metadata(summary, detail)
                
                # Infer Category? 
                # Often there's an icon class or previous header. 
                # For now, default to "Unknown" or Try to parse
                # Maybe use keyword in summary
                category = "기타"
                keywords = {
                    "교통": "교통", "통신": "통신", "마트": "마트/편의점", "편의점": "마트/편의점",
                    "커피": "푸드", "스타벅스": "푸드", "식당": "푸드", "음식": "푸드",
                    "해외": "해외", "여행": "여행/항공", "항공": "여행/항공",
                    "주유": "주유", "쇼핑": "쇼핑", "영화": "문화", "병원": "의료"
                }
                for k, v in keywords.items():
                    if k in summary:
                        category = v
                        break
                
                new_rows.append({
                    'card_id': card_id,
                    'benefit_seq': seq,
                    'category': category,
                    'benefit_type': benefit_type,
                    'rate': rate,
                    'is_selectable': 'N', # Default
                    'icon_type': '',
                    'dt_class': '',
                    'summary': summary,
                    'detail': detail
                })
                seq += 1
                
            except Exception as e:
                # print(f"  Error parsing a DL: {e}")
                continue
                
        return new_rows
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []

def main():
    # 1. Paths
    info_csv_path = "card/cards_info.csv"
    benefits_csv_path = "card/cards_benefits_fixed.csv"
    
    # Check if we should use absolute paths if running from root
    if not os.path.exists(info_csv_path) and os.path.exists("cards_info.csv"):
        info_csv_path = "cards_info.csv" # Adjust if running inside card dir
        benefits_csv_path = "cards_benefits_fixed.csv"
        
    print(f"Loading Card Info from {info_csv_path}")
    if not os.path.exists(info_csv_path):
        print("Error: cards_info.csv not found.")
        return

    info_df = pd.read_csv(info_csv_path)
    
    # 2. Load Existing Benefits
    if os.path.exists(benefits_csv_path):
        df = pd.read_csv(benefits_csv_path)
        print(f"Loaded {len(df)} existing benefit rows.")
    else:
        df = pd.DataFrame(columns=['card_id', 'benefit_seq', 'category', 'benefit_type', 'rate', 'is_selectable', 'icon_type', 'dt_class', 'summary', 'detail'])
        print("Created new DataFrame for benefits.")

    # Convert card_id to same type (str or int)
    # Let's ensure string for matching
    info_df['card_id'] = info_df['card_id'].astype(str)
    df['card_id'] = df['card_id'].astype(str)
    
    # 3. Identify New Cards
    existing_ids = set(df['card_id'].unique())
    all_target_ids = set(info_df['card_id'].unique())
    
    new_ids = all_target_ids - existing_ids
    print(f"Found {len(new_ids)} new cards to scrape.")
    
    driver = get_driver()
    
    try:
        # A. Scrape New Cards
        new_data = []
        for card_id in new_ids:
            # Get URL
            row = info_df[info_df['card_id'] == card_id].iloc[0]
            url = row['url']
            
            scraped_rows = scrape_card_benefits(driver, card_id, url)
            if scraped_rows:
                new_data.extend(scraped_rows)
                print(f"  -> Added {len(scraped_rows)} benefits for card {card_id}")
            time.sleep(1)
            
        if new_data:
            new_df = pd.DataFrame(new_data)
            df = pd.concat([df, new_df], ignore_index=True)
            
        # B. "Fix" Existing Missing Details (Optional, keeping original logic for robustness)
        # Check if there are rows with empty detail
        # But only if we have summary.
        # This part iterates all cards again. To save time, maybe only valid if requested.
        # But let's do a quick pass for any EMPTY details in the *whole* DF
        
        # Filter rows with empty details
        if 'detail' not in df.columns:
            df['detail'] = ""
            
        # Treat NaN as empty
        empty_mask = df['detail'].isna() | (df['detail'].astype(str).str.strip() == "")
        ids_with_empty = df.loc[empty_mask, 'card_id'].unique()
        
        if len(ids_with_empty) > 0:
            print(f"Found {len(ids_with_empty)} cards with missing details. Attempting to fix...")
            
            for card_id in ids_with_empty:
                # Get URL
                # lookup in info_df
                match = info_df[info_df['card_id'] == card_id]
                if match.empty:
                    # If card exists in benefits but not info, we might not have URL. skip.
                    continue
                url = match.iloc[0]['url']
                
                print(f"Fixing Card ID: {card_id}")
                driver.get(url)
                time.sleep(1)
                
                try:
                     # Find DLs
                    dls = driver.find_elements(By.TAG_NAME, "dl")
                    dl_items = []
                    for dl in dls:
                        try:
                            dt = dl.find_element(By.TAG_NAME, "dt")
                            dl_items.append({'dl': dl, 'dt': dt, 'text': dt.text})
                        except:
                            pass
                            
                    # Iterate rows for this card that are empty
                    card_indices = df[(df['card_id'] == card_id) & empty_mask].index
                    
                    for idx in card_indices:
                        row = df.loc[idx]
                        best_match = None
                        max_score = 0
                        
                        for item in dl_items:
                            score = calculate_score(row, item['text'])
                            if score > max_score:
                                max_score = score
                                best_match = item
                        
                        if best_match and max_score >= 3:
                            try:
                                driver.execute_script("arguments[0].click();", best_match['dt'])
                                time.sleep(0.1)
                                dd = best_match['dl'].find_element(By.TAG_NAME, "dd")
                                df.at[idx, 'detail'] = dd.text
                                print(f"  Fixed: {row['summary'][:15]}... -> Found Detail")
                            except:
                                pass
                except Exception as e:
                    print(f"Error fixing {card_id}: {e}")

    finally:
        driver.quit()
        
    # Save
    df.to_csv(benefits_csv_path, index=False, encoding='utf-8-sig')
    print(f"\nSaved updated benefits to {benefits_csv_path}")

if __name__ == "__main__":
    main()

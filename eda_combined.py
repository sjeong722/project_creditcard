
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
import os
from wordcloud import WordCloud
import matplotlib.font_manager as fm

# Setting Korean Font for Mac
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

def clean_fee(fee_str):
    if pd.isna(fee_str):
        return 0
    # Extract numbers only. If multiple numbers (e.g. domestic/foreign), take the max or first?
    # Usually format is "국내전용 10,000원 해외겸용 15,000원". Let's take the max found.
    nums = re.findall(r'[\d,]+', str(fee_str))
    if not nums:
        return 0
    # Clean commas and convert to int
    valid_nums = []
    for n in nums:
        clean_n = n.replace(',', '')
        if clean_n.isdigit():
            valid_nums.append(int(clean_n))
    return max(valid_nums) if valid_nums else 0

def clean_text(text):
    if pd.isna(text):
        return ""
    # Remove special chars, keep Korean, English, Numbers
    return re.sub(r'[^가-힣a-zA-Z0-9\s]', '', str(text))

def main():
    print("Starting EDA Process...")

    # 1. Load Data
    try:
        cards_info = pd.read_csv('card/cards_info.csv')
        cards_benefits = pd.read_csv('card/cards_benefits_fixed.csv')
        yt_videos = pd.read_csv('youtube_20_consumption_analysis.csv')
        yt_comments = pd.read_csv('youtube_comments_analysis.csv')
        print("Files loaded successfully.")
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # Create output directory
    if not os.path.exists('eda_results'):
        os.makedirs('eda_results')

    # LEt's do some cleaning
    cards_info['annual_fee_clean'] = cards_info['annual_fee'].apply(clean_fee)

    # --- Analysis 1: Card Landscape ---
    
    # 1.1 Company Distribution
    plt.figure(figsize=(10, 6))
    sns.countplot(y='company', data=cards_info, order=cards_info['company'].value_counts().index)
    plt.title('Card Issuers Distribution')
    plt.savefig('eda_results/card_issuer_dist.png')
    plt.close()

    # 1.2 Annual Fee Dist
    plt.figure(figsize=(10, 6))
    sns.histplot(cards_info['annual_fee_clean'], bins=20)
    plt.title('Annual Fee Distribution')
    plt.xlabel('Fee (KRW)')
    plt.savefig('eda_results/annual_fee_dist.png')
    plt.close()

    # 1.3 Benefit Categories
    plt.figure(figsize=(12, 8))
    # Filter out empty or '기타' if desired, but let's keep all
    top_categories = cards_benefits['category'].value_counts().head(10)
    sns.barplot(x=top_categories.values, y=top_categories.index)
    plt.title('Top 10 Benefit Categories')
    plt.savefig('eda_results/top_benefit_categories.png')
    plt.close()

    # --- Analysis 2: 20s Consumption Trends (YouTube) ---

    # 2.1 Keyword Extraction from Titles and Tags
    all_text = ""
    # Add Titles
    all_text += " ".join(yt_videos['제목'].dropna().apply(clean_text).tolist()) + " "
    # Add Related Keywords (they are comma separated strings)
    keywords_raw = yt_videos['연관키워드(소비한 물품명)'].dropna().tolist()
    for k in keywords_raw:
        all_text += k.replace(',', ' ') + " "
    
    # Word Cloud
    # Exclude common stop words
    stop_words = {'20대', '30대', '브이로그', '영상', '것', '수', '등', '하는', '있는', '소비', '돈', '모으기', '재테크', '저축'} 
    # '소비', '돈', '재테크' are actual topics, but maybe too generic? Let's keep specific ones.
    
    wordcloud = WordCloud(font_path='/System/Library/Fonts/Supplemental/AppleGothic.ttf',
                          width=800, height=400, 
                          background_color='white',
                          stopwords=stop_words).generate(all_text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title('20s Consumption Trends WordCloud')
    plt.savefig('eda_results/yt_trends_wordcloud.png')
    plt.close()

    # 2.2 Top Keywords Frequency
    words = [w for w in all_text.split() if w not in stop_words and len(w) > 1]
    counter = Counter(words)
    common_words = counter.most_common(15)
    
    words_df = pd.DataFrame(common_words, columns=['Word', 'Count'])
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Count', y='Word', data=words_df)
    plt.title('Top 15 Keywords in 20s Consumption Videos')
    plt.savefig('eda_results/top_keywords_yt.png')
    plt.close()

    # --- Analysis 3: Mapping Trends to Benefits ---
    
    # Simple crossover check: Do top consumption keywords appear in Card Benefit Summaries?
    # Benefit Summaries text
    benefits_text = " ".join(cards_benefits['summary'].dropna().apply(clean_text).tolist())
    
    # Check intersection
    matched_data = []
    for word, count in common_words:
        # Simple string match count in benefits
        benefit_hits = benefits_text.count(word)
        matched_data.append({'Keyword': word, 'YT_Count': count, 'Card_Benefit_Hits': benefit_hits})
        
    match_df = pd.DataFrame(matched_data)
    
    # Plot Comparison
    # Normalize for visualization? Or just raw counts (scales differ vastly)
    # Let's just show a table or dual axis plot. 
    # Actually, saving a CSV report of this is better.
    match_df.to_csv('eda_results/trend_benefit_match.csv', index=False)
    print("Saved Trend vs Benefit analysis to eda_results/trend_benefit_match.csv")

    # --- Analysis 4: Comment Sentiment/Topics (Basic) ---
    comment_text = " ".join(yt_comments['댓글내용'].dropna().apply(clean_text).tolist())
    comment_words = [w for w in comment_text.split() if w not in stop_words and len(w) > 1]
    comment_counter = Counter(comment_words)
    
    comment_common = pd.DataFrame(comment_counter.most_common(15), columns=['Word', 'Count'])
    plt.figure(figsize=(10, 6))
    sns.barplot(x='Count', y='Word', data=comment_common)
    plt.title('Top Words in YouTube Comments')
    plt.savefig('eda_results/comment_keywords.png')
    plt.close()

    print("EDA Complete. Check 'eda_results' folder.")

if __name__ == "__main__":
    main()

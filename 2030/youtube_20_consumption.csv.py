import os
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build

def fetch_videos(youtube, query, required_keywords, max_items=20, order='relevance'):
    print(f"Searching for '{query}' (Order: {order}, Max: {max_items})...")
    
    collected_data = []
    next_page_token = None
    
    while len(collected_data) < max_items:
        try:
            search_request = youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=min(50, max_items - len(collected_data)),
                type="video",
                order=order,
                pageToken=next_page_token
            )
            search_response = search_request.execute()
        except Exception as e:
            print(f"Error during search for {query}: {e}")
            break

        video_ids = []
        for item in search_response.get('items', []):
            title = item['snippet']['title']
            if all(keyword in title for keyword in required_keywords):
                video_ids.append(item['id']['videoId'])
        
        if not video_ids:
            next_page_token = search_response.get('nextPageToken')
            if not next_page_token:
                break
            continue

        try:
            stats_request = youtube.videos().list(
                part="statistics,snippet",
                id=','.join(video_ids)
            )
            stats_response = stats_request.execute()
        except Exception as e:
            print(f"Error fetching stats: {e}")
            break

        for video in stats_response.get('items', []):
            snippet = video['snippet']
            stats = video['statistics']
            title = snippet['title']
            
            # Double check filtering
            if not all(keyword in title for keyword in required_keywords):
                continue

            view_count = stats.get('viewCount', 0)
            like_count = stats.get('likeCount', 0)
            comment_count = stats.get('commentCount', 0)
            tags = snippet.get('tags', [])
            published_at = snippet.get('publishedAt', '')[:10]
            description = snippet.get('description', '')

            # Summary processing
            lines = [line.strip() for line in description.split('\n') if line.strip()]
            summary = ""
            if lines:
                summary = lines[0]
                if len(summary) < 30 and len(lines) > 1:
                    summary += " " + lines[1]
            if len(summary) > 100:
                summary = summary[:97] + "..."

            related_keywords = ", ".join(tags) if tags else ""

            collected_data.append({
                "게시날짜": published_at,
                "제목": title,
                "조회수": view_count,
                "좋아요수": like_count,
                "댓글수": comment_count,
                "연관키워드(소비한 물품명)": related_keywords,
                "영상내용요약": summary
            })

            if len(collected_data) >= max_items:
                break
        
        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break
            
    return collected_data

def main():
    # 1. Load environment variables
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Error: Google API Key not found.")
        return

    # 2. Build the YouTube client
    youtube = build('youtube', 'v3', developerKey=api_key)
    output_file = "youtube_20_consumption_analysis.csv"
    
    # 3. Load existing data if available
    all_data = []
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            all_data = existing_df.to_dict('records')
            print(f"Loaded {len(all_data)} existing records from {output_file}.")
        except Exception as e:
            print(f"Error loading existing file: {e}")

    # 4. Define new search tasks
    # User requested: "20대"and"재태크", "20대"and"플렉스", "20대"and"신용카드" sorted by viewCount
    new_tasks = [
        {"query": "20대 재테크", "keywords": ["20대", "재테크"], "limit": 20},
        {"query": "20대 플렉스", "keywords": ["20대", "플렉스"], "limit": 20},
        {"query": "20대 신용카드", "keywords": ["20대", "신용카드"], "limit": 20}
    ]

    for task in new_tasks:
        new_items = fetch_videos(
            youtube, 
            query=task['query'], 
            required_keywords=task['keywords'], 
            max_items=task['limit'], 
            order='viewCount'  # High view count preference
        )
        all_data.extend(new_items)
        print(f"Added {len(new_items)} videos for '{task['query']}'.")

    # 5. Save combined data
    if all_data:
        df = pd.DataFrame(all_data)
        
        # Remove duplicates based on Title just in case
        original_len = len(df)
        df.drop_duplicates(subset=['제목'], keep='first', inplace=True)
        if len(df) < original_len:
            print(f"Removed {original_len - len(df)} duplicate videos.")

        # Ensure column order
        cols = ['게시날짜', '제목', '조회수', '좋아요수', '댓글수', '연관키워드(소비한 물품명)', '영상내용요약']
        
        # Filter for existing columns only to avoid errors if schema changed slightly
        valid_cols = [c for c in cols if c in df.columns]
        df = df[valid_cols]

        # Sort: User didn't specify final sort order, but "게시날짜" descending is usually good.
        # However, they asked for "viewCount" extraction for new ones. 
        # Let's keep the user's previous preference: "게시날짜 기준 전체 행 내림차순"
        if '게시날짜' in df.columns:
            df.sort_values(by='게시날짜', ascending=False, inplace=True)

        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Successfully saved total {len(df)} videos to '{output_file}'.")
    else:
        print("No data to save.")

if __name__ == "__main__":
    main()

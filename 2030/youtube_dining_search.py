import os
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build

def fetch_videos(youtube, query, max_items=100, order='viewCount'):
    print(f"Searching for '{query}' (Order: {order}, Max: {max_items})...")
    
    collected_data = []
    next_page_token = None
    
    # Try to fetch up to max_items for this query. 
    # YouTube API limits to ~500 items, but we stop earlier if needed.
    while len(collected_data) < max_items:
        try:
            # 1. Search Request
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

        items = search_response.get('items', [])
        if not items:
            break

        video_ids = [item['id']['videoId'] for item in items]
        
        # 2. Get Statistics for these videos
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
            
            view_count = int(stats.get('viewCount', 0))
            like_count = int(stats.get('likeCount', 0))
            comment_count = int(stats.get('commentCount', 0))
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
                "연관키워드": related_keywords,
                "영상내용요약": summary,
                "VideoID": video['id'] 
            })
        
        next_page_token = search_response.get('nextPageToken')
        if not next_page_token:
            break
            
    return collected_data

def main():
    # 1. Load environment variables
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env")
        return

    # 2. Build the YouTube client
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    output_file = "youtube_dining_100.csv"
    target_count = 100
    
    # 3. Strategy: Use multiple similar queries to fill the quota
    # If "기념일 예약 맛집" isn't enough, try synonyms.
    queries = [
        "기념일 예약 맛집",
        "기념일 레스토랑 예약",
        "기념일 디너 추천",
        "서울 기념일 맛집", 
        "분위기 좋은 레스토랑 예약"
    ]
    
    all_videos = {} # Use dict with ID as key to dedup automatically

    for q in queries:
        if len(all_videos) >= target_count:
            break
            
        needed = target_count - len(all_videos)
        # Fetch a bit more than needed to account for duplicates
        print(f"\nQuerying: {q} | Needed: {needed}")
        
        # We ask for 'needed * 2' or at least 50 to have buffer
        fetch_limit = max(50, needed * 2) 
        
        results = fetch_videos(youtube, q, max_items=fetch_limit, order='viewCount')
        
        for vid in results:
            vid_id = vid['VideoID']
            if vid_id not in all_videos:
                # Keep VideoID for comment extraction
                all_videos[vid_id] = vid
                
        print(f"Total Unique Videos collected so far: {len(all_videos)}")

    # 4. Save to CSV
    if all_videos:
        # Convert to list
        final_list = list(all_videos.values())
        
        # Sort by view count descending
        df = pd.DataFrame(final_list)
        df.sort_values(by='조회수', ascending=False, inplace=True)
        
        # Limit to strictly 100 if we have more
        if len(df) > target_count:
            df = df.iloc[:target_count]
            
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\nSuccessfully saved {len(df)} videos to '{output_file}'.")
    else:
        print("No data found.")

if __name__ == "__main__":
    main()

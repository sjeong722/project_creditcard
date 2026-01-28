import os
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
import time

def get_video_map_from_search(youtube, queries):
    """
    Perform searches to rebuild a map of {Title: {'id': videoId, 'commentCount': count, ...}}
    This saves quota compared to searching for every single title one by one.
    """
    video_map = {}
    print("Re-fetching video metadata to match IDs (Quota efficient)...")
    
    for query in queries:
        # User sorted by viewCount originally for some, or date for others. 
        # We try to fetch enough to cover the CSV list. 
        # CSV has ~100 items. Fetching 50 items per query (x4 queries) = 200 items. Should cover most.
        print(f"  - Searching '{query}'...")
        try:
            search_response = youtube.search().list(
                q=query,
                part="id,snippet",
                maxResults=50, 
                type="video"
                # Not specifying order might get relevance which is usually better for title match, 
                # but user used 'viewCount' for the extension. Let's try default relevance to find by title better?
                # Actually, if we used viewCount before, we should use viewCount again to find the same videos.
                # Let's do two passes if needed? No, let's try 'viewCount' as user seems to prefer popular ones.
            ).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
            if not video_ids:
                continue
                
            # Get stats (comment count)
            stats_req = youtube.videos().list(
                part="statistics,snippet",
                id=','.join(video_ids)
            ).execute()
            
            for item in stats_req.get('items', []):
                title = item['snippet']['title']
                vid = item['id']
                stats = item['statistics']
                comment_count = int(stats.get('commentCount', 0))
                
                # Normalize title for better matching (strip)
                clean_title = title.strip()
                video_map[clean_title] = {
                    'id': vid,
                    'commentCount': comment_count,
                    'original_obj': item
                }
                
        except Exception as e:
            print(f"Error searching {query}: {e}")
            
    return video_map

def main():
    # 1. Load Keys
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        print("Error: API Key not found.")
        return

    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # 2. Load Existing CSV
    input_file = "youtube_20_consumption_analysis.csv"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    df = pd.read_csv(input_file)
    original_titles = df['제목'].dropna().str.strip().tolist()
    
    print(f"Loaded {len(df)} records from CSV.")
    
    # 3. Filter Target Rows (Title contains "소비" OR "재테크")
    # Actually, user also said "comment count >= 100". 
    # The CSV has '댓글수' column. We can use it directly!
    # No need to re-check actual API comment count for filtering, we trust the CSV.
    # But we still need VideoId.
    
    # Filter by CSV columns first
    target_df = df[
        (df['댓글수'] >= 100) & 
        (df['제목'].str.contains("소비|재테크|재태크", na=False)) # User wrote "재태크" (typo) so include it
    ].copy()
    
    if target_df.empty:
        print("No videos in CSV match criteria (Comments>=100 AND Title has 소비/재테크).")
        return
        
    print(f"Filtered down to {len(target_df)} target videos from CSV.")
    target_titles = target_df['제목'].str.strip().tolist()
    
    # 4. Re-fetch IDs
    # We use the queries we used before to find these videos again.
    re_search_queries = ["20대 소비", "20대 재테크", "20대 플렉스", "20대 신용카드"]
    
    # We might need to run search with order='date' AND order='viewCount' to catch them all
    # To save quota, let's try 'viewCount' first as they are likely high views if comments > 100.
    
    # Helper to populate map
    # Since we can't pass 'order' blindly, let's assume popular ones are found via viewCount.
    # We'll modify the helper to accept params if needed, but let's keep it simple.
    
    # Custom search loop here to control logic better
    video_id_map = {}
    
    print("Resolving Video IDs...")
    known_ids_count = 0
    
    for query in re_search_queries:
        if known_ids_count >= len(target_titles):
            break 
            
        request = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=50,
            type="video",
            order="viewCount" 
        )
        response = request.execute()
        
        for item in response.get('items', []):
            t = item['snippet']['title'].strip()
            v_id = item['id']['videoId']
            # Store in map if it matches any target
            if t in target_titles:
                video_id_map[t] = v_id
                
    # Check coverage
    found_count = len([t for t in target_titles if t in video_id_map])
    print(f"Found IDs for {found_count} / {len(target_titles)} videos via 'viewCount' search.")
    
    # If missing, try 'relevance' or 'date' for the remaining?
    # Or try searching by specific title for the missing ones? 
    # Searching specific title cost 100 units per video. 
    # If 10 missing, 1000 units. Affordable.
    MISSING_LIMIT_SEARCH = 10 # Allow up to 10 specific searches
    
    missing_titles = [t for t in target_titles if t not in video_id_map]
    if missing_titles:
        print(f"Attempting specific search for {min(len(missing_titles), MISSING_LIMIT_SEARCH)} missing videos...")
        for t in missing_titles[:MISSING_LIMIT_SEARCH]:
            try:
                req = youtube.search().list(
                    q=t,
                    part="id,snippet",
                    maxResults=1,
                    type="video"
                )
                res = req.execute()
                if res.get('items'):
                    video_id_map[t] = res['items'][0]['id']['videoId']
            except:
                pass
                
    # 5. Extract Comments
    all_comments_data = []
    
    for index, row in target_df.iterrows():
        title = row['제목'].strip()
        vid = video_id_map.get(title)
        
        if not vid:
            print(f"Skipping (ID not found): {title[:30]}...")
            continue
            
        print(f"Extracting comments for: {title[:30]}...")
        
        try:
            # Fetch comments
            comment_req = youtube.commentThreads().list(
                part="snippet",
                videoId=vid,
                maxResults=50, # Limit 50 per video
                textFormat="plainText",
                order="relevance"
            )
            comment_res = comment_req.execute()
            
            for thread in comment_res.get('items', []):
                c_snippet = thread['snippet']['topLevelComment']['snippet']
                c_text = c_snippet['textDisplay']
                
                # Clean text
                c_summary = c_text.replace('\n', ' ').strip()
                if len(c_summary) > 200:
                    c_summary = c_summary[:200] + "..."
                    
                # Create row copying original metadata but replacing '영상내용요약'
                new_row = row.copy()
                new_row['영상내용요약'] = c_summary
                all_comments_data.append(new_row)
                
        except Exception as e:
            print(f"Error fetching comments for {vid}: {e}")
            
    # 6. Save
    if all_comments_data:
        out_df = pd.DataFrame(all_comments_data)
        out_file = "youtube_comments_analysis.csv"
        
        # Rename '영상내용요약' -> '댓글내용' first
        out_df.rename(columns={'영상내용요약': '댓글내용'}, inplace=True)
        
        # Ensure column order (Exclude '연관키워드')
        # Columns: 게시날짜, 제목, 조회수, 좋아요수, 댓글수, 댓글내용
        cols = ['게시날짜', '제목', '조회수', '좋아요수', '댓글수', '댓글내용']
        
        # Filter columns that exist
        valid_cols = [c for c in cols if c in out_df.columns]
        out_df = out_df[valid_cols]
        
        out_df.to_csv(out_file, index=False, encoding='utf-8-sig')
        print(f"Successfully saved {len(out_df)} comments to '{out_file}'.")
    else:
        print("No comments extracted.")

if __name__ == "__main__":
    main()

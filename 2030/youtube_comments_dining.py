import os
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
import time

def get_comments(youtube, video_id):
    comments = []
    try:
        request = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,  # Limits per video to avoid quota exhaustion
            textFormat="plainText"
        )
        response = request.execute()

        while response:
            for item in response.get('items', []):
                snippet = item['snippet']['topLevelComment']['snippet']
                text = snippet['textDisplay']
                author = snippet['authorDisplayName']
                like_count = snippet['likeCount']
                
                comments.append({
                    'text': text,
                    'author': author,
                    'likes': like_count
                })

            if 'nextPageToken' in response:
                request = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    pageToken=response['nextPageToken'],
                    maxResults=100,
                    textFormat="plainText"
                )
                response = request.execute()
                # Simple throttle
                # time.sleep(0.1)
                
                # Limit total comments per video to say 200 for now to save quota
                if len(comments) >= 200:
                    break
            else:
                break
    except Exception as e:
        # Comments might be disabled
        # print(f"Could not get comments for video {video_id}: {e}")
        pass
        
    return comments

def main():
    load_dotenv()
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.")
        return

    youtube = build('youtube', 'v3', developerKey=api_key)

    input_file = "youtube_dining_100.csv"
    output_file = "youtube_comments_analysis_dining.csv"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    
    if 'VideoID' not in df.columns:
        print("Error: 'VideoID' column missing in input CSV. Please regenerate the video list.")
        return

    target_keywords = ['흑백요리사', '캐치테이블', '블루리본', '미슐랭', '미쉐린', '테이블링', '예약', '웨이팅', '앱']
    print(f"Extracting comments containing: {target_keywords}")

    final_rows = []
    
    total_videos = len(df)
    print(f"Processing {total_videos} videos...")

    for idx, row in df.iterrows():
        video_id = row['VideoID']
        title = row['제목']
        
        comments = get_comments(youtube, video_id)
        
        for c in comments:
            text = c['text']
            # Check for keywords
            if any(keyword in text for keyword in target_keywords):
                # Format matches 'youtube_comments_analysis.csv'
                final_rows.append({
                    '게시날짜': row['게시날짜'],
                    '제목': title,
                    '조회수': row['조회수'],
                    '좋아요수': row['좋아요수'],
                    '댓글수': row['댓글수'], # Video stats
                    '댓글내용': text
                })
        
        # Throttle to be nice to API
        if idx % 10 == 0:
            print(f"Processed {idx+1} videos. Found {len(final_rows)} relevant comments so far.")
            
    if final_rows:
        result_df = pd.DataFrame(final_rows)
        # Ensure column order
        cols = ['게시날짜', '제목', '조회수', '좋아요수', '댓글수', '댓글내용']
        result_df = result_df[cols]
        
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Successfully saved {len(result_df)} comments to '{output_file}'.")
    else:
        print("No relevant comments found.")

if __name__ == "__main__":
    main()

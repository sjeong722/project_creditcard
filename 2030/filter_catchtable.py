import pandas as pd
import os

def main():
    # Define file paths
    video_file = "/Users/t2024-m0246/Documents/GitHub/project_sojeong/20대/youtube_dining_100.csv"
    comment_file = "/Users/t2024-m0246/Documents/GitHub/project_sojeong/20대/youtube_comments_analysis_dining.csv"
    output_file = "/Users/t2024-m0246/Documents/GitHub/project_sojeong/20대/catchtable_mentions.csv"
    
    keyword = "캐치테이블"
    collected_rows = []

    # 1. Search in Video Info File
    if os.path.exists(video_file):
        print(f"Scanning {video_file}...")
        df_vid = pd.read_csv(video_file)
        
        # Check title, summary, related keywords
        # Fill NaN to avoid errors
        df_vid['제목'] = df_vid['제목'].fillna("")
        df_vid['영상내용요약'] = df_vid['영상내용요약'].fillna("")
        df_vid['연관키워드'] = df_vid['연관키워드'].fillna("")
        
        for _, row in df_vid.iterrows():
            # Check if keyword exists in Title or Summary or Keywords
            content_to_check = f"{row['제목']} {row['영상내용요약']} {row['연관키워드']}"
            if keyword in content_to_check:
                collected_rows.append({
                    'Type': 'Video',
                    'Date': row.get('게시날짜', ''),
                    'Title': row.get('제목', ''),
                    'Content': f"Title: {row['제목']} / Keywords: {row['연관키워드']} / Summary: {row['영상내용요약']}",
                    'Views/Likes': f"Views: {row.get('조회수',0)}",
                    'SourceFile': 'youtube_dining_100.csv'
                })
    else:
        print(f"Warning: {video_file} not found.")

    # 2. Search in Comments File
    if os.path.exists(comment_file):
        print(f"Scanning {comment_file}...")
        df_com = pd.read_csv(comment_file)
        
        df_com['댓글내용'] = df_com['댓글내용'].fillna("")
        
        for _, row in df_com.iterrows():
            # Check if keyword exists in Comment
            if keyword in row['댓글내용']:
                collected_rows.append({
                    'Type': 'Comment',
                    'Date': row.get('게시날짜', ''),
                    'Title': row.get('제목', ''),
                    'Content': row['댓글내용'],
                    'Views/Likes': f"Likes: {row.get('좋아요수',0)}", # For comments usually likes matter more
                    'SourceFile': 'youtube_comments_analysis_dining.csv'
                })
    else:
        print(f"Warning: {comment_file} not found.")

    # 3. Save to new CSV
    if collected_rows:
        result_df = pd.DataFrame(collected_rows)
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Successfully saved {len(result_df)} rows containing '{keyword}' to {output_file}.")
    else:
        print(f"No mentions of '{keyword}' found in either file.")

if __name__ == "__main__":
    main()

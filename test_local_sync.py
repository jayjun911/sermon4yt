import json
import re
from sync_youtube import extract_videos_from_yt_json, clean_string

CONTENT_FILE = r"C:\Users\Jay Jun\.gemini\antigravity-ide\brain\1e97f3eb-b36f-44bf-894e-7d13944ed5b1\.system_generated\steps\151\content.md"

with open(CONTENT_FILE, "r", encoding="utf-8") as f:
    html = f.read()

m = re.search(r"var ytInitialData\s*=\s*({.*?});</script>", html)
if m:
    data = json.loads(m.group(1))
    videos = extract_videos_from_yt_json(data)
    print(f"Extracted {len(videos)} video(s) from local HTML:")
    for v in videos:
        print(f"  ID: {v['video_id']}, Title: {v['title']}, URL: {v['url']}")
else:
    print("ytInitialData regex failed.")

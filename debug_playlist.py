"""Debug: Diagnose why YouTube playlist parsing fails."""
import json
import re
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLSqr4-dP7wJDARLGADNTbBn3H-2lgSoF4"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "CONSENT=YES+cb.20210328-17-p0.ko+FX+430",
}

resp = requests.get(PLAYLIST_URL, headers=headers, timeout=25, verify=False)
html = resp.text

print(f"Status: {resp.status_code}")
print(f"HTML length: {len(html)}")
print(f"Title tag: {re.search(r'<title>(.*?)</title>', html).group(1) if re.search(r'<title>(.*?)</title>', html) else 'N/A'}")

# Check what ytInitialData looks like
print(f"\n--- ytInitialData search ---")
print(f"'var ytInitialData' found: {'var ytInitialData' in html}")
print(f"'ytInitialData' found: {'ytInitialData' in html}")
print(f"'playlistVideoRenderer' count in raw HTML: {html.count('playlistVideoRenderer')}")
print(f"'videoId' count in raw HTML: {html.count('videoId')}")

# Try raw_decode approach
idx = html.find('ytInitialData')
if idx >= 0:
    print(f"\nytInitialData found at index {idx}")
    # Show context around it
    context = html[idx:idx+100]
    print(f"Context: {repr(context)}")
    
    # Find the opening brace
    start_brace = html.find('{', idx)
    print(f"First {{ after ytInitialData at index {start_brace}")
    
    try:
        decoder = json.JSONDecoder()
        data, end_idx = decoder.raw_decode(html, start_brace)
        print(f"JSON parsed successfully! Keys: {list(data.keys())[:10]}")
        
        # Save parsed JSON for inspection
        with open("debug_yt_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Saved full JSON to debug_yt_data.json")
        
        # Count playlistVideoRenderer in parsed JSON
        json_str = json.dumps(data)
        print(f"'playlistVideoRenderer' in parsed JSON: {json_str.count('playlistVideoRenderer')}")
        print(f"'videoId' in parsed JSON: {json_str.count('videoId')}")
        
    except Exception as e:
        print(f"raw_decode failed: {e}")
        # Try to show what character caused the issue
        snippet = html[start_brace:start_brace+200]
        print(f"Snippet at brace: {repr(snippet)}")
else:
    print("ytInitialData NOT found in HTML at all!")
    # Save first 5000 chars for inspection
    with open("debug_yt_html.txt", "w", encoding="utf-8") as f:
        f.write(html[:10000])
    print("Saved first 10000 chars to debug_yt_html.txt")

# Also check for all videoId patterns directly
vid_matches = re.findall(r'"videoId"\s*:\s*"([a-zA-Z0-9_-]{11})"', html)
unique_vids = list(dict.fromkeys(vid_matches))  # preserve order, remove dups
print(f"\nDirect videoId regex matches: {len(vid_matches)} total, {len(unique_vids)} unique")
if unique_vids:
    print("First 10 videoIds:")
    for vid in unique_vids[:10]:
        print(f"  {vid}")

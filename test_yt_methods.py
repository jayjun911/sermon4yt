import re
import xml.etree.ElementTree as ET
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PLAYLIST_ID = "PLSqr4-dP7wJDARLGADNTbBn3H-2lgSoF4"

print("=== Method 1: RSS Feed ===")
rss_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={PLAYLIST_ID}"
try:
    resp = requests.get(rss_url, timeout=15, verify=False)
    if resp.status_code == 200:
        root = ET.fromstring(resp.text)
        entries = root.findall("{http://www.w3.org/2005/Atom}entry")
        print(f"RSS entries found: {len(entries)}")
        for entry in entries[:5]:
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            yt_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
            print(f"  [{yt_id}] {title}")
    else:
        print(f"RSS Status code: {resp.status_code}")
except Exception as e:
    print(f"RSS error: {e}")

print("\n=== Method 2: Mobile User-Agent ===")
mobile_headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept-Language": "ko-KR,ko;q=0.9",
}
try:
    url = f"https://www.youtube.com/playlist?list={PLAYLIST_ID}"
    resp = requests.get(url, headers=mobile_headers, timeout=15, verify=False)
    vids = set(re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', resp.text))
    print(f"Mobile watch IDs found: {len(vids)}")
except Exception as e:
    print(f"Mobile error: {e}")

print("\n=== Method 3: Desktop Page ytInitialData / HTML ===")
desktop_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Cookie": "CONSENT=YES+1",
}
try:
    url = f"https://www.youtube.com/playlist?list={PLAYLIST_ID}"
    resp = requests.get(url, headers=desktop_headers, timeout=15, verify=False)
    html = resp.text
    print(f"Desktop HTML length: {len(html)}")
    
    # Check for ytInitialData
    m = re.search(r'ytInitialData\s*=\s*({.*?});</script>', html)
    if not m:
        m = re.search(r'window\["ytInitialData"\]\s*=\s*({.*?});', html)
    
    if m:
        print("Found ytInitialData pattern!")
        # count playlistVideoRenderer occurrences in raw text
        pvrs = re.findall(r'"playlistVideoRenderer":\s*({.*?}),"playlistVideoRenderer"', html)
        print(f"Raw playlistVideoRenderer count: {len(pvrs)}")
    else:
        print("ytInitialData pattern NOT matched in desktop html.")
except Exception as e:
    print(f"Desktop error: {e}")

print("\n=== Method 4: yt-dlp check ===")
try:
    import yt_dlp
    ydl_opts = {'extract_flat': True, 'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/playlist?list={PLAYLIST_ID}", download=False)
        entries = info.get('entries', [])
        print(f"yt-dlp found {len(entries)} entries!")
        for e in entries[:5]:
            print(f"  [{e.get('id')}] {e.get('title')}")
except ImportError:
    print("yt-dlp is not installed in current environment.")
except Exception as e:
    print(f"yt-dlp error: {e}")

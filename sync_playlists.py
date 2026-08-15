import argparse
import json
import os
import re
import sys
import urllib3
import requests

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERMONS_JSON_FILE = "./sermons.json"
PLAYLISTS_JSON_FILE = "./playlists.json"
PLAYLISTS_TXT_FILE = "./playlists.txt"

def extract_playlist_id(input_str: str) -> str:
    input_str = input_str.strip()
    if "list=" in input_str:
        m = re.search(r"list=([a-zA-Z0-9_-]+)", input_str)
        if m:
            return m.group(1)
    return input_str

def extract_videos_from_yt_json(data) -> list[dict]:
    """Recursively walk JSON tree to find all video items."""
    items = []
    seen = set()

    def walk(node):
        if isinstance(node, dict):
            # NEW format (2024+): lockupViewModel with contentId and lockupMetadataViewModel
            if "lockupViewModel" in node:
                lvm = node["lockupViewModel"]
                vid = lvm.get("contentId")
                content_type = lvm.get("contentType", "")
                if vid and "VIDEO" in content_type and vid not in seen:
                    title = ""
                    meta = lvm.get("metadata", {}).get("lockupMetadataViewModel", {})
                    title_obj = meta.get("title", {})
                    if isinstance(title_obj, dict):
                        title = title_obj.get("content", "")
                    
                    if title:
                        seen.add(vid)
                        items.append({
                            "video_id": vid,
                            "title": title.strip(),
                            "url": f"https://www.youtube.com/watch?v={vid}"
                        })
                for v in lvm.values():
                    if isinstance(v, (dict, list)):
                        walk(v)
            # LEGACY format: playlistVideoRenderer
            elif "playlistVideoRenderer" in node:
                pvr = node["playlistVideoRenderer"]
                vid = pvr.get("videoId")
                title_runs = pvr.get("title", {}).get("runs", [])
                vtitle = "".join(r.get("text", "") for r in title_runs).strip()
                if vid and vtitle and vid not in seen:
                    seen.add(vid)
                    items.append({
                        "video_id": vid,
                        "title": vtitle,
                        "url": f"https://www.youtube.com/watch?v={vid}"
                    })
            else:
                for v in node.values():
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return items

def fetch_playlist_info(playlist_input: str) -> dict:
    playlist_id = extract_playlist_id(playlist_input)
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"\n[Playlist] Fetching {playlist_url} ...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cookie": "CONSENT=YES+cb.20210328-17-p0.ko+FX+430",
    }

    try:
        resp = requests.get(playlist_url, headers=headers, timeout=25, verify=False)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"Error fetching playlist page: {e}")
        return None

    # 1. Extract Playlist Title
    playlist_title = ""
    og_title = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
    if og_title:
        playlist_title = og_title.group(1).strip()
    if not playlist_title:
        title_tag = re.search(r'<title>(.*?)</title>', html)
        if title_tag:
            playlist_title = title_tag.group(1).replace(" - YouTube", "").strip()
    if not playlist_title:
        playlist_title = f"재생목록 ({playlist_id})"

    # 2. Extract Videos from ytInitialData
    idx = html.find('ytInitialData')
    if idx == -1:
        print("Error: ytInitialData not found in page HTML.")
        return None

    start_brace = html.find('{', idx)
    if start_brace == -1:
        print("Error: No JSON object found after ytInitialData.")
        return None

    try:
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(html, start_brace)
    except Exception as e:
        print(f"Error: Failed to parse ytInitialData JSON: {e}")
        return None

    items = extract_videos_from_yt_json(data)
    print(f"  Title: {playlist_title}")
    print(f"  Found {len(items)} video(s).")

    return {
        "id": playlist_id,
        "title": playlist_title,
        "url": playlist_url,
        "video_count": len(items),
        "videos": items
    }

def clean_string(s: str) -> str:
    s = re.sub(r'[\s\(\)\-\_\[\]\:\,\.\~\!\?]', '', s)
    return s.lower()

def edit_distance(a: str, b: str) -> int:
    if len(a) < len(b):
        return edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,
                curr[j] + 1,
                prev[j] + (ca != cb)
            ))
        prev = curr
    return prev[-1]

def fuzzy_contains(needle: str, haystack: str, threshold: float = 0.8) -> float:
    n = len(needle)
    if n == 0:
        return 1.0
    if len(haystack) < n:
        needle, haystack = haystack, needle
        n = len(needle)
    
    best = 0.0
    for window_len in range(max(1, n - 2), n + 3):
        for i in range(len(haystack) - window_len + 1):
            chunk = haystack[i:i + window_len]
            dist = edit_distance(needle, chunk)
            sim = 1.0 - dist / max(len(needle), len(chunk))
            if sim > best:
                best = sim
                if best >= threshold:
                    return best
    return best

def match_video_to_sermons(video: dict, sermons: list[dict]) -> dict:
    """Matches a video to the best corresponding sermon entry in sermons.json."""
    v_title = video["title"]
    v_clean = clean_string(v_title)

    # Tier 1: Exact substring match (title in video title + date check)
    for e in sermons:
        e_title = e.get("title", "")
        e_title_clean = clean_string(e_title)
        e_date = e.get("date", "").strip()

        if not e_title_clean:
            continue

        if e_title_clean in v_clean:
            if not e_date or e_date.replace("-", "") in v_clean or e_date in v_title:
                return e

    # Tier 2: Fuzzy substring match (looser, no date check)
    for e in sermons:
        e_title = e.get("title", "")
        e_title_clean = clean_string(e_title)
        if len(e_title_clean) >= 3 and e_title_clean in v_clean:
            return e

    # Tier 3: Edit-distance similarity match
    best_sim = 0.0
    best_entry = None
    for e in sermons:
        e_title = e.get("title", "")
        e_title_clean = clean_string(e_title)
        if len(e_title_clean) < 3:
            continue
        sim = fuzzy_contains(e_title_clean, v_clean)
        if sim > best_sim:
            best_sim = sim
            best_entry = e
    if best_entry and best_sim >= 0.7:
        return best_entry

    return None

def load_playlist_sources() -> list[str]:
    """Reads playlist URLs/IDs from playlists.txt."""
    if not os.path.exists(PLAYLISTS_TXT_FILE):
        return []
    urls = []
    with open(PLAYLISTS_TXT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls

def sync_all(playlist_inputs: list[str] = None):
    if not playlist_inputs:
        playlist_inputs = load_playlist_sources()
    
    if not playlist_inputs:
        print(f"No playlist inputs provided and {PLAYLISTS_TXT_FILE} is empty.")
        return

    sermons = []
    if os.path.exists(SERMONS_JSON_FILE):
        with open(SERMONS_JSON_FILE, "r", encoding="utf-8") as f:
            sermons = json.load(f)

    for e in sermons:
        if "youtube_url" not in e:
            e["youtube_url"] = None

    playlists_data = []
    total_matched = 0
    total_videos = 0

    for pl_input in playlist_inputs:
        pl_info = fetch_playlist_info(pl_input)
        if not pl_info:
            continue

        enriched_videos = []
        for idx, video in enumerate(pl_info["videos"], start=1):
            total_videos += 1
            matched_sermon = match_video_to_sermons(video, sermons)
            
            video_entry = {
                "index": idx,
                "video_id": video["video_id"],
                "title": video["title"],
                "url": video["url"],
                "sermon_id": matched_sermon["id"] if matched_sermon else None,
                "sermon_title": matched_sermon.get("title") if matched_sermon else video["title"],
                "date": matched_sermon.get("date") if matched_sermon else None,
                "scripture": matched_sermon.get("scripture") if matched_sermon else None,
                "scripture_text": matched_sermon.get("scripture_text") if matched_sermon else None,
                "mp3_url": matched_sermon.get("url") if matched_sermon else None,
            }

            if matched_sermon:
                total_matched += 1
                matched_sermon["youtube_url"] = video["url"]

            enriched_videos.append(video_entry)

        pl_info["videos"] = enriched_videos
        playlists_data.append(pl_info)

    # Save playlists.json & playlists_data.js
    with open(PLAYLISTS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(playlists_data, f, ensure_ascii=False, indent=2)
    with open("./playlists_data.js", "w", encoding="utf-8") as f:
        f.write("window.PLAYLISTS_DATA = " + json.dumps(playlists_data, ensure_ascii=False) + ";\n")
    print(f"\nSaved {len(playlists_data)} playlist(s) to {PLAYLISTS_JSON_FILE} and playlists_data.js")

    # Save updated sermons.json & sermons_data.js
    if sermons:
        with open(SERMONS_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(sermons, f, ensure_ascii=False, indent=2)
        with open("./sermons_data.js", "w", encoding="utf-8") as f:
            f.write("window.SERMONS_DATA = " + json.dumps(sermons, ensure_ascii=False) + ";\n")
        print(f"Updated {SERMONS_JSON_FILE} and sermons_data.js with synced YouTube URLs.")


    print(f"\nFinished! Total {total_matched} / {total_videos} videos matched to sermon archive.")

def main():
    parser = argparse.ArgumentParser(description="Sync multiple YouTube playlists to playlists.json & sermons.json")
    parser.add_argument("playlists", nargs="*", help="Optional YouTube Playlist URLs or IDs")
    args = parser.parse_args()

    sync_all(args.playlists if args.playlists else None)

if __name__ == "__main__":
    main()

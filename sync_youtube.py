import argparse
import json
import os
import re
import urllib3
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_PLAYLIST_ID = "PLSqr4-dP7wJDARLGADNTbBn3H-2lgSoF4"
JSON_FILE = "./sermons.json"

def extract_playlist_id(input_str: str) -> str:
    input_str = input_str.strip()
    if "list=" in input_str:
        m = re.search(r"list=([a-zA-Z0-9_-]+)", input_str)
        if m:
            return m.group(1)
    return input_str

def extract_videos_from_yt_json(data) -> list[dict]:
    """Recursively walk JSON tree to find all video items.
    
    Supports both the new lockupViewModel format (2024+) and
    the legacy playlistVideoRenderer format.
    """
    items = []
    seen = set()

    def walk(node):
        if isinstance(node, dict):
            # NEW format (2024+): lockupViewModel with contentId and lockupMetadataViewModel
            if "lockupViewModel" in node:
                lvm = node["lockupViewModel"]
                vid = lvm.get("contentId")
                content_type = lvm.get("contentType", "")
                # Only process video type lockups
                if vid and "VIDEO" in content_type and vid not in seen:
                    # Extract title from metadata
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
                # Still recurse into children in case of nested items
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

def fetch_playlist_items(playlist_input: str) -> list[dict]:
    playlist_id = extract_playlist_id(playlist_input)
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Fetching playlist from {playlist_url} ...")

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
        return []

    # Parse ytInitialData using JSONDecoder.raw_decode (handles any JSON size)
    idx = html.find('ytInitialData')
    if idx == -1:
        print("Error: ytInitialData not found in page HTML.")
        return []

    start_brace = html.find('{', idx)
    if start_brace == -1:
        print("Error: No JSON object found after ytInitialData.")
        return []

    try:
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(html, start_brace)
    except Exception as e:
        print(f"Error: Failed to parse ytInitialData JSON: {e}")
        return []

    items = extract_videos_from_yt_json(data)
    print(f"Found {len(items)} video(s) in playlist (Public & Unlisted).")
    
    if items:
        print(f"  First: [{items[0]['video_id']}] {items[0]['title']}")
        print(f"  Last:  [{items[-1]['video_id']}] {items[-1]['title']}")

    return items

def clean_string(s: str) -> str:
    s = re.sub(r'[\s\(\)\-\_\[\]\:\,\.\~\!\?]', '', s)
    return s.lower()

def edit_distance(a: str, b: str) -> int:
    """Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        return edit_distance(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,      # deletion
                curr[j] + 1,           # insertion
                prev[j] + (ca != cb)   # substitution
            ))
        prev = curr
    return prev[-1]

def fuzzy_contains(needle: str, haystack: str, threshold: float = 0.8) -> float:
    """Check if needle approximately appears inside haystack using sliding window.
    Returns best similarity ratio (0.0~1.0). Handles typos like 후에/후예."""
    n = len(needle)
    if n == 0:
        return 1.0
    if len(haystack) < n:
        # try the reverse
        needle, haystack = haystack, needle
        n = len(needle)
    
    best = 0.0
    # Slide window of sizes [n-2 .. n+2] across haystack
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

def sync_sermons(playlist_input: str):
    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} not found.")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        sermons = json.load(f)

    playlist_videos = fetch_playlist_items(playlist_input)
    if not playlist_videos:
        print("Error: No videos found in playlist.")
        return

    matched_count = 0
    unmatched_videos = []

    for e in sermons:
        if "youtube_url" not in e:
            e["youtube_url"] = None

    for video in playlist_videos:
        v_title = video["title"]
        v_url = video["url"]
        v_clean = clean_string(v_title)

        matched = False

        # Tier 1: Exact substring match (title in video title + date check)
        for e in sermons:
            e_title = e.get("title", "")
            e_title_clean = clean_string(e_title)
            e_date = e.get("date", "").strip()

            if not e_title_clean:
                continue

            if e_title_clean in v_clean:
                if not e_date or e_date.replace("-", "") in v_clean or e_date in v_title:
                    e["youtube_url"] = v_url
                    matched_count += 1
                    matched = True
                    print(f"  [Match] #{e['id']} [{e.get('date')}] '{e_title}' -> {v_url}")
                    break

        # Tier 2: Fuzzy substring match (looser, no date check)
        if not matched:
            for e in sermons:
                e_title = e.get("title", "")
                e_title_clean = clean_string(e_title)
                if len(e_title_clean) >= 3 and e_title_clean in v_clean:
                    e["youtube_url"] = v_url
                    matched_count += 1
                    matched = True
                    print(f"  [Fuzzy] #{e['id']} [{e.get('date')}] '{e_title}' -> {v_url}")
                    break

        # Tier 3: Edit-distance similarity match (handles typos like 후에/후예)
        if not matched:
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
            # Accept if similarity >= 70%
            if best_entry and best_sim >= 0.7:
                best_entry["youtube_url"] = v_url
                matched_count += 1
                matched = True
                print(f"  [Typo~{best_sim:.0%}] #{best_entry['id']} [{best_entry.get('date')}] '{best_entry['title']}' -> {v_url}")

        if not matched:
            unmatched_videos.append(video)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, ensure_ascii=False, indent=2)

    print(f"\nMatched: {matched_count} / {len(playlist_videos)} video(s)")
    if unmatched_videos:
        print(f"Unmatched ({len(unmatched_videos)}):")
        for v in unmatched_videos:
            print(f"  [{v['video_id']}] {v['title']}")

def main():
    parser = argparse.ArgumentParser(description="Sync YouTube playlist videos to sermons.json youtube_url field")
    parser.add_argument("playlist", nargs="?", default=DEFAULT_PLAYLIST_ID, help="YouTube Playlist URL or Playlist ID")
    parser.add_argument("--playlist", "-p", dest="playlist_opt", help="YouTube Playlist URL or Playlist ID")
    args = parser.parse_args()

    target_playlist = args.playlist_opt or args.playlist
    sync_sermons(target_playlist)

if __name__ == "__main__":
    main()

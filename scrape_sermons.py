import os
import re
import json
import argparse
import urllib3
import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://shalomm.org/"
PAGE_URL = "https://shalomm.org/messages_kor.php"
OUTPUT_DIR = "./sermon"
JSON_FILE = "./sermons.json"

INVALID_CHARS = re.compile(r'[\\/*?:"<>|]')


def safe_filename(name: str) -> str:
    name = INVALID_CHARS.sub("", name)
    name = name.replace("~", "-").strip()
    return name


def make_session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    })
    return s


def parse_entries(soup: BeautifulSoup) -> list[dict]:
    entries = []
    seen_urls = set()

    for a in soup.find_all("a", href=re.compile(r"mp3/")):
        href = a["href"]
        title = a.get_text(strip=True)

        # Skip bare "mp3" duplicate download links
        if not title or title.strip().lower() == "mp3":
            continue

        # Deduplicate by URL
        if href in seen_urls:
            continue
        seen_urls.add(href)

        # Find scripture: search siblings/parent for "책이름 N : N" pattern
        scripture = ""
        parent = a.parent

        passed = False
        for child in parent.children:
            if child == a:
                passed = True
                continue
            if not passed:
                continue
            text = child.get_text(strip=True) if hasattr(child, "get_text") else str(child).strip()
            if re.search(r"[가-힣]+\s+\d+\s*[:：]", text) or re.search(r"\d+\s*[:：]\s*\d+", text):
                scripture = text
                break

        if not scripture:
            for sib in parent.next_siblings:
                text = sib.get_text(strip=True) if hasattr(sib, "get_text") else str(sib).strip()
                if re.search(r"[가-힣]+\s+\d+\s*[:：]", text) or re.search(r"\d+\s*[:：]\s*\d+", text):
                    scripture = text
                    break
                if text:
                    break

        # Find date from preceding <td>
        date = ""
        parent = a.parent
        if parent and parent.name == "td":
            prev_td = parent.find_previous_sibling("td")
            if prev_td:
                text = prev_td.get_text(strip=True)
                if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
                    date = text

        entries.append({
            "id": len(entries) + 1,
            "date": date,
            "title": title,
            "scripture": scripture,
            "url": BASE_URL + href,
        })

    return entries


def cmd_fetch(session: requests.Session) -> list[dict]:
    print(f"Fetching {PAGE_URL} ...")
    resp = session.get(PAGE_URL, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding

    soup = BeautifulSoup(resp.text, "html.parser")
    entries = parse_entries(soup)

    # Preserve existing youtube_url mapping if available
    yt_map = {}
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                old_entries = json.load(f)
                for item in old_entries:
                    if item.get("url") and item.get("youtube_url"):
                        yt_map[item["url"]] = item["youtube_url"]
        except Exception:
            pass

    for entry in entries:
        entry["youtube_url"] = yt_map.get(entry["url"], None)

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(entries)} entries -> {JSON_FILE}")
    return entries


def load_entries() -> list[dict]:
    if not os.path.exists(JSON_FILE):
        raise FileNotFoundError(f"{JSON_FILE} not found. Run --fetch first.")
    with open(JSON_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_spec(spec: str, total: int) -> list[int]:
    """'1,3,5-10,20-' -> sorted list of 1-based indices within [1, total].
    Trailing dash (N-) means N to end."""
    indices: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if re.match(r"^\d+-$", part):          # N- : open range to end
            indices.update(range(int(part[:-1]), total + 1))
        elif re.match(r"^\d+-\d+$", part):     # N-M : closed range
            lo, hi = part.split("-", 1)
            indices.update(range(int(lo), int(hi) + 1))
        elif re.match(r"^\d+$", part):          # N : single
            indices.add(int(part))
    return sorted(i for i in indices if 1 <= i <= total)


def is_search_query(spec: str) -> bool:
    """True if spec looks like a keyword search rather than a number/range spec."""
    return not re.match(r"^[\d\s,\-]+$", spec.strip())


def format_scripture(raw: str) -> str:
    """'에베소서 4 : 1 ~ 6'  ->  '에베소서 4장 1-6절'"""
    raw = raw.strip()
    # book chapter : verse ~ verse
    m = re.match(r"^([가-힣\s]+?)\s+(\d+)\s*[:：]\s*(\d+)\s*[~～\-]\s*(\d+)", raw)
    if m:
        book, ch, v1, v2 = m.group(1).strip(), m.group(2), m.group(3), m.group(4)
        return f"{book} {int(ch):02d}장 {v1}-{v2}절"
    # book chapter : verse  (single verse)
    m = re.match(r"^([가-힣\s]+?)\s+(\d+)\s*[:：]\s*(\d+)", raw)
    if m:
        book, ch, v = m.group(1).strip(), m.group(2), m.group(3)
        return f"{book} {int(ch):02d}장 {v}절"
    # book chapter only
    m = re.match(r"^([가-힣\s]+?)\s+(\d+)", raw)
    if m:
        book, ch = m.group(1).strip(), m.group(2)
        return f"{book} {int(ch):02d}장"
    return raw


def entry_filepath(entry: dict) -> str:
    title = safe_filename(entry["title"])
    scripture = safe_filename(format_scripture(entry["scripture"]))
    date = safe_filename(entry.get("date", "").strip())

    parts = [title]
    if scripture:
        parts.append(f"({scripture})")
    if date:
        parts.append(date)

    filename = f"{' '.join(parts)}.mp3"
    return os.path.join(OUTPUT_DIR, filename)


def print_entries(entries: list[dict]):
    for e in entries:
        flag = "O" if os.path.exists(entry_filepath(e)) else " "
        date_str = f"[{e['date']}] " if e.get("date") else ""
        print(f"[{e['id']:4d}][{flag}] {date_str}{e['title']}  |  {e['scripture']}")


def download_entry(entry: dict, session: requests.Session):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = entry_filepath(entry)
    filename = os.path.basename(filepath)

    if os.path.exists(filepath):
        print(f"  [skip] {filename}")
        return

    print(f"  [down] {filename}")
    try:
        r = session.get(entry["url"], stream=True, timeout=60)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
    except Exception as e:
        print(f"  [err ] {filename}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Sermon metadata & downloader for shalomm.org",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch/refresh sermon list from website -> sermons.json")
    parser.add_argument("--list", metavar="RANGE",
                        help="List entries  e.g. --list 1-20  or  --list 1,5,10-15")
    parser.add_argument("--search", metavar="QUERY",
                        help="Search by title or scripture  e.g. --search 창세기")
    parser.add_argument("--down", metavar="SPEC", nargs="?", const="SEARCH_RESULTS",
                        help="Download entries  e.g. --down 1,3,5-10  or  --search QUERY --down")
    args = parser.parse_args()

    session = make_session()

    # Auto-fetch if JSON missing
    if args.fetch or not os.path.exists(JSON_FILE):
        entries = cmd_fetch(session)
    else:
        entries = load_entries()

    total = len(entries)

    if args.list:
        indices = parse_spec(args.list, total)
        print_entries([entries[i - 1] for i in indices])
        return

    if args.search:
        q = args.search.lower()
        results = [e for e in entries if q in e["title"].lower() or q in e["scripture"].lower() or q in e.get("date", "").lower()]
        print(f"Found {len(results)} result(s) for '{args.search}':")
        print_entries(results)

        if args.down is not None:
            if args.down == "SEARCH_RESULTS":
                targets = results
            elif is_search_query(args.down):
                sub_q = args.down.lower()
                targets = [e for e in results if sub_q in e["title"].lower() or sub_q in e["scripture"].lower()]
            else:
                indices = parse_spec(args.down, len(results))
                targets = [results[i - 1] for i in indices]

            if not targets:
                print("No entries selected for download.")
                return

            print(f"\nDownloading {len(targets)} sermon(s)...")
            for i, entry in enumerate(targets, 1):
                print(f"[{i}/{len(targets)}]", end=" ")
                download_entry(entry, session)
        return

    if args.down is not None:
        if args.down == "SEARCH_RESULTS":
            print("Error: --down requires a range/keyword (e.g. --down 1-10 or --down 창세기) unless used with --search.")
            return

        if is_search_query(args.down):
            q = args.down.lower()
            targets = [e for e in entries if q in e["title"].lower() or q in e["scripture"].lower()]
            print(f"Downloading {len(targets)} result(s) for '{args.down}':")
        else:
            indices = parse_spec(args.down, total)
            targets = [entries[i - 1] for i in indices]

        for i, entry in enumerate(targets, 1):
            print(f"[{i}/{len(targets)}]", end=" ")
            download_entry(entry, session)
        return

    if not args.fetch:
        print(f"Total: {total} sermons  ({JSON_FILE})")
        print()
        print("Options:")
        print("  --fetch              refresh list from website")
        print("  --list 1-20          show entries 1-20")
        print("  --list 100-          show entries 100 to end")
        print("  --search 창세기       search title / scripture")
        print("  --search 창세기 --down search & download matching entries")
        print("  --down 1,3,5-10      download by number/range")
        print("  --down 창세기         download all matching entries")


if __name__ == "__main__":
    main()

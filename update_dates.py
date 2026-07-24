import json
import re
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://shalomm.org/"
PAGE_URL = "https://shalomm.org/messages_kor.php"
JSON_FILE = "./sermons.json"

def main():
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    })
    
    print(f"Fetching {PAGE_URL} ...")
    resp = s.get(PAGE_URL, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    entries = []
    seen_urls = set()
    
    for a in soup.find_all("a", href=re.compile(r"mp3/")):
        href = a["href"]
        title = a.get_text(strip=True)

        if not title or title.strip().lower() == "mp3":
            continue

        if href in seen_urls:
            continue
        seen_urls.add(href)

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

        date = ""
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

    print(f"Parsed {len(entries)} entries with date schema.")
    
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Successfully updated {JSON_FILE}!")

if __name__ == "__main__":
    main()

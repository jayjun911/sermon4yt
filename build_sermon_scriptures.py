import json
import re
from pathlib import Path

BIBLE_FILE = r"./개역개정4판(구약+신약).txt"
SERMONS_FILE = r"./sermons.json"

KOR_TO_ABBREV = {
    "창세기": "창", "출애굽기": "출", "레위기": "레",
    "민수기": "민", "신명기": "신", "여호수아": "수",
    "사사기": "삿", "룻기": "룻", "사무엘상": "삼상",
    "사무엘하": "삼하", "열왕기상": "왕상", "열왕기하": "왕하",
    "역대상": "대상", "역대하": "대하", "에스라": "스",
    "느헤미야": "느", "느헤미아서": "느", "에스더": "에", "욥기": "욥",
    "시편": "시", "사편": "시", "시편편": "시", "잠언": "잠", "전도서": "전",
    "아가": "아", "이사야": "사", "아사야서": "사", "이사야서": "사", "예레미야": "렘",
    "예레미야애가": "애", "에스겔": "겔", "다니엘": "단",
    "호세아": "호", "요엘": "욜", "아모스": "암",
    "오바댜": "옵", "오바디야": "옵", "요나": "욘", "미가": "미",
    "나훔": "나", "하박국": "합", "스바냐": "습",
    "학개": "학", "스가랴": "슥", "스카리야": "슥", "말라기": "말",
    "마태복음": "마", "미태복음": "마", "마태복은": "마", "마가복음": "막", "누가복음": "눅",
    "요한복음": "요", "사도행전": "행", "로마서": "롬",
    "고린도전서": "고전", "고린고전서": "고전", "고린도후서": "고후",
    "갈라디아서": "갈", "갈리디아서": "갈", "에베소서": "엡", "예베소서": "엡", "빌립보서": "빌", "발랍보서": "빌", "빌보서": "빌",
    "골로새서": "골",
    "데살로니가전서": "살전", "데살로니가후서": "살후",
    "디모데전서": "딤전", "디모데후서": "딤후",
    "디도서": "딛", "빌레몬서": "몬", "히브리서": "히",
    "야고보서": "약",
    "베드로전서": "벧전", "베드로후서": "벧후",
    "요한일서": "요일", "요한1서": "요일", "요한이서": "요이", "요한2서": "요이",
    "요한삼서": "요삼", "요한3서": "요삼", "유다서": "유", "요한계시록": "계"
}

def load_bible_db(path: str) -> dict:
    db = {}
    text = ""
    for enc in ("cp949", "euc-kr", "utf-8"):
        try:
            text = Path(path).read_text(encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if not text:
        print("Failed to read Bible file!")
        return db

    pattern = re.compile(r"^([가-힣]+)(\d+):(\d+)\s+(.*)")
    for line in text.splitlines():
        line = line.strip()
        m = pattern.match(line)
        if not m:
            continue
        abbrev, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
        verse_text = re.sub(r"<[^>]+>", "", m.group(4)).strip()
        if verse_text:
            db.setdefault(abbrev, {}).setdefault(ch, {})[v] = verse_text

    total = sum(len(vv) for bk in db.values() for vv in bk.values())
    print(f"Loaded {total} verses across {len(db)} books from {path}")
    return db

def clean_scripture_str(s: str) -> str:
    if not s:
        return ""
    s = s.replace("`", "").replace("’", "").replace("'", "")
    s = s.replace("!", "1")
    s = re.sub(r":\s*:", ":", s)
    s = re.sub(r"([0-9]+)\s*편", r"\1장", s)
    s = re.sub(r"([0-9]+)\s*a\b", r"\1", s, flags=re.IGNORECASE)
    s = re.sub(r"([0-9]+)\s*b\b", r"\1", s, flags=re.IGNORECASE)
    return s.strip()

def parse_scripture_ranges(scripture_str: str, bible_db: dict) -> list[str]:
    s = clean_scripture_str(scripture_str)
    if not s:
        return []

    m_book = re.match(r"^([가-힣\s]+(?:1서|2서|3서|전서|후서)?)\s*(\d.*)$", s)
    if not m_book:
        m_book = re.match(r"^([가-힣\s0-9]+?)\s+(\d.*)$", s)

    if not m_book:
        norm_book = re.sub(r"\s+", "", s)
        abbrev = KOR_TO_ABBREV.get(norm_book)
        if abbrev and abbrev in bible_db:
            lines = []
            for ch in sorted(bible_db[abbrev].keys()):
                for v in sorted(bible_db[abbrev][ch].keys()):
                    lines.append(f"{ch}장 {v}절  {bible_db[abbrev][ch][v]}")
            return lines
        return []

    raw_book = m_book.group(1)
    rest = m_book.group(2).strip()

    norm_book = re.sub(r"\s+", "", raw_book)
    abbrev = KOR_TO_ABBREV.get(norm_book)

    if not abbrev:
        for k, v in KOR_TO_ABBREV.items():
            if k in norm_book or norm_book in k:
                abbrev = v
                break

    # Handle specific typo: 2 Corinthians 16 -> 1 Corinthians 16
    if abbrev == "고후" and rest.startswith("16"):
        abbrev = "고전"

    if not abbrev or abbrev not in bible_db:
        return []

    book_db = bible_db[abbrev]
    lines = []

    m_cross = re.match(r"^(\d+)\s*[:장]\s*(\d+)\s*[~\-–]\s*(\d+)\s*[:장]\s*(\d+)$", rest)
    if m_cross:
        c1, v1, c2, v2 = map(int, m_cross.groups())
        for c in range(c1, c2 + 1):
            if c in book_db:
                c_verses = book_db[c]
                start_v = v1 if c == c1 else 1
                end_v = v2 if c == c2 else max(c_verses.keys())
                for v in range(start_v, end_v + 1):
                    if v in c_verses:
                        lines.append(f"{c}장 {v}절  {c_verses[v]}")
        return lines

    m_range = re.match(r"^(\d+)\s*[:장]\s*(\d+)(?:\s*[~\-–]\s*(\d+))?$", rest)
    if m_range:
        ch = int(m_range.group(1))
        v1 = int(m_range.group(2))
        v2 = int(m_range.group(3)) if m_range.group(3) else v1
        if ch in book_db:
            c_verses = book_db[ch]
            max_v = max(c_verses.keys())
            start_v = min(v1, max_v)
            end_v = min(v2, max_v)
            for v in range(start_v, end_v + 1):
                if v in c_verses:
                    lines.append(f"{v}절  {c_verses[v]}")
        return lines

    m_comma = re.match(r"^(\d+)\s*[:장]\s*([\d\s\,\.]+)", rest)
    if m_comma:
        ch = int(m_comma.group(1))
        v_str = m_comma.group(2)
        v_nums = [int(n) for n in re.findall(r"\d+", v_str)]
        if ch in book_db:
            c_verses = book_db[ch]
            for v in v_nums:
                if v in c_verses:
                    lines.append(f"{v}절  {c_verses[v]}")
        return lines

    m_chap = re.match(r"^(\d+)장?$", rest)
    if m_chap:
        ch = int(m_chap.group(1))
        if ch in book_db:
            c_verses = book_db[ch]
            for v in sorted(c_verses.keys()):
                lines.append(f"{v}절  {c_verses[v]}")
        return lines

    return lines

def main():
    bible_db = load_bible_db(BIBLE_FILE)
    if not bible_db:
        return

    with open(SERMONS_FILE, "r", encoding="utf-8") as f:
        sermons = json.load(f)

    matched_count = 0
    empty_scripture_count = 0
    unmatched_list = []

    for e in sermons:
        scripture = e.get("scripture", "").strip()
        if not scripture:
            e["scripture_text"] = None
            empty_scripture_count += 1
            continue

        lines = parse_scripture_ranges(scripture, bible_db)
        if lines:
            e["scripture_text"] = "\n".join(lines)
            matched_count += 1
        else:
            e["scripture_text"] = None
            unmatched_list.append(e)

    with open(SERMONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sermons, f, ensure_ascii=False, indent=2)

    total_valid_sermons = len(sermons) - empty_scripture_count
    print(f"\n==========================================")
    print(f"Total sermons in JSON: {len(sermons)}")
    print(f"Sermons without scripture field: {empty_scripture_count}")
    print(f"Successfully matched: {matched_count} / {total_valid_sermons} valid scripture sermons!")
    print(f"Overall Coverage: {matched_count / total_valid_sermons * 100:.1f}%")
    print(f"==========================================")

    if unmatched_list:
        print(f"\nRemaining unmatched ({len(unmatched_list)}):")
        for u in unmatched_list:
            print(f"  #{u['id']} [{u.get('date')}] '{u['title']}' | scripture: '{u['scripture']}'")

if __name__ == "__main__":
    main()

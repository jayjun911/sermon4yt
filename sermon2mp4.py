import os
import re
import subprocess
import argparse
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

INPUT_DIR  = "./sermon"
OUTPUT_DIR = "./ytube"
BIBLE_DB   = r"./개역개정4판(구약+신약).txt"
WIDTH, HEIGHT = 1920, 1080

_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgunbd.ttf",
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\gulim.ttc",
]

BG_COLOR         = (18, 28, 55)
COLOR_BOOK_CH    = (255, 215, 100)
COLOR_VERSES     = (255, 200,  60)
COLOR_TITLE      = (240, 240, 240)
COLOR_LINE       = (100, 140, 210)
COLOR_VERSE_TEXT = (210, 222, 235)

# Full Korean book name → abbreviation used in 개역개정 txt file
KOR_TO_ABBREV = {
    "창세기": "창", "출애굽기": "출", "레위기": "레",
    "민수기": "민", "신명기": "신", "여호수아": "수",
    "사사기": "삿", "룻기": "룻", "사무엘상": "삼상",
    "사무엘하": "삼하", "열왕기상": "왕상", "열왕기하": "왕하",
    "역대상": "대상", "역대하": "대하", "에스라": "스",
    "느헤미야": "느", "에스더": "에", "욥기": "욥",
    "시편": "시", "잠언": "잠", "전도서": "전",
    "아가": "아", "이사야": "사", "예레미야": "렘",
    "예레미야애가": "애", "에스겔": "겔", "다니엘": "단",
    "호세아": "호", "요엘": "욜", "아모스": "암",
    "오바댜": "옵", "요나": "욘", "미가": "미",
    "나훔": "나", "하박국": "합", "스바냐": "습",
    "학개": "학", "스가랴": "슥", "말라기": "말",
    "마태복음": "마", "마가복음": "막", "누가복음": "눅",
    "요한복음": "요", "사도행전": "행", "로마서": "롬",
    "고린도전서": "고전", "고린도 전서": "고전",
    "고린도후서": "고후", "고린도 후서": "고후",
    "갈라디아서": "갈", "에베소서": "엡", "빌립보서": "빌",
    "골로새서": "골",
    "데살로니가전서": "살전", "데살로니가 전서": "살전",
    "데살로니가후서": "살후", "데살로니가 후서": "살후",
    "디모데전서": "딤전", "디모데 전서": "딤전",
    "디모데후서": "딤후", "디모데 후서": "딤후",
    "디도서": "딛", "빌레몬서": "몬", "히브리서": "히",
    "야고보서": "약",
    "베드로전서": "벧전", "베드로 전서": "벧전",
    "베드로후서": "벧후", "베드로 후서": "벧후",
    "요한일서": "요일", "요한이서": "요이", "요한삼서": "요삼",
    "유다서": "유", "요한계시록": "계",
}


# ── Bible DB ───────────────────────────────────────────────────────────────────

def load_bible_db(path: str) -> dict:
    """Parse 개역개정 txt → {abbrev: {chapter: {verse: text}}}"""
    db: dict = {}
    for enc in ("cp949", "euc-kr", "utf-8"):
        try:
            text = Path(path).read_text(encoding=enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        print(f"[err] Cannot decode {path}")
        return db

    pattern = re.compile(r"^([가-힣]+)(\d+):(\d+)\s+(.*)")
    for line in text.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        abbrev, ch, v = m.group(1), int(m.group(2)), int(m.group(3))
        verse_text = re.sub(r"<[^>]+>", "", m.group(4)).strip()
        if verse_text:
            db.setdefault(abbrev, {}).setdefault(ch, {})[v] = verse_text

    total = sum(len(vv) for bk in db.values() for vv in bk.values())
    print(f"  [bible] Loaded {total} verses from {Path(path).name}")
    return db


def get_bible_passage(db: dict, book_kor: str, chapter: int,
                      v_start: int, v_end: int) -> str:
    abbrev = KOR_TO_ABBREV.get(book_kor)
    if not abbrev:
        return ""
    ch_data = db.get(abbrev, {}).get(chapter, {})
    lines = [f"{v} {ch_data[v]}" for v in range(v_start, v_end + 1) if v in ch_data]
    return "\n".join(lines)


# ── Fonts ──────────────────────────────────────────────────────────────────────

def find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


# ── Text helpers ───────────────────────────────────────────────────────────────

def shadow_text(draw: ImageDraw.ImageDraw, xy: tuple, text: str,
                font: ImageFont.FreeTypeFont, fill: tuple, offset: int = 2):
    x, y = xy
    draw.text((x + offset, y + offset), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(draw: ImageDraw.ImageDraw, text: str,
              font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    lines, cur = [], ""
    for ch in text:
        trial = cur + ch
        if draw.textlength(trial, font=font) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def text_h(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


# ── Filename parsing ───────────────────────────────────────────────────────────

def parse_filename(stem: str) -> tuple[str, str, str]:
    """
    '창세기 02장 1-14절 - 생기를 받아 생령이 된 사람'
    -> ("창세기 02장", "1-14절", "생기를 받아 생령이 된 사람")
    """
    parts = stem.split(" - ", 1)
    title = parts[1].strip() if len(parts) > 1 else ""
    scripture = parts[0].strip()
    m = re.match(r"^(.*\d+장)\s*(.+)?$", scripture)
    if m:
        return m.group(1).strip(), (m.group(2) or "").strip(), title
    return scripture, "", title


def parse_scripture_ref(book_ch: str, verses_str: str) -> tuple[str, int, int, int]:
    """("창세기 02장", "1-14절") -> ("창세기", 2, 1, 14)"""
    m = re.match(r"^(.*?)\s+(\d+)장$", book_ch)
    if not m:
        return "", 0, 0, 0
    book_kor = m.group(1).strip()
    chapter  = int(m.group(2))
    vm = re.match(r"(\d+)[-~](\d+)절", verses_str)
    if vm:
        return book_kor, chapter, int(vm.group(1)), int(vm.group(2))
    vm = re.match(r"(\d+)절", verses_str)
    if vm:
        v = int(vm.group(1))
        return book_kor, chapter, v, v
    return book_kor, chapter, 0, 0


# ── Frame rendering ────────────────────────────────────────────────────────────

def make_frame(book_ch: str, verses_str: str, title: str,
               bg_path: str | None, bible_text: str) -> Image.Image:
    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)
        overlay = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        img = Image.blend(img, overlay, alpha=0.52)
    else:
        img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
        draw_bg = ImageDraw.Draw(img)
        for y in range(HEIGHT):
            t = y / HEIGHT
            fade = max(0.0, 1 - abs(t - 0.5) * 1.8)
            r = min(255, int(BG_COLOR[0] + 32 * fade))
            g = min(255, int(BG_COLOR[1] + 44 * fade))
            b = min(255, int(BG_COLOR[2] + 65 * fade))
            draw_bg.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(img)
    max_w = int(WIDTH * 0.82)

    font_big   = find_font(90)
    font_med   = find_font(54)
    font_title = find_font(58)
    font_verse = find_font(38)

    y = 80

    # Row 1: "창세기 2장" (big gold) + "1-14절" (smaller gold, baseline-aligned)
    bw = int(draw.textlength(book_ch, font=font_big))
    bh = text_h(draw, book_ch, font=font_big)
    mw = int(draw.textlength(" " + verses_str, font=font_med)) if verses_str else 0
    mh = text_h(draw, " " + verses_str, font=font_med) if verses_str else 0

    x = (WIDTH - bw - mw) // 2
    shadow_text(draw, (x, y), book_ch, font_big, COLOR_BOOK_CH)
    if verses_str:
        shadow_text(draw, (x + bw, y + bh - mh), " " + verses_str, font_med, COLOR_VERSES)
    y += bh + 16

    # Row 2: Sermon title (white, centered)
    for line in (wrap_text(draw, title, font_title, max_w) if title else []):
        lw = int(draw.textlength(line, font=font_title))
        shadow_text(draw, ((WIDTH - lw) // 2, y), line, font_title, COLOR_TITLE)
        y += text_h(draw, line, font_title) + 8
    y += 12

    # Divider
    cx = WIDTH // 2
    draw.line([(cx - 340, y), (cx + 340, y)], fill=COLOR_LINE, width=2)
    y += 36

    # Bible verse text — all verses joined, left-justified
    if bible_text:
        full_text = " ".join(ln.strip() for ln in bible_text.splitlines() if ln.strip())
        
        # Dynamically adjust font size to fit the remaining space (HEIGHT - 56)
        min_font_size = 18
        max_font_size = 38
        best_font_size = max_font_size
        for size in range(max_font_size, min_font_size - 1, -2):
            test_font = find_font(size)
            test_lines = wrap_text(draw, full_text, test_font, max_w)
            total_h = sum(text_h(draw, wline, test_font) + 6 for wline in test_lines)
            if total_h > 0:
                total_h -= 6
            if y + total_h <= HEIGHT - 56:
                best_font_size = size
                break
        else:
            best_font_size = min_font_size

        font_verse = find_font(best_font_size)
        x_left = (WIDTH - max_w) // 2
        for wline in wrap_text(draw, full_text, font_verse, max_w):
            if y > HEIGHT - 56:
                break
            shadow_text(draw, (x_left, y), wline, font_verse, COLOR_VERSE_TEXT)
            y += text_h(draw, wline, font_verse) + 6

    return img


# ── Conversion ─────────────────────────────────────────────────────────────────

def convert(mp3: Path, mp4: Path, bg_path: str | None, bible_db: dict):
    book_ch, verses_str, title = parse_filename(mp3.stem)
    bible_text = ""
    if bible_db:
        book_kor, chapter, v_start, v_end = parse_scripture_ref(book_ch, verses_str)
        if book_kor and v_start:
            bible_text = get_bible_passage(bible_db, book_kor, chapter, v_start, v_end)
            if not bible_text:
                print(f"  [warn] No verses found for {book_kor} {chapter}:{v_start}-{v_end}")

    img = make_frame(book_ch, verses_str, title, bg_path, bible_text)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        img.save(tmp_path, "PNG")
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "1",
            "-i", tmp_path,
            "-i", str(mp3),
            "-c:v", "libx264", "-preset", "slow", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(mp4),
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.decode(errors="replace")[-300:])
    finally:
        os.unlink(tmp_path)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Convert sermon MP3s to YouTube MP4s")
    parser.add_argument("--input",     default=INPUT_DIR, help="MP3 source directory")
    parser.add_argument("--bg",        metavar="IMAGE",   help="Background image (optional)")
    parser.add_argument("--filter",    metavar="QUERY",   help="Exact filename or keyword")
    parser.add_argument("--no-bible",  action="store_true", help="Skip Bible text overlay")
    parser.add_argument("--preview",   action="store_true", help="Save PNG only (no ffmpeg)")
    parser.add_argument("--force",     action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    bible_db = {}
    if not args.no_bible:
        print(f"Loading Bible DB ...")
        bible_db = load_bible_db(BIBLE_DB)

    in_dir  = Path(args.input)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    mp3s = sorted(in_dir.glob("*.mp3"))
    if args.filter:
        if args.filter.lower().endswith(".mp3"):
            target = Path(args.filter).name
            mp3s = [f for f in mp3s if f.name == target]
        else:
            q = args.filter.lower()
            mp3s = [f for f in mp3s if q in f.name.lower()]

    total = len(mp3s)
    print(f"Found {total} MP3 file(s)")

    for i, mp3 in enumerate(mp3s, 1):
        if args.preview:
            out_path = out_dir / (mp3.stem + ".png")
            if out_path.exists() and not args.force:
                print(f"[{i}/{total}] [skip] {out_path.name}")
                continue
            print(f"[{i}/{total}] [prev] {mp3.name}")
            try:
                book_ch, verses_str, title = parse_filename(mp3.stem)
                bible_text = ""
                if bible_db:
                    book_kor, chapter, v_start, v_end = parse_scripture_ref(book_ch, verses_str)
                    if book_kor and v_start:
                        bible_text = get_bible_passage(bible_db, book_kor, chapter, v_start, v_end)
                img = make_frame(book_ch, verses_str, title, args.bg, bible_text)
                img.save(out_path, "PNG")
                print(f"  [saved] {out_path}")
            except Exception as e:
                print(f"  [err ] {e}")
        else:
            mp4 = out_dir / (mp3.stem + ".mp4")
            if mp4.exists() and not args.force:
                print(f"[{i}/{total}] [skip] {mp3.name}")
                continue
            print(f"[{i}/{total}] [conv] {mp3.name}")
            try:
                convert(mp3, mp4, args.bg, bible_db)
            except Exception as e:
                print(f"  [err ] {e}")

    print("Done.")


if __name__ == "__main__":
    main()

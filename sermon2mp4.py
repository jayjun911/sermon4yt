import os
import sys
import re
import subprocess
import argparse
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

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

def parse_filename(stem: str) -> tuple[str, str, str, str]:
    """
    Parse sermon filename into (book_ch, verses_str, title, normalized_stem).
    Rules:
      - '시편' uses '편' instead of '장' (e.g. 시편 132장 -> 시편 132편). Other books use '장'.
      - Dates are wrapped in square brackets: e.g. 2010-05-27 -> [2010-05-27].
      - Standard normalized stem format: "{title} ({scripture}) [{date}]"
    Examples:
      '영원한 하나님의 약속 (시편 132장 10-18절) 2010-05-27'
      -> book_ch: '시편 132편'
         verses_str: '10-18절'
         title: '영원한 하나님의 약속'
         normalized_stem: '영원한 하나님의 약속 (시편 132편 10-18절) [2010-05-27]'
    """
    stem = stem.strip()
    date_str = ""
    title = ""
    raw_scripture = ""

    # 1. New format: Title (Scripture) [Date]
    m = re.match(r"^(.*?)\s*\(([^)]+)\)(?:\s*[\[(]?(\d{4}[-./]\d{2}[-./]\d{2})[\])]?)?\s*$", stem)
    if m:
        title = m.group(1).strip()
        raw_scripture = m.group(2).strip()
        date_str = m.group(3) or ""
    else:
        # 2. Old format: Scripture - Title [Date]
        parts = stem.split(" - ", 1)
        if len(parts) > 1:
            raw_scripture = parts[0].strip()
            title_part = parts[1].strip()
            dm = re.search(r"[\[(]?(\d{4}[-./]\d{2}[-./]\d{2})[\])]?\s*$", title_part)
            if dm:
                date_str = dm.group(1)
                title = title_part[:dm.start()].strip()
            else:
                title = title_part
        else:
            raw_scripture = stem

    # Extract book/chapter and verses from raw_scripture
    sm = re.match(r"^(.*?\d+\s*[장편])\s*(.+)?$", raw_scripture)
    if sm:
        raw_book_ch = sm.group(1).strip()
        verses_str = (sm.group(2) or "").strip()
    else:
        raw_book_ch = raw_scripture
        verses_str = ""

    # Parse book name, chapter number, unit (장 or 편)
    bm = re.match(r"^(.*?)\s*(\d+)\s*([장편])$", raw_book_ch)
    if bm:
        book_kor = bm.group(1).strip()
        chapter = int(bm.group(2))
        unit = "편" if book_kor == "시편" else "장"
        book_ch = f"{book_kor} {chapter}{unit}"
    else:
        book_kor = ""
        chapter = 0
        unit = "장"
        book_ch = raw_book_ch

    # Standard scripture format
    if book_ch:
        scripture_part = f"{book_ch} {verses_str}".strip() if verses_str else book_ch
    else:
        scripture_part = raw_scripture

    formatted_date = f"[{date_str.replace('.', '-').replace('/', '-')}]" if date_str else ""

    if title and scripture_part:
        if formatted_date:
            normalized_stem = f"{title} ({scripture_part}) {formatted_date}"
        else:
            normalized_stem = f"{title} ({scripture_part})"
    elif title:
        normalized_stem = f"{title} {formatted_date}".strip() if formatted_date else title
    elif scripture_part:
        normalized_stem = f"{scripture_part} {formatted_date}".strip() if formatted_date else scripture_part
    else:
        normalized_stem = stem

    return book_ch, verses_str, title, normalized_stem


def parse_scripture_ref(book_ch: str, verses_str: str) -> tuple[str, int, int, int]:
    """("창세기 02장", "1-14절") -> ("창세기", 2, 1, 14)"""
    m = re.match(r"^(.*?)\s*(\d+)[장편]$", book_ch)
    if not m:
        return "", 0, 0, 0
    book_kor = m.group(1).strip()
    chapter  = int(m.group(2))
    vm = re.match(r"(\d+)[-~](\d+)(?:절)?", verses_str)
    if vm:
        return book_kor, chapter, int(vm.group(1)), int(vm.group(2))
    vm = re.match(r"(\d+)(?:절)?", verses_str)
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

    # Row 1: "창세기 2장" / "시편 132편" (big gold) + "10-18절" (smaller gold, baseline-aligned)
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
        
        # Dynamically adjust font size to fit the remaining space
        min_font_size = 18
        max_font_size = 72
        best_font_size = max_font_size
        line_spacing = 10
        
        for size in range(max_font_size, min_font_size - 1, -2):
            test_font = find_font(size)
            test_lines = wrap_text(draw, full_text, test_font, max_w)
            spacing = int(size * 0.4)
            total_h = sum(text_h(draw, wline, test_font) + spacing for wline in test_lines)
            if total_h > 0:
                total_h -= spacing
            
            if y + total_h <= HEIGHT - 140:  # 아랫단 여유 공간(마진)을 140으로 늘림
                best_font_size = size
                line_spacing = spacing
                break
        else:
            best_font_size = min_font_size
            line_spacing = int(min_font_size * 0.4)

        font_verse = find_font(best_font_size)
        final_lines = wrap_text(draw, full_text, font_verse, max_w)
        total_h = sum(text_h(draw, wline, font_verse) + line_spacing for wline in final_lines)
        if total_h > 0:
            total_h -= line_spacing
        
        # Vertically center in the remaining space, shifted up slightly for bottom margin
        remaining_space = HEIGHT - y - 100
        start_y = y + max(0, (remaining_space - total_h) // 2)
        
        y_text = start_y
        x_left = (WIDTH - max_w) // 2
        for wline in final_lines:
            if y_text > HEIGHT - 80:
                break
            shadow_text(draw, (x_left, y_text), wline, font_verse, COLOR_VERSE_TEXT)
            y_text += text_h(draw, wline, font_verse) + line_spacing

    return img


# ── Conversion ─────────────────────────────────────────────────────────────────

def convert(mp3: Path, mp4: Path, bg_path: str | None, bible_db: dict):
    book_ch, verses_str, title, _ = parse_filename(mp3.stem)
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
            imageio_ffmpeg.get_ffmpeg_exe(), "-y",
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
    parser.add_argument("--input",        default=INPUT_DIR, help="MP3 source directory or file")
    parser.add_argument("--bg",           metavar="IMAGE",   help="Background image (optional)")
    parser.add_argument("--filter",       metavar="QUERY",   help="Exact filename or keyword")
    parser.add_argument("--no-bible",     action="store_true", help="Skip Bible text overlay")
    parser.add_argument("--preview",      action="store_true", help="Save PNG only (no ffmpeg)")
    parser.add_argument("--force",        action="store_true", help="Overwrite existing files")
    parser.add_argument("--rename-mp3",   action="store_true", help="Rename original MP3 files to normalized format")
    parser.add_argument("--rename-only",  action="store_true", help="Only rename MP3 files to normalized format")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    if in_path.is_file():
        mp3s = [in_path]
    else:
        mp3s = sorted(in_path.glob("*.mp3"))
    if args.filter:
        if args.filter.lower().endswith(".mp3"):
            target = Path(args.filter).name
            mp3s = [f for f in mp3s if f.name == target]
        else:
            q = args.filter.lower()
            mp3s = [f for f in mp3s if q in f.name.lower()]

    total = len(mp3s)
    print(f"Found {total} MP3 file(s)")

    if args.rename_only:
        for i, mp3 in enumerate(mp3s, 1):
            _, _, _, norm_stem = parse_filename(mp3.stem)
            new_name = norm_stem + mp3.suffix
            if new_name != mp3.name:
                new_path = mp3.with_name(new_name)
                if not new_path.exists():
                    mp3.rename(new_path)
                    print(f"[{i}/{total}] [renamed] {mp3.name} -> {new_name}")
                else:
                    print(f"[{i}/{total}] [skip] Target already exists: {new_name}")
            else:
                print(f"[{i}/{total}] [ok] {mp3.name}")
        print("Done.")
        return

    bible_db = {}
    if not args.no_bible:
        print(f"Loading Bible DB ...")
        bible_db = load_bible_db(BIBLE_DB)

    for i, mp3 in enumerate(mp3s, 1):
        book_ch, verses_str, title, norm_stem = parse_filename(mp3.stem)

        if args.rename_mp3:
            new_name = norm_stem + mp3.suffix
            if new_name != mp3.name:
                new_path = mp3.with_name(new_name)
                if not new_path.exists():
                    mp3.rename(new_path)
                    print(f"  [renamed mp3] {mp3.name} -> {new_name}")
                    mp3 = new_path

        out_stem = norm_stem
        if args.preview:
            out_path = out_dir / (out_stem + ".png")
            print(f"[{i}/{total}] [prev] {mp3.name} -> {out_path.name}")
            try:
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
            mp4 = out_dir / (out_stem + ".mp4")
            print(f"[{i}/{total}] [conv] {mp3.name} -> {mp4.name}")
            try:
                convert(mp3, mp4, args.bg, bible_db)
            except Exception as e:
                print(f"  [err ] {e}")

    print("Done.")


if __name__ == "__main__":
    main()

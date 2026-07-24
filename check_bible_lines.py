import json

BIBLE_FILE = r"c:\Code\sermon2yt\개역개정4판(구약+신약).txt"

with open(BIBLE_FILE, "r", encoding="utf-8", errors="ignore") as f:
    lines = [f.readline().strip() for _ in range(40)]

print("=== BIBLE FILE FIRST 40 LINES ===")
for i, line in enumerate(lines, 1):
    if line:
        print(f"{i:2d}: {repr(line)}")

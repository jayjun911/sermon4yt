"""Inspect Bible text file format."""
with open(r"c:\Code\sermon2yt\개역개정4판(구약+신약).txt", "r", encoding="utf-8", errors="ignore") as f:
    lines = [f.readline() for _ in range(30)]

for i, l in enumerate(lines, 1):
    print(f"{i:2d}: {repr(l.strip())}")

import json

with open("sermons.json", "r", encoding="utf-8") as f:
    sermons = json.load(f)

unmatched = [e for e in sermons if e.get("scripture", "").strip() and not e.get("scripture_text")]
print(f"Remaining unmatched (with scripture): {len(unmatched)}")
for e in unmatched:
    print(f"  #{e['id']} [{e.get('date')}] title: '{e.get('title')}' | scripture: '{e.get('scripture')}'")

const fs = require('fs');
const path = require('path');

const BIBLE_FILE = path.join(__dirname, '개역개정4판(구약+신약).txt');
const SERMONS_FILE = path.join(__dirname, 'sermons.json');

const BOOK_ALIASES = {
  "창": "창세기", "출": "출애굽기", "레": "레위기", "민": "민수기", "신": "신명기",
  "수": "여호수아", "삿": "사사기", "룻": "룻기", "삼상": "사무엘상", "삼하": "사무엘하",
  "왕상": "열왕기상", "왕하": "열왕기하", "대상": "역대상", "대하": "역대하", "스": "에스라",
  "느": "느헤미야", "에": "에스더", "욥": "욥기", "시": "시편", "잠": "잠언",
  "전": "전도서", "아": "아가", "사": "이사야", "렘": "예레미야", "애": "예레미야애가",
  "겔": "에스겔", "단": "다니엘", "호": "호세아", "욜": "요엘", "암": "아모스",
  "오": "오바디야", "욘": "요나", "미": "미가", "나": "나훔", "합": "하박국",
  "습": "스바냐", "학": "학개", "슥": "스카리야", "말": "말라기",
  "마": "마태복음", "막": "마가복음", "눅": "누가복음", "요": "요한복음", "행": "사도행전",
  "롬": "로마서", "고전": "고린도전서", "고후": "고린도후서", "갈": "갈라디아서", "엡": "에베소서",
  "빌": "빌립보서", "골": "골로새서", "살전": "데살로니가전서", "살후": "데살로니가후서",
  "딤전": "디모데전서", "딤후": "디모데후서", "딛": "디도서", "몬": "빌레몬서", "히": "히브리서",
  "야": "야고보서", "벧전": "베드로전서", "벧후": "베드로후서", "요한1": "요한일서", "요1": "요한일서",
  "요한2": "요한이서", "요2": "요한이서", "요한3": "요한삼서", "요3": "요한삼서", "유": "유다서", "계": "요한계시록"
};

function parseBible() {
  const content = fs.readFileSync(BIBLE_FILE, 'utf-8');
  const lines = content.split(/\r?\n/);
  const verses = new Map();

  console.log(`Loaded ${lines.length} lines from Bible file.`);
  if (lines.length > 0) {
    console.log(`Sample Line 1: ${JSON.stringify(lines[0])}`);
    console.log(`Sample Line 2: ${JSON.stringify(lines[1])}`);
  }

  for (let line of lines) {
    line = line.trim();
    if (!line) continue;

    // Matches patterns like:
    // "창1:1 태초에..." or "창 1:1 ..." or "창세기 1:1 ..." or "창세기1:1 ..."
    const m = line.match(/^([가-힣1-3]+)\s*(\d+)[\:\s장]+\s*(\d+)절?\s*(.*)$/);
    if (m) {
      const bookRaw = m[1].trim();
      const chap = parseInt(m[2], 10);
      const ver = parseInt(m[3], 10);
      const text = m[4].trim();
      const book = BOOK_ALIASES[bookRaw] || bookRaw;

      const key = `${book}_${chap}_${ver}`;
      verses.set(key, text);
      continue;
    }

    // Matches "창1/1 태초에..."
    const m2 = line.match(/^([가-힣1-3]+)\s*(\d+)\/(\d+)\s*(.*)$/);
    if (m2) {
      const bookRaw = m2[1].trim();
      const chap = parseInt(m2[2], 10);
      const ver = parseInt(m2[3], 10);
      const text = m2[4].trim();
      const book = BOOK_ALIASES[bookRaw] || bookRaw;

      const key = `${book}_${chap}_${ver}`;
      verses.set(key, text);
    }
  }

  console.log(`Parsed ${verses.size} verses into memory.`);
  return verses;
}

function parseScriptureQuery(scriptureStr) {
  if (!scriptureStr) return null;
  const s = scriptureStr.trim();

  // Extract Book Name (e.g. 창세기, 사무엘상, 고린도전서)
  const mBook = s.match(/^([가-힣0-9]+(?:\s+[가-힣0-9]+)?)\s*(.*)$/);
  if (!mBook) return null;

  const bookRaw = mBook[1].trim();
  const rest = mBook[2].trim();
  const book = BOOK_ALIASES[bookRaw] || bookRaw;

  // Extract Chapter and Verses (e.g., '1:1~10', '4 : 16~26', '1:1-10', '4장 16절~26절')
  const mRange = rest.match(/(\d+)\s*[\:장]\s*(\d+)(?:\s*[\~–\-절]\s*(\d+))?/);
  if (mRange) {
    const chap = parseInt(mRange[1], 10);
    const startVer = parseInt(mRange[2], 10);
    const endVer = mRange[3] ? parseInt(mRange[3], 10) : startVer;
    return { book, chap, startVer, endVer };
  }

  return null;
}

function main() {
  const verses = parseBible();
  const sermons = JSON.parse(fs.readFileSync(SERMONS_FILE, 'utf-8'));

  let matchedCount = 0;

  for (const sermon of sermons) {
    const scripture = sermon.scripture || '';
    const parsed = parseScriptureQuery(scripture);

    if (parsed) {
      const { book, chap, startVer, endVer } = parsed;
      const passageLines = [];

      for (let v = startVer; v <= endVer; v++) {
        const key = `${book}_${chap}_${v}`;
        if (verses.has(key)) {
          passageLines.push(`${v}절 ${verses.get(key)}`);
        }
      }

      if (passageLines.length > 0) {
        sermon.scripture_text = passageLines.join('\n');
        matchedCount++;
      } else {
        sermon.scripture_text = null;
      }
    } else {
      sermon.scripture_text = null;
    }
  }

  fs.writeFileSync(SERMONS_FILE, JSON.stringify(sermons, null, 2), 'utf-8');
  console.log(`Successfully merged scripture texts for ${matchedCount} / ${sermons.length} sermons!`);
}

main();

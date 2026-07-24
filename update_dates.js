const fs = require('fs');
const https = require('https');
const path = require('path');

const JSON_FILE = path.join(__dirname, 'sermons.json');
const CONTENT_FILE = 'C:\\Users\\Jay Jun\\.gemini\\antigravity-ide\\brain\\1e97f3eb-b36f-44bf-894e-7d13944ed5b1\\.system_generated\\steps\\21\\content.md';

function parseHtml(html) {
  const entries = [];
  const seenUrls = new Set();
  
  // Match rows: <tr><td ...>(YYYY-MM-DD)</td><td ...><a ... href="(mp3/...)">(TITLE)</a>...<br>(SCRIPTURE)</td></tr>
  // Regex pattern for rows in shalomm.org html
  const trRegex = /<tr[^>]*>\s*<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*<\/td>\s*<td[^>]*>\s*<a[^>]*href=["'](mp3\/[^"']+)["'][^>]*>(.*?)<\/a>.*?<br\s*\/?>\s*(.*?)\s*<\/td>\s*<\/tr>/gis;
  
  let match;
  let id = 1;
  while ((match = trRegex.exec(html)) !== null) {
    const date = match[1].trim();
    const rawHref = match[2].trim();
    const title = match[3].replace(/<[^>]+>/g, '').trim();
    let scripture = match[4].replace(/<[^>]+>/g, '').trim();
    
    // Clean scripture
    scripture = scripture.replace(/\s+/g, ' ');

    const fullUrl = 'https://shalomm.org/' + rawHref;
    
    if (!title || title.toLowerCase() === 'mp3') continue;
    if (seenUrls.has(fullUrl)) continue;
    seenUrls.add(fullUrl);

    entries.push({
      id: id++,
      date: date,
      title: title,
      scripture: scripture,
      url: fullUrl,
      youtube_url: null
    });
  }

  return entries;
}

try {
  let html = '';
  if (fs.existsSync(CONTENT_FILE)) {
    console.log('Reading from local content.md...');
    html = fs.readFileSync(CONTENT_FILE, 'utf-8');
  }

  const entries = parseHtml(html);
  console.log(`Parsed ${entries.length} entries.`);
  
  if (entries.length > 0) {
    console.log('Sample entry:', JSON.stringify(entries[0], null, 2));
    fs.writeFileSync(JSON_FILE, JSON.stringify(entries, null, 2), 'utf-8');
    console.log(`Successfully updated ${JSON_FILE}`);
  } else {
    console.error('No entries found! Check regex or html source.');
  }
} catch (err) {
  console.error('Error:', err);
}

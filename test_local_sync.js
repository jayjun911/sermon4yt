const fs = require('fs');

const file = 'C:\\Users\\Jay Jun\\.gemini\\antigravity-ide\\brain\\1e97f3eb-b36f-44bf-894e-7d13944ed5b1\\.system_generated\\steps\\151\\content.md';
const html = fs.readFileSync(file, 'utf-8');

const match = html.match(/var ytInitialData\s*=\s*({.*?});<\/script>/);
if (match) {
  const data = JSON.parse(match[1]);
  const items = [];

  function walk(node) {
    if (!node) return;
    if (typeof node === 'object') {
      if (node.playlistVideoRenderer) {
        const pvr = node.playlistVideoRenderer;
        const vid = pvr.videoId;
        const title = (pvr.title && pvr.title.runs) ? pvr.title.runs.map(r => r.text).join('') : '';
        if (vid && title) {
          items.push({ id: vid, title: title });
        }
      } else if (node.videoRenderer) {
        const vr = node.videoRenderer;
        const vid = vr.videoId;
        const title = (vr.title && vr.title.runs) ? vr.title.runs.map(r => r.text).join('') : '';
        if (vid && title) {
          items.push({ id: vid, title: title });
        }
      }
      for (const key of Object.keys(node)) {
        walk(node[key]);
      }
    }
  }

  walk(data);
  console.log(`Found ${items.length} video(s):`);
  items.forEach(v => console.log(`  - [${v.id}] ${v.title}`));
} else {
  console.log("No match");
}

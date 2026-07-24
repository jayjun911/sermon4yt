const https = require('https');

const playlistId = 'PLSqr4-dP7wJDARLGADNTbBn3H-2lgSoF4';

// Test 1: RSS Feed
const rssUrl = `https://www.youtube.com/feeds/videos.xml?playlist_id=${playlistId}`;
https.get(rssUrl, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    console.log(`[RSS] Status: ${res.statusCode}, Length: ${data.length}`);
    const matches = [...data.matchAll(/<entry>[\s\S]*?<yt:videoId>(.*?)<\/yt:videoId>[\s\S]*?<title>(.*?)<\/title>[\s\S]*?<\/entry>/g)];
    console.log(`[RSS] Entries count: ${matches.length}`);
    matches.forEach(m => {
      console.log(`  [RSS Item] ${m[1]} -> ${m[2]}`);
    });

    // Test 2: HTML Page ytInitialData
    testHtmlPage();
  });
}).on('error', err => console.error('[RSS] Error:', err.message));

function testHtmlPage() {
  const options = {
    hostname: 'www.youtube.com',
    path: `/playlist?list=${playlistId}`,
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
      'Cookie': 'CONSENT=YES+cb.20210328-17-p0.ko+FX+430'
    }
  };

  https.get(options, (res) => {
    let html = '';
    res.on('data', chunk => html += chunk);
    res.on('end', () => {
      console.log(`[HTML] Status: ${res.statusCode}, Length: ${html.length}`);
      const m = html.match(/var ytInitialData\s*=\s*({[\s\S]*?});<\/script>/);
      if (m) {
        console.log(`[HTML] Found ytInitialData! Length of JSON string: ${m[1].length}`);
        try {
          const json = JSON.parse(m[1]);
          const videos = [];
          function walk(node) {
            if (!node) return;
            if (typeof node === 'object') {
              if (node.playlistVideoRenderer) {
                const pvr = node.playlistVideoRenderer;
                const vid = pvr.videoId;
                const title = (pvr.title && pvr.title.runs) ? pvr.title.runs.map(r => r.text).join('') : '';
                if (vid && title) videos.push({ vid, title });
              }
              for (const k of Object.keys(node)) walk(node[k]);
            }
          }
          walk(json);
          console.log(`[HTML] Parsed ${videos.length} videos from ytInitialData:`);
          videos.forEach(v => console.log(`  [HTML Item] ${v.vid} -> ${v.title}`));
        } catch (e) {
          console.error('[HTML] JSON parse error:', e.message);
        }
      } else {
        console.log('[HTML] var ytInitialData regex NOT matched');
      }
    });
  }).on('error', err => console.error('[HTML] Error:', err.message));
}

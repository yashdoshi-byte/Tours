// Makes the two client PDFs for every tour:
//   pdf/<slug>-overview.pdf  the website page (docs/<slug>/index.html)
//   pdf/<slug>-detailed.pdf  the detailed itinerary (print/<slug>-detailed.html)
// Run `python3 build.py --strict` first. Usage: node tools/make_pdf.js [slug ...]
// HERO_FALLBACK=/path/to/photo.webp swaps in a local photo only where the hero cannot be downloaded.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), http = require('http');
const root = path.resolve(__dirname, '..');

(async () => {
  const want = process.argv.slice(2);
  const slugs = fs.readdirSync(path.join(root, 'print'))
    .filter(f => f.endsWith('-detailed.html')).map(f => f.replace('-detailed.html', ''))
    .filter(s => !want.length || want.includes(s));
  fs.mkdirSync(path.join(root, 'pdf'), { recursive: true });
  // A small local server, so photos can be re-encoded as JPEG in the page (keeps each PDF small enough to email).
  const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
  const server = http.createServer((req, res) => {
    const f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
    if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
  }).listen(0);
  const base = `http://127.0.0.1:${server.address().port}/`;
  const browser = await chromium.launch();
  let problems = 0;
  for (const slug of slugs) {
    for (const [kind, file] of [['overview', `docs/${slug}/index.html`], ['detailed', `print/${slug}-detailed.html`]]) {
      const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
      if (process.env.HERO_FALLBACK) {
        await page.route('**/uploads/**', r => r.fulfill({ path: process.env.HERO_FALLBACK, contentType: 'image/webp' }));
      }
      await page.goto(base + file, { waitUntil: 'networkidle' });
      await page.evaluate(async () => {
        document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; });
        document.querySelectorAll('details').forEach(d => { d.open = true; });  // FAQs print open
        await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
        await document.fonts.ready;
      });
      // Re-encode every local photo and map as a JPEG no wider than 1400px.
      await page.evaluate(async () => {
        for (const i of [...document.images]) {
          if (!i.naturalWidth || i.src.startsWith('data:') || new URL(i.src).origin !== location.origin) continue;
          const w = Math.min(1400, i.naturalWidth), h = Math.round(i.naturalHeight * w / i.naturalWidth);
          const c = document.createElement('canvas'); c.width = w; c.height = h;
          const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.drawImage(i, 0, 0, w, h);
          if (/emblem|logo/.test(i.src)) continue;  // keep the logo's transparency
          i.src = c.toDataURL('image/jpeg', 0.8);
          await i.decode().catch(() => {});
        }
      });
      const broken = await page.evaluate(() => [...document.images].filter(i => !i.naturalWidth).map(i => i.src));
      if (broken.length) { problems++; console.error(`✗ ${slug} ${kind}: images did not load:\n  ` + broken.join('\n  ')); }
      await page.emulateMedia({ media: 'print' });
      const out = path.join(root, 'pdf', `${slug}-${kind}.pdf`);
      await page.pdf({ path: out, printBackground: true, preferCSSPageSize: true });
      console.log(`✓ ${path.relative(root, out)}`);
      await page.close();
    }
  }
  await browser.close(); server.close();
  if (problems) process.exit(1);
})();

// Makes the two client PDFs for every tour:
//   pdf/<slug>-overview.pdf  the website page (docs/<slug>/index.html)
//   pdf/<slug>-detailed.pdf  the detailed itinerary (print/<slug>-detailed.html)
// Run `python3 build.py --strict` first. Usage: node tools/make_pdf.js [slug ...]
// HERO_FALLBACK=/path/to/photo.webp swaps in a local photo only where the cover photo cannot be downloaded.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), http = require('http');
const root = path.resolve(__dirname, '..');

(async () => {
  const want = process.argv.slice(2);
  const slugs = fs.readdirSync(path.join(root, 'print'))
    .filter(f => f.endsWith('-detailed.html')).map(f => f.replace('-detailed.html', ''))
    .filter(s => !want.length || want.includes(s));
  fs.mkdirSync(path.join(root, 'pdf'), { recursive: true });

  // A small local server. Every photo, including the cover from the main website, is served from the
  // same address as the page, so the page can re-encode it as a JPEG and keep each PDF small enough to email.
  const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
  const server = http.createServer(async (req, res) => {
    if (req.url.startsWith('/__photo?u=')) {
      const u = decodeURIComponent(req.url.slice('/__photo?u='.length));
      try {
        const r = await fetch(u);
        if (!r.ok) throw new Error(String(r.status));
        res.writeHead(200, { 'Content-Type': r.headers.get('content-type') || 'image/webp' });
        return res.end(Buffer.from(await r.arrayBuffer()));
      } catch (e) {
        if (process.env.HERO_FALLBACK) {
          res.writeHead(200, { 'Content-Type': 'image/webp' });
          return fs.createReadStream(process.env.HERO_FALLBACK).pipe(res);
        }
        res.writeHead(502); return res.end();
      }
    }
    const f = path.join(root, decodeURIComponent(req.url.split('?')[0]));
    if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  }).listen(0);
  const base = `http://127.0.0.1:${server.address().port}/`;

  const browser = await chromium.launch();
  let problems = 0;
  for (const slug of slugs) {
    for (const [kind, file] of [['overview', `docs/${slug}/index.html`], ['detailed', `print/${slug}-detailed.html`]]) {
      const page = await browser.newPage({ viewport: { width: 794, height: 1123 } });
      await page.goto(base + file, { waitUntil: 'networkidle' });
      await page.evaluate(async () => {
        for (const i of document.images) {
          if (/^https?:/.test(i.getAttribute('src') || '') && new URL(i.src).origin !== location.origin) i.src = '/__photo?u=' + encodeURIComponent(i.src);
        }
        document.querySelectorAll('img[loading=lazy]').forEach(i => { i.loading = 'eager'; });
        document.querySelectorAll('details').forEach(d => { d.open = true; });  // FAQs print open
        await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
        await document.fonts.ready;
      });
      // Re-encode every photo and map as a JPEG no wider than 1400px. The logo keeps its transparency.
      await page.evaluate(async () => {
        for (const i of [...document.images]) {
          if (!i.naturalWidth || i.src.startsWith('data:') || /emblem|logo/.test(i.src)) continue;
          const w = Math.min(1400, i.naturalWidth), h = Math.round(i.naturalHeight * w / i.naturalWidth);
          const c = document.createElement('canvas'); c.width = w; c.height = h;
          const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.drawImage(i, 0, 0, w, h);
          i.src = c.toDataURL('image/jpeg', 0.8);
          await i.decode().catch(() => {});
        }
      });
      const broken = await page.evaluate(() => [...document.images].filter(i => !i.naturalWidth).map(i => i.src.slice(0, 120)));
      if (broken.length) { problems++; console.error(`✗ ${slug} ${kind}: images did not load:\n  ` + broken.join('\n  ')); }
      await page.emulateMedia({ media: 'print' });
      const out = path.join(root, 'pdf', `${slug}-${kind}.pdf`);
      await page.pdf({ path: out, printBackground: true, preferCSSPageSize: true });
      const mb = fs.statSync(out).size / 1e6;
      console.log(`✓ ${path.relative(root, out)} · ${mb.toFixed(1)} MB`);
      if (mb > 10) { problems++; console.error(`✗ ${slug} ${kind}: over 10 MB, too big to email comfortably`); }
      await page.close();
    }
  }
  await browser.close(); server.close();
  if (problems) process.exit(1);
})();

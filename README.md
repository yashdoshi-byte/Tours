# Blue Diamond Voyage – Tour pages

SEO-friendly itinerary pages for Blue Diamond Voyage, published with GitHub Pages from the `docs/` folder.

Live: https://yashdoshi-byte.github.io/Tours/

## Add or edit a tour
1. Copy `data/tours/bali-honeymoon-nusa-dua.json` to `data/tours/<new-slug>.json` and fill in the fields
   (slug, title, meta_title ≤ 60 chars, meta_description ≤ 160 chars, days, hotel, inclusions, FAQs).
2. Run `python3 build.py` (needs `jinja2`).
3. Commit and push. GitHub Pages republishes in about a minute.

Each page gets: its own title and meta description, canonical URL, Open Graph tags,
TouristTrip + FAQPage + BreadcrumbList structured data, and an entry in `docs/sitemap.xml`.

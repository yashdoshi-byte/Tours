# Blue Diamond Voyage – Tour pages

SEO-friendly itinerary pages for Blue Diamond Voyage, published with GitHub Pages from the `docs/` folder.

Live: https://yashdoshi-byte.github.io/Tours/

**The rulebook for every tour page is [STANDARDS.md](STANDARDS.md).** Read it before writing a tour.

## Add or edit a tour
1. Copy `data/tours/bali-honeymoon-nusa-dua.json` to `data/tours/<new-slug>.json` and fill in the fields
   (slug, title, meta_title ≤ 60 chars, meta_description ≤ 160 chars, days, hotel, inclusions, FAQs).
2. Run `python3 tools/media.py <slug>` for photos, pins, road routes and maps (needs internet). If the
   computer you use cannot reach OpenStreetMap or Wikimedia, just push: the "Build tour media" GitHub
   workflow runs it and commits the results. Check `media/<slug>/places.md` and `contact_sheet.jpg`.
3. Run `python3 build.py` (needs `jinja2`). It runs the rule checks; `--strict` before publishing.
4. Commit and push. GitHub Pages republishes in about a minute.

Each page gets: its own title and meta description, canonical URL, Open Graph tags,
TouristTrip + FAQPage + BreadcrumbList structured data, and an entry in `docs/sitemap.xml`.

## The page format (same as the Blue Diamond Voyage travel pack)

Every tour page follows one running order, so all tours read the same way:

1. **Cover**: style line, title, tagline, quote buttons, then a facts bar (`facts`).
2. **Journey**: intro, stays ribbon (`stays`), highlights.
3. **At a glance**: one line per day linking to the day, plus a Google Maps route (`route`).
4. **Day cards**: each day has a `pill` (Arrival day, Full day, Free day, Departure), a `title`
   that names the day, a `strip` of up to five fixed points (drive time, sunset, pick-up),
   stacked `rows` (time `label` above the entry, optional `flag`, `title`, `text`, `bullets`,
   `notes` callouts, `meal`), `places` (each becomes a Google Maps pin), and one concierge `note`.
   `summary` is a one-line description used for Google's structured data.
5. **Where you stay**: hotel card with room, meals, check-in, check-out and a map-linked address.
6. **Included / not included**.
7. **Visa, entry and phones** (`entry`, `entry_notes`).
8. **Good to know** cards (`good_to_know`) and the emergency block (`emergency`, plus the 24/7 desk).
9. **Dining** for dietary briefs (`dining`, `dining_avoid`, `food_card` in the local language and Hindi).
10. **Best time to go** (`best_time`, `seasons`), **FAQs**, and the quote sign-off.

Callout tags always mean the same thing: `TIP`/`NOTE` our advice · `CARE` what goes wrong if ignored ·
`TIME` entry windows · `WEAR` dress code · `KIDS` the children's version · `EAT`/`BUY` what to order or take
home · `MONEY` cash, deposits, levies. Never show a package price: use `price_note`. Entry fees and meal
costs are written as "about". Every optional section can be left out and the page still builds.

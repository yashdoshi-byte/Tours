#!/usr/bin/env python3
"""Build the static tour site into docs/ (served by GitHub Pages).
Add a tour: drop a JSON file in data/tours/ (copy an existing one), then run: python3 build.py
"""
import json, pathlib, shutil, datetime, re, sys, urllib.parse
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT / "tools"))
from rules import check_tour  # noqa: E402
OUT = ROOT / "docs"
PRINT = ROOT / "print"  # private pages for the PDFs, never served
site = json.loads((ROOT / "data/site.json").read_text())
tours = [json.loads(p.read_text()) for p in sorted((ROOT / "data/tours").glob("*.json"))]
env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]))
base = site["base_url"].rstrip("/") + "/"
dump = lambda o: json.dumps(o, ensure_ascii=False).replace("</", "<\\/")

org = {"@type": "TravelAgency", "name": site["brand"], "url": site["main_site"], "logo": site["logo"],
       "telephone": site["phone"], "email": site["email"], "sameAs": [site["instagram"]],
       "address": {"@type": "PostalAddress", "streetAddress": "Arpan Complex, opp. Swaminarayan Temple",
                   "addressLocality": "Rajkot", "addressRegion": "Gujarat", "addressCountry": "IN"}}

if OUT.exists():
    shutil.rmtree(OUT)
(OUT / "assets").mkdir(parents=True)
shutil.copy(ROOT / "assets/style.css", OUT / "assets/style.css")
shutil.copy(ROOT / "assets/site.js", OUT / "assets/site.js")
shutil.copytree(ROOT / "assets/logo", OUT / "assets/logo")
shutil.copytree(ROOT / "assets/deco", OUT / "assets/deco")
(OUT / ".nojekyll").write_text("")

STRICT = "--strict" in sys.argv
errors = warnings = 0


def coords_of(m, name):
    c = m.get("coords", {}).get(name)
    return f"{c[0]},{c[1]}" if c else None


def directions(t, m, stops):
    """Google Maps driving directions through the day's stops, by exact coordinates where known."""
    pts = [coords_of(m, n) for n in stops]
    if len(pts) < 2 or not all(pts):  # directions only through verified pins
        return None
    q = {"api": 1, "origin": pts[0], "destination": pts[-1], "travelmode": "driving"}
    if len(pts) > 2:
        q["waypoints"] = "|".join(pts[1:-1])
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(q)



for t in tours:
    mfile = ROOT / "media" / t["slug"] / "media.json"
    m = json.loads(mfile.read_text()) if mfile.exists() else {"days": {}, "photos": {}}
    if (ROOT / "media" / t["slug"]).exists():
        dst = OUT / "media" / t["slug"]; dst.mkdir(parents=True)
        for f in (ROOT / "media" / t["slug"]).glob("*.webp"):
            shutil.copy(f, dst / f.name)
    t["_media"] = m
    n = t.get("hero_from_day")  # the cover uses a day photo, never a banner with prices or dates printed on it
    if n and m["days"].get(str(n), {}).get("photo"):
        t["_hero_rel"] = f"media/{t['slug']}/{m['days'][str(n)]['photo']['img']}"
        t["hero_image"] = base + t["_hero_rel"]
    pts = list(m.get("coords", {}).values())  # verified pins only
    if pts:  # where the trip is, on the 84N to 58S world map in the cover
        lat = sum(p[0] for p in pts) / len(pts); lon = sum(p[1] for p in pts) / len(pts)
        t["_pin"] = (round((lon + 180) / 360 * 100, 2), round((84 - lat) / 142 * 100, 2))
    for ph in [v.get("photo") for v in m["days"].values()] + list(m.get("photos", {}).values()):
        if ph:  # credit names only: no raw links in the caption
            ph["author"] = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", ph.get("author") or "")).strip(" ,;-") or ph.get("provider", "")
    for i, d in enumerate(t["days"], 1):
        dm = m["days"].get(str(i), {})
        d["_map"], d["_photo"], d["_km"] = dm.get("map"), dm.get("photo"), dm.get("km")
        d["_unverified"] = dm.get("unverified")
        d["_stops"] = dm.get("stops") or d.get("route") or []
        d["_directions"] = directions(t, m, d.get("route") or [])
    credits = [dict(m["days"][k]["photo"], where=t["days"][int(k) - 1].get("photo_caption") or f"Day {k}") for k in sorted(m["days"], key=int) if m["days"][k].get("photo")]
    credits += [dict(v, where="Where you stay") for v in m.get("photos", {}).values()]
    t["_credits"] = credits
    t["_hotel_photo"] = m.get("photos", {}).get("hotel-1")
    e, w = check_tour(t, m)
    for msg in e:
        print(f"  ✗ {t['slug']}: {msg}")
    for msg in w:
        print(f"  ⚠ {t['slug']}: {msg}")
    errors += len(e); warnings += len(w)

if errors or (STRICT and warnings):
    sys.exit(f"Stopped: {errors} error(s), {warnings} warning(s). See STANDARDS.md section 17.")

for t in tours:
    url = base + t["slug"] + "/"
    trip = {"@context": "https://schema.org", "@type": "TouristTrip", "name": t["title"],
            "description": t["meta_description"], "url": url, "image": t["hero_image"],
            "touristType": t["style"], "provider": org,
            **({"dateModified": t["date_modified"]} if t.get("date_modified") else {}),
            "itinerary": {"@type": "ItemList", "numberOfItems": len(t["days"]), "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": f"Day {i+1}: {d['title']}", "description": d.get("summary") or d.get("body", "")}
                for i, d in enumerate(t["days"])]}}
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in t["faqs"]]}
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": site["main_site"] + "/"},
        {"@type": "ListItem", "position": 2, "name": "Tours", "item": base},
        {"@type": "ListItem", "position": 3, "name": t["title"], "item": url}]}
    # no FAQPage schema: the FAQs are not shown on the client page
    html = env.get_template("tour.html").render(
        site=site, t=t, root="../", canonical=url, og_type="article", og_image=t["hero_image"],
        meta_title=t["meta_title"], meta_description=t["meta_description"],
        jsonld=[dump(trip), dump(crumbs)], others=[o for o in tours if o["slug"] != t["slug"]][:3])
    d = OUT / t["slug"]; d.mkdir()
    (d / "index.html").write_text(html)
    # The detailed itinerary is not published on the website. It is written to print/ and made
    # into a PDF by tools/make_pdf.js, for Yash to send when a client asks for it.
    PRINT.mkdir(exist_ok=True)
    (PRINT / f"{t['slug']}-detailed.html").write_text(env.get_template("detailed.html").render(
        site=site, t=t, root="../docs/", canonical=url, og_type="article", og_image=t["hero_image"],
        meta_title="Detailed itinerary: " + t["title"], meta_description=t["meta_description"],
        jsonld=[], others=[]))

listing = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
    {"@type": "ListItem", "position": i + 1, "url": base + t["slug"] + "/", "name": t["title"]} for i, t in enumerate(tours)]}
(OUT / "index.html").write_text(env.get_template("index.html").render(
    site=site, tours=tours, root="", canonical=base, og_type="website",
    og_image=tours[0]["hero_image"] if tours else site["logo"],
    meta_title=site["index_title"], meta_description=site["index_description"],
    jsonld=[dump(listing), dump(dict(org, **{"@context": "https://schema.org"}))]))

today = datetime.date.today().isoformat()
urls = [base] + [base + t["slug"] + "/" for t in tours]
(OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n")
print(f"Built {len(tours)} tour page(s) into {OUT} · {warnings} warning(s)")

#!/usr/bin/env python3
"""Build the static tour site into docs/ (served by GitHub Pages).
Add a tour: drop a JSON file in data/tours/ (copy an existing one), then run: python3 build.py
"""
import json, pathlib, shutil, datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "docs"
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
if (ROOT / "assets/img").is_dir():
    shutil.copytree(ROOT / "assets/img", OUT / "assets/img")
(OUT / ".nojekyll").write_text("")

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
    html = env.get_template("tour.html").render(
        site=site, t=t, root="../", canonical=url, og_type="article", og_image=t["hero_image"],
        meta_title=t["meta_title"], meta_description=t["meta_description"],
        jsonld=[dump(trip), dump(faq), dump(crumbs)], others=[o for o in tours if o["slug"] != t["slug"]][:3])
    d = OUT / t["slug"]; d.mkdir()
    (d / "index.html").write_text(html)

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
print(f"Built {len(tours)} tour page(s) into {OUT}")

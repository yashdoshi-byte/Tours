"""The rule checks from STANDARDS.md section 17. build.py runs them on every tour.

check_tour(t, media) returns (errors, warnings). Errors stop the build; warnings stop it with --strict.
"""
import datetime, re

TAGS = {"TIP", "NOTE", "CARE", "TIME", "WEAR", "KIDS", "EAT", "BUY", "MONEY"}
PRICE = re.compile(r"(₹|\bRs\.?\s?\d|\bINR\s?\d|\bUSD\s?\d|\$\s?\d|\d\s?(lakh|per couple|per person twin))", re.I)
GENERIC_TITLE = re.compile(r"^(day\s*\d+|sightseeing|free day|leisure|tour|excursion)\W*$", re.I)
FORBIDDEN = re.compile(r"[←-⇿☀-➿⭐✅✔✖\U0001F000-\U0001FAFF]")
INTERNAL = re.compile(r"\b(TODO|TBC|TBD|net rate|supplier|markup|commission)\b", re.I)


def texts(o, path=""):
    """Every string in the tour, with where it is, skipping technical fields."""
    if isinstance(o, str):
        yield path, o
    elif isinstance(o, dict):
        for k, v in o.items():
            if not k.startswith("_") and k not in ("slug", "hero_image", "geo", "photo_files", "photo"):
                yield from texts(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from texts(v, f"{path}[{i}]")


def check_tour(t, m):
    E, W = [], []
    # --- hard rules
    if len(t.get("meta_title", "")) > 60:
        E.append(f"meta_title is {len(t['meta_title'])} characters (60 at most)")
    if len(t.get("meta_description", "")) > 160:
        E.append(f"meta_description is {len(t['meta_description'])} characters (160 at most)")
    if "personalised quote" not in t.get("price_note", "").lower():
        E.append('price_note must say "Contact us for a personalised quote"')
    for where, s in texts(t):
        if FORBIDDEN.search(s):
            E.append(f"{where}: arrow, star, tick or emoji character: write it in words")
        if INTERNAL.search(s):
            E.append(f"{where}: internal note left in ({INTERNAL.search(s).group(0)})")
        if where.split(".")[0] in ("title", "intro", "highlights", "included", "tagline", "facts") and PRICE.search(s):
            E.append(f"{where}: looks like a package price. Never show prices")
    for i, d in enumerate(t["days"], 1):
        if not d.get("title") or GENERIC_TITLE.match(d["title"]):
            E.append(f"day {i}: the title must name the day, not '{d.get('title', '')}'")
        for j, r in enumerate(d.get("rows", []), 1):
            for tag, _ in r.get("notes", []):
                if tag not in TAGS:
                    E.append(f"day {i} entry {j}: callout tag {tag!r} is not in the taxonomy")
            if r.get("meal") and not re.search(r"\b(included|not included|pay)\b", r["meal"][1], re.I):
                E.append(f"day {i} entry {j}: the meal must say Included or Not included")
    # --- warnings
    for i, d in enumerate(t["days"], 1):
        n = len(d.get("rows", []))
        if n > 9:
            W.append(f"day {i}: {n} entries. More than 9 is a march: split the day")
        if len(d.get("strip", [])) > 5:
            W.append(f"day {i}: strip has {len(d['strip'])} items (5 at most)")
        if not d.get("note"):
            W.append(f"day {i}: no concierge note")
        if not d.get("places"):
            W.append(f"day {i}: no places to pin on Google Maps")
        if len(d.get("route") or []) >= 2 and not d.get("_map"):
            W.append(f"day {i}: no route map yet. Run tools/media.py")
        if (d.get("photo_query") or d.get("photo")) and not d.get("_photo"):
            W.append(f"day {i}: no photo yet. Run tools/media.py")
    if len(t.get("faqs", [])) < 4:
        W.append("fewer than 4 FAQs")
    if not t.get("good_to_know"):
        W.append("no good_to_know section")
    if t.get("country", "India") != "India" and not t.get("emergency"):
        W.append("international tour without an emergency block")
    if t.get("route") and not m.get("overview"):
        W.append("no trip overview map yet. Run tools/media.py")
    if m.get("pins_to_check"):
        W.append(f"{m['pins_to_check']} map pin(s) need checking: see media/{t['slug']}/places.md")
    fc = t.get("facts_checked_iso") or t.get("date_modified")
    if not t.get("facts_checked"):
        W.append("no facts_checked date")
    elif fc and (datetime.date.today() - datetime.date.fromisoformat(fc)).days > 365:
        W.append("facts were last checked more than 12 months ago")
    return E, W

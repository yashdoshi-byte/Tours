#!/usr/bin/env python3
"""Fetch the media for every tour: photos, coordinates, road routes and map images.

    python3 tools/media.py            # fetch what is missing for every tour
    python3 tools/media.py bali-...   # one tour only
    python3 tools/media.py --refresh  # ignore caches and fetch everything again

Sources (all credited on the page):
  * Places  -> OpenStreetMap Nominatim (coordinates). Cached in data/cache/geo.json.
  * Routes  -> OSRM road routing on OpenStreetMap data. Cached in data/cache/routes.json.
  * Maps    -> OpenStreetMap tiles, drawn with Pillow into media/<slug>/map-*.webp.
  * Photos  -> 1. a photo chosen by hand in the tour file ("photo" on a day or a hotel): the hotel's or
                  tourism board's own website, a blog with the owner's OK, Unsplash, any free site;
               2. a search, in this order: Pexels and Pixabay (when PEXELS_API_KEY / PIXABAY_API_KEY
                  are set), Wikimedia Commons, Openverse. Open licences only.
               Cached in data/cache/photos.json with author, licence and source page.
Hotel photos are never searched: give the hotel's own image URL in the tour file.

Corrections live in the tour file, never in code:
  "geo":    {"Place name": [lat, lon]}         pin a place by hand
  "photo_files": {"query": "File:Name.jpg"}     choose a specific Commons photo
The network is needed only here. build.py works offline from the caches and media/.
"""
import hashlib, html, io, json, math, os, pathlib, re, sys, time
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "data/cache"
MEDIA = ROOT / "media"
UA = {"User-Agent": "BDV-Tours-builder/1.0 (+https://github.com/yashdoshi-byte/Tours)"}
OK_LICENCES = ("cc by", "cc-by", "cc0", "public domain", "pd")
S = requests.Session(); S.headers.update(UA)
_last = {}


def polite(host, gap):
    """Respect each service's rate limit (Nominatim asks for one request per second)."""
    wait = _last.get(host, 0) + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.time()


def load(name):
    p = CACHE / name
    return json.loads(p.read_text()) if p.exists() else {}


def save(name, data):
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / name).write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


# ---------------------------------------------------------------- places
GENERIC = set("the of and a an at in on to by de la le el temple pura hotel resort beach airport international "
              "station market palace bay rice terrace waterfall forest sanctuary bali island city old new "
              "museum park street road jalan".split())
CHECKS = {}  # place -> verification record, written to media/<slug>/places.md


def words(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 2 and w not in GENERIC}


def in_bbox(t, lat, lon):
    b = t.get("bbox")  # [south, west, north, east]
    return not b or (b[0] <= lat <= b[2] and b[1] <= lon <= b[3])


def nominatim(q, t):
    params = {"q": q, "format": "jsonv2", "limit": 5, "addressdetails": 1, "accept-language": "en"}
    if t.get("country_code"):
        params["countrycodes"] = t["country_code"]
    if t.get("bbox"):  # search only inside the tour's area
        s_, w, n, e = t["bbox"]
        params.update(viewbox=f"{w},{n},{e},{s_}", bounded=1)
    polite("nominatim", 1.1)
    r = S.get("https://nominatim.openstreetmap.org/search", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def lookup(name, query, t, geo, refresh):
    """One OpenStreetMap search. Returns (record, status, why)."""
    key = f'v2|{t.get("country_code", "")}|{t.get("bbox", "")}|{query}'
    if key not in geo or refresh or not isinstance(geo[key], dict):
        hits = nominatim(query, t)
        if not hits and t.get("destination"):  # try again with the region added
            hits = nominatim(f'{query}, {t["destination"]}', t)
        want = words(query)
        # prefer a real place (not a street) whose own name shares the most distinctive words with ours
        best = max(hits, key=lambda h: (h.get("category") != "highway", len(want & words(h.get("name") or "")),
                                        -hits.index(h)), default=None)
        geo[key] = None if not best else {
            "lat": round(float(best["lat"]), 5), "lon": round(float(best["lon"]), 5),
            "found": best.get("display_name", ""), "osm_name": best.get("name") or "",
            "type": f'{best.get("category", "")}/{best.get("type", "")}'}
    g = geo[key]
    if not g:
        return None, "NOT FOUND", ""
    want = words(query)
    # the place's OWN name must match: a match in the address ("…, Tegallalang, Gianyar") is not enough
    if want and len(want & words(g["osm_name"])) < max(1, (len(want) + 1) // 2):
        return g, "CHECK", "the name it found does not match ours"
    if g["type"].startswith("highway/") and not re.search(r"\b(jalan|jl|road|street|gang)\b", name, re.I):
        return g, "CHECK", "OpenStreetMap returned a street with this name"
    if not in_bbox(t, g["lat"], g["lon"]):
        return g, "CHECK", "outside the tour's area"
    return g, "OK", ""


def geocode(name, t, geo, refresh):
    """Coordinates for a place, with a record of how sure we are."""
    if name in t.get("geo", {}):
        g = t["geo"][name]
        lat, lon = g[:2]
        src = g[2] if len(g) > 2 else "the tour file"
        CHECKS[name] = {"lat": lat, "lon": lon, "found": f"Pinned by hand from {src}", "type": "",
                        "status": "PINNED" if in_bbox(t, lat, lon) else "CHECK"}
        return [lat, lon]
    queries = t.get("geo_query", {}).get(name, name)
    queries = [queries] if isinstance(queries, str) else list(queries)
    tried = []
    for query in queries:  # several spellings may be given: the first one that verifies wins
        g, status, why = lookup(name, query, t, geo, refresh)
        tried.append((g, status, why))
        if status == "OK":
            break
    g, status, why = next((x for x in tried if x[1] == "OK"), tried[0])
    if not g:
        CHECKS[name] = {"status": "NOT FOUND", "found": "", "type": "", "lat": None, "lon": None}
        print(f"  ✗ place {name!r}: NOT FOUND. Pin it under \"geo\" in the tour file.")
        return None
    CHECKS[name] = dict(g, status=status, why=why)
    mark = "✓" if status == "OK" else "⚠"
    print(f'  {mark} place {name!r:50} -> {g["lat"]}, {g["lon"]}  {g["found"][:70]}')
    return [g["lat"], g["lon"]]


def check_spread(t, pts):
    """Flag a pin far from the others: usually a same-name place elsewhere."""
    good = [p for p in pts.values() if p]
    if len(good) < 3:
        return
    lat = sorted(p[0] for p in good)[len(good) // 2]; lon = sorted(p[1] for p in good)[len(good) // 2]
    for n, p in pts.items():
        if p and haversine(p, (lat, lon)) > t.get("max_km_from_centre", 250):
            CHECKS[n]["status"] = "CHECK"
            CHECKS[n]["why"] = f"{haversine(p, (lat, lon)):.0f} km from the rest of the trip"
            print(f"  ⚠ {n!r} is {haversine(p, (lat, lon)):.0f} km from the rest. Check it, or pin it under \"geo\".")


def places_report(slug, t):
    """The pin list to approve: every place, where it landed, and a link to check it on Google Maps."""
    rows = ["| Status | Place in the itinerary | Pin | What OpenStreetMap found | Check |", "|---|---|---|---|---|"]
    for n, c in CHECKS.items():
        ll = f'{c["lat"]}, {c["lon"]}' if c.get("lat") is not None else "none"
        link = f'[open](https://www.google.com/maps/search/?api=1&query={c["lat"]},{c["lon"]})' if c.get("lat") is not None else ""
        found = (c.get("found") or "").replace("|", "/")[:120] + (f' ({c["why"]})' if c.get("why") else "")
        rows.append(f'| {c["status"]} | {n} | {ll} | {found} | {link} |')
    bad = sum(c["status"] in ("CHECK", "NOT FOUND") for c in CHECKS.values())
    head = (f"# Pins for {t['title']}\n\nEvery place on this tour's maps. OK means OpenStreetMap's name matches ours; "
            f"CHECK means look at it; PINNED was set by hand. Open each CHECK link: if the pin is wrong, copy the right "
            f"coordinates from Google Maps into \"geo\" in the tour file.\n\n**{bad} pin(s) to check.**\n\n")
    (MEDIA / slug / "places.md").write_text(head + "\n".join(rows) + "\n")
    return bad


def haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- routes
def road_route(coords, routes, refresh):
    key = ";".join(f"{lon},{lat}" for lat, lon in coords)
    if key in routes and not refresh:
        return routes[key]
    polite("osrm", 1.0)
    r = S.get(f"https://router.project-osrm.org/route/v1/driving/{key}",
              params={"overview": "full", "geometries": "geojson"}, timeout=60)
    data = r.json()
    if data.get("code") != "Ok":
        print(f"  ⚠ no road route ({data.get('code')}); the map draws straight lines instead")
        routes[key] = None
        return None
    rt = data["routes"][0]
    line = rt["geometry"]["coordinates"]
    step = max(1, len(line) // 400)  # keep the cache small
    routes[key] = {"km": [round(l["distance"] / 1000, 1) for l in rt["legs"]],
                   "line": [[round(y, 5), round(x, 5)] for x, y in line[::step] + [line[-1]]]}
    return routes[key]


# ---------------------------------------------------------------- map images
TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_tiles = {}


def px(lat, lon, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def tile(z, x, y):
    k = (z, x, y)
    if k not in _tiles:
        polite("tiles", 0.05)
        r = S.get(TILE.format(z=z, x=x % (2 ** z), y=y), timeout=30)
        r.raise_for_status()
        _tiles[k] = Image.open(io.BytesIO(r.content)).convert("RGB")
    return _tiles[k]


def font(size):
    for f in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def render(points, line, labels, size, fit=None, nums=None, attribution=True, max_zoom=14):
    """Draw one map. points: [(lat, lon)]; line: road geometry or None; fit: the points to frame
    (default: everything); nums: the number printed on each point (default 1, 2, 3...)."""
    W, H = size
    fitp = list(fit) if fit else list(points) + list(line or [])
    pad = 150 if labels and W > 700 else 45
    z = 17
    while z > 2:
        xs, ys = zip(*(px(a, b, z) for a, b in fitp))
        if max(xs) - min(xs) <= W - 2 * pad and max(ys) - min(ys) <= H - 2 * pad:
            break
        z -= 1
    z = min(z, max_zoom)
    xs, ys = zip(*(px(a, b, z) for a, b in fitp))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    x0, y0 = cx - W / 2, cy - H / 2
    img = Image.new("RGB", (W, H), "#e8eef3")
    for tx in range(int(x0 // 256), int((x0 + W) // 256) + 1):
        for ty in range(int(y0 // 256), int((y0 + H) // 256) + 1):
            if 0 <= ty < 2 ** z:
                img.paste(tile(z, tx, ty), (int(tx * 256 - x0), int(ty * 256 - y0)))
    img = Image.blend(img, Image.new("RGB", (W, H), "#ffffff"), 0.25)  # soften so the route reads first
    d = ImageDraw.Draw(img)
    to = lambda a, b: (px(a, b, z)[0] - x0, px(a, b, z)[1] - y0)
    route = [to(a, b) for a, b in line] if line else []
    if len(route) > 1:
        d.line(route, fill="#ffffff", width=9, joint="curve")
        d.line(route, fill="#be2e21", width=5, joint="curve")
    nums = nums or list(range(1, len(points) + 1))
    f, fl = font(22 if W > 700 else 19), font(20 if W > 700 else 17)
    groups = {}  # pins within 30 px share one marker: "3/4"
    for n, (a, b), lab in zip(nums, points, labels or [""] * len(points)):
        x, y = to(a, b)
        if not (-40 < x < W + 40 and -40 < y < H + 40):
            continue
        key = next((k for k in groups if abs(k[0] - x) < 30 and abs(k[1] - y) < 30), (x, y))
        g = groups.setdefault(key, {"n": [], "names": []})
        if n not in g["n"]:
            g["n"].append(n)
        if lab and lab not in g["names"]:
            g["names"].append(lab)
    marks, boxes = [], []
    for (x, y), g in groups.items():
        label = "/".join(map(str, g["n"]))
        r = 17 if len(label) < 3 else 26
        marks.append((x, y, r, label, " · ".join(g["names"])))
        boxes.append((x - r - 3, y - r - 3, x + r + 3, y + r + 3))
    hit = lambda bx: any(not (bx[2] < o[0] or bx[0] > o[2] or bx[3] < o[1] or bx[1] > o[3]) for o in boxes)
    unplaced = []
    for x, y, r, num, name in marks:  # labels: right, left, below, above; never over a pin or label
        if not name:
            continue
        name = name if len(name) <= 44 else name[:43] + "…"
        tw = d.textlength(name, font=fl) + 16
        for bx in ((x + r + 6, y - 16, x + r + 6 + tw, y + 16), (x - r - 6 - tw, y - 16, x - r - 6, y + 16),
                   (x - tw / 2, y + r + 6, x + tw / 2, y + r + 38), (x - tw / 2, y - r - 38, x + tw / 2, y - r - 6)):
            if bx[0] >= 4 and bx[2] <= W - 4 and bx[1] >= 4 and bx[3] <= H - 30 and not hit(bx):
                d.rounded_rectangle(bx, radius=6, fill="#ffffff", outline="#0d2238", width=1)
                d.text((bx[0] + 7, (bx[1] + bx[3]) / 2), name, fill="#0d2238", font=fl, anchor="lm")
                boxes.append(bx)
                break
        else:
            unplaced.append(num)
    for x, y, r, label, _ in marks:
        d.ellipse((x - r - 3, y - r - 3, x + r + 3, y + r + 3), fill="#ffffff")
        d.ellipse((x - r, y - r, x + r, y + r), fill="#0d2238")
        d.text((x, y), label, fill="#ffffff", font=f if len(label) < 4 else font(17), anchor="mm")
    if attribution:  # required by the OpenStreetMap licence
        att, fa = "© OpenStreetMap contributors", font(14)
        tw = d.textlength(att, font=fa)
        d.rectangle((W - tw - 16, H - 26, W, H), fill="#ffffff")
        d.text((W - tw - 8, H - 13), att, fill="#333333", font=fa, anchor="lm")
    return img, z, to, unplaced


def draw_map(points, line, path, labels=None, size=(1200, 760)):
    """The day or trip map. When several stops sit too close to tell apart (an old town, a palace and
    the market opposite), a zoomed inset shows them, so every stop is readable."""
    W, H = size
    img, z, to, _ = render(points, line, labels, size)
    # find the stops that share a marker on the main map
    xy = [to(a, b) for a, b in points]
    close = sorted({i for i in range(len(points)) for j in range(len(points))
                    if i != j and abs(xy[i][0] - xy[j][0]) < 30 and abs(xy[i][1] - xy[j][1]) < 30
                    and haversine(points[i], points[j]) > 0.05})
    if close:  # draw again with the cluster labelled "see close-up", then add the close-up
        main_labels = [("See close-up" if i in close else l) for i, l in enumerate(labels or [""] * len(points))]
        img, z, to, _ = render(points, line, main_labels, size)
        cpts = [points[i] for i in close]
        iw, ih = 470, 330
        inset, iz, _, _ = render(points, line, labels, (iw, ih), fit=cpts, attribution=False, max_zoom=17)
        if iz > z:
            cx = sum(xy[i][0] for i in close) / len(close)
            cy = sum(xy[i][1] for i in close) / len(close)
            # the corner furthest from the cluster
            corners = [(16, 16), (W - iw - 16, 16), (16, H - ih - 46), (W - iw - 16, H - ih - 46)]
            ox, oy = max(corners, key=lambda c: (c[0] + iw / 2 - cx) ** 2 + (c[1] + ih / 2 - cy) ** 2)
            d = ImageDraw.Draw(img)
            d.rectangle((cx - 34, cy - 34, cx + 34, cy + 34), outline="#0d2238", width=3)
            d.line((cx, cy, ox + iw / 2, oy + ih / 2), fill="#0d2238", width=2)
            d.rectangle((ox - 4, oy - 4, ox + iw + 4, oy + ih + 4), fill="#0d2238")
            img.paste(inset, (ox, oy))
            d.rectangle((ox, oy, ox + 92, oy + 26), fill="#0d2238")
            d.text((ox + 8, oy + 13), "Close-up", fill="#ffffff", font=font(15), anchor="lm")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "WEBP", quality=84)
    print(f"  map    {path.name}  (zoom {z}{', with close-up' if close else ''})")


# ---------------------------------------------------------------- photos
def strip(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", h or ""))).strip()


def commons_info(params):
    polite("commons", 0.5)
    base = {"action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1600}
    r = S.get("https://commons.wikimedia.org/w/api.php", params={**base, **params}, timeout=30)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    return sorted(pages.values(), key=lambda p: p.get("index", 0))


def usable(p, need_landscape=True):
    ii = (p.get("imageinfo") or [{}])[0]
    meta = ii.get("extmetadata", {})
    lic = strip(meta.get("LicenseShortName", {}).get("value", "")).lower()
    if not ii or ii.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
        return None
    if not any(l in lic for l in OK_LICENCES) or "nc" in lic.split() or "nd" in lic.split():
        return None
    if need_landscape and (ii["width"] < 1200 or ii["width"] < ii["height"] * 1.25):
        return None
    return {"file": p["title"], "src": ii.get("thumburl") or ii["url"], "page": ii["descriptionurl"],
            "author": strip(meta.get("Artist", {}).get("value", ""))[:80] or "Unknown",
            "licence": strip(meta.get("LicenseShortName", {}).get("value", "")),
            "licence_url": meta.get("LicenseUrl", {}).get("value", "")}


def pexels(query):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    polite("pexels", 0.5)
    r = S.get("https://api.pexels.com/v1/search", params={"query": query, "orientation": "landscape", "per_page": 15},
              headers={"Authorization": key}, timeout=30)
    r.raise_for_status()
    return [{"file": f'pexels:{p["id"]}', "src": p["src"]["large2x"], "page": p["url"],
             "author": p["photographer"], "licence": "Pexels licence", "licence_url": "https://www.pexels.com/license/",
             "provider": "Pexels"} for p in r.json().get("photos", []) if p["width"] >= 1200]


def pixabay(query):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    polite("pixabay", 0.7)
    r = S.get("https://pixabay.com/api/", params={"key": key, "q": query[:100], "image_type": "photo",
              "orientation": "horizontal", "min_width": 1200, "safesearch": "true", "per_page": 15}, timeout=30)
    r.raise_for_status()
    return [{"file": f'pixabay:{h["id"]}', "src": h["largeImageURL"], "page": h["pageURL"], "author": h["user"],
             "licence": "Pixabay licence", "licence_url": "https://pixabay.com/service/license-summary/",
             "provider": "Pixabay"} for h in r.json().get("hits", [])]


def openverse(query):
    """Openverse (WordPress) indexes openly licensed photos from Flickr, museums and more. No key needed."""
    polite("openverse", 1.0)
    r = S.get("https://api.openverse.org/v1/images/", params={"q": query, "license": "by,by-sa,cc0,pdm",
              "aspect_ratio": "wide", "size": "large", "mature": "false", "page_size": 20}, timeout=30)
    r.raise_for_status()
    out = []
    for h in r.json().get("results", []):
        if (h.get("width") or 0) < 1200:
            continue
        lic = f'CC {h["license"].upper()} {h.get("license_version") or ""}'.strip() if h["license"] not in ("cc0", "pdm") \
            else ("CC0" if h["license"] == "cc0" else "Public domain")
        out.append({"file": f'openverse:{h["id"]}', "src": h["url"], "page": h.get("foreign_landing_url") or h["url"],
                    "author": (h.get("creator") or "Unknown")[:80], "licence": lic,
                    "licence_url": h.get("license_url", ""), "provider": h.get("source", "Openverse").title()})
    return out


def commons(query):
    hits = [usable(p) for p in commons_info({"generator": "search", "gsrsearch": f"{query} filetype:bitmap",
                                             "gsrnamespace": 6, "gsrlimit": 20})]
    return [dict(h, provider="Wikimedia Commons") for h in hits if h]


PROVIDERS = {"pexels": pexels, "pixabay": pixabay, "openverse": openverse, "commons": commons}
DEFAULT_PROVIDERS = ["pexels", "pixabay", "commons", "openverse"]


def given_photo(spec):
    """A photo chosen by hand: hotel or tourism-board website, a blog (with the owner's OK), Unsplash..."""
    return {"file": spec["url"], "src": spec["url"], "page": spec.get("page") or spec["url"],
            "author": spec.get("credit", ""), "licence": spec.get("licence", "Courtesy of the owner"),
            "licence_url": spec.get("licence_url", ""), "provider": spec.get("source", "")}


def find_photo(query, t, photos, refresh, given=None):
    if given:
        return given_photo(given)
    pinned = t.get("photo_files", {}).get(query)
    if query in photos and photos[query] and not refresh and (not pinned or photos[query].get("file") == pinned):
        return photos[query]
    hits = []
    if pinned:
        hits = [dict(h, provider="Wikimedia Commons") for h in
                (usable(p, need_landscape=False) for p in commons_info({"titles": pinned})) if h]
    else:
        for name in t.get("photo_providers", DEFAULT_PROVIDERS):
            try:
                hits = PROVIDERS[name](query)
            except requests.RequestException as e:
                print(f"  ⚠ {name} failed for {query!r}: {e}")
            if hits:
                break
    photos[query] = hits[0] if hits else None
    print(f'  photo  {query!r:40} -> {(hits[0]["provider"] + " " + hits[0]["file"]) if hits else "none found"}')
    return photos[query]


def save_photo(info, path, refresh):
    if path.exists() and not refresh:
        return
    polite("commons-img", 0.5)
    r = S.get(info["src"], timeout=60)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    im.thumbnail((1600, 1600))
    # crop to 16:9 from the centre so every day photo has the same shape
    w, h = im.size
    th = int(w * 9 / 16)
    if h > th:
        top = (h - th) // 2
        im = im.crop((0, top, w, top + th))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=80)


def contact_sheet(slug, files):
    """One image of every photo chosen, to look at before publishing."""
    if not files:
        return
    ims = [Image.open(f).resize((400, 225)) for f in files]
    cols = 3
    sheet = Image.new("RGB", (cols * 410 + 10, ((len(ims) + cols - 1) // cols) * 260 + 10), "white")
    d = ImageDraw.Draw(sheet)
    for i, (im, f) in enumerate(zip(ims, files)):
        x, y = 10 + (i % cols) * 410, 10 + (i // cols) * 260
        sheet.paste(im, (x, y))
        d.text((x, y + 230), f.name, fill="black", font=font(14))
    sheet.save(MEDIA / slug / "contact_sheet.jpg", quality=80)


# ---------------------------------------------------------------- per tour
def day_stops(t, d):
    return d.get("route") or d.get("places") or []


def photo_query(d):
    if "photo_query" in d:
        return d["photo_query"]
    for p in d.get("places", []):
        if not re.search(r"airport|hotel|resort|station", p, re.I):
            return p
    return None


def short(t, name):
    """The label printed on a map: a short name from the tour file, or the place name itself."""
    return t.get("map_labels", {}).get(name, name)


def fingerprint(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:10]


def run(t, refresh=False):
    slug = t["slug"]
    print(f"\n== {slug}")
    geo, routes, photos = load("geo.json"), load("routes.json"), load("photos.json")
    out = MEDIA / slug
    manifest = {"days": {}, "photos": {}}
    CHECKS.clear()
    try:
        # trip overview: the stops of the whole journey, in order
        names = list(dict.fromkeys(t.get("route", [])))
        pts = {n: geocode(n, t, geo, refresh) for n in names}
        for d in t["days"]:
            for n in day_stops(t, d) + d.get("places", []):
                if n not in pts:
                    pts[n] = geocode(n, t, geo, refresh)
        check_spread(t, pts)
        # a pin that is not verified never goes on a map or into directions
        pts = {n: (p if CHECKS.get(n, {}).get("status") in ("OK", "PINNED") else None) for n, p in pts.items()}
        out.mkdir(parents=True, exist_ok=True)
        manifest["pins_to_check"] = places_report(slug, t)
        manifest["coords"] = {n: p for n, p in pts.items() if p}
        ov = [(n, pts[n]) for n in names if pts.get(n)]
        if len(ov) >= 2:
            fp = fingerprint([p for _, p in ov], names, 4)
            f = out / f"map-overview-{fp}.webp"
            if refresh or not f.exists():
                draw_map([p for _, p in ov], None, f, labels=[short(t, n) for n, _ in ov])
            manifest["overview"] = {"map": f.name, "stops": [n for n, _ in ov]}

        for i, d in enumerate(t["days"], 1):
            entry = {}
            stops = [(n, pts.get(n)) for n in day_stops(t, d)]
            missing = [n for n, p in stops if not p]
            stops = [(n, p) for n, p in stops if p]
            if missing:
                entry["unverified"] = missing
            if len(stops) >= 2 and not missing:
                rt = road_route([p for _, p in stops], routes, refresh)
                fp = fingerprint([p for _, p in stops], [n for n, _ in stops], bool(rt), 4)
                f = out / f"map-day-{i}-{fp}.webp"
                if refresh or not f.exists():
                    draw_map([p for _, p in stops], rt and rt["line"], f, labels=[short(t, n) for n, _ in stops])
                entry.update(map=f.name, stops=[n for n, _ in stops], km=rt and rt["km"])
            q = photo_query(d)
            if q or d.get("photo"):
                info = find_photo(q, t, photos, refresh, d.get("photo"))
                if info:
                    f = out / f"day-{i}-{fingerprint(info['file'])}.webp"
                    save_photo(info, f, refresh)
                    entry["photo"] = dict(info, img=f.name)
            manifest["days"][str(i)] = entry
        for j, h in enumerate(t.get("hotels") or [t.get("hotel", {})], 1):
            if h.get("photo"):  # hotels: only the hotel's own image, never a search
                info = given_photo(h["photo"])
                f = out / f"hotel-{j}-{fingerprint(info['file'])}.webp"
                save_photo(info, f, refresh)
                manifest["photos"][f"hotel-{j}"] = dict(info, img=f.name)
    finally:
        save("geo.json", geo); save("routes.json", routes); save("photos.json", photos)

    # remove media no longer referenced, then write the manifest build.py reads
    used = {manifest.get("overview", {}).get("map")} | {p["img"] for p in manifest["photos"].values()}
    used |= {v.get(k, {}).get("img") if k == "photo" else v.get(k) for v in manifest["days"].values() for k in ("map", "photo")}
    for f in out.glob("*.webp"):
        if f.name not in used:
            f.unlink()
    contact_sheet(slug, sorted(out.glob("day-*.webp"), key=lambda p: int(p.name.split("-")[1])))
    (out / "media.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    refresh = "--refresh" in sys.argv
    for p in sorted((ROOT / "data/tours").glob("*.json")):
        t = json.loads(p.read_text())
        if not args or t["slug"] in args:
            run(t, refresh)

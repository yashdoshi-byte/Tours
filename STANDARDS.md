# Blue Diamond Voyage: tour page rulebook

This is the rulebook for every itinerary published on the tour site. Every rule here comes from the
Blue Diamond Voyage travel pack, adapted for a public web page. Follow it for each new tour, and for each
change to an existing one. `python3 build.py` checks most of these rules on its own (see section 17),
and it will not publish a page that breaks a hard rule.

**The house voice.** Every page is written by a consultant with eight years of worldwide experience,
who has personally checked the timings, the distances and the local sensitivities. Blue Diamond Voyage &
Vision Pvt. Ltd. is the name on every page. Glocalique (creative tour design for agencies and event
planners) and Luxury Honeymoon UK (with the National Asian Wedding Show) use the same voice.

---

## 0 · One template, never hand-built

* Every tour is one data file, `data/tours/<slug>.json`. Copy `bali-honeymoon-nusa-dua.json` as the
  worked example.
* The design lives in `templates/` and `assets/style.css`. Change it there, once, and every page
  updates. Never style one tour by hand.
* If the template truly cannot show something, add an optional field to the template and document it
  here. Never fork the template for one tour.
* The cover design does not change from tour to tour.

## 1 · Intake: ask before building

Before writing a tour, get from Yash:

* The tour's source: the itinerary PDF, the operator's or package document, notes or the brief.
  If the package wording must be kept word for word, say so in the data file.
* Who the tour is for: honeymooners, families with children, older travellers, groups. A five-year-old
  and a grandmother change the plan, not just the rooming.
* The dietary angle to cover: Jain, vegan, vegetarian, halal; and whether alcohol belongs in it.
* Mobility and pace: how much walking, stairs, heat.
* Where the audience lives and comes from. An Indian family living in the USA wants different things
  pointed out than one flying from Rajkot.
* Whether a vehicle is included, for how many days, and what it excludes.
* One or two clean landscape photos with no text on them, if Yash has them, and the hotel's own website.

## 2 · Research before building

Read every document given. Then verify by search everything that changes with the date, and write the
date checked in `facts_checked`:

* The **closed day** and **opening hours** of every attraction.
* What happens to a **late arrival** on each timed ticket.
* **Public holidays and festivals** in the season, in both directions: a festival can be a gift
  (Dussehra lights, a flamenco biennial) or a warning (Gandhi Jayanti queues, Nyepi closing Bali).
* **Sunrise, sunset and typical weather**, quoted as "about".
* Restaurant opening days, and whether the kitchen can cook to the brief.
* Fares, entry fees, levies and transport rules, always written as "about".
* **Official sources first**: the venue's own site, the tourism board, the embassy or consulate,
  the government portal. A blog is a lead to check, never the source.

Never start the data file until the facts are in hand.

## 3 · The build

```bash
cp data/tours/bali-honeymoon-nusa-dua.json data/tours/<slug>.json   # start from the worked example
python3 tools/media.py <slug>     # coordinates, road routes, map images, photos (needs internet)
#   LOOK at media/<slug>/contact_sheet.jpg before going further
python3 build.py                  # builds docs/ and runs every rule check in section 17
python3 build.py --strict         # warnings become errors; use before publishing
```

`tools/media.py` needs internet access to OpenStreetMap and Wikimedia. When it cannot run on the
computer you are using, push the branch: the GitHub workflow "Build tour media" runs it on GitHub and
commits the results to the same branch.

## 4 · Readability

The site is read on phones, often by older travellers.

* Body text is 17 px on desktop and 16 px on a phone. Never smaller than 14 px anywhere.
* **Short sentences, one idea each.** "About twenty minutes", never "~20m".
* **Nothing important in grey.** Times, gates, phone numbers and warnings go in bold or in a callout.
* **A day is 5 to 9 entries** (fewer is fine on arrival, departure and free days). More is not a day,
  it is a march: split it, or move something to "if you have an hour".
* No arrows, stars, ticks or emoji typed into the text. Write stars as words
  ("Five-star · Luxury Collection") and use `»` for an arrow.

## 5 · How a day is written

The day is **stacked**: the time is a label above each entry, not a column beside it.

```json
{
  "pill": "Arrival day",
  "title": "Land in Seville, then the Alcázar and the river",
  "summary": "One line for Google: what the day is.",
  "strip": ["About 29° / 16°", "Sunset about 20:10", "Drive about 30 minutes", "Walking about 3 km"],
  "route": ["Hotel name", "First stop", "Second stop", "Hotel name"],
  "photo_query": "Real Alcazar Seville",
  "rows": [
    {"label": "13:30 · timed ticket", "flag": "be on time",
     "title": "Real Alcázar · enter at the Puerta del León",
     "text": "Palace rooms first, then the shaded gardens. About two hours.",
     "bullets": ["Be at the gate ten minutes early."],
     "notes": [["CARE", "Carry your passport: photo ID can be asked for."],
               ["TIME", "Entry from 15 minutes before to 30 minutes after your slot."]],
     "meal": ["Lunch", "Not included", "About €20 to €25 per person"]}
  ],
  "places": ["Real Alcázar de Sevilla", "Hotel Alfonso XIII"],
  "note": "What a friend who lives there would add."
}
```

* **The title names the day.** "Land in Seville, then the Alcázar and the river", never
  "Day 1 sightseeing". A reader should find a day by its name.
* **The `pill`** says what kind of day it is: Arrival day, Transfer day, Full day, Easy day,
  Free day, Activity day, Departure.
* **The `strip`** carries the fixed points: weather, sunset, drive time, check-in, how far they walk.
  Five items at most.
* **Every entry answers "then what?"**: the time, the gate to enter by, how long it takes, what to see
  first inside.
* **Say how long and how far.** "About two hours", "eight minutes on foot from lunch", "about €20 by
  taxi, 25 minutes".
* **Risk goes in a `CARE` callout**, never buried in prose.
* **Meals always say included or not**, and roughly what they cost.
* **Name the restaurant, the street and the dish.**
* **Say who they will meet**: the driver with the name sign, the guide at the gate.
* **One concierge note per day** (`note`), in our voice: festivals, closures, what to pack tonight,
  tomorrow's pick-up time.
* **`route`** lists the day's stops in the order driven, start and end included. It draws the day's
  road map and the "Open this route in Google Maps" button. Without it, `places` is used.
* **`places`** lists everything the reader has to find that day. Each becomes a Google Maps pin.

**Callout taxonomy.** The colour always means the same thing, on every page:

| Tag | Means |
|---|---|
| `TIP` / `NOTE` | our advice |
| `CARE` | what goes wrong if ignored |
| `TIME` | entry windows, last admission, timings that matter |
| `WEAR` | dress code and weather |
| `KIDS` | the children's version |
| `EAT` / `BUY` | what to order, what to take home |
| `MONEY` | cash, tipping, deposits, levies, city tax |

## 6 · The running order of a page

| Section | Data field(s) | Required |
|---|---|---|
| Cover: style, title, tagline, quote buttons | `style`, `title`, `tagline`, `hero_image` | yes |
| Facts bar | `duration`, `facts` | yes |
| Journey: intro, stays ribbon, highlights | `intro`, `stays`, `highlights` | yes |
| At a glance: one line per day, the trip map, the route | `days`, `route` | yes |
| Day cards: photo, strip, entries, route map, pins, concierge note | `days[]` | yes |
| Where you stay | `hotel` | yes |
| Included / not included | `included`, `excluded` | yes |
| Visa, entry and phones | `entry`, `entry_notes` | international tours |
| Good to know, and the emergency block | `good_to_know`, `emergency` | yes |
| Dining for dietary briefs, and the food card | `dining`, `dining_avoid`, `food_card` | when relevant |
| If you have an hour | `extras` | optional |
| Best time to go | `best_time`, `seasons` | yes |
| FAQs | `faqs` | yes, 4 or more |
| Sign-off: personalised quote | `price_note` | yes |
| Photo and map credits | made by the build | automatic |

A short city break may leave out the optional sections. The page still builds.

## 7 · "Good to know": house standards

These appear on nearly every page. Get the numbers for the destination, but keep the advice:

* **Hotel deposit**: use a **credit card** for the deposit or pre-authorisation at check-in,
  **never a forex or debit card**. Forex cards cannot hold funds, hotels often refuse them, and a credit
  card hold is released back faster and more safely.
* **City or tourism tax**: paid at the hotel, per person per night. Give the approximate amount and a
  total for the stay, e.g. "Barcelona €9.24 per person per night (3 nights ≈ €55 for two)". Say where it is nil.
* **Card machines**: always choose the **local currency**, never "pay in INR / USD". Say what tipping is
  actually expected.
* **Cash**: how much a day, and what still needs it (markets, taxis, temples). Note local charges that
  surprise, such as Italy's coperto.
* **Timed tickets**: the entry window, and what happens if late.
* **Dress code**: temples, churches, mosques: shoulders and knees, shoes off, no photography where forbidden.
* **Pickpockets**: name the actual squares, stations and queues.
* **Plugs, voltage, tap water, meal times, kitchen closing hours.**
* **Emergency block**: the local emergency number, the Indian embassy or consulate with address and
  phone, and the Blue Diamond Voyage 24/7 desk (added automatically from `data/site.json`).

## 8 · Dietary briefs

Where a dietary angle exists, it shapes the whole page, not one section.

* **Jain**: no onion, garlic, ginger, potato, sweet potato, carrot, beetroot, mushrooms or any root or
  tuber. **Jain + vegan** adds no dairy (butter, cream, cheese, ghee), no egg, no honey.
* Give **cuisine variety**, not five Indian restaurants.
* For each restaurant: **cuisine, address, phone, closed days** (`open_daily: false` shows it in red)
  **and exactly what to order**, with the local-language qualifier ("pizza *sin mozzarella*").
* Name what to **avoid and why** (`dining_avoid`): gazpacho starts with garlic; falafel has onion;
  Balinese spice paste has shallot and garlic.
* Add a **food card** in the local language plus Hindi for Indian restaurants.
* Always say **"ask for it to be cooked fresh"**: sauces are made ahead.
* If the audience does not drink, cut wine-based activities and say which drinks contain alcohol.

## 9 · Yash's own contacts

When a restaurant or supplier knows Yash personally, say so in the reader's words: "Ask for Mr. Jatinder
Gill: he knows Mr. Yash Doshi & Blue Diamond Voyage." Never drop one in an edit, and **never invent one**.

## 10 · Packages: reproduce, do not improve

When a tour comes from a package or an operator's document:

* **Include only the sightseeing the package lists.** Do not add attractions because they are nearby
  or famous. Optional extras go in `extras` and are labelled optional.
* **Reproduce a restriction in the package's own words.**
* **State the exclusions plainly** in `excluded`: what the vehicle does not cover, rides, ropeways,
  adventure activities, entry fees, guide charges, lunches, heaters, anything personal.
* **Parking and last-motorable-point limits** go in the vehicle entry, not as a surprise on the day.
* **Do not invent operational advice.** No "the driver pays the toll", no "pack warm clothes" unless
  the operator says it or you have verified it.
* Keep the route map to the places in the package. No extra cities.
* Fix anything that does not work on the ground, and say why (for example, a scuba day trip to Lombok
  from Nusa Dua).

## 11 · Families and children

* A `KIDS` callout on the moments that belong to the children, and lighter afternoons built in.
* **Original photo ID for every guest, including children**, at check-in. NRIs and foreign nationals
  carry passports.
* Height restrictions at theme parks, last entry times, what a child's meal includes.

## 12 · Transfers, trains and self-drive

* Every transfer: from, to, the pick-up trigger ("flight lands", "hotel lobby 07:45").
* **The driver waits with a name sign**, at hotels for about ten minutes. Say so.
* If immigration is quick, the reader **waits**: the driver cannot come early.
* Trains: operator, boarding closes a couple of minutes before departure, bags scanned, be there
  30 minutes early.
* Self-drive: car park to car park, with distance, driving time and the roads. The day's `route`
  gives the Google Maps directions link.
* Border crossings: passports ready, 5 to 10 minutes, what to have open on the phone.

## 13 · Flights

Public pages name the flight time and airports only in general terms ("flights from Mumbai and Delhi
connect through Singapore or Kuala Lumpur, about 9 to 11 hours"). Never a fare, PNR or fare basis.
Say web check-in opens 24 hours before, 48 for some carriers.

## 14 · Visas and entry

* A table of entry permits: country, permit, who it covers, approximate cost.
* Say plainly that **we arrange the paperwork** and share documents on the WhatsApp group before departure.
* Biometric or arrival-card steps at first entry, and the extra time to allow.
* Phone and internet compared: eSIM before flying, local SIM, home roaming, with the trade-off on
  keeping their own number.
* Currency: where to exchange and which currencies are needed.

## 15 · Links and photographs: official sources only

* **Reference links** go to the venue's or operator's own site, an official tourism board, an embassy,
  or a government portal. Never an OTA, aggregator, Wikipedia or blog.
* **Google Maps pins on everything the reader has to find**: hotels, airports, stations, attractions,
  restaurants, meeting points. Each day's `places` become pins; each day's `route` becomes a
  directions link.
* **Where photographs come from**, in this order:
  1. **Chosen by hand** in the tour file (`"photo"` on a day or on the hotel):
     the hotel's or operator's **own website** or press page, an **official tourism board** media
     library, a **free photo site** (Unsplash, Pexels, Pixabay), or a **blog, only with the owner's
     written OK**. Record where it came from:
     `"photo": {"url": "<image url>", "page": "<page it is on>", "credit": "<owner>", "source": "<site name>", "licence": "<terms>"}`.
     Photos on hotel sites, tourism boards and blogs are copyrighted: use hotel and tourism-board photos
     to promote that hotel or destination only, and never a blog photo without permission.
  2. **Searched automatically** by `tools/media.py`: Pexels and Pixabay (when their free API keys are
     set as GitHub secrets `PEXELS_API_KEY` and `PIXABAY_API_KEY`), then Wikimedia Commons, then
     Openverse. Open licences only (Pexels and Pixabay licences, CC BY, CC BY-SA, CC0, public domain).
* Every photo is **credited under the photo and in the credits section**, with author, licence and a
  link to the page it came from. The build does this from `data/cache/photos.json`.
* Look at `media/<slug>/contact_sheet.jpg` before publishing: a search can return the wrong temple or a
  snowy day. Fix a bad pick by choosing one by hand (`"photo"`), or with
  `"photo_files": {"<query>": "File:<exact Commons name>.jpg"}`.
* **A photo search never chooses a hotel photograph.** Hotel, tour and vehicle photos come only from
  the property's or operator's own website or press page, its official Google Business listing, or the
  booking actually made. If none is in hand, show the hotel card without a photo. A neighbourhood
  picture captioned as the hotel is noticed on arrival. A hotel photo links to the hotel's own site
  (`hotel.website`).
* **No photo with text, a watermark, or identifiable people as the subject.**
* Hero images: landscape, `.webp` or `.jpg`, no baked-in text.

## 16 · Maps and coordinates: precision is critical

The maps tell travellers where they are going, so every pin must be right.

* **Coordinates are never typed from memory.** `tools/media.py` looks every place up in OpenStreetMap
  (Nominatim), restricted to the tour's country (`country_code`) and to the tour's area
  (`bbox`: `[south, west, north, east]`, e.g. Bali `[-8.86, 114.42, -8.05, 115.72]`), and saves it in
  `data/cache/geo.json` with the address it matched. A pin outside the box is marked CHECK.
* When OpenStreetMap spells a place differently, give the search name in
  `"geo_query": {"Tegalalang Rice Terrace": "Tegallalang Rice Terrace"}`; the page keeps our spelling.
* **Every pin is verified two ways**: the name OpenStreetMap returns must share the distinctive words of
  our place name, and the pin must lie within 250 km of the rest of the trip. A pin that fails either
  is marked **CHECK**; a place not found is marked **NOT FOUND**.
* **The pin list is approved before publishing.** `media/<slug>/places.md` lists every place, its
  coordinates, the address matched, its status, and a Google Maps link to check it. It is also shown in
  the GitHub run summary. The build warns while any pin needs checking, and `--strict` refuses.
* **Fix a pin in the tour file**, never in code: `"geo": {"<place>": [lat, lon, "<where it came from>"]}`,
  with the coordinates copied from the place's own Google Maps page (right-click the exact gate, jetty or
  entrance), or from the hotel's own listing on its website or a booking site. Pinned places show as
  PINNED with their source.
* **A pin that is not verified never reaches the page.** A day whose stops are not all OK or PINNED gets
  no map and no directions button until it is fixed, and the build warns.
* **Pin the point the traveller actually goes to**: the temple's entrance car park, the jetty, the
  hotel lobby, the meeting point, not the middle of a park.
* Each day lists its stops in driving order in `route`, start and end included. The day map draws the
  **real road route** (OSRM on OpenStreetMap data), with **numbered pins and name labels**, and a legend
  with the distance by road between stops. A round trip shows one pin numbered "1/5".
* **"Open this route in Google Maps"** uses the exact coordinates of every stop, so Google navigates to
  the verified pin, not to a same-name place.
* The trip map shows every stop of the journey in order, numbered and labelled.
* Short map labels come from `"map_labels": {"<place>": "Your resort"}`.
* Distances are by road; drive times on the page come from our experience of local traffic, written as
  "about".
* Every map image carries "© OpenStreetMap contributors", as the licence requires.
* Keep each map to the places in the trip.

## 17 · The rule checks (run by `build.py`)

**Errors, the page will not build:**
* a price, rate or "₹ / Rs / INR / USD" amount in the package description (`price_note` must say
  "Contact us for a personalised quote")
* `meta_title` over 60 characters or `meta_description` over 160
* a callout tag outside the taxonomy in section 5
* a meal without "Included" or "Not included"
* a day without a `title`, or with a generic title ("Day 3", "Sightseeing")
* a forbidden character in the text (arrows, stars, ticks, emoji)
* an internal note left in (`TODO`, `TBC`, `net rate`, `supplier`)

**Warnings, fix before publishing (`--strict` makes them errors):**
* a day with more than 9 entries, or a strip with more than 5 items
* a day with no concierge note, no `places`, or no route map
* fewer than 4 FAQs; no `good_to_know`; no `emergency` block on an international tour
* no `facts_checked` date, or one older than 12 months
* a day photo or map missing because `tools/media.py` has not run
* any map pin marked CHECK or NOT FOUND in `media/<slug>/places.md`

## 18 · When Yash asks for changes

* Apply the list **literally and completely**, then rebuild and run the checks.
* A named restaurant or viewpoint to add or remove is exact: remove the one named, add the one named,
  keep the rest.
* **"Remove …" usually means invented advice.** Delete the line; do not rewrite it more cautiously.
* **"Highlight it"** means a `CARE` callout.
* A stated time replaces whatever was planned, and the entries around it move to suit.
* When a private guide is included, do not also mention the audio guide.
* Visual requests (bigger text, spacing, a different day layout) are template changes, never hand edits
  to one page.
* Say in one line what changed since the last version.

## 19 · Before a page goes live

* `python3 build.py --strict` passes with no warnings.
* The page is **looked at on a desktop and a phone**. Every mistake ever shipped was visible in the
  render and invisible in the data.
* The contact sheet of photos is looked at; the overview and day maps are looked at.
* **The pin list (`media/<slug>/places.md`) is approved**: no CHECK or NOT FOUND left.
* Two or three Google Maps pins and one directions button are clicked by hand.
* Hotel names and place names are spelled exactly as in the source document.
* **No package prices, no net rates, no supplier names, no internal notes.**
* The page carries the enquiry phone, WhatsApp, the 24/7 desk +91 98242 21400 and
  instagram.com/bluediamondvoyage (from `data/site.json`).
* The change is added to the change log in the website admin guide.

import json, re, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import date
from pathlib import Path

CFG = Path("settings.json")
CACHE = Path("osm_cache.json")
UA = {"User-Agent": "ShawonClientFinder/3.0 (freelancer lead research)", "Accept": "*/*"}
CATS = {
    "restaurant": '["amenity"="restaurant"]', "cafe": '["amenity"="cafe"]',
    "clothing shop": '["shop"="clothes"]', "salon / beauty": '["shop"~"hairdresser|beauty"]',
    "clinic / dentist": '["amenity"~"clinic|dentist|doctors"]', "gym": '["leisure"="fitness_centre"]',
    "hotel": '["tourism"="hotel"]', "school / coaching": '["amenity"~"school|kindergarten|college"]',
    "real estate": '["office"="estate_agent"]', "pharmacy": '["amenity"="pharmacy"]',
    "electronics shop": '["shop"="electronics"]', "furniture shop": '["shop"="furniture"]',
    "bakery": '["shop"="bakery"]', "auto repair": '["shop"="car_repair"]',
    "travel agency": '["office"="travel_agent"]', "supermarket": '["shop"="supermarket"]',
    "marketing agency": '["office"~"advertising|marketing"]',
    "design agency": '["office"~"graphic_design|design"]',
    "software company": '["office"="it"]', "law firm": '["office"="lawyer"]',
    "accounting firm": '["office"="accountant"]',
    "construction company": '["office"~"construction|architect"]',
    "car dealer": '["shop"="car"]', "veterinary clinic": '["amenity"="veterinary"]',
    "photography studio": '["craft"="photographer"]',
    "event company": '["office"="event_management"]',
    "fitness studio": '["leisure"~"fitness_centre|sports_centre"]'}


def load_cfg():
    try: return json.loads(CFG.read_text(encoding="utf-8"))
    except Exception: return {}

def save_cfg(d): CFG.write_text(json.dumps(d, indent=2), encoding="utf-8")

def http(url, data=None, headers=None, timeout=15):
    h = dict(UA); h.update(headers or {})
    if isinstance(data, (dict, list)): data = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    elif isinstance(data, str): data = data.encode()
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=timeout) as r:
        return r.status, r.read(500000).decode("utf-8", "replace"), r.geturl(), time.time() - t0


# ---------- Lead sources ----------
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://overpass.openstreetmap.ru/cgi/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://api.openstreetmap.fr/oapi/interpreter",
)


def _cache_get(key):
    try:
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        hit = d.get(key)
        if hit and time.time() - hit.get("ts", 0) < 24 * 3600:
            return hit.get("rows")
    except Exception:
        pass
    return None


def _cache_put(key, rows):
    try:
        try:
            d = json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        d[key] = {"ts": time.time(), "rows": rows}
        CACHE.write_text(json.dumps(d), encoding="utf-8")
    except Exception:
        pass


LAST_ERRORS = []


def _overpass_one(endpoint, q):
    """Try POST first, then GET — different networks/middleboxes treat them differently."""
    try:
        _, body, _, _ = http(endpoint, data=urllib.parse.urlencode({"data": q}),
                             headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
        return json.loads(body)
    except Exception:
        url = endpoint + "?" + urllib.parse.urlencode({"data": q})
        _, body, _, _ = http(url, timeout=30)
        return json.loads(body)


def _race_overpass(q):
    """Ask all mirrors at once; return the first valid answer, else None.
    Hard cap ~35s so a search never spins forever. Per-server errors are
    collected in LAST_ERRORS so a failure message can say what really happened."""
    global LAST_ERRORS
    LAST_ERRORS = []
    pool = ThreadPoolExecutor(max_workers=len(OVERPASS_ENDPOINTS))
    try:
        futs = {pool.submit(_overpass_one, ep, q): ep for ep in OVERPASS_ENDPOINTS}
        for window in (35, 10):
            done, _ = wait(futs, timeout=window, return_when=FIRST_COMPLETED)
            for f in done:
                ep = futs[f]
                try:
                    r = f.result()
                    if isinstance(r, dict) and "elements" in r:
                        return r
                    LAST_ERRORS.append(f"{ep.split('/')[2]}: bad reply")
                except Exception as e:
                    LAST_ERRORS.append(f"{ep.split('/')[2]}: {type(e).__name__} {str(e)[:60]}")
            futs = {f: ep for f, ep in futs.items() if not f.done()}
            if not futs:
                return None
        return None
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def osm(cat, city, country, limit=80):
    """Search public OSM listings. Coverage varies by country and category."""
    city, country = city.strip(), country.strip()
    if not city or not country:
        raise Exception("Enter both a city and a country.")
    selector = CATS.get(cat)
    if not selector:
        raise Exception("Unsupported business category.")
    limit = min(max(int(limit), 1), 100)
    ckey = f"{cat}|{city.casefold()}|{country.casefold()}|{limit}"
    cached = _cache_get(ckey)
    if cached is not None:
        return cached
    geo_url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": f"{city}, {country}", "format": "jsonv2", "limit": 1, "addressdetails": 1})
    _, geo_text, _, _ = http(geo_url, headers={"Accept-Language": "en"}, timeout=15)
    places = json.loads(geo_text)
    if not places:
        raise Exception(f"Could not locate {city}, {country}. Check the spelling.")
    lat, lon = places[0]["lat"], places[0]["lon"]
    # Light query: 3 km radius around the city centre instead of the whole city box.
    q = (f'[out:json][timeout:25];nwr{selector}["name"]'
         f'(around:3000,{lat},{lon});out center tags {limit};')
    # Race every public Overpass mirror in parallel; the first good answer wins.
    # If every mirror is busy, wait a few seconds and race once more — the
    # "too many requests" responses usually clear within seconds.
    result = None
    for attempt in range(2):
        if attempt:
            time.sleep(5)
        result = _race_overpass(q)
        if result is not None:
            break
    if result is None:
        detail = "; ".join(LAST_ERRORS[:4]) or "no reply from any server"
        raise Exception("Map servers did not answer. Details: " + detail)
    out, seen = [], set()
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        name = (tags.get("name") or "").strip()
        if not name:
            continue
        website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
        if website and not website.startswith(("http://", "https://")):
            website = "https://" + website
        phone = tags.get("phone") or tags.get("contact:phone") or ""
        email = tags.get("email") or tags.get("contact:email") or ""
        address = ", ".join(x for x in [
            tags.get("addr:housenumber"), tags.get("addr:street"),
            tags.get("addr:city") or tags.get("addr:town"),
            tags.get("addr:state"), tags.get("addr:postcode")
        ] if x)
        key = (name.casefold(), website.casefold(), address.casefold())
        if key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "website": website, "phone": phone, "email": email,
                    "address": address, "src": f"https://www.openstreetmap.org/{el['type']}/{el['id']}"})
    _cache_put(ckey, out)
    return out

# ---------- Website audit + public email finder ----------
JUNK = re.compile(r"\.(png|jpg|jpeg|gif|webp|svg)$|sentry|example\.|wixpress|domain\.com", re.I)

def emails_from(html):
    return sorted({m for m in re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", html) if not JUNK.search(m)})[:3]

def audit(url):
    """Basic heuristic checks and public email discovery on a few same-site pages."""
    sig, mails = [], []
    if not url:
        return {"signals": ["No website found"], "emails": []}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if re.search(r"(facebook\.com|instagram\.com|linktr\.ee)", url, re.I):
        return {"signals": ["Uses a social page instead of a standalone website"], "emails": []}
    try:
        _, html, final, secs = http(url, timeout=18)
    except Exception:
        try:
            _, html, final, secs = http(url.replace("https://", "http://", 1), timeout=18)
            sig.append("HTTPS request failed; HTTP page responded")
        except Exception:
            return {"signals": ["Website unreachable during this check"], "emails": []}
    if secs > 4:
        sig.append(f"Initial response was slow ({secs:.1f}s)")
    if not re.search(r'name=["\']viewport', html, re.I):
        sig.append("No viewport meta tag detected")
    yrs = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\D{0,12}((?:19|20)\d\d)", html, re.I)]
    if yrs and max(yrs) <= date.today().year - 3:
        sig.append(f"Footer year may be outdated (© {max(yrs)})")
    if not re.search(r"<title>\s*\S{4,}", html, re.I):
        sig.append("Missing or very short page title")
    if re.search(r"under construction|coming soon|parked domain", html, re.I):
        sig.append("Possible placeholder or unfinished website")
    base_host = urllib.parse.urlparse(final).netloc.lower().removeprefix("www.")
    pages = [final] + [urllib.parse.urljoin(final, x) for x in
                       ("/contact", "/contact-us", "/about", "/about-us", "/get-in-touch")]
    for page in pages[:6]:
        try:
            _, page_html, page_final, _ = http(page, timeout=10)
            host = urllib.parse.urlparse(page_final).netloc.lower().removeprefix("www.")
            if host == base_host:
                mails.extend(emails_from(page_html))
        except Exception:
            continue
    mails = sorted(set(mails))[:5]
    return {"signals": sig or ["No obvious issue detected by this basic check"], "emails": mails}

# ---------- AI pitch writer (all free options) ----------
PROVIDERS = ["Template (offline, no key)", "Pollinations (free, no key)", "Gemini (free key)", "Groq (free key)"]
OBS = {"No website": "doesn't appear to have a website yet", "social page": "seems to rely on a social media page instead of its own website",
       "unreachable": "has a website that wasn't loading when I checked", "HTTPS": "has a website without a working secure (HTTPS) connection",
       "mobile": "has a site that doesn't display well on phones", "Slow": "has a website that loads slowly",
       "Outdated": "has a site that looks like it hasn't been updated in a few years", "title": "has a few basic SEO gaps on its website",
       "favicon": "could use stronger branding on its website", "Placeholder": "has a website that still looks unfinished"}

def template(d):
    obs = [v for k, v in OBS.items() if k.lower() in (d.get("need_signal") or "").lower()][:2]
    b = d["business"]
    line = f"I was looking at local businesses and noticed that {b} " + " and ".join(obs) + "." if obs else f"I came across {b} while researching local businesses."
    who = (" " + d["contact"]) if d.get("contact") else ""
    return (f"Subject: Quick idea for {b}\n\nHello{who},\n\n{line} I'm a freelancer and I help businesses with {d['service'].lower()}. "
            f"If it's useful, I can send a few ideas or examples tailored to {b} - no obligation.\n\nWould you be open to a quick reply?\n\nBest regards,\nShawon\n\n"
            "P.S. If you'd rather not hear from me, just reply \"no\" and I won't contact you again.")

def _chat(url, key, model, prompt):
    h = {"Authorization": "Bearer " + key} if key else {}
    _, t, _, _ = http(url, data={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 500}, headers=h, timeout=45)
    return json.loads(t)["choices"][0]["message"]["content"]

def pitch(cfg, d):
    """Returns (text, note). Falls back to the offline template if an AI call fails."""
    prov = cfg.get("provider") or PROVIDERS[1]
    prompt = (f"Write a short, honest cold outreach email (subject + body, max 120 words) in {cfg.get('pitch_lang') or 'English'} from a freelancer "
              f"offering '{d['service']}' to the business '{d['business']}' ({d.get('city','')}, {d.get('country','')}). Base it ONLY on these observed facts: "
              f"{d.get('need_signal') or 'none recorded'}. Do not invent facts, praise or guarantees. Polite, one clear call to action, end with an opt-out line.")
    try:
        if prov.startswith("Template"): return template(d), "Offline template (no AI used)."
        if prov.startswith("Gemini"):
            if not cfg.get("gemini_key"): raise Exception("Gemini key missing")
            _, t, _, _ = http("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + cfg["gemini_key"],
                              data={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
            return json.loads(t)["candidates"][0]["content"]["parts"][0]["text"], "Written by Gemini (free)."
        if prov.startswith("Groq"):
            if not cfg.get("groq_key"): raise Exception("Groq key missing")
            return _chat("https://api.groq.com/openai/v1/chat/completions", cfg["groq_key"], "llama-3.3-70b-versatile", prompt), "Written by Groq (free)."
        return _chat("https://text.pollinations.ai/openai", "", "openai", prompt), "Written by Pollinations (free, no key)."
    except Exception as ex:
        return template(d), f"AI unavailable ({str(ex)[:70]}) - offline template used instead."

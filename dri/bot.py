"""DRI editorial bot: research -> independent check -> 4:5 cover -> Buffer draft.

This helper creates drafts. Publishing policy is enforced in publishing.py.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import textwrap
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dri" / "out"
ASSETS = ROOT / "dri" / "assets"
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
BUFFER_ENDPOINT = "https://api.buffer.com"
COMMONS_ENDPOINT = "https://commons.wikimedia.org/w/api.php"
TZ = ZoneInfo("Europe/Copenhagen")
UA = "DRI-EditorialBot/1.0 (personal editorial use; contact via repository owner)"
MODEL = os.environ.get("OPENAI_MODEL", "gpt-6.1-sol")
TRUSTED_DOMAINS = (
    "reuters.com", "ft.com", "bloomberg.com", "apnews.com", "wsj.com",
    "ecb.europa.eu", "bankofengland.co.uk", "federalreserve.gov",
    "nationalbanken.dk", "dst.dk", "ec.europa.eu", "eurostat.ec.europa.eu",
    "consilium.europa.eu", "europa.eu", "bis.org", "imf.org", "oecd.org",
    "worldbank.org", "bls.gov", "bea.gov", "treasury.gov", "eia.gov",
    "iea.org", "stats.gov.cn", "boj.or.jp", "statbank.dk", "eur-lex.europa.eu", "nasdaq.com",
    "investor.nvidia.com", "investors.microsoft.com", "investor.apple.com",
    "investors.tsmc.com", "sec.gov", "fred.stlouisfed.org",
)


def now_local():
    return datetime.now(TZ)


def should_run(instant: datetime, force: bool = False):
    local = instant.astimezone(TZ)
    if force:
        return True
    return local.weekday() in (0, 1, 2, 3, 4, 6) and local.hour == 7


def mode_for(instant: datetime):
    return "weekly" if instant.astimezone(TZ).weekday() == 6 else "daily"


def api_request(url, *, body=None, params=None, headers=None, method="POST", timeout=180):
    response = requests.request(
        method, url, json=body, params=params,
        headers={"User-Agent": UA, **(headers or {})}, timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def llm_call(prompt: str, *, model=MODEL, search=True, max_tokens=9000):
    raise RuntimeError("Paid AI APIs are disabled. Research must run in the existing ChatGPT subscription.")


def parse_json(text: str):
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start, end = clean.find("{"), clean.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(clean[start:end+1])


def is_trusted(url):
    try:
        parts = urlparse(url)
        domain = (parts.hostname or "").lower()
        return parts.scheme == "https" and any(domain == d or domain.endswith("." + d) for d in TRUSTED_DOMAINS)
    except Exception:
        return False


def research_prompt(instant: datetime):
    day = instant.astimezone(TZ).strftime("%Y-%m-%d")
    mode = mode_for(instant)
    base = f'''Du er en kritisk dansk makroøkonomisk nyhedsredaktør for Facebook-siden Den Rationelle Investor.
Dagsdato i København: {day}. Du SKAL bruge live websearch og tjekke dato for hændelse og offentliggørelse.
Prioritér Danmark og Europa; inkluder USA og globale forhold ved reel økonomisk eller finansiel betydning.
Vælg kun væsentlige begivenheder og verificer konkrete tal fra autoritative nylige kilder (Nationalbanken, Danmarks Statistik, ECB, Eurostat, Fed, BEA, BLS, IEA, selskabsmeddelelser, Reuters/FT).
Frasortér støj og overlappende historier. Skeln mellem tal, årsagsforklaring, risiko og fortolkning. Ingen em dash. Ingen støjende emojis eller sensationelle rubrikker.
Output MÅ KUN være et JSON-objekt, uden kodeblok, med felterne:
{{"facebook_text":"hele opslaget som én dansk tekst uden kildetags", "sources":[{{"headline":"historie", "urls":["https://..."], "event_date":"YYYY-MM-DD", "source_date":"YYYY-MM-DD", "core_fact":"det kontrollerede centrale faktum"}}], "photo_subject":"2-5 engelske ord for en passende dokumentarisk arkivfotografisk motivsøgning hos Wikimedia Commons", "cover_title":"kort overskrift til billede max 60 tegn", "cover_subtitle":"kort undertitel max 80 tegn"}}
Kilder må kun være rigtige fulde og direkte URL'er, du faktisk har besøgt via søgning. Hold kildekontrollen UDEN FOR facebook_text. Facebook-teksten skal kunne kopieres direkte, ikke indeholde citat-tags eller URL'er. Kompakte afsnit med gode linjeskift.
'''
    if mode == "weekly":
        return base + '''SØNDAG: Skriv "UGEN DER GIK: ..." med én overordnet analytisk tese, ca. 700-1000 danske ord, 3-4 forbundne makrohistorier fra seneste afsluttede handelsuge (mandag-fredag), hvad der overraskede, alternative forklaringer, konsekvenser for danske investorer og næste uges konkrete begivenheder. Angiv mindst tre historier med kilder i sources. Gentag ikke dagsbriefingformatet.'''
    return base + '''HVERDAG: Overskrift "X TING INVESTORER SKAL VIDE I DAG" hvor X = 3-5 reelt vigtige nye historier, helst fem men aldrig fyldstof. Ca. 450-700 ord. For hver historie: kort rubrik, hvad der nyt, økonomisk konsekvens og konkret observation at holde øje med. Undgå gårsdagens historier uden nyt. Slut med "DAGENS VIGTIGSTE POINTE" og original syntese. Sources skal indeholde præcis én post pr. valgt historie.'''


def audit_prompt(instant: datetime, draft: dict):
    date = instant.astimezone(TZ).strftime("%Y-%m-%d")
    return f'''Du er uvildig faktaredaktør. Søg på nettet UAFHÆNGIGT for at kontrollere følgende kladde til et Facebook-opslag skrevet {date}. Kontrollér ALLE aktuelle tal, begivenhedsdatoer, navne, hændelser og at kilderne faktisk dokumenterer udsagnene. Kræv korrekte tidsstempler og erstat overdrivelser med præcis formulering. Hvis væsentlige fejl eller ingen dokumentation: approved=false; ellers approved=true. Du må rette teksten, men må ALDRIG tilføje udokumenterede nyheder. Ingen em dash. Fjern citation-markører fra selve facebook_text.
Returnér KUN JSON: {{"approved":true, "facebook_text":"KORRIGERET fuldstændig Facebook-opslag", "issues":["eventuelle kontrolbemærkninger"], "sources":[{{"headline":"overskrift", "urls":["https://..."], "event_date":"YYYY-MM-DD", "source_date":"YYYY-MM-DD", "core_fact":"..."}}]}}.
Hvis approved=false, må facebook_text gerne være tom, men issues skal forklare hvorfor.
KLADDE:
{json.dumps(draft, ensure_ascii=False)}'''


def validate_result(result: dict, instant: datetime):
    if not result.get("approved"):
        raise RuntimeError("Faktatjek afviste kladde: " + str(result.get("issues")))
    text = result.get("facebook_text", "")
    if not isinstance(text, str) or len(text) < 950 or len(text) > 12500:
        raise RuntimeError("Usædvanlig tekstlængde. Kladde stoppet til manuel kontrol.")
    if "—" in text or "" in text:
        raise RuntimeError("Opslaget indeholder citation-tags eller em dash.")
    sources = result.get("sources", [])
    expected_min = 3
    if len(sources) < expected_min:
        raise RuntimeError("For få dokumenterede nyhedshistorier")
    for item in sources:
        urls = item.get("urls", [])
        if not urls or not any(is_trusted(url) for url in urls):
            raise RuntimeError("Nyhed mangler autoritativ URL: " + str(item.get("headline")))
        event_date = item.get("event_date", "")
        try:
            d = datetime.strptime(event_date, "%Y-%m-%d").date()
        except ValueError:
            raise RuntimeError("Ugyldig begivenhedsdato i kildekontrol")
        if d > instant.astimezone(TZ).date() + timedelta(days=1):
            raise RuntimeError("Fremtidig begivenhedsdato, faktatjek skal gennemgås")
    if mode_for(instant) == "daily" and "INVESTORER" not in text.upper():
        raise RuntimeError("Mangler genkendelig daglig rubrik")
    return text


def strip_html(fragment):
    return html.unescape(re.sub("<[^>]*>", "", fragment or "")).strip()


def commons_photo(subject: str):
    # Use only free-to-derivate licenses where attribution can be embedded and posted.
    searches = [subject, "European Central Bank building", "European Parliament building", "Frankfurt stock exchange"]
    candidates = []
    for search in searches:
        payload = api_request(COMMONS_ENDPOINT, method="GET", timeout=40, params={
            "action": "query", "generator": "search", "gsrsearch": search + " filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": 16, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 1500, "format": "json", "formatversion": 2,
        })
        for page in payload.get("query", {}).get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {})
            license_name = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
            # Explicitly allow only unrestricted licenses or standard CC BY.
            normalized = license_name.lower().replace(" ", "")
            permitted = (normalized in ("cc0", "publicdomain", "pd") or normalized.startswith("ccby-") or normalized == "ccby")
            if not permitted or "sa" in normalized or "nc" in normalized or "nd" in normalized:
                continue
            src = info.get("thumburl") or info.get("url", "")
            if not src.startswith("https://") or info.get("width", 0) < 850 or info.get("height", 0) < 650:
                continue
            rights_url = strip_html(meta.get("LicenseUrl", {}).get("value", ""))
            artist = strip_html(meta.get("Artist", {}).get("value", ""))
            if not artist or (normalized.startswith("ccby") and not rights_url.startswith("https://creativecommons.org/licenses/by/")):
                continue
            record = {
                "title": page.get("title", ""), "url": src,
                "page_url": info.get("descriptionurl") or "https://commons.wikimedia.org/",
                "license": license_name, "license_url": rights_url,
                "artist": artist or "Wikimedia Commons",
                "kind": "archive_photo",
            }
            height_ratio = info.get("height", 1) / info.get("width", 1)
            score = (10 if height_ratio >= 1.15 else 0) + (3 if height_ratio >= .9 else 0)
            candidates.append((score, record))
        if candidates:
            break
    return sorted(candidates, key=lambda v: v[0], reverse=True)[0][1] if candidates else None


def font(sz: int, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, sz)
    return ImageFont.load_default()


def wrap_lines(draw, text, ft, max_width):
    words = re.sub(r"\s+", " ", text.strip()).split()
    out, line = [], ""
    for word in words:
        maybe = f"{line} {word}".strip()
        if draw.textbbox((0, 0), maybe, font=ft)[2] <= max_width:
            line = maybe
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


def make_cover(headline: str, subtitle: str, photo: dict | None, out_file: Path):
    image = Image.new("RGB", (1080, 1350), "#f3f0e9")
    draw = ImageDraw.Draw(image)
    ink, accent = "#172d3b", "#b68a41"
    draw.rectangle((0, 0, 1080, 145), fill=ink)
    draw.text((70, 54), "DEN RATIONELLE INVESTOR", fill="#ffffff", font=font(36, True))
    archive_line = None
    if photo:
        try:
            resp = requests.get(photo["url"], headers={"User-Agent": UA}, timeout=25)
            resp.raise_for_status()
            if len(resp.content) > 20_000_000:
                raise RuntimeError("Photo over size limit")
            raw = Image.open(BytesIO(resp.content)).convert("RGB")
            # Preserve full image: letterbox rather than crop people/buildings.
            fitted = ImageOps.contain(raw, (1080, 760), method=Image.Resampling.LANCZOS)
            fill = Image.new("RGB", (1080, 760), "#d1d8d9")
            fill.paste(fitted, ((1080-fitted.width)//2, (760-fitted.height)//2))
            image.paste(fill, (0, 145))
            archive_line = f"Arkivfoto: {photo['artist'][:65]} / Wikimedia Commons · {photo['license']}"
        except Exception as exc:
            print(f"Kunne ikke hente lovligt foto, bruger grafisk forside: {exc}", file=sys.stderr)
            photo = None
    if not photo:
        draw.rectangle((0, 145, 1080, 905), fill="#e6e9e8")
        # Deliberately a graphic, not a representation of a real market chart.
        draw.line((110, 750, 300, 590, 475, 670, 660, 400, 900, 310), fill=ink, width=15, joint="curve")
        draw.ellipse((885, 295, 915, 325), fill=accent)
        draw.text((85, 210), "MAKRO  /  MARKEDER  /  RENTER", fill=ink, font=font(28, True))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 905, 1080, 1350), fill=ink)
    draw.rectangle((70, 953, 190, 964), fill=accent)
    headline = headline.upper()
    ft = font(62, True)
    lines = wrap_lines(draw, headline, ft, 940)
    if len(lines) > 3:
        ft = font(51, True)
        lines = wrap_lines(draw, headline, ft, 940)[:3]
    y = 1000
    for line in lines:
        draw.text((70, y), line, font=ft, fill="#ffffff")
        y += 73
    sub_ft = font(27)
    for ln in wrap_lines(draw, subtitle, sub_ft, 940)[:2]:
        draw.text((70, y + 15), ln, font=sub_ft, fill="#e0d9c9")
        y += 37
    if archive_line:
        # Attribution inside image + full attribution in Facebook copy.
        draw.rectangle((0, 863, 1080, 905), fill="#172d3b")
        draw.text((20, 872), archive_line[:108], font=font(19), fill="#ffffff")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_file, "JPEG", quality=88, optimize=True)
    return photo


def buffer_graphql(query: str, variables: dict | None = None):
    key = os.environ["BUFFER_API_KEY"]
    response = api_request(BUFFER_ENDPOINT,
        body={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {key}"}, timeout=45)
    if response.get("errors"):
        raise RuntimeError("Buffer GraphQL error: " + str(response["errors"])[:1000])
    return response.get("data") or {}


def find_channel():
    if os.environ.get("BUFFER_CHANNEL_ID"):
        return os.environ["BUFFER_CHANNEL_ID"]
    account = buffer_graphql("query { account { organizations { id } } }")
    orgs = (account.get("account") or {}).get("organizations") or []
    matches = []
    for org in orgs:
        result = buffer_graphql("query { channels(input: { organizationId: " + json.dumps(org["id"]) + " }) { id name displayName service } }")
        for channel in result.get("channels") or []:
            names = " ".join(str(channel.get(v, "")) for v in ("name", "displayName")).lower()
            if "rationelle investor" in names and "facebook" in str(channel.get("service", "")).lower():
                matches.append(channel["id"])
    if len(matches) != 1:
        raise RuntimeError(f"Kunne ikke finde entydig Facebook-kanal til Den Rationelle Investor ({len(matches)} matches). Tilføj BUFFER_CHANNEL_ID i GitHub Secrets.")
    return matches[0]


def draft_in_buffer(text: str, public_image_url: str | None):
    channel = find_channel()
    query = '''mutation ($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id text status } }
        ... on MutationError { message }
      }
    }'''
    inp = {"text": text, "channelId": channel, "schedulingType": "automatic",
           "mode": "addToQueue", "saveToDraft": True, "needsApproval": False, "assets": [], "aiAssisted": True, "metadata": {"facebook": {"type": "post"}}}
    if public_image_url:
        inp["assets"] = [{"image": {"url": public_image_url}}]
    data = buffer_graphql(query, {"input": inp})
    result = data.get("createPost") or {}
    if result.get("message"):
        raise RuntimeError("Buffer afviste kladden: " + result["message"])
    post = result.get("post") or {}
    if not post.get("id"):
        raise RuntimeError("Buffer bekræftede ikke kladden: " + str(result))
    if post.get("status") != "draft":
        raise RuntimeError("Buffer did not confirm draft status; do not retry automatically")
    return post["id"]


def create_draft(instant: datetime, force: bool):
    if not should_run(instant, force):
        print("Uden for kørselsvindue, ingen kladde oprettet.")
        return
    stamp = instant.astimezone(TZ).strftime("%Y-%m-%d")
    OUT.mkdir(parents=True, exist_ok=True)
    state = OUT / f"{stamp}.json"
    if state.exists() and not force:
        print("Eksisterende lokal kladde, springer over.")
        return
    print("Research og uafhængigt faktatjek:", stamp, mode_for(instant))
    draft = llm_call(research_prompt(instant))
    audit = llm_call(audit_prompt(instant, draft))
    text = validate_result(audit, instant)
    photo_subject = draft.get("photo_subject") or "European Central Bank building"
    try:
        photo = commons_photo(photo_subject)
    except Exception as exc:
        print("Commons ikke tilgængeligt, bruger original grafik:", exc)
        photo = None
    title = str(draft.get("cover_title") or ("UGEN DER GIK" if mode_for(instant) == "weekly" else "DAGENS MARKEDER"))[:100]
    sub = str(draft.get("cover_subtitle") or "Makroøkonomi, renter og finansmarkeder")[:100]
    asset = ASSETS / f"{stamp}.jpg"
    used_photo = make_cover(title, sub, photo, asset)
    if used_photo:
        credit = f"\n\nFoto: {used_photo['artist']} / Wikimedia Commons, {used_photo['license']}. Arkivfoto. Kilde: {used_photo['page_url']}"
        text += credit
    bundle = {"date": stamp, "mode": mode_for(instant), "text": text,
              "sources": audit.get("sources", []), "audit_issues": audit.get("issues", []),
              "photo": used_photo, "asset": f"dri/assets/{stamp}.jpg"}
    state.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / f"{stamp}.txt").write_text(text, encoding="utf-8")
    print("Kladde og billedfil forberedt. Billedfil:", asset)
    print("Antal kildegrupper:", len(bundle["sources"]))


def submit_draft(instant: datetime, force: bool):
    if not should_run(instant, force):
        return
    stamp = instant.astimezone(TZ).strftime("%Y-%m-%d")
    state = OUT / f"{stamp}.json"
    if not state.exists():
        raise RuntimeError("Mangler godkendt tekst- og kildepakke fra generering")
    bundle = json.loads(state.read_text(encoding="utf-8"))
    marker = OUT / f"{stamp}.buffer-id"
    if marker.exists():
        print("Allerede kladdeoprettet i denne kørsel", marker.read_text())
        return
    image_url = f"https://raw.githubusercontent.com/cstoDK/economics-n-stuff/main/dri/assets/{stamp}.jpg"
    # Image must be live first; don't silently publish a post without the intended graphic.
    for attempt in range(6):
        try:
            check = requests.get(image_url, timeout=15)
            if check.status_code == 200 and check.headers.get("Content-Type", "").startswith("image/"):
                break
        except requests.RequestException:
            pass
        time.sleep(5)
    else:
        raise RuntimeError("Offentlig billed-URL endnu ikke tilgængelig; ingen Buffer-kladde oprettet")
    post_id = draft_in_buffer(bundle["text"], image_url)
    marker.write_text(post_id, encoding="utf-8")
    print("BUFFER DRAFT CREATED (NOT PUBLISHED):", post_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("generate", "buffer"))
    parser.add_argument("--force", action="store_true", help="Manual workflow run regardless of local weekday and time")
    args = parser.parse_args()
    raise RuntimeError("Legacy entrypoint disabled. Use dri/pipeline.py with verified ChatGPT input.")


if __name__ == "__main__":
    main()

"""Enforce the single-story contract before creating or publishing a draft."""
import json
import re
from datetime import date
from urllib.parse import urlsplit

from verification import digest


def title_key(title):
    words = re.findall(r"[^\W_]+", title.casefold())
    return set(words) - {"af", "de", "den", "det", "en", "et", "for", "fra", "i", "med", "og", "om", "på", "til"}


def similar_title(first, second):
    a, b = title_key(first), title_key(second)
    return bool(a and b and len(a & b) / len(a | b) >= 0.75)


def validate_editorial(data, body):
    review = data.get("editorial")
    if not isinstance(review, dict) or review.get("status") != "passed":
        raise RuntimeError("Missing or failed editorial review")
    if (data.get("verification") or {}).get("reviewed_text") != body:
        raise RuntimeError("Editorial review must cover the exact final text")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){2,9}", str(review.get("story_key", ""))):
        raise RuntimeError("Provide a specific, stable story key")
    for field in ("new_development", "mechanism", "reader_relevance", "image_relevance"):
        value = review.get(field)
        if not isinstance(value, str) or not 20 <= len(value.strip()) <= 500:
            raise RuntimeError(f"Missing concrete editorial judgment: {field}")
    if not re.fullmatch(r"File:[^|#<>\r\n]+\.(?:jpe?g|png|webp)", str(review.get("photo_file", "")), re.I):
        raise RuntimeError("Select one exact Wikimedia Commons photo file")
    for field, limit in (("cover_title", 60), ("cover_subtitle", 80)):
        value = data.get(field)
        if not isinstance(value, str) or not 8 <= len(value.strip()) <= limit or "\n" in value:
            raise RuntimeError(f"Missing or invalid {field}")
    headline = body.strip().splitlines()[0]
    for title in (headline, data["cover_title"]):
        if len(title) > 110 or re.search(
            r"ting\s+investorer|dagens vigtigste pointe|dagens markeder|ugen der gik|signaler\s+(om|fra)\s+europas økonomi",
            title, re.I,
        ):
            raise RuntimeError("Use a specific headline without the recurring roundup template")
    if not 260 <= len(body.split()) <= 550 or re.search(r"https?://|\[\[|chatgpt-content-reference|[—–!]", body, re.I):
        raise RuntimeError("Use 260–550 words of clean DRI copy without links, dashes or exclamation marks")
    sources = set()
    for item in data["sources"]:
        url = urlsplit((item.get("evidence") or {}).get("url") or "")
        if url.hostname:
            sources.add((url.hostname, url.path.rstrip("/")))
    if not 2 <= len(sources) == len(data["sources"]) <= 5:
        raise RuntimeError("Provide 2–5 distinct evidence pages for the same story")


def editorial_digest(data):
    material = {key: data[key] for key in ("editorial", "cover_title", "cover_subtitle")}
    return digest(json.dumps(material, sort_keys=True, ensure_ascii=False))


def check_history(data, photo, state, incoming):
    today = date.fromisoformat(data["date"])
    recent_count = 0
    for path in state.glob("*.publication.json"):
        previous_day = path.name.split(".", 1)[0]
        age = (today - date.fromisoformat(previous_day)).days
        if not 1 <= age <= 30:
            continue
        publication = json.loads(path.read_text(encoding="utf-8"))
        if publication.get("status") not in {"sent", "reserved", "scheduled", "sending"}:
            continue
        recent_count += age <= 6
        previous = json.loads((incoming / f"{previous_day}.json").read_text(encoding="utf-8"))
        old_review = previous.get("editorial") or {}
        old_headline = previous["facebook_text"].strip().splitlines()[0]
        if (data["editorial"]["story_key"] == old_review.get("story_key")
                or similar_title(data["facebook_text"].strip().splitlines()[0], old_headline)
                or similar_title(data["cover_title"], previous.get("cover_title") or "")):
            raise RuntimeError(f"Story or headline repeats the {previous_day} edition")
        receipt = state / f"{previous_day}.delivery.json"
        old_photo = json.loads(receipt.read_text(encoding="utf-8")).get("photo") if receipt.exists() else None
        if old_photo and (photo["sha1"] == old_photo.get("sha1") or photo["title"] == old_photo.get("title")):
            raise RuntimeError(f"Cover photo already used on {previous_day}")
    if recent_count >= 3:
        raise RuntimeError("Three editions already sent or in progress in this seven-day window")

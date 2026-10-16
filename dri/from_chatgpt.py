"""Bridge: ChatGPT Scheduled Task -> GitHub JSON -> licensed cover -> Buffer draft.
This module NEVER uses the OpenAI API and NEVER publishes to Facebook.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from bot import (
    TZ, ROOT, OUT, ASSETS, now_local, mode_for, validate_result,
    commons_photo, make_cover, draft_in_buffer
)

STATE = ROOT / "dri" / "state"
INCOMING = ROOT / "dri" / "incoming"


def validate_file(filename: str):
    f = Path(filename)
    resolved = f.resolve()
    if not resolved.is_relative_to(INCOMING.resolve()) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", f.name):
        raise RuntimeError("Only files named dri/incoming/YYYY-MM-DD.json are permitted")
    data = json.loads(resolved.read_text(encoding="utf-8"))
    date_string = f.stem
    if data.get("date") != date_string:
        raise RuntimeError("Payload date and filename do not match")
    instant = datetime.strptime(date_string, "%Y-%m-%d").replace(hour=7,minute=30,tzinfo=TZ)
    if abs((now_local().date()-instant.date()).days) > 1:
        raise RuntimeError("Outdated or future-dated post, refusing to create draft")
    if mode_for(instant) != data.get("mode") or instant.weekday() == 5:
        raise RuntimeError("Mode does not match date / no Saturday edition")
    if data.get("approved") is not True:
        raise RuntimeError("Editorial fact-check not approved, refusing draft")
    body = validate_result(data, instant)
    return instant, data, body


def prepare(filename: str):
    instant, data, body = validate_file(filename)
    date = instant.date().isoformat()
    marker = STATE / f"{date}.buffer-id"
    if marker.exists():
        print("Already delivered:", date)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    photo = None
    try:
        photo = commons_photo(str(data.get("photo_subject") or "European Central Bank building"))
    except Exception as e:
        print("Photo unavailable, using clearly illustrated cover:", e)
    title = str(data.get("cover_title") or ("UGEN DER GIK" if data["mode"] == "weekly" else "DAGENS MARKEDER"))[:100]
    subtitle = str(data.get("cover_subtitle") or "Makroøkonomi, renter og finansmarkeder")[:100]
    asset = ASSETS / f"{date}.jpg"
    used = make_cover(title, subtitle, photo, asset)
    if used:
        body += ("\n\nArkivfoto: " + used["artist"] + " / Wikimedia Commons (" + used["license"]
                 + "). Kilde og licens: " + used["page_url"])
    bundle = {
        "date": date, "text": body, "sources": data["sources"],
        "asset": str(asset.relative_to(ROOT)), "photo": used,
        "editorial_review_required": True,
    }
    (OUT / f"{date}.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2),encoding="utf-8")
    (OUT / f"{date}.txt").write_text(body,encoding="utf-8")
    print("Validated draft and 1080x1350 cover created:", date)


def deliver(filename: str):
    instant, _, _ = validate_file(filename)
    date = instant.date().isoformat()
    marker = STATE / f"{date}.buffer-id"
    if marker.exists():
        print("Already delivered, skipping duplicate.")
        return
    bundle = json.loads((OUT / f"{date}.json").read_text(encoding="utf-8"))
    # The GitHub workflow commits the cover before this step.
    from bot import requests, time
    image_url = f"https://raw.githubusercontent.com/cstoDK/economics-n-stuff/main/dri/assets/{date}.jpg"
    for _ in range(10):
        try:
            result = requests.get(image_url, timeout=15)
            if result.status_code == 200 and result.headers.get("Content-Type", "").startswith("image/"):
                break
        except requests.RequestException:
            pass
        time.sleep(4)
    else:
        raise RuntimeError("Cover not yet publicly reachable; refusing text-only draft.")
    # draft_in_buffer enforces saveToDraft=True. There is NO publish branch.
    post_id = draft_in_buffer(bundle["text"], image_url)
    STATE.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(post_id), encoding="utf-8")
    print("Created Buffer DRAFT (not published). ID:", post_id)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("prepare", "deliver"))
    p.add_argument("filename")
    args = p.parse_args()
    if args.stage == "prepare":
        prepare(args.filename)
    else:
        deliver(args.filename)

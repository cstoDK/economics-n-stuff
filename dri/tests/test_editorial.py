import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot
from editorial import check_history, validate_editorial


class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.body = "ECB ændrer sikkerhedskravet til banker\n\n" + "En dokumenteret mekanisme for danske opsparere. " * 46
        self.data = {
            "date": "2026-11-08",
            "facebook_text": self.body,
            "cover_title": "ECB ændrer bankernes sikkerhedskrav",
            "cover_subtitle": "Hvilke aktiver bankerne kan stille som sikkerhed",
            "verification": {"reviewed_text": self.body},
            "editorial": {"status": "passed", "story_key": "ecb-sikkerhed-bankers-obligationer",
                          "new_development": "Den nye afgørelse ændrer listen over aktiver.",
                          "mechanism": "Banker kan bruge flere typer aktiver som sikkerhed.",
                          "reader_relevance": "Ændringen kan påvirke efterspørgslen efter visse obligationer.",
                          "image_relevance": "Fotoet viser den konkrete type obligation, som indgår i beslutningen.",
                          "photo_file": "File:Reviewed bond.jpg"},
            "sources": [{"evidence": {"url": f"https://www.ecb.europa.eu/decision/{i}"}} for i in range(2)],
        }

    def test_valid_editorial_structure(self):
        validate_editorial(self.data, self.body)

    def test_old_roundup_template_is_rejected_even_with_new_review(self):
        self.data["cover_title"] = "Fire signaler fra Europas økonomi"
        with self.assertRaisesRegex(RuntimeError, "recurring roundup"):
            validate_editorial(self.data, self.body)

    def test_edited_copy_and_duplicate_evidence_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "exact final text"):
            validate_editorial(self.data, self.body + " Ny påstand.")
        self.data["sources"][1] = {"evidence": {"url": "https://www.ecb.europa.eu/decision/0?utm_source=x"}}
        with self.assertRaisesRegex(RuntimeError, "distinct evidence"):
            validate_editorial(self.data, self.body)

    def test_old_edition_and_same_image_under_another_name_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            state = incoming = Path(folder)
            (state / "2026-10-23.publication.json").write_text('{"status":"sent"}')
            (incoming / "2026-10-23.json").write_text(json.dumps({
                "facebook_text": "En anden historie", "cover_title": "Fire signaler om Europas økonomi",
            }))
            original_title = self.data["cover_title"]
            self.data["cover_title"] = "Fire signaler fra Europas økonomi"
            photo = {"title": "File:Different name.jpg", "sha1": "same-photo"}
            with self.assertRaisesRegex(RuntimeError, "repeats"):
                check_history(self.data, photo, state, incoming)
            self.data["cover_title"] = original_title
            (state / "2026-10-23.delivery.json").write_text('{"photo":{"title":"File:Old name.jpg","sha1":"same-photo"}}')
            with self.assertRaisesRegex(RuntimeError, "photo already used"):
                check_history(self.data, photo, state, incoming)

    def test_fourth_edition_in_seven_days_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            state = incoming = Path(folder)
            for day in ("2026-11-02", "2026-11-04", "2026-11-06"):
                (state / f"{day}.publication.json").write_text('{"status":"sent"}')
                (incoming / f"{day}.json").write_text('{"facebook_text":"Anden historie"}')
            with self.assertRaisesRegex(RuntimeError, "Three editions"):
                check_history(self.data, {"title": "File:New photo.jpg", "sha1": "new"}, state, incoming)

    def test_exact_photo_lookup_never_searches_for_generic_images(self):
        with patch.object(bot, "api_request", return_value={"query": {"pages": []}}) as lookup:
            self.assertIsNone(bot.commons_photo("File:Missing photo.jpg", exact=True))
            lookup.assert_called_once()
            self.assertEqual(lookup.call_args.kwargs["params"]["titles"], "File:Missing photo.jpg")
            self.assertNotIn("generator", lookup.call_args.kwargs["params"])

    def test_exact_photo_accepts_commons_thumbnail_and_standard_cc_by_name(self):
        title = "File:Reviewed photo.jpg"
        url = "https://thumb.wikimedia.org/wikipedia/commons/thumb/example.jpg"
        metadata = {
            "LicenseShortName": {"value": "CC BY 2.0"},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by/2.0/"},
            "Artist": {"value": "Photographer"},
        }
        response = {"query": {"pages": [{"ns": 6, "title": title, "imageinfo": [{
            "thumburl": url, "mime": "image/jpeg", "sha1": "hash",
            "width": 5184, "height": 3456, "extmetadata": metadata,
        }]}]}}
        with patch.object(bot, "api_request", return_value=response):
            self.assertEqual(bot.commons_photo(title, exact=True)["url"], url)
            metadata["LicenseShortName"]["value"] = "CC BY-SA 2.0"
            self.assertIsNone(bot.commons_photo(title, exact=True))

    def test_photo_render_failure_never_produces_fallback_art(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bot.requests, "get", side_effect=TimeoutError):
            target = Path(folder) / "cover.jpg"
            with self.assertRaisesRegex(RuntimeError, "could not be rendered"):
                bot.make_cover("Titel", "Undertitel", {"url": "https://upload.wikimedia.org/photo"}, target,
                               require_photo=True)
            self.assertFalse(target.exists())

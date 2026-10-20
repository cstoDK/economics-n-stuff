import copy
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bot
import verification as v
import pipeline
import from_chatgpt as bridge


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 20, 7, 30, tzinfo=bot.TZ)
        self.data = {'mode': 'daily', 'facebook_text': 'Reviewed final text',
                     'verification': {'status': 'passed', 'method': 'independent_source_review',
                                      'reviewed_text': 'Reviewed final text', 'unresolved_claims': []},
                     'sources': [{'urls': ['https://www.ecb.europa.eu/news'], 'source_date': '2026-10-20', 'event_date': '2026-10-20',
                                  'evidence': {'url': 'https://www.ecb.europa.eu/news', 'verified': True,
                                               'checked_at': '2026-10-20T07:20:00+02:00',
                                               'excerpt': 'This exact excerpt is documented.',
                                               'supported_claims': ['Claim checked separately']}}]}
    def test_verified_evidence(self):
        self.assertEqual(v.verify(self.data, self.instant, lambda u: 'this exact excerpt is documented.'), v.digest(self.data['facebook_text']))
    def test_missing_review_blocks(self):
        del self.data['verification']
        with self.assertRaises(RuntimeError): v.verify(self.data, self.instant)
    def test_changed_text_blocks(self):
        self.data['facebook_text'] += ' unchecked claim'
        with self.assertRaises(RuntimeError): v.verify(self.data, self.instant)
    def test_unresolved_claim_blocks(self):
        self.data['verification']['unresolved_claims'] = ['not verified']
        with self.assertRaises(RuntimeError): v.verify(self.data, self.instant)
    def test_missing_excerpt_blocks(self):
        with self.assertRaises(RuntimeError): v.verify(self.data, self.instant, lambda u: 'paywall')
    def test_fetch_error_blocks(self):
        with self.assertRaises(TimeoutError): v.verify(self.data, self.instant, Mock(side_effect=TimeoutError))
    def test_redirect_to_untrusted_host_blocks(self):
        response = Mock(status_code=302, headers={'Location': 'https://example.com/private'})
        with patch.object(v.requests, 'get', return_value=response) as get:
            with self.assertRaises(RuntimeError): v.read_source('https://www.ecb.europa.eu/news')
            self.assertEqual(get.call_count, 1)
    def test_future_source_blocks(self):
        self.data['sources'][0]['source_date'] = '2026-10-21'
        with self.assertRaises(RuntimeError): v.verify(self.data, self.instant)


class DeliveryTests(unittest.TestCase):
    def test_draft_only_payload_and_status(self):
        with patch.object(bot, 'find_channel', return_value='channel'), patch.object(bot, 'buffer_graphql', return_value={'createPost': {'post': {'id': 'id', 'status': 'draft'}}}) as api:
            self.assertEqual(bot.draft_in_buffer('test', 'https://image.test/cover.jpg'), 'id')
            payload = api.call_args.args[1]['input']
            self.assertIs(payload['saveToDraft'], True)
            self.assertNotIn('dueAt', payload)
            self.assertEqual(payload['metadata']['facebook']['type'], 'post')
    def test_unexpected_status_blocks_success(self):
        with patch.object(bot, 'find_channel', return_value='channel'), patch.object(bot, 'buffer_graphql', return_value={'createPost': {'post': {'id': 'id', 'status': 'scheduled'}}}):
            with self.assertRaises(RuntimeError): bot.draft_in_buffer('test', 'https://image.test/cover.jpg')
    def test_paid_api_disabled(self):
        with patch.object(bot.requests, 'request') as request:
            with self.assertRaises(RuntimeError): bot.llm_call('test')
            request.assert_not_called()
    def test_old_receipt_skips_all_preparation(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bridge, 'STATE', Path(folder)), patch.object(bridge, 'prepare') as prepare:
            (Path(folder)/'2026-10-19.buffer-id').write_text('existing')
            pipeline.deliver_one('dri/incoming/2026-10-19.json')
            prepare.assert_not_called()
    def test_reservation_blocks_replay(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bridge, 'STATE', Path(folder)), patch.object(bridge, 'prepare') as prepare:
            (Path(folder)/'2026-10-20.delivery.json').write_text('{}')
            with self.assertRaises(RuntimeError): pipeline.deliver_one('dri/incoming/2026-10-20.json')
            prepare.assert_not_called()
    def test_failure_after_remote_acceptance_never_retries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(bridge, 'ROOT', root), patch.object(bridge, 'STATE', root/'dri/state'), patch.object(bridge, 'prepare'), patch.object(pipeline, 'persist', return_value='a'*40), patch.object(bridge, 'deliver', side_effect=TimeoutError('response lost')) as deliver, patch.dict(os.environ, {'GITHUB_RUN_ID': '123'}):
                with self.assertRaises(TimeoutError): pipeline.deliver_one('dri/incoming/2026-10-20.json')
                with self.assertRaises(RuntimeError): pipeline.deliver_one('dri/incoming/2026-10-20.json')
                self.assertEqual(deliver.call_count, 1)
    def test_failed_reservation_push_never_calls_buffer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(bridge, 'ROOT', root), patch.object(bridge, 'STATE', root/'dri/state'), patch.object(bridge, 'prepare'), patch.object(pipeline, 'persist', side_effect=RuntimeError('push rejected')), patch.object(bridge, 'deliver') as deliver, patch.dict(os.environ, {'GITHUB_RUN_ID': '123'}):
                with self.assertRaises(RuntimeError): pipeline.deliver_one('dri/incoming/2026-10-20.json')
                deliver.assert_not_called()

if __name__ == '__main__': unittest.main()

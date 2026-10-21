import copy
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import publishing as p
from verification import digest


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.state = self.root / 'dri/state'
        self.state.mkdir(parents=True)
        self.policy = self.root / 'dri/publishing.json'
        self.policy.write_text(json.dumps({'enabled': True, 'start_date': '2026-10-21'}))
        self.receipt = {'status': 'delivered', 'buffer_id': 'recorded',
                        'text_sha256': digest('reviewed'), 'verified_text_sha256': digest('reviewed'),
                        'image_url': 'https://cover'}
        (self.state/'2026-10-21.delivery.json').write_text(json.dumps(self.receipt))
        (self.state/'2026-10-21.buffer-id').write_text('recorded')
        self.claim = self.state/'2026-10-21.publication.json'
        self.draft = {'id': 'recorded', 'status': 'draft', 'channelId': 'dri', 'text': 'reviewed',
                      'schedulingType': 'automatic', 'assets': [{'mimeType': 'image/jpeg', 'source': 'https://cover'}]}
        self.sent = dict(self.draft, status='sent', sentAt='2026-10-21T11:00:00Z', externalLink='https://facebook.com/test')
        self.stack.enter_context(patch.object(p.bridge, 'ROOT', self.root))
        self.stack.enter_context(patch.object(p.bridge, 'STATE', self.state))
        self.stack.enter_context(patch.object(p.bridge, 'validate_file', return_value=(datetime(2026,10,21), {}, 'reviewed')))
        self.stack.enter_context(patch.dict(os.environ, {'GITHUB_RUN_ID': 'test'}))
        self.channel = self.stack.enter_context(patch.object(p, 'check_channel', return_value={'id': 'dri'}))
        self.get = self.stack.enter_context(patch.object(p, 'get_post', side_effect=[self.draft, self.draft, self.sent]))
        self.verify = self.stack.enter_context(patch.object(p, 'verify'))
        self.mutate = self.stack.enter_context(patch.object(p, 'request_publication'))
        self.persist = Mock()

    def run_publish(self):
        return p.publish_one('dri/incoming/2026-10-21.json', self.persist)

    def test_publish_after_verification_and_durable_reservation(self):
        def mutation(_):
            self.verify.assert_called_once()
            self.assertEqual(json.loads(self.claim.read_text())['status'], 'reserved')
            self.persist.assert_called_once()
        self.mutate.side_effect = mutation
        self.assertEqual(self.run_publish()['status'], 'sent')
        self.assertEqual(json.loads(self.claim.read_text())['external_link'], 'https://facebook.com/test')
        self.mutate.assert_called_once_with('recorded')

    def test_disabled_policy_never_contacts_buffer(self):
        self.policy.write_text('{"enabled": false}')
        with self.assertRaises(RuntimeError): self.run_publish()
        self.channel.assert_not_called()
        self.mutate.assert_not_called()

    def test_failed_source_verification_never_reserves_or_publishes(self):
        self.verify.side_effect = RuntimeError('unverified')
        with self.assertRaises(RuntimeError): self.run_publish()
        self.assertFalse(self.claim.exists())
        self.mutate.assert_not_called()

    def test_changed_live_text_blocks(self):
        self.draft['text'] = 'not reviewed'
        with self.assertRaises(RuntimeError): self.run_publish()
        self.mutate.assert_not_called()

    def test_changed_live_cover_blocks(self):
        self.draft['assets'][0]['source'] = 'https://other'
        with self.assertRaises(RuntimeError): self.run_publish()
        self.mutate.assert_not_called()

    def test_wrong_channel_blocks(self):
        self.draft['channelId'] = 'other'
        with self.assertRaises(RuntimeError): self.run_publish()
        self.mutate.assert_not_called()

    def test_failed_git_push_never_publishes(self):
        self.persist.side_effect = RuntimeError('push failed')
        with self.assertRaises(RuntimeError): self.run_publish()
        self.mutate.assert_not_called()

    def test_ambiguous_timeout_never_repeats_mutation(self):
        self.mutate.side_effect = TimeoutError('response lost')
        with self.assertRaises(TimeoutError): self.run_publish()
        self.get.side_effect = None
        self.get.return_value = self.draft
        with self.assertRaises(RuntimeError): self.run_publish()
        self.mutate.assert_called_once()

    def test_sent_post_reconciles_without_publication(self):
        self.claim.write_text('{"buffer_id": "recorded", "status": "reserved"}')
        self.get.side_effect = None
        self.get.return_value = self.sent
        self.run_publish()
        self.mutate.assert_not_called()
        self.verify.assert_not_called()

    def test_mutation_releases_existing_id_for_automatic_publishing(self):
        result = {'editPost': {'post': {'id': 'recorded', 'status': 'sending', 'schedulingType': 'automatic'}}}
        with patch.object(p, 'buffer_graphql', return_value=result) as api:
            # Call the actual function behind the local test mock.
            real_request_publication('recorded')
            payload = api.call_args.args[1]['input']
            self.assertEqual(payload, {'id': 'recorded', 'mode': 'shareNow', 'schedulingType': 'automatic', 'saveToDraft': False})


real_request_publication = p.request_publication
if __name__ == '__main__': unittest.main()

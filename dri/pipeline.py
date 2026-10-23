"""Serialized delivery with a durable reservation before the Buffer mutation."""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path
import from_chatgpt as bridge
from bot import buffer_graphql, now_local


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def persist(paths, message):
    git('config', 'user.name', 'dri-bot')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    git('add', '--', *paths)
    if git('diff', '--cached', '--name-only'):
        git('commit', '-m', message)
        # Fail closed if the branch moved; never perform the Buffer mutation
        # unless the reservation is confirmed remotely. No force pushes.
        git('push', 'origin', 'HEAD:main')
    return git('rev-parse', 'HEAD')


def deliver_one(filename):
    path = Path(filename)
    if not re.fullmatch(r'dri/incoming/\d{4}-\d{2}-\d{2}\.json', filename):
        raise RuntimeError('Invalid incoming path')
    day = path.stem
    marker = bridge.STATE / f'{day}.buffer-id'
    if marker.exists():
        print('SKIP_ALREADY_DELIVERED', day, marker.read_text().strip())
        return
    claim = bridge.STATE / f'{day}.delivery.json'
    if claim.exists():
        raise RuntimeError('Prior delivery reservation exists. Reconcile Buffer before retrying; possible accepted request.')
    bundle = bridge.prepare(filename)
    bridge.STATE.mkdir(parents=True, exist_ok=True)
    from verification import digest
    record = {'status': 'reserved', 'run_id': os.environ['GITHUB_RUN_ID'], 'date': day,
              'text_sha256': digest(bundle['text']),
              'verified_text_sha256': bundle['verified_text_sha256']}
    claim.write_text(json.dumps(record, indent=2))
    revision = persist([str(claim.relative_to(bridge.ROOT)), f'dri/assets/{day}.jpg'],
                       f'chore(dri): reserve {day} delivery and save cover')
    os.environ['DRI_ASSET_COMMIT'] = revision
    bridge.deliver(filename)
    record.update(status='delivered', buffer_id=marker.read_text().strip(),
                  image_url=f'https://raw.githubusercontent.com/cstoDK/economics-n-stuff/{revision}/dri/assets/{day}.jpg')
    claim.write_text(json.dumps(record, indent=2))
    persist([str(claim.relative_to(bridge.ROOT)), str(marker.relative_to(bridge.ROOT))],
            f'chore(dri): record {day} Buffer draft receipt')


def audit():
    """Read-only live check of existing receipts; never create a test post."""
    expected = {p.read_text().strip() for p in bridge.STATE.glob('*.buffer-id')}
    found = {}
    orgs = buffer_graphql('query { account { organizations { id } } }')['account']['organizations']
    for org in orgs:
        cursor = None
        for _ in range(100):
            query = '''query($input: PostsInput!, $after: String) {
              posts(first: 100, after: $after, input: $input) {
                edges { node { id status assets { id mimeType } } }
                pageInfo { hasNextPage endCursor }
              }
            }'''
            result = buffer_graphql(query, {'input': {'organizationId': org['id']}, 'after': cursor})['posts']
            for edge in result['edges']:
                post = edge['node']
                if post['id'] in expected:
                    found[post['id']] = post
            if not result['pageInfo']['hasNextPage']: break
            cursor = result['pageInfo']['endCursor']
        else:
            raise RuntimeError('Audit pagination limit reached')
    from publishing import check_channel, get_post
    from verification import digest
    channel = check_channel()
    for post_id in expected:
        live = get_post(post_id)
        found[post_id] = {k: live[k] for k in ('id', 'status', 'assets', 'externalLink', 'sentAt', 'schedulingType')}
        found[post_id]['text_sha256'] = digest(live['text'])
    report = {'expected_ids': sorted(expected), 'posts': found, 'channel': channel, 'read_only': True}
    bridge.OUT.mkdir(parents=True, exist_ok=True)
    (bridge.OUT / 'buffer-audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    if set(found) != expected:
        raise RuntimeError('One or more recorded Buffer posts were not found')
    for marker in bridge.STATE.glob('*.buffer-id'):
        post = found[marker.read_text().strip()]
        publication = bridge.STATE / (marker.stem + '.publication.json')
        publication_status = json.loads(publication.read_text()).get('status') if publication.exists() else None
        allowed = ('draft',) if publication_status in (None, 'reconciled_rejection') else ('scheduled', 'sending', 'sent')
        if post['status'] not in allowed or not post.get('assets'):
            raise RuntimeError('Recorded post has an unexpected status or missing image; inspect report')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['deliver', 'publish', 'audit'])
    parser.add_argument('--file', default='')
    args = parser.parse_args()
    if args.mode == 'audit': audit()
    else:
        filename = args.file or f'dri/incoming/{now_local().date().isoformat()}.json'
        if not Path(filename).is_file():
            raise RuntimeError('No verified edition for today; no delivery')
        if args.mode == 'deliver':
            deliver_one(filename)
        policy = json.loads((bridge.ROOT / 'dri/publishing.json').read_text())
        if policy.get('enabled') is not True:
            print('PUBLICATION_DISABLED: editorial publication is paused; no Facebook release')
        else:
            from publishing import publish_one
            publish_one(filename, persist)

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
    bridge.prepare(filename)
    bridge.STATE.mkdir(parents=True, exist_ok=True)
    claim.write_text(json.dumps({'status': 'reserved', 'run_id': os.environ['GITHUB_RUN_ID'],
                                 'date': day}, indent=2))
    revision = persist([str(claim.relative_to(bridge.ROOT)), f'dri/assets/{day}.jpg'],
                       f'chore(dri): reserve {day} delivery and save cover')
    os.environ['DRI_ASSET_COMMIT'] = revision
    bridge.deliver(filename)
    claim.write_text(json.dumps({'status': 'delivered', 'date': day,
                                'buffer_id': marker.read_text().strip()}, indent=2))
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
    channel = check_channel()
    for post_id in expected:
        live = get_post(post_id)
        found[post_id] = {k: live[k] for k in ('id', 'status', 'assets', 'externalLink', 'sentAt', 'schedulingType')}
    report = {'expected_ids': sorted(expected), 'posts': found, 'channel': channel, 'read_only': True}
    bridge.OUT.mkdir(parents=True, exist_ok=True)
    (bridge.OUT / 'buffer-audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
    if set(found) != expected:
        raise RuntimeError('One or more recorded Buffer posts were not found')
    if any(p['status'] != 'draft' or not p.get('assets') for p in found.values()):
        raise RuntimeError('Recorded post is not a draft with an attached asset; inspect report')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['deliver', 'audit'])
    parser.add_argument('--file', default='')
    args = parser.parse_args()
    if args.mode == 'audit': audit()
    else:
        filename = args.file or f'dri/incoming/{now_local().date().isoformat()}.json'
        if not Path(filename).is_file():
            raise RuntimeError('No verified edition for today; no delivery')
        deliver_one(filename)

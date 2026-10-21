"""Automatic publication of verified DRI editions; controlled by publishing.json."""
import json
import os
import time
import from_chatgpt as bridge
from bot import buffer_graphql, find_channel
from verification import digest, verify

POST_FIELDS = '''id status text channelId schedulingType externalLink sentAt
  assets { mimeType source } error { message }'''


def get_post(post_id):
    return buffer_graphql('query($input: PostInput!) { post(input: $input) { '
                          + POST_FIELDS + ' } }', {'input': {'id': post_id}})['post']


def check_channel():
    channel = buffer_graphql('''query($input: ChannelInput!) {
      channel(input: $input) { id name displayName service type externalLink
        isDisconnected isLocked isQueuePaused allowedActions }
    }''', {'input': {'id': find_channel()}})['channel']
    names = ' '.join(str(channel.get(k) or '') for k in ('name', 'displayName')).casefold()
    if channel['service'] != 'facebook' or 'rationelle investor' not in names:
        raise RuntimeError('Publication target is not the DRI Facebook channel')
    if channel['isDisconnected'] or channel['isLocked'] or channel['isQueuePaused']:
        raise RuntimeError('DRI channel disconnected, locked or paused; publication blocked')
    if 'scheduleUpdates' not in channel['allowedActions']:
        raise RuntimeError('Buffer connection lacks permission to publish on DRI')
    return channel


def validate_post(post, receipt, channel_id):
    if post['id'] != receipt['buffer_id'] or post['channelId'] != channel_id:
        raise RuntimeError('Post or channel differs from the recorded delivery')
    if digest(post['text']) != receipt['text_sha256']:
        raise RuntimeError('Live Buffer text changed after verification; publication blocked')
    assets = post.get('assets') or []
    if len(assets) != 1 or not assets[0]['mimeType'].startswith('image/'):
        raise RuntimeError('Verified cover is missing or extra media was attached')
    if assets[0]['source'] != receipt['image_url']:
        raise RuntimeError('Live Buffer image differs from the licensed verified cover')


def request_publication(verified_post):
    post_id = verified_post["id"]
    # Edit the recorded post; never create a second post as a retry.
    result = buffer_graphql('''mutation($input: EditPostInput!) {
      editPost(input: $input) {
        ... on PostActionSuccess { post { id status schedulingType } }
        ... on MutationError { message }
      }
    }''', {'input': {'id': post_id, 'mode': 'shareNow',
                     'schedulingType': 'automatic', 'saveToDraft': False,
                     'text': verified_post['text'],
                     'assets': [{'image': {'url': asset['source']}} for asset in verified_post['assets']],
                     'metadata': {'facebook': {'type': 'post'}}}})['editPost']
    if result.get('message'):
        raise RuntimeError('Buffer rejected publication: ' + result['message'])
    post = result.get('post') or {}
    if post.get('id') != post_id or post.get('status') not in ('scheduled', 'sending', 'sent'):
        raise RuntimeError('Buffer did not accept automatic publication; do not retry blindly')
    if post.get('schedulingType') != 'automatic':
        raise RuntimeError('Buffer requires manual notification publishing')
    return post


def publish_one(filename, persist):
    policy = json.loads((bridge.ROOT / 'dri/publishing.json').read_text())
    if policy.get('enabled') is not True:
        raise RuntimeError('Automatic publication is disabled')
    instant, data, body = bridge.validate_file(filename)
    day = instant.date().isoformat()
    if day < policy['start_date']:
        raise RuntimeError('Edition precedes automatic publication authorization')
    receipt = json.loads((bridge.STATE / f'{day}.delivery.json').read_text())
    post_id = (bridge.STATE / f'{day}.buffer-id').read_text().strip()
    if receipt.get('status') != 'delivered' or receipt.get('buffer_id') != post_id:
        raise RuntimeError('Missing confirmed draft delivery')
    if receipt.get('verified_text_sha256') != digest(body):
        raise RuntimeError('Incoming text differs from the verified delivered edition')
    channel = check_channel()
    post = get_post(post_id)
    validate_post(post, receipt, channel['id'])
    claim = bridge.STATE / f'{day}.publication.json'

    def save(status, current):
        record = {'date': day, 'buffer_id': post_id, 'status': status,
                  'run_id': os.environ['GITHUB_RUN_ID'],
                  'text_sha256': receipt['text_sha256'],
                  'external_link': current.get('externalLink'), 'sent_at': current.get('sentAt')}
        claim.write_text(json.dumps(record, indent=2))
        persist([str(claim.relative_to(bridge.ROOT))], f'chore(dri): record {day} publication {status}')

    if claim.exists() and json.loads(claim.read_text()).get('buffer_id') != post_id:
        raise RuntimeError('Publication reservation belongs to another post')
    if post['status'] == 'draft':
        if claim.exists() and json.loads(claim.read_text()).get('status') != 'reconciled_rejection':
            raise RuntimeError('Ambiguous earlier publication attempt: reconcile before retrying')
        # Only maintenance may mark a definitive rejection reconciled after a live
        # read proves the original post is still a draft. The reservation below
        # consumes that one-time retry; timeouts always remain blocked.
        verify(data, instant)
        post = get_post(post_id)
        validate_post(post, receipt, channel['id'])
        if post['status'] != 'draft':
            raise RuntimeError('Post state changed during verification; no mutation performed')
        save('reserved', post)
        request_publication(post)
    elif post['status'] not in ('scheduled', 'sending', 'sent'):
        raise RuntimeError('Buffer publication blocked: ' + str(post.get('error') or post['status']))
    elif post.get('schedulingType') != 'automatic':
        raise RuntimeError('Existing post requires manual publishing')

    # Retries reconcile the same id; never repeat an ambiguous mutation.
    for attempt in range(25):
        post = get_post(post_id)
        validate_post(post, receipt, channel['id'])
        if post['status'] == 'sent' and post.get('sentAt'):
            save('sent', post)
            print('PUBLISHED', day, post_id, post.get('externalLink'))
            return post
        if post['status'] not in ('scheduled', 'sending'):
            raise RuntimeError('Publication failed: ' + str(post.get('error') or post['status']))
        if attempt < 24:
            time.sleep(5)
    save(post['status'], post)
    raise RuntimeError('Publication accepted but not confirmed sent; receipt retained, never recreate')

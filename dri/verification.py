"""Fail closed on missing editorial review or unavailable source evidence.
This checks evidence records and excerpts, not the truth of semantic claims.
"""
import hashlib
import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin
import requests
from bot import TZ, UA, is_trusted


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def read_source(url):
    for _ in range(5):
        if not is_trusted(url):
            raise RuntimeError('Untrusted source or redirect')
        response = requests.get(url, headers={'User-Agent': UA}, timeout=30, allow_redirects=False)
        if response.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, response.headers['Location'])
            continue
        response.raise_for_status()
        if 'html' not in response.headers.get('Content-Type', ''):
            raise RuntimeError('Source must be readable HTML; select an accessible primary source')
        parser = PageText()
        parser.feed(response.text)
        return normalize(' '.join(parser.parts))
    raise RuntimeError('Too many source redirects')


def verify(data, instant, fetch=read_source):
    review = data.get('verification') or {}
    if review.get('status') != 'passed' or review.get('unresolved_claims') != []:
        raise RuntimeError('Missing or failed source verification')
    if review.get('reviewed_text') != data['facebook_text']:
        raise RuntimeError('Fact-check must cover the exact final text')
    if review.get('method') != 'independent_source_review':
        raise RuntimeError('Independent source review is required')
    for source in data['sources']:
        evidence = source.get('evidence') or {}
        url = evidence.get('url')
        quote = evidence.get('excerpt', '')
        if url not in source.get('urls', []) or not is_trusted(url):
            raise RuntimeError('Missing verified authoritative source URL')
        if evidence.get('verified') is not True or not evidence.get('supported_claims'):
            raise RuntimeError('Missing verified claims')
        if not isinstance(quote, str) or len(quote.strip()) < 20 or len(quote.split()) > 25:
            raise RuntimeError('Evidence needs a short exact excerpt (at most 25 words)')
        checked = datetime.fromisoformat(evidence.get('checked_at', ''))
        if checked.tzinfo is None or checked.astimezone(TZ).date() != instant.date():
            raise RuntimeError('Evidence must be checked on the edition date with a timezone')
        event_day = datetime.strptime(source.get('event_date', ''), '%Y-%m-%d').date()
        if not 0 <= (instant.date() - event_day).days <= (9 if data['mode'] == 'weekly' else 3):
            raise RuntimeError('Event date is future or stale')
        source_day = datetime.strptime(source.get('source_date', ''), '%Y-%m-%d').date()
        age = (instant.date() - source_day).days
        if not 0 <= age <= (9 if data['mode'] == 'weekly' else 3):
            raise RuntimeError('Source publication date is missing, future or stale')
        if normalize(quote) not in fetch(url):
            raise RuntimeError('Source excerpt could not be independently retrieved; delivery blocked')
    return digest(data['facebook_text'])

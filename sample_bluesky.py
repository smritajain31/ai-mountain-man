#!/usr/bin/env python3
"""Listen to the free Bluesky Jetstream feed for a while and count how many new
posts mention "artificial intelligence" or "superintelligence".

Counts are stored per UTC hour, together with how many seconds were actually
listened, so the site can turn samples into honest daily estimates:
    estimate = mentions / seconds_listened * seconds_in_day

Writes data/bluesky.json. If the file already exists (the workflow downloads the
live copy first), new hours are added to it, so history keeps growing and a
failed run never wipes older days.

Usage:  SAMPLE_SECONDS=1800 python3 sample_bluesky.py
"""
import asyncio
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import websockets

OUT = 'data/bluesky.json'
KEEP_DAYS = 45
SECONDS = int(os.environ.get('SAMPLE_SECONDS', '1800'))
HOSTS = os.environ.get('JETSTREAM_HOSTS', 'jetstream2.us-east.bsky.network,jetstream1.us-east.bsky.network,'
                       'jetstream1.us-west.bsky.network,jetstream2.us-west.bsky.network').split(',')
SCHEME = os.environ.get('JETSTREAM_SCHEME', 'wss')
RX_AI = re.compile(r'artificial[\s-]+intelligence', re.I)
RX_SI = re.compile(r'super[\s-]?intelligen', re.I)
FIELDS = ('secs', 'posts', 'ai', 'si', 'posts_en', 'ai_en', 'si_en')


def hour_key(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y%m%d%H')


def credit(hours, start, end):
    """Add listened seconds to each UTC hour between start and end."""
    while start < end:
        boundary = (int(start) // 3600 + 1) * 3600
        stop = min(end, boundary)
        hours[hour_key(start)]['secs'] += stop - start
        start = stop


async def listen(duration):
    hours = defaultdict(lambda: dict.fromkeys(FIELDS, 0))
    langs = defaultdict(lambda: defaultdict(int))
    deadline = time.time() + duration
    attempt = 0
    while time.time() < deadline - 5:
        host = HOSTS[attempt % len(HOSTS)].strip()
        attempt += 1
        uri = f'{SCHEME}://{host}/subscribe?wantedCollections=app.bsky.feed.post'
        last = None
        try:
            async with websockets.connect(uri, max_size=2 ** 22, open_timeout=20, ping_interval=20,
                                          user_agent_header='AI-Mountain-Man/3.0 (portfolio data visualization)') as ws:
                print(f'Connected to {host}', flush=True)
                last = time.time()
                while time.time() < deadline:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=max(1, min(45, deadline - time.time() + 1)))
                    except asyncio.TimeoutError:
                        if time.time() >= deadline:
                            credit(hours, last, time.time())  # connected but quiet until the end
                            break
                        raise
                    now = time.time()
                    credit(hours, last, now)
                    last = now
                    try:
                        msg = json.loads(raw)
                    except ValueError:
                        continue
                    commit = msg.get('commit') or {}
                    if commit.get('operation') != 'create' or commit.get('collection', 'app.bsky.feed.post') != 'app.bsky.feed.post':
                        continue
                    rec = commit.get('record') or {}
                    text = rec.get('text') or ''
                    tags = [str(x).lower() for x in (rec.get('langs') or []) if x]
                    english = any(t.startswith('en') for t in tags)
                    h = hours[hour_key(now)]
                    h['posts'] += 1
                    h['posts_en'] += english
                    is_ai, is_si = bool(RX_AI.search(text)), bool(RX_SI.search(text))
                    if is_ai:
                        h['ai'] += 1
                        h['ai_en'] += english
                    if is_si:
                        h['si'] += 1
                        h['si_en'] += english
                    if is_ai or is_si:
                        day = hour_key(now)[:8]
                        langs[day][(tags[0].split('-')[0] if tags else 'unknown')] += 1
        except Exception as exc:  # noqa: BLE001
            # time after the last received post is not credited: nothing was being counted
            print(f'{host}: {type(exc).__name__}: {exc}', flush=True)
            await asyncio.sleep(min(30, 3 * attempt))
    return hours, langs


def main():
    data = {'hours': {}, 'langs': {}}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding='utf-8') as f:
                old = json.load(f)
            data['hours'] = old.get('hours') or {}
            data['langs'] = old.get('langs') or {}
            print(f"Loaded {len(data['hours'])} existing hours")
        except Exception as exc:  # noqa: BLE001
            print(f'Ignoring unreadable existing file: {exc}')

    print(f'Listening for {SECONDS} seconds…', flush=True)
    hours, langs = asyncio.run(listen(SECONDS))
    listened = sum(h['secs'] for h in hours.values())
    found = sum(h['ai'] + h['si'] for h in hours.values())
    posts = sum(h['posts'] for h in hours.values())
    print(f'Listened {listened:.0f}s · {posts} posts · {found} mentions')

    for k, h in hours.items():
        slot = data['hours'].setdefault(k, dict.fromkeys(FIELDS, 0))
        for f in FIELDS:
            total = slot.get(f, 0) + h[f]
            slot[f] = round(total, 1) if f == 'secs' else int(total)
    for day, counts in langs.items():
        slot = data['langs'].setdefault(day, {})
        for lang, n in counts.items():
            slot[lang] = slot.get(lang, 0) + n

    if not data['hours']:
        sys.exit('Nothing collected and nothing saved before; the site will show sample data.')

    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime('%Y%m%d')
    data['hours'] = {k: data['hours'][k] for k in sorted(data['hours']) if k[:8] >= cutoff}
    data['langs'] = {k: data['langs'][k] for k in sorted(data['langs']) if k >= cutoff}
    os.makedirs('data', exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'source': 'Bluesky Jetstream (sampled)', 'updated_at': datetime.now(timezone.utc).isoformat(),
                   'timezone': 'UTC', 'terms': {'ai': 'artificial intelligence', 'si': 'super intelligence (any spelling)'},
                   'hours': data['hours'], 'langs': data['langs']}, f, separators=(',', ':'))
    os.replace(tmp, OUT)
    print(f"Saved {len(data['hours'])} hours")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Collect daily news-article counts for "artificial intelligence" and
"superintelligence" from the free GDELT DOC 2.0 API, worldwide and US-only.

Writes data/gdelt.json in the shape the site reads:
  {"updated_at": "...", "days": {"YYYYMMDD": {"world": {"ai", "si", "total"}, "us": {...}}}}

If data/gdelt.json already exists (the workflow downloads the live copy first),
new numbers are merged into it, so history keeps growing past GDELT's window and
a failed run never wipes out older days.
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ENDPOINT = 'https://api.gdeltproject.org/api/v2/doc/doc'
OUT = 'data/gdelt.json'
KEEP_DAYS = 180
TERMS = {'ai': '"artificial intelligence"', 'si': 'superintelligence'}
REGIONS = {'world': '', 'us': ' sourcecountry:US'}
PAUSE = 6  # GDELT asks for at most one request every 5 seconds


def fetch(query):
    params = urllib.parse.urlencode({'query': query, 'mode': 'timelinevolraw', 'timespan': '30d', 'format': 'json'})
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(f'{ENDPOINT}?{params}', headers={
                'User-Agent': 'AI-Mountain-Man/2.0 (portfolio data visualization)', 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=75) as r:
                payload = json.load(r)
            timelines = payload.get('timeline') or []
            series = next((t for t in timelines if not any(w in t.get('series', '').lower() for w in ('total', 'all '))), None) \
                or (timelines[0] if timelines else None)
            if not series or not isinstance(series.get('data'), list):
                raise ValueError('no timeline in response')
            days = {}
            for p in series['data']:
                key = str(p.get('date', ''))[:8]
                v, n = p.get('value'), p.get('norm')
                if len(key) != 8 or not key.isdigit() or not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0:
                    continue
                d = days.setdefault(key, {'v': 0, 'n': 0})
                d['v'] += v  # sums hourly or 15-minute buckets into a UTC day
                if isinstance(n, (int, float)) and math.isfinite(n):
                    d['n'] += n
            if not days:
                raise ValueError('no usable counts')
            return days
        except Exception as e:  # noqa: BLE001
            last = e
            print(f'  attempt {attempt + 1} failed: {type(e).__name__}: {e}', flush=True)
            time.sleep(PAUSE * (attempt + 2))
    raise RuntimeError(f'GDELT unavailable for {query!r}: {last}')


def main():
    existing = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding='utf-8') as f:
                existing = json.load(f).get('days', {}) or {}
            print(f'Loaded {len(existing)} existing days')
        except Exception as e:  # noqa: BLE001
            print(f'Ignoring unreadable existing file: {e}')

    days = {k: dict(v) for k, v in existing.items()}
    ok = 0
    for reg, suffix in REGIONS.items():
        for term, query in TERMS.items():
            print(f'Fetching {reg}/{term} …', flush=True)
            try:
                got = fetch(query + suffix)
                ok += 1
                for k, d in got.items():
                    slot = days.setdefault(k, {}).setdefault(reg, {})
                    slot[term] = int(round(d['v']))
                    if term == 'ai' and d['n']:
                        slot['total'] = int(round(d['n']))
            except Exception as e:  # noqa: BLE001
                print(f'  skipped: {e}', file=sys.stderr)
            time.sleep(PAUSE)

    if not ok and not existing:
        raise SystemExit('No data from GDELT and nothing saved before; leaving site without news data.')

    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).strftime('%Y%m%d')
    days = {k: days[k] for k in sorted(days) if k >= cutoff}
    os.makedirs('data', exist_ok=True)
    tmp = OUT + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({'source': 'GDELT DOC 2.0 timelinevolraw', 'updated_at': datetime.now(timezone.utc).isoformat(),
                   'timezone': 'UTC', 'queries': {**TERMS, 'us_filter': 'sourcecountry:US'}, 'days': days},
                  f, separators=(',', ':'))
    os.replace(tmp, OUT)
    print(f'Saved {len(days)} days ({ok}/4 series refreshed)')


if __name__ == '__main__':
    main()

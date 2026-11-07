#!/usr/bin/env python3
"""Fetch two GDELT timelines and publish only a complete, validated pair."""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ENDPOINT = 'https://api.gdeltproject.org/api/v2/doc/doc'

def fetch(term):
    params = urllib.parse.urlencode({'query': term, 'mode': 'timelinevolraw', 'timespan': '14d', 'format': 'json'})
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(ENDPOINT + '?' + params, headers={'User-Agent': 'AI-Mountain-Man/1.0 (public news data visualization)', 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=75) as response:
                payload = json.load(response)
            timelines = payload.get('timeline') or []
            series = next((x for x in timelines if 'matching' in x.get('series','').lower()), timelines[0] if timelines else None)
            if not series or not isinstance(series.get('data'), list):
                raise ValueError('GDELT did not return a timeline')
            points = {}
            for point in series['data']:
                key = str(point.get('date', ''))[:8]
                value = point.get('value')
                if len(key) == 8 and key.isdigit() and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                    points[key] = value
            if not points:
                raise ValueError('GDELT returned no usable counts')
            return points
        except Exception as exc:
            last_error = exc
            print(f'GDELT attempt {attempt + 1} failed: {type(exc).__name__}: {exc}', flush=True)
            if attempt < 2:
                time.sleep(20 * (attempt + 1))
    raise RuntimeError(f'GDELT unavailable after retries: {last_error}')

def main():
    ai = fetch('"artificial intelligence"')
    time.sleep(7)
    si = fetch('superintelligence')
    now = datetime.now(timezone.utc)
    dates = [(now - timedelta(days=offset)).strftime('%Y%m%d') for offset in range(6, -1, -1)]
    rows = [{'date': k, 'ai': ai.get(k), 'si': si.get(k)} for k in dates]
    if not any(row['ai'] is not None or row['si'] is not None for row in rows):
        raise ValueError('Neither timeline returned data for the last seven UTC days')
    result = {'source':'GDELT DOC 2.0 TimelineVolRaw', 'updated_at':datetime.now(timezone.utc).isoformat(), 'timezone':'UTC', 'queries': {'ai':'"artificial intelligence"','si':'superintelligence'}, 'days':rows}
    os.makedirs('data', exist_ok=True)
    with open('data/gdelt.json.tmp', 'w', encoding='utf-8') as f:
        json.dump(result, f, separators=(',', ':'))
    os.replace('data/gdelt.json.tmp', 'data/gdelt.json')
    print(f'Saved {len(rows)} UTC days, with missing source values marked unavailable; last date {dates[-1]}')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'Update failed: {e}', file=sys.stderr)
        sys.exit(1)

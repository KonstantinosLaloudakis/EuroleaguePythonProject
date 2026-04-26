"""Fetch and cache the Euroleague season schedule (date + tip-off time per game).

Used by export_dashboard_data.py to populate scheduled dates/times for upcoming
playoff games on the Series Hub timeline.
"""
import argparse
import json
import os
import sys

from euroleague_api.schedule import Schedule


SCHEDULE_COLUMNS = [
    'gameday', 'round', 'date', 'startime', 'gamecode',
    'hometeam', 'homecode', 'awayteam', 'awaycode',
    'arenaname', 'confirmeddate', 'confirmedtime', 'played',
]


def fetch_and_cache_schedule(season=2025):
    out_path = f'schedule_{season}.json'
    force_fetch = '--force' in sys.argv

    if os.path.exists(out_path) and not force_fetch:
        print(f"Loading cached schedule from {out_path}")
        with open(out_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    print(f"Fetching schedule for {season} season...")
    sched = Schedule(competition='E')
    df = sched.get_schedule(season)

    keep = [c for c in SCHEDULE_COLUMNS if c in df.columns]
    df = df[keep].copy()

    for col in ('gameday', 'gamecode'):
        if col in df.columns:
            df[col] = df[col].astype(str)

    records = df.to_dict(orient='records')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(records)} schedule rows to {out_path}")
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch Euroleague schedule')
    parser.add_argument('--season', type=int, default=2025, help='Season year (default: 2025)')
    parser.add_argument('--force', action='store_true', help='Force re-fetch even if cached')
    args = parser.parse_args()
    fetch_and_cache_schedule(season=args.season)

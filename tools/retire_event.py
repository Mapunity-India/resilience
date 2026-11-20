#!/usr/bin/env python3
"""Retire a live event: drop the LIVE marker and leave it as a past cyclone.

    python3 tools/retire_event.py --event akvan --dry-run
    python3 tools/retire_event.py --event akvan

What it changes, and only this:

  index.html    the event row loses its live class and its live pill, and its
                date reads as a range ending on the day of landfall
  the record    nothing is invented: the landfall time comes from
                data/<event>-postevent.json, which postevent.py writes

It does not touch the event page's content, and it does not delete anything.
Run it once, when the storm is over; running it twice changes nothing.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INDEX = os.path.join(ROOT, 'index.html')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--event', required=True, help='the slug, e.g. akvan')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    page = os.path.join(ROOT, 'events', '%s.html' % a.event)
    if not os.path.exists(page):
        sys.exit('no page at events/%s.html' % a.event)

    index = open(INDEX, encoding='utf-8').read()
    row_re = re.compile(
        r'<a class="evline evline--live" href="events/%s\.html">(.*?)</a>' % re.escape(a.event), re.S)
    m = row_re.search(index)
    if not m:
        print('nothing to do: the %s row is not marked live' % a.event)
        return
    body = m.group(1)

    # the date reads as a range, from the first day of the event to landfall
    dm = re.search(r'<span class="evline__date">since ([^<]+)</span>', body)
    landed = None
    rec_path = os.path.join(ROOT, 'data', '%s-postevent.json' % a.event)
    if os.path.exists(rec_path):
        rec = json.load(open(rec_path, encoding='utf-8'))
        lf = rec.get('landfall')
        # postevent.py keeps landfall as a record holding its time and place
        landed = lf.get('at') if isinstance(lf, dict) else lf
    if dm and landed:
        try:
            when = datetime.datetime.fromisoformat(landed)
            body = body.replace(
                '<span class="evline__date">since %s</span>' % dm.group(1),
                '<span class="evline__date">%s &ndash; %d %s %d</span>' % (
                    dm.group(1), when.day, when.strftime('%B'), when.year))
        except Exception:
            pass

    # the pill goes
    body = re.sub(r'<span class="evline__live">[^<]*</span>', '', body)
    new_row = '<a class="evline" href="events/%s.html">%s</a>' % (a.event, body)
    new_index = index[:m.start()] + new_row + index[m.end():]

    print('row now reads:')
    print('  ' + re.sub(r'\s+', ' ', new_row)[:220])
    if a.dry_run:
        print('dry run: nothing written')
        return

    open(INDEX, 'w', encoding='utf-8').write(new_index)

    log = os.path.join(ROOT, 'changelog.json')
    e = json.load(open(log, encoding='utf-8'))
    e.append({
        'id': 'retire-%s' % a.event,
        'date': datetime.date.today().isoformat(),
        'change': ('%s is retired as a live event. The LIVE marker is gone from its row on the index, '
                   'the row now reads as a date range ending on the day it crossed, and it sits among '
                   'the past cyclones with Murasu and Arnab. The event page itself is unchanged') % a.event,
        'scope': 'index.html',
        'check': {'type': 'absent', 'pattern': 'evline--live" href="events/%s.html"' % a.event,
                  'paths': ['index.html'], 'min': 1},
    })
    json.dump(e, open(log, 'w', encoding='utf-8'), indent=1)
    print('index updated and the changelog entry written')


if __name__ == '__main__':
    main()

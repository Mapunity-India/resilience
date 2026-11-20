#!/usr/bin/env python3
"""Retire a live event: name it by its peak, drop the LIVE marker, close the row.

    python3 tools/retire_event.py --event akvan --dry-run
    python3 tools/retire_event.py --event akvan

IMD names a storm in the record by the highest category it ever reached, not by
what it was at the coast: the report on Vardah is titled a very severe cyclonic
storm, though Vardah crossed near Chennai as a severe one. So on retirement the
page takes the peak category as its name, and the note beneath it says how long
it held that strength and what it was when it came ashore.

What it changes, and only this:

  the page title   <title> and the header h1 take the peak category from
                   data/event.json, so "Deep depression Akvan" becomes
                   "Severe Cyclonic Storm Akvan"
  the note         rewritten from the record: when it peaked, and what it was at
                   the coast
  index.html       the event row loses its live class and its live pill, and its
                   date reads as a range ending on the day of landfall
  the record       data/event.json is marked past, with the peak as descriptor

Nothing is invented: every value comes from the record, and if the peak is not
there the tool refuses rather than guessing. Running it twice changes nothing.
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

    page_path = os.path.join(ROOT, 'events', '%s.html' % a.event)
    if not os.path.exists(page_path):
        sys.exit('no page at events/%s.html' % a.event)

    ev_path = os.path.join(ROOT, 'data', 'event.json')
    ev = json.load(open(ev_path, encoding='utf-8'))
    peak = (ev.get('peak') or '').strip()
    if not peak:
        sys.exit('data/event.json has no peak category: add it before retiring, so the '
                 'page is named by the strongest the storm got rather than by what it was '
                 'when it came ashore')
    name = ev.get('name') or a.event.title()
    archive_title = '%s %s' % (peak.title(), name)     # Severe Cyclonic Storm Akvan

    note = ev.get('note') or ''
    if ev.get('peak_from') and ev.get('landfall_descriptor'):
        note = '%s from %s to %s; crossed %s as a %s' % (
            peak.lower(), ev['peak_from'], ev.get('peak_to', ''), 
            ev.get('landfall_where', 'the coast'), ev['landfall_descriptor'])

    page = open(page_path, encoding='utf-8').read()
    new_page = re.sub(r'<title>[^<]*</title>',
                      '<title>%s &mdash; Resilience</title>' % archive_title, page, count=1)
    new_page = re.sub(
        r'(<h1 class="header__title">)[^<]*(<span class="header__title-note">)[^<]*(</span>)',
        lambda m: '%s%s %s%s%s' % (m.group(1), archive_title, m.group(2), note, m.group(3)),
        new_page, count=1)
    changed_page = new_page != page

    index = open(INDEX, encoding='utf-8').read()
    row_re = re.compile(
        r'<a class="evline evline--live" href="events/%s\.html">(.*?)</a>' % re.escape(a.event), re.S)
    m = row_re.search(index)
    new_index = index
    if m:
        body = m.group(1)
        dm = re.search(r'<span class="evline__date">since ([^<]+)</span>', body)
        rec_path = os.path.join(ROOT, 'data', '%s-postevent.json' % a.event)
        landed = None
        if os.path.exists(rec_path):
            rec = json.load(open(rec_path, encoding='utf-8'))
            lf = rec.get('landfall')
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
        body = re.sub(r'<span class="evline__live">[^<]*</span>', '', body)
        new_row = '<a class="evline" href="events/%s.html">%s</a>' % (a.event, body)
        new_index = index[:m.start()] + new_row + index[m.end():]

    print('page title becomes: %s' % archive_title)
    print('note becomes      : %s' % note)
    print('index row         : %s' % ('no live marker to remove' if m is None else 'live marker removed'))
    if a.dry_run:
        print('dry run: nothing written')
        return

    if changed_page:
        open(page_path, 'w', encoding='utf-8').write(new_page)
    if m:
        open(INDEX, 'w', encoding='utf-8').write(new_index)
    ev['status'] = 'past'
    ev['descriptor'] = peak
    json.dump(ev, open(ev_path, 'w', encoding='utf-8'), indent=1)

    log = os.path.join(ROOT, 'changelog.json')
    e = json.load(open(log, encoding='utf-8'))
    e.append({
        'id': 'retire-%s' % a.event,
        'date': datetime.date.today().isoformat(),
        'change': ('%s is retired as a live event. It takes the name of the strongest it got, %s, '
                   'the way IMD names a storm in the record by its peak rather than by what it was '
                   'at the coast, and the note beneath it says how long it held that strength and '
                   'what it was when it crossed. The LIVE marker is gone from its row on the index, '
                   'which now reads as a date range ending on the day it crossed, so it sits among '
                   'the past cyclones with Murasu and Arnab') % (name, archive_title),
        'scope': 'index.html, events/%s.html' % a.event,
        'check': {'type': 'absent', 'pattern': 'evline--live" href="events/%s.html"' % a.event,
                  'paths': ['index.html'], 'min': 1},
    })
    json.dump(e, open(log, 'w', encoding='utf-8'), indent=1)
    print('page, index and changelog written')


if __name__ == '__main__':
    main()

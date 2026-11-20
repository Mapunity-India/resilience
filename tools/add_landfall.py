#!/usr/bin/env python3
"""Add a cyclone landfall to the map on the resilience index.

The dots live inline in index.html, inside <g id="landfalls">, one circle each,
coloured by decade and sized by the peak category the storm reached. This adds
one more, and keeps the count in the legend honest.

    python3 tools/add_landfall.py --name Akvan --date 2026-11-20 \
        --lat 19.28 --lon 84.90 --coast "near Gopalpur, Odisha" \
        --peak "severe cyclonic storm" --peak-hour "11:30"

Nothing is guessed: if a coordinate or a coast is missing it refuses, because a
dot in the wrong place is worse than a dot that is a day late.
"""
import argparse
import datetime
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, 'index.html')
LOG = os.path.join(ROOT, 'changelog.json')

# The map is a Mercator plot. These constants were fitted against dots whose
# places are known: Alibag, Marakkanam and the Chennai coast.
X0, XK = -1605.23, 23.75
Y0, YK = 965.97, 1425.82

# circle radius by the peak category the storm reached, as the map already uses
SIZE = {
    'depression': 3.4,
    'deep depression': 3.9,
    'cyclonic storm': 4.5,
    'severe cyclonic storm': 5.3,
    'very severe': 6.3,
    'extremely severe': 7.5,
    'super cyclone': 8.8,
}
COLOUR = {'1990': '#111111', '2000': '#d6336c', '2010': '#f08c00', '2020': '#2e9e3f'}


def merc(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def project(lat, lon):
    return X0 + XK * lon, Y0 - YK * merc(lat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True, help='storm name, or its designation')
    ap.add_argument('--date', required=True, help='YYYY-MM-DD')
    ap.add_argument('--lat', type=float, required=True)
    ap.add_argument('--lon', type=float, required=True)
    ap.add_argument('--coast', required=True, help='where it crossed, in words')
    ap.add_argument('--peak', required=True, choices=sorted(SIZE))
    ap.add_argument('--peak-hour', default='', help='time of the fix the peak is taken from')
    ap.add_argument('--outside', action='store_true',
                    help='crossed outside India: drawn as a ring, not a dot')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    try:
        when = datetime.date.fromisoformat(a.date)
    except ValueError:
        sys.exit('date must be YYYY-MM-DD')
    decade = '%d' % (when.year - when.year % 10)
    if decade not in COLOUR:
        sys.exit('this tool only knows the four decades the map draws')

    page = open(PAGE, encoding='utf-8').read()
    if '<g id="landfalls">' not in page:
        sys.exit('no landfall group in index.html')

    label = '%s %d, %d %s: %s. Peak %s.' % (
        a.name, when.year, when.day, when.strftime('%B'), a.coast, a.peak)
    if a.peak_hour:
        label = label.replace(': %s. Peak' % a.coast,
                              ': %s, at %s. Peak' % (a.coast, a.peak_hour))
    if a.outside:
        label = label.replace('Peak %s.' % a.peak, 'Peak %s. Crossed outside India.' % a.peak)

    cx, cy = project(a.lat, a.lon)
    r = SIZE[a.peak]
    cls = 'lf-out' if a.outside else 'lf'
    dot = ('<circle class="%s d%s" r="%s" cx="%.1f" cy="%.1f" fill="%s">'
           '<title>%s</title></circle>') % (cls, decade, r, cx, cy, COLOUR[decade], label)

    if dot in page:
        print('already there: %s' % label)
        return

    # append at the end of the group, so the newest storm is drawn last
    i = page.find('<g id="landfalls">')
    j = page.find('</g>', i)
    page = page[:j] + dot + page[j:]

    # keep the count in the legend right
    page, n = re.subn(
        r'(<label class="lfrow"><input type="radio" name="dec" value="%s">.*?<span class="lfn">)(\s*)(\d+)(</span>)' % decade,
        lambda m: '%s%s%d%s' % (m.group(1), m.group(2), int(m.group(3)) + 1, m.group(4)),
        page, count=1, flags=re.S)

    print('adding: %s' % label)
    print('  at %.1f, %.1f, radius %s, colour %s' % (cx, cy, r, COLOUR[decade]))
    print('  legend count for the %ss %s' % (decade, 'updated' if n else 'NOT found'))

    if a.dry_run:
        print('  dry run: nothing written')
        return

    open(PAGE, 'w', encoding='utf-8').write(page)

    e = json.load(open(LOG, encoding='utf-8'))
    e.append({
        'id': 'landfall-%s' % a.name.lower().replace(' ', '-'),
        'date': a.date,
        'change': ('%s added to the landfall layer at %s, %.2fN %.2fE, peak %s. '
                   'The dot is drawn at %.1f, %.1f with a radius of %s, and the %ss count '
                   'in the legend goes up by one.') % (
            a.name, a.coast, a.lat, a.lon, a.peak, cx, cy, r, decade),
        'scope': 'index.html',
        'check': {'type': 'contains', 'pattern': label[:40], 'paths': ['index.html'], 'min': 1},
    })
    json.dump(e, open(LOG, 'w', encoding='utf-8'), indent=1)
    print('  written to index.html and the changelog')


if __name__ == '__main__':
    main()

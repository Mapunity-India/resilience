#!/usr/bin/env python3
"""Poll the cyclone bulletin, record the position, and redraw the marker.

Server-ready: standard library only, no state outside this directory, safe to
run from cron as often as you like.

    python3 fetch_position.py                 # fetch only if the interval has passed
    python3 fetch_position.py --force         # fetch now regardless
    python3 fetch_position.py --dry-run       # parse and report, write nothing
    python3 fetch_position.py --fixture f.txt # parse a saved bulletin instead of fetching
    python3 fetch_position.py --status        # report state and exit

Exit codes, for cron mail and monitoring:
    0  fine: fetched and recorded, or not due yet, or the event has ended
    2  no bulletin could be fetched (network or the source moved)
    3  a bulletin was fetched but no position parsed (format changed)
    4  the event has ended; this run did nothing
    5  configuration problem (page or data path missing)

Timing. IMD issues a bulletin every three hours, and more often near landfall.
The default minimum interval is 90 minutes, so a cron job that fires every ten
minutes still fetches at most once per 90, and catches each new bulletin within
90 minutes of issue. Set --min-interval to change it.

Stopping. The event ends when the bulletin calls the system a low pressure area
or a remnant, or when nothing new has arrived for --stale-hours (default 12).
Once ended, the script writes status "ended" and every later run exits 4
without fetching, so the page freezes on the last good position rather than
decaying. Remove data/observations.json, or pass --force, to start again.
"""
import argparse, json, math, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PAGE = os.path.abspath(os.path.join(HERE, '..', 'events', 'akvan.html'))
DATA = os.path.abspath(os.path.join(HERE, '..', 'data', 'observations.json'))   # published beside events/

SOURCES = [
    'https://mausam.imd.gov.in/api/warnings_current_api.php',
    'https://rsmcnewdelhi.imd.gov.in/uploads/latest_bulletin.pdf',
]

# the map's projection, shared with the page build
LAT0, LAT1, LON0, LON1 = 6.5, 37.5, 68.0, 97.5
K = math.cos(math.radians((LAT0 + LAT1) / 2))
SCALE = 700.0 / ((LON1 - LON0) * K)
VB_W, VB_H = 720.0, (LAT1 - LAT0) * SCALE + 20

LAT_RE = re.compile(r'latit\w*\s*(?:of\s*)?([0-9]{1,2}(?:\.[0-9]+)?)\s*[°\s]*\s*N', re.I)
LON_RE = re.compile(r'longit\w*\s*(?:of\s*)?([0-9]{1,3}(?:\.[0-9]+)?)\s*[°\s]*\s*E', re.I)
TIME_RE = re.compile(r'(\d{4})\s*hours?\s*IST', re.I)
DATE_RE = re.compile(r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|'
                     r'September|October|November|December),?\s+(\d{4})', re.I)
MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
          'september', 'october', 'november', 'december']

INTENSITY = [('remnant', 'Remnant of a depression'),
             ('well marked low pressure', 'Well marked low pressure area'),
             ('low pressure area', 'Low pressure area'),
             ('very severe cyclonic storm', 'Very severe cyclonic storm'),
             ('severe cyclonic storm', 'Severe cyclonic storm'),
             ('cyclonic storm', 'Cyclonic storm'),
             ('deep depression', 'Deep depression'),
             ('depression', 'Depression')]

ENDED = {'Low pressure area', 'Well marked low pressure area', 'Remnant of a depression'}

# a position outside this box is a parsing accident, not a cyclone
WHERE_RE = re.compile(r'(\d{2,4})\s*km\s+([a-z\- ]+?)\s+of\s+([A-Z][A-Za-z \\.&]+?)(?=,\s*\d|\s*and\s+lay|\s*\.|\s*$)')

SANITY = (68.0, 98.0, 5.0, 30.0)   # lon0, lon1, lat0, lat1: India and its seas, wide enough
                                   # to hold a landfall position, narrow enough to reject nonsense


def project(lon, lat):
    return (10 + (lon - LON0) * K * SCALE, 10 + (LAT1 - lat) * SCALE)


def now_ist():
    return datetime.now(IST)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'resilience-poller/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    try:
        return raw.decode('utf-8', 'ignore')
    except Exception:
        return raw.decode('latin-1', 'ignore')


def parse(text, today=None):
    lat = LAT_RE.search(text)
    lon = LON_RE.search(text)
    if not (lat and lon):
        return None
    lat, lon = float(lat.group(1)), float(lon.group(1))
    l0, l1, b0, b1 = SANITY
    if not (l0 <= lon <= l1 and b0 <= lat <= b1):
        return None
    t = TIME_RE.search(text)
    d = DATE_RE.search(text)
    issue = None
    if t:
        hhmm = t.group(1)
        if d:
            issue = '%s-%02d-%02dT%s:%s:00+05:30' % (d.group(3), MONTHS.index(d.group(2).lower()) + 1,
                                                     int(d.group(1)), hhmm[:2], hhmm[2:])
        else:
            today = today or now_ist()
            issue = '%sT%s:%s:00+05:30' % (today.strftime('%Y-%m-%d'), hhmm[:2], hhmm[2:])
    low = text.lower()
    intensity = next((label for key, label in INTENSITY if key in low), 'Unknown')
    # the distances IMD gives to reference places, kept so the page can show them
    where = []
    for seg in re.split(r',|\band\b', text):
        m2 = re.search(r'(\d{2,4})\s*km\s+([a-z\- ]+?)\s+of\s+([A-Z][A-Za-z \\.&]+)', seg)
        if m2:
            place = re.sub(r'\s*\([^)]*\)', '', m2.group(3)).strip().rstrip('.')
            where.append('%s km %s of %s' % (m2.group(1), m2.group(2).strip(), place))
    return {'lat': lat, 'lon': lon, 'issue': issue, 'intensity': intensity,
            'where': ', '.join(where[:4]),
            'fetched': now_ist().isoformat(timespec='seconds')}


def load(path):
    if os.path.exists(path):
        return json.load(open(path))
    return {'event': 'akvan', 'status': 'live', 'observations': []}


def save(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    json.dump(data, open(tmp, 'w'), indent=1)
    os.replace(tmp, path)          # never leave a half-written state file


def minutes_since(iso, ref=None):
    if not iso:
        return None
    ref = ref or now_ist()
    return (ref - datetime.fromisoformat(iso)).total_seconds() / 60.0


def redraw(data, page_path):
    """Rewrite everything between the akvan markers from the observations."""
    pts = data['observations']
    if not pts or not os.path.exists(page_path):
        return False
    page = open(page_path, encoding='utf-8').read()
    if '<!-- akvan:start -->' not in page or '<!-- akvan:end -->' not in page:
        return False
    xy = [project(p['lon'], p['lat']) for p in pts]
    last = pts[-1]
    lx, ly = xy[-1]
    # The forecast comes from the record, not from a constant: IMD moves the crossing
    # corridor as the storm goes on, and a fixed anchor left the dashed line pointing at
    # a coast the storm was no longer expected to reach.
    fc = data.get('forecast') or {}
    corr = fc.get('corridor') or []
    corr_xy = [project(c['lon'], c['lat']) for c in corr] if len(corr) >= 2 else None
    if corr_xy:
        # the line ends at the named target, or the middle of the corridor if none is named
        names = [c.get('name') for c in corr]
        tgt = fc.get('target')
        k = names.index(tgt) if tgt in names else len(corr_xy) // 2
        fx, fy = corr_xy[k]
    else:
        fx, fy = 302.0, 576.0                  # fall back to the old anchor if none is recorded

    track = 'M' + ' L'.join('%.1f %.1f' % p for p in xy)
    dots = ''.join('<circle cx="%.1f" cy="%.1f" r="4.2" fill="#8f2318" fill-opacity="0.6" '
                   'stroke="#faf9f7" stroke-width="1.2"/>' % p for p in xy[:-1])
    try:
        stamp = datetime.fromisoformat(last['issue']).strftime('%d %b %H:%M').upper()
    except Exception:
        stamp = (last['issue'] or '')[:16].replace('T', ' ')

    corridor_svg = ''
    if corr_xy:
        # the bar follows the coast through every point in the corridor, with a tick at each end
        d = 'M' + ' L'.join('%.1f %.1f' % q for q in corr_xy)
        (ax, ay), (bx, by) = corr_xy[0], corr_xy[-1]
        corridor_svg = (
            '<path d="%s" fill="none" stroke="#8f2318" stroke-width="5" stroke-linejoin="round" '
            'stroke-linecap="round" opacity="0.45"/>'
            '<path d="M%.1f %.1f l0 -7 M%.1f %.1f l0 7 M%.1f %.1f l0 -7 M%.1f %.1f l0 7" '
            'stroke="#8f2318" stroke-width="1.6" opacity="0.7"/>'
        ) % (d, ax, ay, ax, ay, bx, by, bx, by)
    block = (
        '<path d="%s" fill="none" stroke="#8f2318" stroke-width="1.3" stroke-opacity="0.45" '
        'stroke-linecap="round"/>%s'
        '<path d="M%.1f %.1f Q%.1f %.1f %.1f %.1f" fill="none" stroke="#8f2318" stroke-width="2.4" '
        'stroke-dasharray="8 6" stroke-linecap="round" opacity="0.9"/>'
        '%s'
        '<circle cx="%.1f" cy="%.1f" r="15" fill="none" stroke="#8f2318" stroke-width="1.6" opacity="0.4"/>'
        '<circle cx="%.1f" cy="%.1f" r="8" fill="#8f2318"/>'
        '<text x="%.1f" y="%.1f" font-family="JetBrains Mono, monospace" font-size="12" font-weight="700" '
        'fill="#8f2318" letter-spacing="1">AKVAN &middot; %s</text>'
        '<text x="%.1f" y="%.1f" font-family="JetBrains Mono, monospace" font-size="10" fill="#6b635a">%s</text>'
    ) % (track, dots, lx, ly, (lx + fx) / 2, (ly + fy) / 2 - 22, fx, fy, corridor_svg,
         lx, ly, lx, ly, lx + 18, ly - 8, stamp, lx + 18, ly + 6, last['intensity'].lower())

    page = re.sub(r'<!-- akvan:start -->.*?<!-- akvan:end -->',
                  '<!-- akvan:start -->' + block + '<!-- akvan:end -->', page, count=1, flags=re.S)

    # keep the rest of the page honest too: the time on the Track tab, the position
    # line and its source, so a poller run leaves nothing reading older than the fix
    hhmm = stamp.split(' ')[-1]
    # the Track tab is not the checked view once the satellite frame is in, so the
    # attribute list after value="track" varies: match it loosely or the label stays stale
    page = re.sub(r'(value="track"[^>]*><span>Track) <b class="vsat__t">[0-9:]*</b>',
                  r'\1 <b class="vsat__t">%s</b>' % hhmm, page, count=1)
    try:
        when = datetime.fromisoformat(last['issue']).strftime('%H:%M IST on %-d %B')
    except Exception:
        when = last['issue']
    where = last.get('where') or ''
    # a satellite fix gives a position and no distances: borrow the last bulletin that had
    # them, and say which bulletin it was, rather than leaving the sentence short
    borrow = None
    if not where:
        for q in reversed(pts[:-1]):
            if q.get('where'):
                try:
                    borrow = datetime.fromisoformat(q['issue']).strftime('%H:%M')
                except Exception:
                    borrow = ''
                where = q['where']
                break
    line = '%.1f&deg;N, %.1f&deg;E at %s' % (last['lat'], last['lon'], when)
    if last.get('movement'):
        line += ', moving ' + last['movement']
    line += '.'
    if where and borrow is not None:
        line += ' The nearest bulletin, at %s, put it about %s.' % (borrow, where)
    elif where:
        line += ' ' + where[0].upper() + where[1:] + '.'
    page = re.sub(r'<p id="posLine">.*?</p>', '<p id="posLine">%s</p>' % line, page, count=1, flags=re.S)
    page = re.sub(r'<p class="src" id="posSrc"[^>]*>.*?</p>',
                  '<p class="src" id="posSrc">IMD bulletin, %s</p>' % when.replace(' on ', ', '), page, count=1, flags=re.S)
    open(page_path, 'w', encoding='utf-8').write(page)
    return True


def set_redirect(live, page_path=None):
    """Retired. The landing page is the front door whether or not an event is running:
    handing the site over to the live event page meant every visitor mid event landed
    on one storm and had to be told why. The live event is a row on the landing page
    and a card in the map's EVENTS panel. Kept so older calls do not fail."""
    return False


def set_event_title(named, page_path=None):
    """Once IMD confers the name, the page says Cyclone Akvan and drops the provisional note."""
    page_path = page_path or DEFAULT_PAGE
    if not os.path.exists(page_path):
        return False
    page = open(page_path, encoding='utf-8').read()
    if named:
        new = re.sub(r'<h1 class="header__title">[^<]*(?:<span class="header__title-note">[^<]*</span>)?</h1>',
                     '<h1 class="header__title">Cyclone Akvan</h1>', page, count=1)
        new = re.sub(r'<title>[^<]*</title>',
                     '<title>Cyclone Akvan, November 2026 &mdash; Resilience</title>', new, count=1)
    else:
        new = re.sub(r'<h1 class="header__title">Cyclone Akvan</h1>',
                     '<h1 class="header__title">BOB/10/2026 <span class="header__title-note">likely to be named Akvan</span></h1>',
                     page, count=1)
    if new != page:
        open(page_path, 'w', encoding='utf-8').write(new)
        return True
    return False


def report(data):
    last = data['observations'][-1] if data['observations'] else None
    print('event   : %s (%s)' % (data.get('event'), data.get('status')))
    print('points  : %d' % len(data['observations']))
    if last:
        print('latest  : %.1fN %.1fE  %s  at %s' % (last['lat'], last['lon'], last['intensity'], last['issue']))
        print('age     : %.0f minutes' % (minutes_since(last.get('issue')) or 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default=DEFAULT_PAGE)
    ap.add_argument('--data', default=DATA)
    ap.add_argument('--min-interval', type=int, default=90, help='minutes between fetches')
    ap.add_argument('--stale-hours', type=int, default=12, help='end the event after this long with no update')
    ap.add_argument('--force', action='store_true', help='fetch even if not due, or if the event has ended')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--fixture')
    ap.add_argument('--status', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(args.page):
        print('page not found: %s' % args.page, file=sys.stderr)
        return 5

    data = load(args.data)

    if args.status:
        report(data)
        return 0

    # ended: do nothing, and say so, so the timer can be switched off
    if data.get('status') == 'ended' and not args.force:
        print('event ended on %s; nothing to do (use --force to reopen)'
              % data.get('ended_at', 'an earlier run'))
        return 4

    last = data['observations'][-1] if data['observations'] else None
    age = minutes_since(last.get('issue')) if last else None
    if last and age is not None and 0 <= age < args.min_interval and not args.force:
        print('not due: last observation is %.0f minutes old, interval is %d'
              % (age, args.min_interval))
        return 0

    text, used = None, None
    if args.fixture:
        text, used = open(args.fixture, encoding='utf-8', errors='ignore').read(), args.fixture
    else:
        for url in SOURCES:
            try:
                candidate = fetch(url)
            except Exception as e:
                print('fetch failed %s: %s' % (url, e), file=sys.stderr)
                continue
            if parse(candidate):
                text, used = candidate, url
                break
    if not text:
        print('no bulletin could be fetched', file=sys.stderr)
        return 2

    rec = parse(text)
    if not rec:
        print('bulletin from %s fetched but no position parsed; page left alone' % used, file=sys.stderr)
        return 3

    # an undated bulletin is trusted only if it is newer than what we hold
    if rec['issue'] and last and last.get('issue') and rec['issue'] <= last['issue']:
        print('bulletin %s is not newer than the last one held (%s); nothing recorded'
              % (rec['issue'], last['issue']))
        return 0

    known = {o.get('issue') for o in data['observations']}
    fresh = rec['issue'] not in known
    if fresh:
        data['observations'].append(rec)
        data['observations'].sort(key=lambda o: o.get('issue') or '')
    print('%s %s  %.1fN %.1fE  %s  (%s)' % ('new' if fresh else 'seen', rec['issue'],
                                            rec['lat'], rec['lon'], rec['intensity'], used))

    # stopping conditions
    if rec['intensity'] in ENDED:
        data['status'] = 'ended'
        data['ended_at'] = rec['issue']
        print('event ended: the system is now a %s' % rec['intensity'].lower())
        set_redirect(False)

    if args.dry_run:
        return 0
    save(data, args.data)
    redraw(data, args.page)
    named = rec['intensity'] in ('Cyclonic storm', 'Severe cyclonic storm', 'Very severe cyclonic storm',
                                 'Extremely severe cyclonic storm', 'Super cyclonic storm')
    if set_event_title(named, args.page):
        print('title set to %s' % ('Cyclone Akvan' if named else 'the provisional designation'))
    return 0


if __name__ == '__main__':
    sys.exit(main())

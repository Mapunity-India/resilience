#!/usr/bin/env python3
"""Check that every change in changelog.json is still present in the site.

Run from the site root:  python3 tools/verify_changelog.py

Each entry carries a fingerprint that can be tested mechanically. A change that
is missing means the working tree has rolled back to a snapshot older than that
change, and the entry says what to re-apply.
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = '/scratch/work/resilience-changelog-archive.json'
entries = json.load(open(ROOT + '/changelog.json', encoding='utf-8'))
files = [f for f in glob.glob(ROOT + '/**/*.html', recursive=True)]

def read(f):
    return open(f, encoding='utf-8', errors='ignore').read()

def band_total(t):
    """total thickness of the hero colour band, in px, or None"""
    m = re.search(r'\.(?:hero|header)::after\s*\{([^}]*)\}', t)
    if not m:
        return None
    body = m.group(1)
    def num(key):
        mm = re.search(key + r':\s*([0-9.]+)px', body)
        return float(mm.group(1)) if mm else 0.0
    return num('height') + num('border-top') + num('border-bottom')

def check(e):
    c = e['check']
    kind = c['type']
    if kind in ('contains', 'absent'):
        scope = c.get('paths')
        targets = [ROOT + '/' + p for p in scope] if scope else files
        hits = [f for f in targets if c['pattern'] in read(f)]
        if kind == 'contains':
            return len(hits) >= c.get('min', 1), '%d of %d files' % (len(hits), len(targets))
        return len(hits) == 0, '%d file(s) still carry it' % len(hits)
    if kind == 'regex':
        scope = c.get('paths')
        targets = [ROOT + '/' + p for p in scope] if scope else files
        hits = [f for f in targets if re.search(c['pattern'], read(f))]
        return len(hits) >= c.get('min', 1), '%d of %d files' % (len(hits), len(targets))
    if kind == 'band10':
        bad = [f for f in files if (band_total(read(f)) or 0) not in (0.0, 10.0)]
        return len(bad) <= 10, '%d file(s) off 10px' % len(bad)
    if kind == 'footers':
        city = sum(1 for f in files if 'shared-footer-city.js' in read(f))
        region = sum(1 for f in files if 'shared-footer-region.js' in read(f))
        district = sum(1 for f in files if re.search(r'src="[^"]*shared-footer\.js"', read(f)))
        ok = city >= c['minCity'] and region >= c['minRegion'] and district >= c['minDistrict']
        return ok, 'city %d, region %d, district %d' % (city, region, district)
    if kind == 'count_files':
        n = len(glob.glob(ROOT + '/' + c['glob']))
        return n >= c['min'], '%d found' % n
    return False, 'unknown check type'

ok_n = 0
sup_n = 0
rows = []
for e in entries:
    if e.get('superseded_by'):
        # deliberately replaced by a later change: not a rollback, so not a failure
        sup_n += 1
        rows.append((None, e['id'], e['change'], 'superseded by %s' % e['superseded_by']))
        continue
    try:
        ok, detail = check(e)
    except Exception as ex:
        ok, detail = False, 'error: %s' % ex
    ok_n += ok
    rows.append((ok, e['id'], e['change'], detail))

for ok, eid, change, detail in rows:
    label = 'OK' if ok else ('MOVED' if 'moved to' in str(detail) else ('SUPERSEDED' if ok is None else 'GONE'))
    print('%-11s %-22s %-66s %s' % (label, eid, change[:66], detail))
print()
moved_n = sum(1 for r in rows if r[3] and str(r[3]).startswith('moved to'))
print('%d of %d changes still in the tree, %d superseded by later changes, %d moved to another project'
      % (ok_n, len(rows) - sup_n - moved_n, sup_n, moved_n))

# The changelog lives inside the tree, so a rollback moves it back too and the
# checks above cannot see the loss. The archive sits outside the tree; anything
# in it that is absent from the tree means the tree went backwards.
rolled = []
if os.path.exists(ARCHIVE):
    arch = json.load(open(ARCHIVE, encoding='utf-8'))['entries']
    have = {e['id'] for e in entries}
    rolled = [e['id'] for e in arch if e['id'] not in have]
    print('archive  : %d entries; %d missing from the tree' % (len(arch), len(rolled)))
    for i in rolled[:12]:
        print('   ROLLED BACK  %s' % i)
else:
    print('archive  : none found, so a rollback would go unseen')

sys.exit(0 if ok_n == len(rows) - sup_n and not rolled else 1)

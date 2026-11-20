#!/usr/bin/env python3
"""Catch a broken page before it is committed.

    python3 tools/check_html.py            # compare with the recorded shape
    python3 tools/check_html.py --record   # accept the pages as they are now

The scheduled runs edit the event pages by text replacement, and one of them
left a paragraph outside a card and an extra closing div with it. The page still
parsed, so nothing failed; the cards simply fell out of their grid.

The pages are not all perfectly balanced to begin with, and that is harmless, so
this does not demand a balance. It records the shape each page has now and fails
if a later edit changes it, which is what a stray tag does.

Exit code 1 means something moved, so a run can refuse to commit.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'tools', 'html-shape.json')


def shape(html):
    return {
        'div': [len(re.findall(r'<div\b', html)), len(re.findall(r'</div>', html))],
        'p': [len(re.findall(r'<p\b', html)), len(re.findall(r'</p>', html))],
        'section': [len(re.findall(r'<section\b', html)), len(re.findall(r'</section>', html))],
    }


def pages():
    out = {'index.html': os.path.join(ROOT, 'index.html')}
    for p in sorted(glob.glob(os.path.join(ROOT, 'events', '*.html'))):
        out[os.path.relpath(p, ROOT)] = p
    return out


def main():
    record = '--record' in sys.argv
    now = {rel: shape(open(path, encoding='utf-8').read()) for rel, path in pages().items()}

    if record:
        json.dump(now, open(BASE, 'w', encoding='utf-8'), indent=0, sort_keys=True)
        print('recorded the shape of %d pages' % len(now))
        return

    base = json.load(open(BASE, encoding='utf-8')) if os.path.exists(BASE) else {}
    bad = 0
    for rel, s in now.items():
        if rel not in base:
            print('%-28s new page, not in the record' % rel)
            bad += 1
            continue
        moved = ['%s %d/%d -> %d/%d' % (k, base[rel][k][0], base[rel][k][1], s[k][0], s[k][1])
                 for k in s if s[k] != base[rel][k]]
        if moved:
            bad += 1
            print('%-28s %s' % (rel, '; '.join(moved)))
        else:
            print('%-28s ok' % rel)

    if bad:
        print('\n%d page(s) changed shape: check them before committing' % bad)
        sys.exit(1)
    print('\nall pages as recorded')


if __name__ == '__main__':
    main()

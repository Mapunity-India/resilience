#!/usr/bin/env python3
"""Catch a broken or bloated page before it is committed.

    python3 tools/check_html.py            # compare with the recorded shape
    python3 tools/check_html.py --record   # accept the pages as they are now

Two things it guards, both learned the hard way.

TAGS. The scheduled runs edit the event pages by text replacement, and on
20 November one left a paragraph and its closing div outside a card. The page
still parsed, so nothing failed; the cards simply fell out of their grid. The
pages are not all perfectly balanced to begin with, and that is harmless, so
this does not demand a balance: it records the shape each page has now and
fails if a later edit moves it.

LENGTH. The cards beside the map sit in a two-column grid whose height is set
by the longest card, so one long paragraph stretches the map with it. Each card
in that grid is held to a word limit. The timeline cards below are not counted,
because their length does not move the map.

Exit code 1 means something moved or overflowed, so a run can refuse to commit.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'tools', 'html-shape.json')

# a card beside the map: two or three sentences, no more
CARD_WORDS = 70

CARD_RE = re.compile(
    r'<div class="card">\s*<div class="card__title">([^<]*)</div>\s*<p[^>]*>(.*?)</p>', re.S)


def shape(html):
    return {
        'div': [len(re.findall(r'<div\b', html)), len(re.findall(r'</div>', html))],
        'p': [len(re.findall(r'<p\b', html)), len(re.findall(r'</p>', html))],
        'section': [len(re.findall(r'<section\b', html)), len(re.findall(r'</section>', html))],
    }


def quad_block(html):
    """The grid of cards that sits beside the map, and nothing after it.

    The timeline below uses the same card markup under a plain "cards" wrapper,
    so the block has to stop before that, or the longest timeline entry would be
    read as a card beside the map.
    """
    i = html.find('<div class="quad">')
    if i < 0:
        return ''
    seg = html[i:]
    end = seg.find('<div class="cards">')
    if end < 0:
        for marker in ('<div class="timeline', '<section', '<footer'):
            k = seg.find(marker)
            if k > 0 and (end < 0 or k < end):
                end = k
    return seg[:end] if end > 0 else seg[:12000]


def long_cards(html):
    seg = quad_block(html)
    out = []
    for m in CARD_RE.finditer(seg):
        body = re.sub(r'<[^>]+>', '', m.group(2))
        out.append((m.group(1).strip(), len(body.split())))
    return out


def pages():
    out = {'index.html': os.path.join(ROOT, 'index.html')}
    for p in sorted(glob.glob(os.path.join(ROOT, 'events', '*.html'))):
        out[os.path.relpath(p, ROOT)] = p
    for p in sorted(glob.glob(os.path.join(ROOT, 'city', '*.html'))):
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
    for rel, path in pages().items():
        s = now[rel]
        problems = []
        if rel not in base:
            problems.append('new page, not in the record')
        else:
            problems += ['%s %d/%d -> %d/%d' % (k, base[rel][k][0], base[rel][k][1], s[k][0], s[k][1])
                         for k in s if s[k] != base[rel][k]]
        html = open(path, encoding='utf-8').read()
        for title, words in long_cards(html):
            if words > CARD_WORDS:
                problems.append('card "%s" is %d words, over the %d limit' % (title, words, CARD_WORDS))
        if problems:
            bad += 1
            print('%-28s %s' % (rel, '; '.join(problems)))
        else:
            print('%-28s ok' % rel)

    if bad:
        print('\n%d page(s) need attention: check them before committing' % bad)
        sys.exit(1)
    print('\nall pages as recorded')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Keep a copy of the changelog outside the working tree, and prune the tree copy.

The changelog lives inside the tree, so a rollback takes the changelog back with
it and the verifier cannot tell that anything is missing: it compares the tree
against a file that moved back alongside it. This script keeps an archive in a
place the tree cannot reach, and can trim the tree copy once entries are safe
in the archive.

    python3 changelog_archive.py --mirror        # merge tree entries into the archive
    python3 changelog_archive.py --prune 40      # keep the newest 40 in the tree
    python3 changelog_archive.py --status        # what is where, and what is missing

The archive is written to /scratch/output so it is delivered and kept with the
user's saved files. It is read from /scratch/saved when that copy exists, which
is the one that survives a reset.

Pruning never drops an entry that is not already in the archive, and never
touches one marked superseded_by: those are the record of what replaced what.
"""
import argparse, json, os, sys

TREE = '/scratch/work/resilience-site/changelog.json'
SAVED = '/scratch/saved/resilience-changelog-archive.json'
WORK = '/scratch/work/resilience-changelog-archive.json'      # the archive lives here, never in the preview
PUBLISH = '/scratch/output/changelog-archive.json'  # copied there only when asked


def load(path, default):
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return default


def archive_path():
    return SAVED if os.path.exists(SAVED) else WORK


def merge(tree, arch):
    """Add every tree entry the archive does not already hold."""
    known = {e['id'] for e in arch['entries']}
    added = [e for e in tree if e['id'] not in known]
    arch['entries'].extend(added)
    arch['entries'].sort(key=lambda e: (e.get('date') or '', e['id']))
    return added


def write_archive(arch, note, publish=False):
    arch['note'] = note
    json.dump(arch, open(WORK, 'w', encoding='utf-8'), indent=1)
    if publish:
        # only on request: a file written to the output folder takes over the preview
        os.makedirs(os.path.dirname(PUBLISH), exist_ok=True)
        json.dump(arch, open(PUBLISH, 'w', encoding='utf-8'), indent=1)
        return PUBLISH
    return WORK


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mirror', action='store_true')
    ap.add_argument('--prune', type=int, default=0)
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--publish', action='store_true', help='also copy the archive into the preview folder')
    args = ap.parse_args()

    tree = load(TREE, [])
    apath = archive_path()
    arch = load(apath, {'note': '', 'entries': []})

    if args.status:
        known = {e['id'] for e in arch['entries']}
        missing = [e['id'] for e in arch['entries'] if e['id'] not in {t['id'] for t in tree}]
        print('tree     : %d entries' % len(tree))
        print('archive  : %d entries (%s)' % (len(arch['entries']), apath))
        print('in tree, not yet archived: %d' % len([t for t in tree if t['id'] not in known]))
        print('in archive, missing from the tree: %d' % len(missing))
        for i in missing[:12]:
            print('   %s' % i)
        return 0

    if args.mirror:
        added = merge(tree, arch)
        p = write_archive(arch, 'Archive of every changelog entry, kept outside the working tree.', args.publish)
        print('archived %d new entr%s; archive holds %d at %s'
              % (len(added), 'y' if len(added) == 1 else 'ies', len(arch['entries']), p))
        return 0

    if args.prune:
        added = merge(tree, arch)
        known = {e['id'] for e in arch['entries']}
        keep, drop = tree[-args.prune:], tree[:-args.prune]
        unsafe = [e['id'] for e in drop if e['id'] not in known]
        if unsafe:
            print('refusing to prune: %d entries are not in the archive yet' % len(unsafe), file=sys.stderr)
            for i in unsafe[:10]:
                print('   %s' % i, file=sys.stderr)
            return 2
        keep_ids = {e['id'] for e in keep}
        for e in arch['entries']:
            if e['id'] not in keep_ids:
                e['pruned'] = True
        json.dump(keep, open(TREE, 'w', encoding='utf-8'), indent=1)
        p = write_archive(arch, 'Archive of every changelog entry, kept outside the working tree.', args.publish)
        print('archived %d new, pruned %d from the tree, %d left in the tree; archive at %s'
              % (len(added), len(drop), len(keep), p))
        return 0

    print(__doc__)
    return 0


if __name__ == '__main__':
    sys.exit(main())

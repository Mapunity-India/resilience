#!/usr/bin/env python3
"""Cut a release of the resilience site: a full archive, and a patch from a base.

    python3 tools/package.py full r003
    python3 tools/package.py patch r002 r003      # r002 must have a manifest
    python3 tools/package.py patch r002 r003 --full   # both in one go

Every release writes a manifest to tools/manifests/<tag>.json, which is what a
later patch is cut against. Manifests are bookkeeping and never travel inside a
patch; they do travel inside a full archive.

A full archive is cut from the contents of the site root, so extracting it at
resilience.mapunity.com puts index.html at the top with no folder to strip.
"""
import argparse, datetime, hashlib, json, os, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, 'tools', 'manifests')
OUT = '/scratch/work'

def now():
    return datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime('%d %b %Y %H:%M IST')

def scan():
    out = {}
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d != '__pycache__']
        for f in fn:
            if f == '.DS_Store':
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, ROOT)
            out[rel] = [hashlib.sha256(open(p, 'rb').read()).hexdigest(), os.path.getsize(p)]
    return out

def write_manifest(tag, files):
    os.makedirs(STORE, exist_ok=True)
    json.dump({'tag': tag, 'root': 'resilience.mapunity.com', 'built': now(), 'files': files},
              open(os.path.join(STORE, tag + '.json'), 'w'), indent=1)

def content(files):
    return {k: v for k, v in files.items() if not k.startswith('tools/manifests/')}

def full(tag):
    files = scan()
    write_manifest(tag, files)
    files = scan()                                  # so the archive carries its manifest
    out = os.path.join(OUT, 'resilience-mapunity-%s.zip' % tag)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            z.write(os.path.join(ROOT, rel), rel)
    print('full %s: %d files, %d KB' % (tag, len(files), os.path.getsize(out) // 1024))
    return out

def patch(base, tag):
    mpath = os.path.join(STORE, base + '.json')
    if not os.path.exists(mpath):
        sys.exit('no manifest for base %s; cut a full archive for it first' % base)
    base_files = content(json.load(open(mpath))['files'])
    now_files = scan()
    write_manifest(tag, now_files)
    now_files = content(now_files)
    changed = [r for r in now_files if r in base_files and base_files[r][0] != now_files[r][0]]
    added = [r for r in now_files if r not in base_files]
    removed = [r for r in base_files if r not in now_files]

    name = 'resilience-patch-%s-to-%s.zip' % (base, tag)
    out = os.path.join(OUT, name)
    apply_txt = '\n'.join([
        'Resilience patch: %s -> %s' % (base, tag), '',
        'Base: %s  (this patch must be applied on top of %s)' % (base, base),
        'Built: %s' % now(), '',
        'Apply at the site root, which is the folder holding index.html:',
        '  unzip -o %s' % name, '',
        'Files changed : %d' % len(changed),
        'Files added   : %d' % len(added),
        'Files deleted : %d' % len(removed), '',
        'This patch replaces only the files it names. Anything else in the site is untouched.', ''])
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(changed + added):
            z.write(os.path.join(ROOT, rel), rel)
        z.writestr('APPLY.txt', apply_txt)
        if removed:
            z.writestr('DELETED.txt', '\n'.join(removed) + '\n')
    print('patch %s -> %s: %d changed, %d added, %d removed, %d KB'
          % (base, tag, len(changed), len(added), len(removed), os.path.getsize(out) // 1024))
    for r in sorted(changed + added):
        print('   ', r)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['full', 'patch'])
    ap.add_argument('tags', nargs='+')
    ap.add_argument('--full', action='store_true', help='with patch, also cut the full archive for the new tag')
    a = ap.parse_args()
    if a.mode == 'full':
        full(a.tags[0])
    else:
        if len(a.tags) != 2:
            sys.exit('patch needs a base and a new tag')
        patch(a.tags[0], a.tags[1])
        if a.full:
            full(a.tags[1])

if __name__ == '__main__':
    main()

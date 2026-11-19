#!/usr/bin/env python3
"""Fetch the current INSAT frame from IMD, crop it to the Bay, and put it on the page.

    python3 tools/fetch_image.py                    # fetch, crop, save, update the page
    python3 tools/fetch_image.py --keep landfall    # also keep a permanent copy for the record
    python3 tools/fetch_image.py --dry-run          # report what it would do

IMD overwrites https://mausam.imd.gov.in/Satellite/3Dasiasec_ir1.jpg every half
hour. We fetch it once per run, crop the Bay of Bengal out of the full Asia
sector, and serve our own copy: one request to IMD per run, rather than one per
visitor.

The caption records when we fetched it. It does not claim a scan window, because
the window is printed inside IMD's header band, which we crop away and cannot
verify.
"""
import io, json, os, sys, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SATELLITE = os.path.join(ROOT, 'data', 'satellite')
PAGE = os.path.join(ROOT, 'events', 'akvan.html')
SOURCE = 'https://mausam.imd.gov.in/Satellite/3Dasiasec_ir1.jpg'

# the Bay of Bengal window inside IMD's 2002x2242 Asia sector
CROP = (980, 1020, 1660, 1610)
SIZE = (900, 780)

def ist():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))


def strip_station_codes(im):
    """IMD stamps regional station codes across its satellite frames in orange.
    They sit on land, away from the storm, and they date the product in a way that
    has nothing to do with the weather, so they come off. The fill is a local
    median from the surrounding pixels, which holds the land tone underneath."""
    import numpy as np
    a = np.array(im.convert('RGB')).astype(np.int16)
    def mask_of(x):
        R,G,B = x[:,:,0].astype(int), x[:,:,1].astype(int), x[:,:,2].astype(int)
        return ((R-B)>45)&((R-G)>18)&(R>105)&(G<185)&(B<130)
    def grow(m,n=2):
        for _ in range(n):
            g=m.copy(); g[1:,:]|=m[:-1,:]; g[:-1,:]|=m[1:,:]
            g[:,1:]|=m[:,:-1]; g[:,:-1]|=m[:,1:]; m=g
        return m
    def fill(x,m,rad=7):
        out=x.copy(); h,w=m.shape
        for y,xx in zip(*np.where(m)):
            y0,y1=max(0,y-rad),min(h,y+rad+1); x0,x1=max(0,xx-rad),min(w,xx+rad+1)
            patch=x[y0:y1,x0:x1]; pm=m[y0:y1,x0:x1]; vals=patch[~pm]
            if len(vals)>=10: out[y,xx]=np.median(vals,axis=0)
        return out
    for _ in range(3):
        m = grow(mask_of(a),2)
        if not m.any(): break
        a = fill(a,m)
    from PIL import Image as _I
    return _I.fromarray(np.clip(a,0,255).astype(np.uint8))



def orange_left(im):
    """Count pixels that still look like IMD's station codes, so a frame can be
    checked after the strip rather than assumed clean."""
    import numpy as np
    a = np.array(im.convert('RGB')).astype(int)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return int((((R - B) > 45) & ((R - G) > 18) & (R > 105) & (G < 185) & (B < 130)).sum())


def main():
    dry = '--dry-run' in sys.argv
    stamp = ist()
    try:
        req = urllib.request.Request(SOURCE, headers={'User-Agent': 'resilience-poller/1.0'})
        raw = urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        print('fetch failed, page left alone: %s' % e); return 1
    try:
        from PIL import Image
    except ImportError:
        print('Pillow missing, page left alone'); return 1
    im = Image.open(io.BytesIO(raw)).convert('RGB')
    if im.size != (2002, 2242):
        print('unexpected image size %s, page left alone' % (im.size,)); return 1
    out = os.path.join(SATELLITE, 'bay-%s-insat-ir.jpg' % stamp.strftime('%Y-%m-%d'))
    if dry:
        print('would write %s from %d bytes' % (out, len(raw))); return 0
    frame = strip_station_codes(im.crop(CROP).resize(SIZE, Image.LANCZOS))
    frame.save(out, quality=88, optimize=True)
    left = orange_left(Image.open(out))
    if left:
        frame = strip_station_codes(Image.open(out))
        frame.save(out, quality=88, optimize=True)
        left = orange_left(Image.open(out))
    print('station codes left in the frame: %d' % left)
    keep = None
    if '--keep' in sys.argv:
        label = sys.argv[sys.argv.index('--keep') + 1]
        keep = os.path.join(SATELLITE, 'akvan-%s-%s.jpg' % (label, stamp.strftime('%Y-%m-%d')))
        frame.save(keep, quality=90, optimize=True)
    meta = {'file': os.path.basename(out), 'fetched_ist': stamp.strftime('%Y-%m-%dT%H:%M:%S+05:30'),
            'fetched_label': stamp.strftime('%H:%M IST on %-d %B %Y'), 'source': SOURCE}
    if keep:
        meta['kept'] = os.path.basename(keep)
    json.dump(meta, open(os.path.join(SATELLITE, 'latest.json'), 'w'), indent=1)
    # point the page at it and restate the caption
    t = open(PAGE, encoding='utf-8').read()
    import re
    stamp_q = stamp.strftime('%Y%m%d%H%M')
    t = re.sub(r'src="\.\./data/satellite/bay-[^"]+-insat-ir\.jpg(\?v=[0-9]+)?"',
               'src="../data/satellite/%s?v=%s"' % (meta['file'], stamp_q), t, count=1)
    # keep the time on the Satellite tab current as well
    t = re.sub(r'(value="sat"><span>Satellite) <b class="vsat__t">[0-9:]*</b>',
               r'\1 <b class="vsat__t">%s</b>' % stamp.strftime('%H:%M'), t, count=1)
    t = re.sub(r"var S='INSAT-3DS[^']*';",
               "var S='INSAT-3DS, the latest frame, fetched at %s. The white mass over the south-west Bay is the storm. Image: IMD.';" % meta['fetched_label'], t, count=1)
    open(PAGE, 'w', encoding='utf-8').write(t)
    print('wrote %s (%d KB), fetched %s' % (meta['file'], os.path.getsize(out)//1024, meta['fetched_label']))
    if keep:
        print('kept a copy for the record: %s' % os.path.basename(keep))
    return 0

if __name__ == '__main__':
    sys.exit(main())

# Resilience: handoff to its own working thread

This note carries everything a fresh conversation needs to pick up the Resilience
work without the District Mocha history in the way. Read it first, then work from
the repository, not from memory.

## What this is

Resilience is a site at **resilience.mapunity.com** that puts climate exposure on a
map for India, and doubles as a live tracker when a storm is running. It is a
separate project from District Mocha and City Latte, with its own repository, its
own changelog and its own releases. The only thread between them is the Public AI
page, which carries a card linking here.

## Where everything lives

    repository   github.com/Mapunity-India/resilience   (branch main, public)
    live site    resilience.mapunity.com
    site root    index.html, events/, data/, logos/, tools/, changelog.json

The page set: an index with the country map and the event list, and event pages
under `events/` for Akvan, Murasu, Arnab and El Nino. A new storm gets a new page
under `events/` and a row on the index.

## How work is done here

Every change is logged. `changelog.json` holds one entry per change with a
fingerprint test, and `tools/verify_changelog.py` proves the tree still contains
what the log claims. Run it before every commit; a change with no entry is a
change that will be lost without trace at the next sandbox reset.

Every commit goes to main. Releases are cut deliberately, not on every commit:
`tools/package.py` makes a full archive and a patch from a named base, and the
manifests under `tools/manifests` record what each release contained. The current
line is r005; the next is r006.

Two checks before committing anything that touches a page:

    python3 tools/check_html.py      # page shape unchanged, cards not bloated
    python3 tools/verify_changelog.py

## Rules that came from mistakes, not from theory

- **Never invent a coordinate.** A position is recorded only when the bulletin
  states a latitude and longitude. Distances from a port are not a position, and
  a forecast table is not a position. Where a place name is all there is, derive
  the coordinate from the named place and say so in the entry.
- **A scheduled run always commits something**, including a run-log line. Silence
  is indistinguishable from failure.
- **The map draws from the record.** Nothing about a storm's position or forecast
  is hard-coded in the page. The corridor lives in `data/observations.json` as a
  list of points along the coast, and both the build and the runtime redraw read
  it from there. A constant in the drawing code is a bug waiting for the forecast
  to move.
- **Name a storm by its peak, describe it by its current state.** IMD titles its
  reports by the highest category reached, even when the storm weakened before
  the coast: the Vardah report is a very severe cyclonic storm although it
  crossed as a severe one. Live pages carry the current descriptor; a retired
  page takes the peak. `tools/retire_event.py` does that switch.
- **Cards beside the map stay short.** The grid takes its height from the tallest
  card, so one long paragraph stretches the map. The four cards in that grid are
  held to 70 words by `check_html.py`; the timeline cards below are not counted.
- **LIVE is a claim, not decoration.** When an event is over, the marker comes off
  and the row reads as a date range. Murasu and Arnab show what a retired row
  looks like.

## The tools, and what each is for

    tools/fetch_image.py     IMD INSAT frame, cropped to the Bay, station codes and
                             markers stripped; --keep landfall saves a permanent copy
    tools/fetch_position.py  the observation record and the marker drawing
    tools/export_track.py    the track as CSV
    tools/set_event.py       the storm's descriptor, and with it the title
    tools/postevent.py       the record of what the storm did after it crossed:
                             deaths, shelters, crop, rainfall, appended with sources
    tools/add_landfall.py    one more dot on the index map's landfall layer
    tools/retire_event.py    close a live event: peak name, LIVE off, row as a range
    tools/check_html.py      page shape and card length
    tools/verify_changelog.py
    tools/package.py         full archive, patch, and a check

## Where Akvan stands

It crossed the south Odisha and north Andhra coast close to Gopalpur between
07:30 and 08:30 on 20 November 2026 as a cyclonic storm with 70 to 80 kmph
gusting 90, having weakened from severe the night before. It is in the
observation record, on the landfall layer at 19.2N 84.8E, and in the post-event
record. A three-hourly job runs until noon on 22 November, when its last run
retires the event: the page becomes Severe Cyclonic Storm Akvan, the LIVE marker
comes off the index row, and the job deletes itself.

The page keeps its live content after retirement, frozen at what it held when the
storm crossed. Deaths, shelters and crop loss are deliberately not on it yet;
they arrive over weeks, and `postevent.py` is where they go when they do.

## Open questions

- **Netlify.** Pushes reach GitHub reliably, but the published site has at times
  served an older build while the record beside it was current. A `_headers` file
  now sets the HTML and JSON to revalidate. If a change is on main but not on the
  site, check the deploy list before assuming the code is wrong.
- **Heat** needs a data.gov.in key, and there is no machine-readable national
  district classification for landslide, which is why landslides came off the map.
- **The Places card** and the standing link from the Public AI page are still
  undecided.

## House style

No em-dashes in prose written for Ashwin; en-dashes inside the site are fine.
Numbers in Indian conventions: lakh and crore, metric, IST, dates as dd/mm/yyyy in
prose. Do not add a footer where the file has none. When asked for a file, put it
in the preview panel and match the browser tab to its title.

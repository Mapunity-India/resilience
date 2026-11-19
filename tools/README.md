# Poller for the Akvan event page

`fetch_position.py` reads the cyclone bulletin, records the observed position,
and redraws the marker, the past dots and the observed track in
`resilience.html`. Standard library only, no state outside this folder.

## Running it by hand

```bash
python3 fetch_position.py --status       # what it holds, and how old
python3 fetch_position.py                # fetch if the interval has passed
python3 fetch_position.py --force        # fetch now regardless
python3 fetch_position.py --dry-run      # parse and report, write nothing
python3 fetch_position.py --fixture f.txt  # parse a saved bulletin
```

Exit codes: `0` fine or not due, `2` nothing fetchable, `3` fetched but not
parseable, `4` event ended, `5` bad path.

## On a server

Cron, every ten minutes, letting the script decide whether it is due. It only
fetches once the last observation is 90 minutes old, so the interval lives in
one place rather than in the schedule.

```cron
*/10 * * * * cd /srv/resilience/tools && /usr/bin/python3 fetch_position.py >> /var/log/resilience-poller.log 2>&1
```

Systemd, if you would rather have the journal:

```ini
# /etc/systemd/system/resilience-poller.service
[Unit]
Description=Resilience cyclone position poller

[Service]
Type=oneshot
WorkingDirectory=/srv/resilience/tools
ExecStart=/usr/bin/python3 fetch_position.py
```

```ini
# /etc/systemd/system/resilience-poller.timer
[Unit]
Description=Run the resilience poller every ten minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
```

```bash
systemctl enable --now resilience-poller.timer
journalctl -u resilience-poller -f
```

## What it will not do

It will not guess. If the bulletin cannot be fetched, or the position cannot be
parsed, it exits non-zero and leaves the page as it was, so the page shows the
last good position and its time rather than something invented.

It will not record the same bulletin twice. Observations are keyed on the
bulletin's own issue time, not on when the run happened, so a schedule that
fires every ten minutes still produces one dot per bulletin.

It will not run past the event. When the bulletin calls the system a low
pressure area or a remnant, or nothing new arrives for `--stale-hours` (12 by
default), it sets `status: ended` and every later run exits 4. The page then
holds its last state. Remove `data/observations.json`, or pass `--force`, to
reopen.

## Files

- `data/observations.json`: the record. One entry per bulletin, with the
  position, the issue time, the intensity and the time it was fetched.
- `../resilience.html`: the page. The marker block sits between
  `<!-- akvan:start -->` and `<!-- akvan:end -->` and is regenerated whole on
  each run, so the page never accumulates stale fragments.

## Before a new season

Point `SOURCES` at the season's bulletin URLs, change `event` in
`data/observations.json`, and update the bounding box in `SANITY` if the basin
is not the Bay of Bengal. The forecast anchor `(fx, fy)` in `redraw()` is the
only hard-coded geography and should be moved to the new landfall area.

## Publishing

The page is static and stays static. What makes it live is one small file:

- `resilience/events/akvan.html` is the page
- `resilience/data/observations.json` is the record the poller writes

Upload both, keeping that structure, and the page will check the record on load
and every ten minutes. When the record carries a newer bulletin than the page
was built with, the marker, the dots, the track, the label and the Position card
redraw themselves in the browser. If the fetch fails, the page keeps the
position it was published with, so a dead network never shows a blank map.

The poller writes to `resilience/data/observations.json` for that reason. Nothing
else needs to be regenerated when a bulletin lands.

## Keeping every fix

The record in `data/observations.json` is the source of truth, and the page is
only a drawing of it. Two rules keep the track whole once the storm is over:

1. **Append, never overwrite.** Each poll adds one entry per bulletin it can
   verify. Nothing is deleted, and a fix is never replaced by a later one.
2. **Export at every run.** `python3 tools/export_track.py` writes
   `data/<event>-track.csv` from the record and reports any gap longer than
   four hours. Run it after every poll and once more when the event closes.

Why this matters: the tracks on the Arnab and Murasu pages carry six and eleven
fixes, because they were drawn by hand from the bulletins that were quoted in
the press, not from a running record. A three-hourly storm over five days has
thirty to forty fixes. Akvan's record starts on 15 November and every one of
them is kept.

IMD's post-event report carries the full track table for each storm. When those
reports are published for Arnab and Murasu, their records can be rebuilt from
the table rather than from news reports, and their pages redrawn.

## When a system is named or reclassified

IMD confers a name when a depression becomes a cyclonic storm, and then changes
the descriptor as the storm strengthens: cyclonic, severe cyclonic, very severe
cyclonic, extremely severe. The name stays; the words in front of it change.
Each of those is one fact living in three places, so all three change together
or the suite contradicts itself:

1. **The event page** title, `resilience/events/<event>.html`, from the
   designation to the name. Keep the standfirst as it is.
2. **The index page**, `resilience/index.html`, where the live row in the EVENTS
   card names the event and links to the page. This is the one that gets
   forgotten, because it is a different file from the one being edited. It
   carries the full descriptor, so it reads "Severe Cyclonic Storm Akvan" once
   IMD says so, not "Cyclone Akvan".
3. **The record**, `data/observations.json`: the `named` block for the name, and
   the `intensity` of each fix for the descriptor, which changes bulletin by
   bulletin.

A live row is dated "since <day>", not with a closed range, until the event ends.

## After landfall

Landfall is the moment the centre crosses, not the end of the storm. Half the
system is still at sea, the rear eyewall has not come ashore, and the heaviest
rain and the highest water often arrive after the crossing. So:

- The page stays live until the rear of the system has cleared the coast or the
  storm has weakened inland. Log that moment separately:
  `python3 tools/postevent.py --cleared "<ISO time>" --where "<where the rear was>"`.
- Keep satellite frames at three points, not one: at landfall, about six hours
  later as the rear bands come ashore, and at clearance.
  `python3 tools/fetch_image.py --keep landfall`, then `--keep landfall-after`,
  then `--keep cleared`.
- Figures gathered before clearance are recorded with `phase: provisional`. They
  will move, and often upward. Once clearance is logged, later entries are
  `settled`.

The live page answers "where is it". Once the storm crosses, the questions change:
how many died, how many were in shelters, what crop was lost, how much rain fell,
when the power came back. Those arrive over days, from many sources, and are
worth keeping for the record.

    python3 tools/postevent.py --landfall "2026-11-20T11:30+05:30" --where "between Nellore and Tuni"
    python3 tools/postevent.py --add deaths --value 12 --source "State relief commissioner, 21 Nov" --note "all in Nellore district"
    python3 tools/postevent.py --show

Entries are appended with their source and the time they were found, never
overwritten, in `data/<event>-postevent.json`.

**Keep the picture.** A satellite frame near landfall is the one image that
cannot be fetched again later, because IMD overwrites its own. At landfall, and
again a few hours either side, keep a permanent copy:

    python3 tools/fetch_image.py --keep landfall

That writes `data/satellite/akvan-landfall-<date>.jpg` beside the working frame
and names it in `latest.json`.

## Labelling a track map

The label layout follows the shape of the track, not a fixed rule.

A **north-south** track, like Akvan's, leaves the sea clear on either side, so
labels sit beside their points and the landfall label goes to the right of it.

An **east-west** track, like Arnab's, has no room beside the line: a label placed
to the left or right of a point runs along the track and collides with the dots.
Put those labels above and below the line in turn, and keep the landfall label
and its place name on the side away from the busiest stretch of track.

Keep the place line short: "near Yanam", not the crossing window, which belongs
in the landfall card. Months are mixed case, Oct rather than OCT.

Font sizes are set in the drawing, so a map with a narrower viewBox renders the
same number larger on the page. Scale the label type by the ratio of the two
viewBox widths when you copy a layout between events.

## Scheduled updates

While a storm is live the page can be kept current by a scheduled run of this
agent, hourly, which fetches the frame, appends any new fix and redraws.

Two things to know before switching it on. Every run opens a new chat session
named after the job, so a long event leaves a trail of them in the account, and
the run has to be pointed at this site root, not at a folder inside another
project, or it will find nothing to update.

The jobs created for Akvan were deleted on 18 November 2026, partly because they
still pointed at the old location inside the District Mocha suite. If they are
wanted again, create them against `resilience-site` and expect a session per run.

## The repository

The site lives in `Mapunity-India/resilience` on GitHub, at the root of the
`main` branch, so `index.html` sits at the top of the repository and a hosting
service can serve it with no build step and no folder to configure.

Each release is a commit on `main` plus a tag named for it: `r004`, `r005` and
so on. The tag and the zip carry the same name, so a release can be fetched
either way, and the history makes it possible to see what changed between two
releases and to go back to any of them.

    python3 tools/package.py full r005            # the archive and its manifest
    git add -A && git commit -m "Release r005"
    git tag r005 && git push origin main --tags

The manifest in `tools/manifests` is committed with the release, which is what
lets the next patch be cut against this one.

## What a scheduled run must leave behind

A run that finds no new bulletin must still write something: update
`last_checked` and its note in `data/observations.json`, commit that, and push.
Silence is not an acceptable outcome, because a run that leaves no trace is
indistinguishable from a run that never happened, which is exactly the doubt
the 19:30 and 20:30 runs on 18 November created.

Two further rules, learned the same evening. A position is recorded only when a
bulletin states the latitude and longitude: distances from a port are not a
position, and neither is a forecast position read off a track table. And the
commit message names the fix it added, or says plainly that none was added.

Every scheduled run appends one line to `tools/run-log.jsonl` and commits it,
whether or not it found anything. The file is the answer to "did the run happen
and what did it decide", which the chat sessions cannot give us at a glance and
the record alone cannot distinguish.

## Keeping the frame at landfall

The landfall frame is the one image that cannot be fetched again: IMD
overwrites its own product every half hour. When a bulletin reports the centre
crossing the coast, keep a permanent copy at once:

    python3 tools/fetch_image.py --keep landfall
    python3 tools/fetch_image.py --keep cleared     # as the rear clears

The Murasu and Arnab pages carry no such image, and cannot now, because no copy
was kept at the time. Every live event from here should end with one.

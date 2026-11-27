#!/usr/bin/env python3
"""Build cities.html from data/city/*.json.

One JSON file per city, one page that renders any number of them. With a single
city the page opens straight into it; with several it opens a chooser.
"""
import json, pathlib, sys, datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'city'
OUT  = ROOT / 'cities.html'

TEMPLATE = r"""<!DOCTYPE html>
<!-- cities | built __BUILT__ -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cities &mdash; Resilience</title>
<link rel="icon" type="image/png" href="logos/resilience-icon.png">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f0d0b;--muted:#2b2721;--accent:#772a0c;--line:rgba(32,88,0,.26);--warm:#faf9f7;
 --display:'Instrument Serif',Georgia,serif;--body:'DM Sans',system-ui,sans-serif;--mono:'JetBrains Mono',monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--warm);color:var(--ink);font-family:var(--body);line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1190px;margin:0 auto;padding:0 24px}
.header{position:relative;display:flex;align-items:flex-end;justify-content:space-between;gap:28px;padding:11px 0 21px;margin:0 0 26px}
.header::after{content:'';position:absolute;left:-24px;right:-24px;bottom:0;height:2px;
 border-top:4px solid #205800;border-bottom:4px solid #60a000;background:transparent}
.header__eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:2.5px;text-transform:uppercase;font-weight:700;margin:0 0 6px}
.header__title{font-family:var(--display);font-size:40px;font-weight:400;margin:2px 0;color:var(--accent);line-height:1.15}
.header__sub{font-size:16px;margin:0;max-width:62ch}
.header__logo{height:125px;width:auto;flex-shrink:0;margin-right:-10px;position:relative;top:10px}
.facts{display:flex;gap:30px;flex-wrap:wrap;margin:0 0 4px}
.fact{font-size:13px;color:var(--muted)}
.fact b{display:block;font-family:var(--display);font-size:24px;color:var(--ink);font-weight:400;line-height:1.2}
h2{font-family:var(--mono);font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);
 margin:32px 0 12px;display:flex;align-items:center;gap:10px}
h2::before{content:'';width:8px;height:8px;border-radius:50%;background:currentColor;flex-shrink:0}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top;font-size:13.5px}
th{font-family:var(--mono);font-size:9.5px;letter-spacing:1.3px;text-transform:uppercase;color:var(--muted);background:#f7f5f1;font-weight:600}
tr:last-child td{border-bottom:none}
td.h{font-weight:600;white-space:nowrap}
.src{font-family:var(--mono);font-size:9.5px;letter-spacing:.6px;color:var(--muted);text-transform:uppercase}
.note{font-size:13px;color:var(--muted);margin:10px 0 0}
.top{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:16px;align-items:start}
.mapcard{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px 12px}
.stack{display:grid;gap:12px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px 15px}
.card__t{font-family:var(--mono);font-size:9.5px;letter-spacing:1.4px;text-transform:uppercase;color:var(--muted);margin:0 0 7px}
.card__big{font-family:var(--display);font-size:26px;line-height:1.15;margin:0 0 3px}
.card p{margin:0;font-size:12.5px;color:var(--muted);line-height:1.45}
.card .row{padding:6px 0;border-bottom:1px solid #efe9df}
.card .row:last-child{border-bottom:none}
.card .row .k{display:flex;justify-content:space-between;gap:12px;align-items:baseline;font-size:13px}
.card .row .k b{font-family:var(--mono);font-size:11px;letter-spacing:.5px;white-space:nowrap}
.card .row .n{display:block;font-size:11.5px;color:var(--muted);margin-top:1px}
.ev{padding:8px 0;border-bottom:1px solid #efe9df}
.ev:last-child{border-bottom:none}
.ev__h{display:flex;align-items:baseline;gap:8px}
.ev__t{font-size:13.5px;font-weight:600;flex:1}
.ev__live{font-family:var(--mono);font-size:8px;letter-spacing:1.2px;text-transform:uppercase;
 background:#8f2318;color:#fff;padding:2px 5px;border-radius:3px;font-weight:700}
.ev__d{display:block;font-family:var(--mono);font-size:9.5px;letter-spacing:.8px;color:var(--muted);
 text-transform:uppercase;margin:2px 0 3px}
.ev__n{display:block;font-size:12px;color:var(--muted);line-height:1.4}
.ev__sep{font-family:var(--mono);font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
 color:var(--muted);opacity:.75;padding:10px 0 2px;border-top:1px solid #efe9df;margin-top:6px}
@media (max-width:900px){.top{grid-template-columns:1fr}}
.mapcard svg{width:100%;max-width:720px;height:auto;display:block;margin:0 auto}
.maplabel{display:flex;align-items:center;gap:8px;margin:-14px -16px 12px;padding:10px 16px;
 background:#f2eee6;border-bottom:1px solid var(--line);border-radius:12px 12px 0 0}
.maplabel span{font-size:11.5px;letter-spacing:.7px;text-transform:uppercase;font-weight:600;
 color:var(--ink);padding-bottom:3px}
.maplabel em{font-family:var(--mono);font-style:normal;font-size:10px;letter-spacing:1px;
 text-transform:uppercase;color:var(--muted);margin-left:auto}
.mapcard .cap{font-size:12.5px;color:var(--muted);margin:8px 0 0}
.measured{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.measured div{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.measured b{display:block;font-family:var(--display);font-size:22px;font-weight:400;margin-bottom:2px}
.measured span{font-size:12.5px;color:var(--muted)}
.pick{display:grid;gap:10px;margin:10px 0 0}
.pick a{display:block;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;
 text-decoration:none;color:var(--ink)}
.pick a:hover{border-color:#205800}
.pick b{font-family:var(--display);font-size:22px;font-weight:400;display:block}
.pick span{font-size:12.5px;color:var(--muted)}
footer{margin:38px 0 40px;padding-top:16px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
@media (max-width:820px){.measured{grid-template-columns:1fr}th,td{padding:9px 10px;font-size:12.5px}}
</style>
</head>
<body>
<div class="wrap">
  <header class="header">
    <div>
      <div class="header__eyebrow">Resilience</div>
      <h1 class="header__title">City resilience</h1>
      <p class="header__sub">What starts a response, who acts, and where.</p>
    </div>
    <a href="index.html" aria-label="Resilience home"><img class="header__logo" src="logos/resilience-mark.png" alt="Resilience"></a>
  </header>

  <div id="view"></div>

  <footer>
    One JSON file per city in <b>data/city/</b>; <b>tools/build_city.py</b> renders this page from them.
    Thresholds are national scales, owners are municipal roles, and the geography is measured per city.
  </footer>
</div>

<script>
var CITIES = __DATA__;
var current = 0;
function esc(s){ return String(s).replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }

function cityPage(c){
  var rows = c.hazards.map(function(h){
    return '<tr><td class="h">' + esc(h.hazard) + '</td>' +
      '<td>' + esc(h.trigger) + '<div class="src">' + esc(h.scale) + '</div></td>' +
      '<td>' + esc(h.starts) + '</td>' +
      '<td>' + esc(h.owner) + '<div class="src">' + esc(h.window) + '</div></td>' +
      '<td>' + esc(h.where) + '</td></tr>';
  }).join('');
  var assets = c.assets.map(function(a){
    return '<tr><td class="h">' + esc(a.item) + '</td><td>' + esc(a.role) + '</td><td>' + esc(a.status) + '</td></tr>';
  }).join('');
  var measured = c.measured.map(function(m){
    return '<div><b>' + esc(m.value) + '</b><span>' + esc(m.label) + '</span></div>';
  }).join('');

  var map = '';
  if (c.map){
    map = '<div class="mapcard"><div class="maplabel"><span>' + esc(c.city) + '</span>' +
      '<em>' + c.area_km2 + ' km&sup2; &middot; ' + c.wards + ' wards</em></div>' +
      '<svg viewBox="0 0 ' + c.map.w + ' ' + c.map.h + '" role="img" aria-label="' + esc(c.city) + ' outline">' +
      '<path d="' + c.map.outline + '" fill="#f1ece3" stroke="#8d3f1c" stroke-width="1.6" stroke-linejoin="round"/>' +
      '</svg></div>';
  }

  var evs = c.events || [];
  function monthName(iso){ var m=['January','February','March','April','May','June','July','August','September','October','November','December'];
    return m[parseInt(iso.slice(5,7),10)-1] + ' ' + iso.slice(0,4); }
  function evRow(e){
    return '<div class="ev"><div class="ev__h"><span class="ev__t">' + esc(e.title) + '</span>' +
      (e.status === 'live' ? '<span class="ev__live">Live</span>' : '') + '</div>' +
      '<span class="ev__d">' + monthName(e['from']) + ' &ndash; ' + monthName(e['to']) + '</span>' +
      '<span class="ev__n">' + esc(e.note || '') + '</span></div>';
  }
  var liveEv = evs.filter(function(e){ return e.status === 'live'; }).map(evRow).join('');
  var pastEv = evs.filter(function(e){ return e.status !== 'live'; }).map(evRow).join('');
  var eventsCard = '<div class="card"><div class="card__t">Events</div>' +
    (liveEv || '<p style="margin:0;font-size:12.5px;color:var(--muted)">Nothing running.</p>') +
    (pastEv ? '<div class="ev__sep">Earlier</div>' + pastEv : '') + '</div>';

  var st = c.status || {lines: []};
  var statusRows = (st.lines || []).map(function(l){
    return '<div class="row"><div class="k"><span>' + esc(l.k) + '</span><b>' + esc(l.v) + '</b></div>' +
           '<span class="n">' + esc(l.n) + '</span></div>';
  }).join('');

  return '<div class="top">' + map +
      '<div class="stack">' +
        eventsCard +
        '<div class="card"><div class="card__t">Now &middot; ' + esc(st.as_of || '') + '</div>' +
          '<div class="card__big">' + esc(st.season || '') + '</div>' +
          '<p>What is armed, and what is not, on the day this page was built.</p>' +
          statusRows + '</div>' +
        '<div class="card"><div class="card__t">Water</div>' +
          '<div class="card__big">28 sites, 0.64 km&sup2;</div>' +
          '<p>Took water in February 2017 and no longer do. Each one is a place the corporation no longer has to hold rain in.</p></div>' +
      '</div></div>' +
    '<h2>What changed</h2><div class="measured">' + measured + '</div>' +
    '<h2>The register</h2>' +
    '<p class="note">The standing reference: what threshold starts a response, who acts, and within what window.</p>' +
    '<table><thead><tr><th>Hazard</th><th>Trigger</th><th>What starts</th><th>Who acts</th><th>Where it bites</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '<p class="note">' + esc(c.note) + '</p>' +
    '<h2>Assets the triggers act on</h2>' +
    '<table><thead><tr><th>Item</th><th>Climate role</th><th>Status</th></tr></thead><tbody>' + assets + '</tbody></table>';
}

function chooser(){
  return '<h2>Cities with a register</h2><div class="pick">' + CITIES.map(function(c, i){
    return '<a href="#' + c.slug + '" onclick="current=' + i + ';render();return false;"><b>' + esc(c.city) +
      '</b><span>' + esc(c.authority) + ' &middot; ' + c.area_km2 + ' km&sup2; &middot; ' + c.hazards.length + ' triggers</span></a>';
  }).join('') + '</div>';
}

function render(){
  document.getElementById('view').innerHTML = (CITIES.length === 1) ? cityPage(CITIES[0]) : chooser();
}
render();
</script>
</body>
</html>
"""

def main():
    files = sorted(p for p in DATA.glob('*.json') if not p.name.startswith('_'))
    if not files:
        sys.exit('no city files in data/city')
    cities = [json.loads(p.read_text(encoding='utf-8')) for p in files]
    built = (datetime.datetime.now(ZoneInfo('Asia/Kolkata')) if ZoneInfo
             else datetime.datetime.utcnow()).strftime('%Y-%m-%d %H:%M IST')
    html = TEMPLATE.replace('__DATA__', json.dumps(cities, ensure_ascii=False)).replace('__BUILT__', built)
    OUT.write_text(html, encoding='utf-8')
    print('wrote %s from %d city file(s): %s' % (OUT.name, len(files), ', '.join(c['slug'] for c in cities)))

if __name__ == '__main__':
    main()

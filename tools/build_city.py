#!/usr/bin/env python3
"""Build city/index.html from data/city/*.json.

The city register is generic: one JSON file per city, one page that renders any
number of them. Adding a city means adding a file, not writing code.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'city'
OUT  = ROOT / 'city' / 'index.html'

TEMPLATE = r"""<!DOCTYPE html>
<!-- city | built __BUILT__ -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>City resilience &mdash; Resilience</title>
<link rel="icon" type="image/png" href="../logos/resilience-icon.png">
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#0f0d0b;--muted:#2b2721;--accent:#772a0c;--line:rgba(32,88,0,.26);--warm:#faf9f7;
 --display:'Instrument Serif',Georgia,serif;--body:'DM Sans',system-ui,sans-serif;--mono:'JetBrains Mono',monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--warm);color:var(--ink);font-family:var(--body);line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1190px;margin:0 auto;padding:0 24px}
.header{position:relative;display:flex;align-items:flex-end;justify-content:space-between;gap:28px;padding:11px 0 21px;margin:0 0 26px}
.header__eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:2.5px;text-transform:uppercase;font-weight:700;margin:0 0 6px}
.header__title{font-family:var(--display);font-size:40px;font-weight:400;margin:2px 0;color:var(--accent);line-height:1.15}
.header__sub{font-size:16px;margin:0;max-width:62ch}
.header__logo{height:125px;width:auto;flex-shrink:0;margin-right:-10px;position:relative;top:10px}
.header::after{content:'';position:absolute;left:-24px;right:-24px;bottom:0;height:2px;
 border-top:4px solid #205800;border-bottom:4px solid #60a000;background:transparent}
.cities{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 18px}
.cities button{font-family:var(--mono);font-size:10.5px;letter-spacing:1.1px;text-transform:uppercase;
 border:1px solid var(--line);background:#fff;color:var(--muted);border-radius:999px;padding:7px 14px;cursor:pointer}
.cities button[aria-pressed="true"]{border-color:#205800;color:#205800;background:#f1f6ec}
.facts{display:flex;gap:26px;flex-wrap:wrap;margin:0 0 22px}
.fact{font-size:13.5px;color:var(--muted)}
.fact b{display:block;font-family:var(--display);font-size:24px;color:var(--ink);font-weight:400;line-height:1.2}
h2{font-family:var(--mono);font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);
 margin:30px 0 12px;display:flex;align-items:center;gap:10px}
h2::before{content:'';width:8px;height:8px;border-radius:50%;background:currentColor;flex-shrink:0}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top;font-size:13.5px}
th{font-family:var(--mono);font-size:9.5px;letter-spacing:1.3px;text-transform:uppercase;color:var(--muted);
 background:#f7f5f1;font-weight:600}
tr:last-child td{border-bottom:none}
td.h{font-weight:600;white-space:nowrap}
td.trig{font-size:13px}
.src{font-family:var(--mono);font-size:9.5px;letter-spacing:.6px;color:var(--muted);text-transform:uppercase}
.note{font-size:13px;color:var(--muted);margin:10px 0 0}
.measured{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.measured div{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.measured b{display:block;font-family:var(--display);font-size:22px;font-weight:400;margin-bottom:2px}
.measured span{font-size:12.5px;color:var(--muted)}
footer{margin:40px 0 40px;padding-top:16px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
@media (max-width:820px){.measured{grid-template-columns:1fr}th,td{padding:9px 10px;font-size:12.5px}}
</style>
</head>
<body>
<div class="wrap">
  <header class="header">
    <div>
      <div class="header__eyebrow">Resilience</div>
      <h1 class="header__title">City resilience</h1>
      <p class="header__sub">A hazard-trigger register for a city corporation: what threshold starts a response, who acts, and within what window.</p>
    </div>
    <img class="header__logo" src="../logos/resilience-mark.png" alt="Resilience">
  </header>

  <div class="cities" id="cities" role="group" aria-label="City"></div>
  <div id="view"></div>

  <footer>
    One JSON file per city in <b>data/city/</b>; <b>tools/build_city.py</b> renders this page from them.
    Thresholds are national scales; owners are municipal roles; the geography is measured per city.
  </footer>
</div>

<script>
var CITIES = __DATA__;
var current = 0;

function esc(s){ return String(s).replace(/[&<>]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]; }); }

function render(){
  var c = CITIES[current];
  var tabs = document.getElementById('cities');
  tabs.innerHTML = '';
  CITIES.forEach(function(x, i){
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = x.city;
    b.setAttribute('aria-pressed', i === current ? 'true' : 'false');
    b.onclick = function(){ current = i; render(); };
    tabs.appendChild(b);
  });

  var rows = c.hazards.map(function(h){
    return '<tr><td class="h">' + esc(h.hazard) + '</td>' +
           '<td class="trig">' + esc(h.trigger) + '<div class="src">' + esc(h.scale) + '</div></td>' +
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

  document.getElementById('view').innerHTML =
    '<div class="facts">' +
      '<div class="fact"><b>' + esc(c.authority) + '</b>corporation</div>' +
      '<div class="fact"><b>' + c.area_km2 + ' km&sup2;</b>area</div>' +
      '<div class="fact"><b>' + c.wards + '</b>wards</div>' +
    '</div>' +
    '<h2>The register</h2>' +
    '<table><thead><tr><th>Hazard</th><th>Trigger</th><th>What starts</th><th>Who acts</th><th>Where it bites</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>' +
    '<p class="note">' + esc(c.note) + '</p>' +
    '<h2>Assets the triggers act on</h2>' +
    '<table><thead><tr><th>Item</th><th>Climate role</th><th>Status</th></tr></thead><tbody>' + assets + '</tbody></table>' +
    '<h2>What is measured for this city</h2>' +
    '<div class="measured">' + measured + '</div>';
}
render();
</script>
</body>
</html>
"""

def main():
    import datetime, zoneinfo
    files = sorted(p for p in DATA.glob('*.json') if not p.name.startswith('_'))
    if not files:
        sys.exit('no city files in data/city')
    cities = [json.loads(p.read_text(encoding='utf-8')) for p in files]
    built = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M IST')
    html = (TEMPLATE
            .replace('__DATA__', json.dumps(cities, ensure_ascii=False))
            .replace('__BUILT__', built))
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding='utf-8')
    print('wrote %s from %d city file(s): %s' % (OUT.relative_to(ROOT), len(files),
          ', '.join(c['slug'] for c in cities)))

if __name__ == '__main__':
    main()

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
/* hero standard — the same numbers on every Resilience page.
   Measured from cities.html: header 148px, rule at its foot, mark 109px
   pinned to the corner, text block ending 23px above the rule. */
.header{position:relative !important;display:flex !important;align-items:flex-end !important;
 justify-content:space-between !important;gap:28px !important;height:148px !important;
 box-sizing:border-box !important;padding:0 0 23px !important;margin:0 0 30px !important}
.header::after{content:'';position:absolute;left:-24px;right:-24px;bottom:0;height:2px;
 border-top:4px solid #205800;border-bottom:4px solid #60a000;background:transparent}
.header>div:first-child{max-width:calc(100% - 160px)}
.header__eyebrow{font-family:var(--mono) !important;font-size:11px !important;line-height:1.55 !important;
 letter-spacing:2.5px !important;text-transform:uppercase !important;font-weight:700 !important;margin:0 0 6px !important}
.header__title{font-family:var(--display) !important;font-size:40px !important;line-height:1.15 !important;
 font-weight:400 !important;margin:2px 0 !important;color:var(--accent) !important;letter-spacing:0 !important}
.header__sub{font-size:16px !important;line-height:1.55 !important;margin:0 !important}
.header__logo{position:absolute !important;right:-10px !important;bottom:9px !important;
 height:109px !important;width:auto !important;margin:0 !important;top:auto !important;flex:none !important}





.facts{display:flex;gap:30px;flex-wrap:wrap;margin:0 0 4px}
.fact{font-size:13px;color:var(--muted)}
.fact b{display:block;font-family:var(--display);font-size:24px;color:var(--ink);font-weight:400;line-height:1.2}
h2{font-family:var(--mono);font-size:16px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);
 margin:32px 0 12px;display:flex;align-items:center;gap:10px}
h2::before{content:'';width:8px;height:8px;border-radius:50%;background:currentColor;flex-shrink:0}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:11px 14px;border-bottom:1px solid var(--line);vertical-align:top;font-size:15.5px}
th{font-family:var(--mono);font-size:11.5px;letter-spacing:1.3px;text-transform:uppercase;color:var(--muted);background:#f7f5f1;font-weight:600}
tr:last-child td{border-bottom:none}
td.h{font-weight:600;white-space:nowrap}
.src{font-family:var(--mono);font-size:11.5px;letter-spacing:.6px;color:var(--muted);text-transform:uppercase}
.note{font-size:15px;color:var(--muted);margin:10px 0 0}
.top{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:16px;align-items:stretch}
.mapcard{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px 12px;
 display:flex;flex-direction:column;min-height:0}
.stack{display:grid;gap:12px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:13px 15px;
 display:flex;flex-direction:column}
.card__t{font-family:var(--mono);font-size:11.5px;letter-spacing:1.4px;text-transform:uppercase;color:var(--muted);margin:0 0 7px}
.card__big{font-family:var(--display);font-size:26px;line-height:1.15;margin:0 0 3px}
.card p{margin:0;font-size:15.5px;color:var(--muted);line-height:1.45}
.card .row{padding:6px 0;border-bottom:1px solid #efe9df}
.card .row:last-child{border-bottom:none}
.card .row .k{display:flex;justify-content:space-between;gap:12px;align-items:baseline;font-size:15px}
.card .row .k b{font-family:var(--mono);font-size:11px;letter-spacing:.5px;white-space:nowrap}
.card .row .n{display:block;font-size:13.5px;color:var(--muted);margin-top:1px}
.ev{padding:10px 0;border-bottom:1px solid #efe9df}
.ev:last-child{border-bottom:none}
.ev--live{background:var(--warm);box-shadow:inset 4px 0 0 #60a000;margin:0 -15px;padding:10px 15px}
.ev__top{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:3px}
.ev__d{font-family:var(--mono);font-size:10.5px;letter-spacing:.4px;color:#14110e;text-transform:uppercase}
.ev__live{font-family:var(--mono);font-size:9.5px;letter-spacing:1px;text-transform:uppercase;
 background:#8f2318;color:#fff;padding:2px 5px;border-radius:3px;font-weight:700}
.ev__t{display:block;font-family:var(--display);font-size:21px;line-height:1.2;color:#0f0d0b;font-weight:400}
.ev__n{display:block;font-size:15px;color:var(--muted);margin-top:3px;line-height:1.45}
.ev__sep{font-family:var(--mono);font-size:9px;letter-spacing:1.4px;text-transform:uppercase;
 color:var(--muted);opacity:.75;padding:10px 0 2px;border-top:1px solid #efe9df;margin-top:6px}
@media (max-width:900px){.top{grid-template-columns:1fr}}
.mapcard svg{width:100%;max-width:720px;height:100%;min-height:0;display:block;margin:0 auto;flex:1}
.maplabel{display:flex;align-items:center;gap:8px;margin:-14px -16px 12px;padding:10px 16px;
 background:#f2eee6;border-bottom:1px solid var(--line);border-radius:12px 12px 0 0}
.maplabel span{font-size:13.5px;letter-spacing:.7px;text-transform:uppercase;font-weight:600;
 color:var(--ink);padding-bottom:3px}
.maplabel em{font-family:var(--mono);font-style:normal;font-size:12px;letter-spacing:1px;
 text-transform:uppercase;color:var(--muted);margin-left:auto}
.mapcard .cap{font-size:12.5px;color:var(--muted);margin:8px 0 0}
.plan{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:0 0 6px}
.thrust{position:relative;background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px;
 height:400px;display:flex;flex-direction:column;overflow:hidden}
.thrust.scrolls::after{content:'';position:absolute;left:1px;right:1px;bottom:1px;height:30px;
 background:linear-gradient(rgba(255,255,255,0),#fff 78%);border-radius:0 0 9px 9px;pointer-events:none}
.thrust h3{font-family:var(--mono);font-size:12.5px;letter-spacing:1.2px;text-transform:uppercase;
 color:var(--accent);margin:0 0 8px;font-weight:700;line-height:1.35}
.act{display:flex;gap:8px;font-size:15px;line-height:1.42;padding:5px 0;border-top:1px solid #f1ece3}
.act:first-of-type{border-top:none;padding-top:0}
.act b{font-family:var(--mono);font-size:12.5px;letter-spacing:.3px;color:var(--muted);white-space:nowrap;padding-top:2px;flex:none}
.ttabs{display:flex;gap:6px;margin:2px 0 9px;padding-bottom:8px;border-bottom:1px solid #efe9df}
.ttab{font-family:var(--mono);font-size:11px;letter-spacing:1.1px;text-transform:uppercase;
 background:#e6f0d6;border:1px solid #a8c781;border-radius:5px;padding:4px 9px;cursor:pointer;
 color:#1d4d00;opacity:1;font-weight:700}
.ttab:hover{background:#dbeac5;color:#123300}
.ttab.on{background:var(--accent);border-color:var(--accent);color:#fff;opacity:1;font-weight:700}
.ttabs--trig .ttab{font-size:12px;letter-spacing:1.2px;padding:5px 10px;background:#e6f0d6;
 border:1px solid #a8c781;color:#1d4d00;opacity:1;font-weight:700}
.ttabs--trig .ttab:hover{background:#dbeac5;color:#123300}
.ttabs--trig .ttab.on{background:var(--pc,var(--accent));border-color:var(--pc,var(--accent));
 color:#fff;opacity:1;font-weight:700;padding-bottom:5px}
.pane{display:none;flex:1;min-height:0;overflow-y:auto;padding-right:6px}
.tabgroup > .pane{padding-top:2px}
.rule{border:1px solid var(--line);border-radius:10px;background:#fff;margin:0 0 12px;overflow:hidden}
.rule__when{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:11px 16px;
 background:#f2eee6;border-bottom:1px solid var(--line)}
.rule__th{font-family:var(--display);font-size:20px;line-height:1.25;flex:1;min-width:220px}
.rule__body{display:grid;grid-template-columns:118px 1fr;gap:0 16px;padding:12px 16px}
.rule__k{display:flex;align-items:center;font-family:var(--mono);font-size:10.5px;letter-spacing:1.1px;
 text-transform:uppercase;color:var(--muted);padding:5px 0;border-top:1px solid #f1ece3}
.rule__v{display:flex;align-items:center;font-size:15px;padding:5px 0;border-top:1px solid #f1ece3}
.rule__v b{font-weight:600}
.rule__on{display:flex;flex-wrap:wrap;gap:6px}
.rule__on span{font-family:var(--mono);font-size:10.5px;letter-spacing:.4px;background:#f2eee6;
 border:1px solid #e6e0d4;border-radius:4px;padding:2px 6px;color:var(--muted)}
@media (max-width:700px){.rule__body{grid-template-columns:1fr}.rule__k{padding-top:9px}}
.pane.on{display:block}
.pane::-webkit-scrollbar{width:8px}
.pane::-webkit-scrollbar-thumb{background:rgba(32,88,0,.22);border-radius:4px}
.pane::-webkit-scrollbar-track{background:transparent}
.pane{scrollbar-width:thin;scrollbar-color:rgba(32,88,0,.22) transparent}
.wkh{font-family:var(--mono);font-size:8.5px;letter-spacing:1.1px;text-transform:uppercase;color:#1f4e79;
 margin:10px 0 4px;padding-top:8px;border-top:1px solid #dfe7ee}
.wk{display:flex;gap:8px;font-size:14px;line-height:1.4;padding:3px 0}
.wk b{font-family:var(--mono);font-size:11px;letter-spacing:.3px;color:#1f4e79;white-space:nowrap;flex:none;padding-top:2px}
.wk em{font-style:normal;font-family:var(--mono);font-size:10.5px;letter-spacing:.5px;color:var(--muted);opacity:.8;margin-left:auto;flex:none;padding-top:2px}
@media (max-width:1000px){.plan{grid-template-columns:repeat(2,1fr)}}
@media (max-width:700px){.plan{grid-template-columns:1fr}}
.footrule{margin:36px -24px 34px;height:2px;border-top:4px solid #205800;border-bottom:4px solid #60a000}
.measured{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
.measured div{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.measured b{display:block;font-family:var(--display);font-size:22px;font-weight:400;margin-bottom:2px}
.measured span{font-size:13.5px;color:var(--muted)}
.pick{display:grid;gap:10px;margin:10px 0 0}
.pick a{display:block;background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;
 text-decoration:none;color:var(--ink)}
.pick a:hover{border-color:#205800}
.pick b{font-family:var(--display);font-size:22px;font-weight:400;display:block}
.pick span{font-size:12.5px;color:var(--muted)}
footer{margin:38px 0 40px;padding-top:16px;border-top:1px solid var(--line);font-size:13.5px;color:var(--muted)}
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
  <div class="footrule" aria-hidden="true"></div>

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
  var assetById = {};
  (c.assets || []).forEach(function(a){ assetById[a.id] = a; });
  var ruleTabs = (c.hazards || []).map(function(h, i){
    return '<button class="ttab' + (i === 0 ? ' on' : '') + '" role="tab" aria-selected="' + (i === 0 ? 'true' : 'false') +
      '" data-pane="rt-' + i + '"' + (h.pillColour ? ' style="--pc:' + esc(h.pillColour) + '"' : '') + '>' +
      esc(h.pill || h.hazard) + '</button>';
  }).join('');
  var ruleCards = (c.hazards || []).map(function(h){
    var on = (h.assets || []).map(function(id){
      var a = assetById[id];
      return '<span>' + esc(a ? a.item : id) + '</span>';
    }).join('');
    return '<div class="rule">' +
      '<div class="rule__when"><span class="rule__th">' + esc(h.trigger) + '</span></div>' +
      '<div class="rule__body">' +
        '<div class="rule__k">Who acts</div><div class="rule__v"><b>' + esc(h.owner) + '</b></div>' +
        '<div class="rule__k">What starts</div><div class="rule__v">' + esc(h.starts) + '</div>' +
        '<div class="rule__k">On</div><div class="rule__v"><div class="rule__on">' + on + '</div></div>' +
        '<div class="rule__k">Within</div><div class="rule__v">' + esc(h.window) + '</div>' +
        '<div class="rule__k">Armed</div><div class="rule__v">' + esc(h.armed || '') + '</div>' +
        '<div class="rule__k">Where</div><div class="rule__v">' + esc(h.where) + '</div>' +
      '</div></div>';
  });
  var rules = '<div class="tabgroup"><div class="ttabs ttabs--trig" role="tablist">' + ruleTabs + '</div>' +
    (c.hazards || []).map(function(h, i){
      return '<div class="pane' + (i === 0 ? ' on' : '') + '" id="rt-' + i + '" role="tabpanel">' + ruleCards[i] + '</div>';
    }).join('') + '</div>';

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
    return '<div class="ev' + (e.status === 'live' ? ' ev--live' : '') + '">' +
      '<div class="ev__top"><span class="ev__d">' + monthName(e['from']) + ' &ndash; ' + monthName(e['to']) + '</span>' +
      (e.status === 'live' ? '<span class="ev__live">live</span>' : '') + '</div>' +
      '<span class="ev__t">' + esc(e.title) + '</span>' +
      '<span class="ev__n">' + esc(e.note || '') + '</span></div>';
  }
  var liveEv = evs.filter(function(e){ return e.status === 'live'; }).map(evRow).join('');
  var pastEv = evs.filter(function(e){ return e.status !== 'live'; }).map(evRow).join('');
  var eventsCard = '<div class="card"><div class="card__t">Events</div>' +
    (liveEv || '<p style="margin:0;font-size:12.5px;color:var(--muted)">Nothing running.</p>') +
    (pastEv ? '<div class="ev__sep">Earlier</div>' + pastEv : '') + '</div>';

  var planBlock = '';
  if (c.plan && c.plan.thrusts && c.plan.thrusts.length){
    planBlock = '<h2>' + esc(c.plan.title || 'Climate action plan') + '</h2>' +
      '<div class="plan">' + c.plan.thrusts.map(function(t){
        var items = (c.plan.items || []).filter(function(i){ return i.thrust === t.name; });
        var wid = 'th' + Math.random().toString(36).slice(2, 8);
        var worksPane = items.length
          ? items.map(function(i){
              return '<div class="wk"><b>' + esc(i.asset || i.kind) + '</b><span>' + esc(i.item) + '</span>' +
                     '<em>' + esc(i.role) + '</em></div>';
            }).join('')
          : '<p class="note" style="margin:2px 0 0">None budgeted under this thrust.</p>';
        return '<div class="thrust"><h3>' + esc(t.name) + '</h3>' +
          '<div class="tabgroup"><div class="ttabs" role="tablist">' +
            '<button class="ttab on" role="tab" aria-selected="true" data-pane="' + wid + '-a">Actions (' + t.actions.length + ')</button>' +
            '<button class="ttab" role="tab" aria-selected="false" data-pane="' + wid + '-w">Budgeted works' +
              (items.length ? ' (' + items.length + ')' : '') + '</button>' +
          '</div>' +
          '<div class="pane on" id="' + wid + '-a" role="tabpanel">' +
            t.actions.map(function(a){
              return '<div class="act"><b>' + esc(a.id) + '</b><span>' + esc(a.text) + '</span></div>';
            }).join('') +
          '</div>' +
          '<div class="pane" id="' + wid + '-w" role="tabpanel">' + worksPane + '</div>' +
          '</div></div>';
      }).join('') + '</div>';
  }

  var st = c.status || {lines: []};
  var statusRows = (st.lines || []).map(function(l){
    return '<div class="row"><div class="k"><span>' + esc(l.k) + '</span><b>' + esc(l.v) + '</b></div>' +
           '<span class="n">' + esc(l.n) + '</span></div>';
  }).join('');

  return '<div class="top">' + map +
      '<div class="stack">' + eventsCard + '</div></div>' +
    '<h2>Responding to triggers</h2>' +
    rules +
    planBlock;
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
function markScroll(){
  document.querySelectorAll('.thrust').forEach(function(c){
    var pane = c.querySelector('.pane.on');
    c.classList.toggle('scrolls', !!pane && pane.scrollHeight > pane.clientHeight + 1);
  });
}
document.addEventListener('click', function(ev){
  var b = ev.target.closest('.ttab');
  if (!b) return;
  var card = b.closest('.tabgroup');
  if (!card) return;
  card.querySelectorAll('.ttab').forEach(function(x){
    var on = x === b;
    x.classList.toggle('on', on);
    x.setAttribute('aria-selected', on ? 'true' : 'false');
    var pane = document.getElementById(x.getAttribute('data-pane'));
    if (pane) pane.classList.toggle('on', on);
  });
  markScroll();
});
render();
markScroll();
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

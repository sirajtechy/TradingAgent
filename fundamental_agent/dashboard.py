"""
dashboard.py  v2
~~~~~~~~~~~~~~~~
Generates a rich, self-contained, mobile-friendly HTML dashboard from
sector_backtest_results.json.

Features
--------
* Live filter bar — search by ticker, sector, outcome, score threshold
* Click-sortable columns
* Monthly sparkline dots with hover tooltips
* Per-ticker detail modal (full month-by-month breakdown)
* Excel download (3 sheets: Ticker Summary, Monthly Detail, Confusion Matrices)
* CSV download
* Four interactive Chart.js charts
* Colour-coded confusion matrix tiles per sector
* Sticky nav with scroll-to-section links
* Fully mobile-responsive (Tailwind CSS CDN)

No extra Python dependencies — all rendering is done in the browser.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_dashboard(
    results_json: str | Path = "sector_backtest_results.json",
    output_html: str | Path = "backtest_dashboard.html",
) -> Path:
    with open(results_json) as fh:
        data: Dict[str, Any] = json.load(fh)
    out = Path(output_html)
    out.write_text(_build_html(data), encoding="utf-8")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers (output JSON for the browser to consume)
# ─────────────────────────────────────────────────────────────────────────────

def _sector_color(sector: str) -> str:
    return {
        "Technology":       "#6366f1",
        "Healthcare":       "#10b981",
        "Financials":       "#3b82f6",
        "Consumer_Staples": "#f59e0b",
        "Energy":           "#ef4444",
    }.get(sector, "#94a3b8")


def _ticker_rows_data(sectors: Dict) -> list:
    rows = []
    for sector_name, sector_data in sectors.items():
        for ticker, data in sector_data.get("tickers", {}).items():
            if data is None:
                rows.append({
                    "ticker": ticker,
                    "sector": sector_name.replace("_", " "),
                    "signals": 0, "correct": 0, "neutral": 0,
                    "hit_pct": None, "avg_score": None,
                    "band": "error", "outcome": "error", "monthly": [],
                })
                continue
            s = data["summary"]
            periods = data["periods"]
            scores = [
                p["experimental_score"] for p in periods
                if p["experimental_score"] is not None
            ]
            bands = [p["score_band"] for p in periods if p["score_band"]]
            common_band = max(set(bands), key=bands.count) if bands else None
            sigs = s["directional_signals"]
            corr = s["correct_signals"]
            acc  = s["accuracy_pct"]
            neut = s["total_periods"] - sigs
            if acc is None:   outcome = "neutral"
            elif acc >= 65:   outcome = "strong"
            elif acc >= 50:   outcome = "moderate"
            else:             outcome = "weak"
            monthly = [
                {
                    "month":      p["month"],
                    "signal":     p.get("signal", ""),
                    "correct":    p["signal_correct"],
                    "return_pct": p["price_return_pct"],
                    "score":      p["experimental_score"],
                    "band":       p.get("score_band", ""),
                }
                for p in periods
            ]
            rows.append({
                "ticker":    ticker,
                "sector":    sector_name.replace("_", " "),
                "signals":   sigs,
                "correct":   corr,
                "neutral":   neut,
                "hit_pct":   acc,
                "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
                "band":      common_band or "mixed",
                "outcome":   outcome,
                "monthly":   monthly,
            })
    return rows


def _sector_summary_data(sectors: Dict) -> list:
    out = []
    for name, data in sectors.items():
        cm = data.get("confusion_matrix", {})
        out.append({
            "name":        name.replace("_", " "),
            "color":       _sector_color(name),
            "accuracy":    cm.get("accuracy_pct"),
            "precision":   cm.get("precision_pct"),
            "recall":      cm.get("recall_pct"),
            "f1":          cm.get("f1_pct"),
            "specificity": cm.get("specificity_pct"),
            "abstention":  cm.get("abstention_rate_pct"),
            "tp":      cm.get("TP", 0),
            "fp":      cm.get("FP", 0),
            "tn":      cm.get("TN", 0),
            "fn":      cm.get("FN", 0),
            "signals": cm.get("directional_signals", 0),
            "neutral": cm.get("neutral_count", 0),
            "errors":  cm.get("error_count", 0),
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Main HTML builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_html(data: Dict[str, Any]) -> str:
    meta    = data.get("meta", {})
    overall = data.get("overall_confusion_matrix", {})
    sectors = data.get("sectors", {})

    generated_at = datetime.now().strftime("%d %b %Y, %H:%M")
    window  = meta.get("window", "")
    n_ticks = str(meta.get("tickers", ""))
    src     = meta.get("data_source", "yfinance")

    ticker_rows_json    = json.dumps(_ticker_rows_data(sectors))
    sector_summary_json = json.dumps(_sector_summary_data(sectors))
    overall_json        = json.dumps(overall)

    return (
        _HTML_TEMPLATE
        .replace("__WINDOW__", window)
        .replace("__N_TICKS__", n_ticks)
        .replace("__SRC__", src)
        .replace("__GENERATED_AT__", generated_at)
        .replace("__TICKER_ROWS__", ticker_rows_json)
        .replace("__SECTOR_SUM__", sector_summary_json)
        .replace("__OVERALL__", overall_json)
    )


# ─────────────────────────────────────────────────────────────────────────────
# HTML / JS template  (plain string — no f-string escaping needed)
# ─────────────────────────────────────────────────────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Backtest Dashboard &#8212; __WINDOW__</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<style>
body{font-family:system-ui,sans-serif;background:#f1f5f9}
.badge{display:inline-block;padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:700;letter-spacing:.03em}
.badge-green{background:#dcfce7;color:#166534}
.badge-teal{background:#d1fae5;color:#065f46}
.badge-blue{background:#dbeafe;color:#1d4ed8}
.badge-gray{background:#f1f5f9;color:#475569}
.badge-red{background:#fee2e2;color:#991b1b}
.kpi-card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);text-align:center}
.kpi-value{font-size:1.75rem;font-weight:800;color:#4338ca}
.kpi-label{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8;margin-top:2px}
.section-card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08);margin-bottom:16px}
.cm-tp{background:#dcfce7;color:#166534;font-weight:700}
.cm-fp{background:#fee2e2;color:#991b1b;font-weight:700}
.cm-tn{background:#dbeafe;color:#1d4ed8;font-weight:700}
.cm-fn{background:#fef3c7;color:#92400e;font-weight:700}
.sortable th{cursor:pointer;user-select:none}
.sortable th:hover{background:#e0e7ff}
.sortable th.asc::after{content:" \u2191"}
.sortable th.desc::after{content:" \u2193"}
th,td{white-space:nowrap}
.pill-btn{padding:5px 14px;border-radius:9999px;font-size:12px;font-weight:600;border:2px solid transparent;cursor:pointer;transition:all .15s}
.pill-btn.active{background:#6366f1;color:#fff;border-color:#6366f1}
.pill-btn:not(.active){background:#fff;color:#6366f1;border-color:#e0e7ff}
input[type=range]{accent-color:#6366f1}
.nav-link{font-size:13px;font-weight:600;color:#6366f1;padding:4px 12px;border-radius:9999px;text-decoration:none;transition:background .15s}
.nav-link:hover{background:#e0e7ff}
#tickerTableBody tr:hover{background:#f8faff}
.monthly-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 1px;cursor:pointer}
@media(max-width:640px){
  .kpi-value{font-size:1.3rem}
  .hide-mobile{display:none!important}
}
</style>
</head>
<body>

<!-- NAV -->
<header class="sticky top-0 z-50 bg-white shadow-sm border-b border-gray-100">
  <div class="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
    <div class="flex items-center gap-3">
      <span class="text-2xl">&#x1F4CA;</span>
      <div>
        <p class="font-extrabold text-gray-800 leading-none text-base">Backtest Dashboard</p>
        <p class="text-xs text-gray-400">__WINDOW__ &middot; __N_TICKS__ tickers &middot; __SRC__</p>
      </div>
    </div>
    <nav class="flex gap-1 flex-wrap">
      <a href="#summary"  class="nav-link">Summary</a>
      <a href="#charts"   class="nav-link">Charts</a>
      <a href="#sectors"  class="nav-link">Sectors</a>
      <a href="#tickers"  class="nav-link">Tickers</a>
    </nav>
    <div class="flex gap-2">
      <button onclick="downloadExcel()"
        class="flex items-center gap-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-bold rounded-lg shadow transition">
        &#11015; Excel
      </button>
      <button onclick="downloadCSV()"
        class="flex items-center gap-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow transition">
        &#11015; CSV
      </button>
    </div>
  </div>
</header>

<main class="max-w-7xl mx-auto px-4 py-6 space-y-8">

<!-- KPI STRIP -->
<section id="summary">
  <p class="text-xs font-bold uppercase tracking-widest text-gray-400 mb-3">Overall Performance &middot; __WINDOW__</p>
  <div id="kpiGrid" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3"></div>
</section>

<!-- CHARTS -->
<section id="charts">
  <p class="text-xs font-bold uppercase tracking-widest text-gray-400 mb-3">Performance Analytics</p>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div class="section-card lg:col-span-2">
      <p class="text-sm font-bold text-gray-600 mb-3">Accuracy &amp; F1 by Sector</p>
      <div style="height:240px"><canvas id="sectorBarChart"></canvas></div>
    </div>
    <div class="section-card">
      <p class="text-sm font-bold text-gray-600 mb-3">Signal Distribution</p>
      <div style="height:240px"><canvas id="doughnutChart"></canvas></div>
    </div>
    <div class="section-card">
      <p class="text-sm font-bold text-gray-600 mb-3">Abstention Rate by Sector</p>
      <div style="height:220px"><canvas id="abstentionChart"></canvas></div>
    </div>
    <div class="section-card lg:col-span-2">
      <p class="text-sm font-bold text-gray-600 mb-3">Precision vs Recall (bubble = sector)</p>
      <div style="height:220px"><canvas id="scatterChart"></canvas></div>
    </div>
  </div>
</section>

<!-- SECTOR CARDS -->
<section id="sectors">
  <p class="text-xs font-bold uppercase tracking-widest text-gray-400 mb-3">Sector Confusion Matrices</p>
  <div id="sectorGrid" class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4"></div>
</section>

<!-- TICKER TABLE -->
<section id="tickers">
  <div class="section-card">
    <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
      <p class="text-sm font-bold text-gray-700">Ticker Explorer</p>
      <div class="flex flex-wrap gap-2 items-center">
        <input id="searchInput" type="text" placeholder="Search ticker&hellip;" onkeyup="applyFilters()"
          class="border border-gray-200 rounded-lg px-3 py-1.5 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-indigo-300"/>
        <div id="sectorPills" class="flex gap-1 flex-wrap"></div>
        <select id="outcomeFilter" onchange="applyFilters()"
          class="border border-gray-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
          <option value="all">All outcomes</option>
          <option value="strong">Strong (&ge;65%)</option>
          <option value="moderate">Moderate (50&ndash;64%)</option>
          <option value="weak">Weak (&lt;50%)</option>
          <option value="neutral">All Neutral</option>
          <option value="error">Error</option>
        </select>
        <div class="flex items-center gap-1 text-xs text-gray-500">
          Score &ge;
          <input id="scoreFilter" type="range" min="0" max="100" value="0" step="5"
            onchange="applyFilters();document.getElementById('scoreVal').textContent=this.value" class="w-20"/>
          <span id="scoreVal" class="font-bold text-indigo-600 w-6">0</span>
        </div>
        <span id="rowCount" class="text-xs text-gray-400 font-semibold"></span>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse sortable" id="mainTable">
        <thead>
          <tr class="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
            <th class="p-3 text-left border-b"  data-col="ticker">Ticker</th>
            <th class="p-3 text-left border-b hide-mobile" data-col="sector">Sector</th>
            <th class="p-3 text-center border-b" data-col="signals">Signals</th>
            <th class="p-3 text-center border-b" data-col="correct">Correct</th>
            <th class="p-3 text-center border-b" data-col="hit_pct">Hit %</th>
            <th class="p-3 text-center border-b hide-mobile" data-col="neutral">Neutral</th>
            <th class="p-3 text-center border-b hide-mobile" data-col="avg_score">Avg Score</th>
            <th class="p-3 text-center border-b hide-mobile" data-col="band">Band</th>
            <th class="p-3 text-center border-b">Monthly</th>
            <th class="p-3 text-center border-b">Detail</th>
          </tr>
        </thead>
        <tbody id="tickerTableBody"></tbody>
      </table>
    </div>
  </div>
</section>

<!-- MODAL -->
<div id="modalBackdrop" onclick="closeModal()"
  class="fixed inset-0 bg-black/40 z-40 hidden flex-col items-center justify-center p-4">
  <div id="modalBox" onclick="event.stopPropagation()"
    class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-screen overflow-y-auto p-6 relative z-50">
    <button onclick="closeModal()"
      class="absolute top-4 right-4 text-gray-400 hover:text-gray-700 text-xl font-bold">&#10005;</button>
    <h2 id="modalTitle" class="text-xl font-extrabold text-gray-800 mb-4"></h2>
    <div id="modalBody"></div>
  </div>
</div>

<!-- FOOTER -->
<footer class="text-center text-xs text-gray-400 py-6 border-t border-gray-200">
  Fundamental Backtest Agent &middot; Deterministic scoring &middot; Data via __SRC__ &middot; Generated __GENERATED_AT__
</footer>
</main>

<script>
// Embedded data ---------------------------------------------------------------
const TICKER_ROWS = __TICKER_ROWS__;
const SECTOR_SUM  = __SECTOR_SUM__;
const OVERALL     = __OVERALL__;

// KPI strip -------------------------------------------------------------------
function pct(v){ return v!=null ? v.toFixed(1)+'%' : 'N/A'; }
const kpis=[
  ['Tickers',   TICKER_ROWS.length,              '&#x1F4CA;'],
  ['Signals',   OVERALL.directional_signals,     '&#x1F4E1;'],
  ['Accuracy',  pct(OVERALL.accuracy_pct),       '&#x1F3AF;'],
  ['Precision', pct(OVERALL.precision_pct),      '&#x1F52C;'],
  ['Recall',    pct(OVERALL.recall_pct),         '&#x1F4C8;'],
  ['F1 Score',  pct(OVERALL.f1_pct),             '&#x2696;&#xFE0F;'],
  ['TP',        OVERALL.TP,                      '&#x2705;'],
  ['Abstained', pct(OVERALL.abstention_rate_pct),'&#x1F910;'],
];
const kg=document.getElementById('kpiGrid');
kpis.forEach(([label,val,icon])=>{
  kg.innerHTML+=`<div class="kpi-card"><div style="font-size:1.6rem">${icon}</div>
    <div class="kpi-value">${val}</div><div class="kpi-label">${label}</div></div>`;
});

// Sector pills ----------------------------------------------------------------
const allSectors=[...new Set(TICKER_ROWS.map(r=>r.sector))].sort();
const activeSectors=new Set(['all']);
function renderPills(){
  const d=document.getElementById('sectorPills'); d.innerHTML='';
  const ab=document.createElement('button');
  ab.textContent='All'; ab.className='pill-btn'+(activeSectors.has('all')?' active':'');
  ab.onclick=()=>{activeSectors.clear();activeSectors.add('all');renderPills();applyFilters();};
  d.appendChild(ab);
  allSectors.forEach(s=>{
    const b=document.createElement('button'); b.textContent=s;
    b.className='pill-btn'+((!activeSectors.has('all')&&activeSectors.has(s))?' active':'');
    b.onclick=()=>{
      activeSectors.delete('all');
      activeSectors.has(s)?activeSectors.delete(s):activeSectors.add(s);
      if(!activeSectors.size) activeSectors.add('all');
      renderPills(); applyFilters();
    };
    d.appendChild(b);
  });
}
renderPills();

// Sector cards ----------------------------------------------------------------
const sg=document.getElementById('sectorGrid');
SECTOR_SUM.forEach(s=>{
  sg.innerHTML+=`<div class="section-card border-t-4" style="border-color:${s.color}">
    <div class="flex items-center justify-between mb-3">
      <p class="font-extrabold text-gray-800">${s.name}</p>
      <span class="badge badge-blue">Acc ${pct(s.accuracy)}</span>
    </div>
    <div class="grid grid-cols-2 gap-2 mb-3">
      <div class="rounded-lg p-3 text-center cm-tp"><div class="text-xl font-black">${s.tp}</div><div class="text-xs mt-1 opacity-80">TP (Correct &uarr;)</div></div>
      <div class="rounded-lg p-3 text-center cm-fp"><div class="text-xl font-black">${s.fp}</div><div class="text-xs mt-1 opacity-80">FP (Wrong &uarr;)</div></div>
      <div class="rounded-lg p-3 text-center cm-fn"><div class="text-xl font-black">${s.fn}</div><div class="text-xs mt-1 opacity-80">FN (Wrong &darr;)</div></div>
      <div class="rounded-lg p-3 text-center cm-tn"><div class="text-xl font-black">${s.tn}</div><div class="text-xs mt-1 opacity-80">TN (Correct &darr;)</div></div>
    </div>
    <div class="grid grid-cols-3 gap-2 text-xs text-center">
      <div class="bg-indigo-50 rounded p-1"><div class="font-bold text-indigo-700">${pct(s.precision)}</div><div class="text-gray-400">Precision</div></div>
      <div class="bg-indigo-50 rounded p-1"><div class="font-bold text-indigo-700">${pct(s.recall)}</div><div class="text-gray-400">Recall</div></div>
      <div class="bg-indigo-50 rounded p-1"><div class="font-bold text-indigo-700">${pct(s.f1)}</div><div class="text-gray-400">F1</div></div>
      <div class="bg-gray-50 rounded p-1 col-span-2"><div class="font-bold text-gray-600">${s.signals} signals &middot; ${s.neutral} neutral</div></div>
      <div class="bg-gray-50 rounded p-1"><div class="font-bold text-gray-600">${pct(s.abstention)}</div><div class="text-gray-400">Abstained</div></div>
    </div>
    ${s.errors>0?`<p class="text-xs text-red-500 mt-2">&#9888; ${s.errors} error(s)</p>`:''}
  </div>`;
});

// Helpers ---------------------------------------------------------------------
const BAND_CSS={strong:'badge-green',good:'badge-teal',mixed_positive:'badge-blue',
                mixed:'badge-gray',weak:'badge-red',error:'badge-red'};
function bandBadge(b){
  return `<span class="badge ${BAND_CSS[b]||'badge-gray'}">${(b||'N/A').replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</span>`;
}
function hitClass(v){
  if(v==null) return 'text-gray-400';
  if(v>=65) return 'text-green-600 font-bold';
  if(v>=50) return 'text-amber-600 font-semibold';
  return 'text-red-600 font-bold';
}
function sparkDots(monthly){
  return monthly.map(m=>{
    const ret=m.return_pct!=null?(m.return_pct>=0?'+':'')+m.return_pct.toFixed(1)+'%':'?';
    let bg,title;
    if(m.correct===true){bg='#22c55e';title=`${m.month}: \u2713 ${m.signal} ${ret}`;}
    else if(m.correct===false){bg='#ef4444';title=`${m.month}: \u2717 ${m.signal} ${ret}`;}
    else{bg='#cbd5e1';title=`${m.month}: neutral (${ret})`;}
    return `<span class="monthly-dot" style="background:${bg}" title="${title}"></span>`;
  }).join('');
}

// Filter / sort ---------------------------------------------------------------
let sortCol='hit_pct',sortDir='desc';
function applyFilters(){
  const q=document.getElementById('searchInput').value.toLowerCase().trim();
  const outcome=document.getElementById('outcomeFilter').value;
  const minScore=parseFloat(document.getElementById('scoreFilter').value)||0;
  const rows=TICKER_ROWS.filter(r=>{
    if(q&&!r.ticker.toLowerCase().includes(q)&&!r.sector.toLowerCase().includes(q)) return false;
    if(!activeSectors.has('all')&&!activeSectors.has(r.sector)) return false;
    if(outcome!=='all'&&r.outcome!==outcome) return false;
    if(r.avg_score!=null&&r.avg_score<minScore) return false;
    return true;
  });
  renderTable(rows);
}
function sortBy(col){
  if(sortCol===col) sortDir=sortDir==='asc'?'desc':'asc';
  else{sortCol=col;sortDir='desc';}
  document.querySelectorAll('#mainTable th').forEach(th=>{
    th.classList.remove('asc','desc');
    if(th.dataset.col===col) th.classList.add(sortDir);
  });
  applyFilters();
}
document.querySelectorAll('#mainTable th[data-col]').forEach(th=>th.onclick=()=>sortBy(th.dataset.col));

function renderTable(rows){
  const sorted=[...rows].sort((a,b)=>{
    let va=a[sortCol],vb=b[sortCol];
    if(va==null&&vb==null)return 0;
    if(va==null)return 1; if(vb==null)return -1;
    if(typeof va==='string'){va=va.toLowerCase();vb=vb.toLowerCase();}
    return(va<vb?-1:va>vb?1:0)*(sortDir==='asc'?1:-1);
  });
  document.getElementById('rowCount').textContent=`${rows.length}/${TICKER_ROWS.length} rows`;
  document.getElementById('tickerTableBody').innerHTML=sorted.map(r=>`<tr>
    <td class="p-3 font-mono font-bold text-gray-800 border-b">${r.ticker}</td>
    <td class="p-3 border-b hide-mobile"><span class="badge badge-gray">${r.sector}</span></td>
    <td class="p-3 text-center border-b">${r.signals}</td>
    <td class="p-3 text-center border-b">${r.correct}</td>
    <td class="p-3 text-center border-b ${hitClass(r.hit_pct)}">${r.hit_pct!=null?r.hit_pct.toFixed(1)+'%':'&mdash;'}</td>
    <td class="p-3 text-center border-b text-gray-400 hide-mobile">${r.neutral}</td>
    <td class="p-3 text-center border-b font-mono hide-mobile">${r.avg_score!=null?r.avg_score.toFixed(1):'&mdash;'}</td>
    <td class="p-3 text-center border-b hide-mobile">${bandBadge(r.band)}</td>
    <td class="p-3 text-center border-b">${sparkDots(r.monthly)}</td>
    <td class="p-3 text-center border-b">
      <button onclick='openModal(${JSON.stringify(r)})'
        class="text-indigo-600 hover:text-indigo-800 text-xs font-bold px-2 py-1 rounded hover:bg-indigo-50">View &rarr;</button>
    </td>
  </tr>`).join('');
}
applyFilters();

// Modal -----------------------------------------------------------------------
function openModal(r){
  document.getElementById('modalTitle').textContent=r.ticker+' \u2014 '+r.sector;
  const mrows=r.monthly.map(m=>{
    let icon,cls;
    if(m.correct===true){icon='\u2713';cls='text-green-600 font-bold';}
    else if(m.correct===false){icon='\u2717';cls='text-red-600 font-bold';}
    else{icon='\u2013';cls='text-gray-400';}
    const ret=m.return_pct!=null
      ?(m.return_pct>=0
        ?`<span class="text-green-600">+${m.return_pct.toFixed(2)}%</span>`
        :`<span class="text-red-600">${m.return_pct.toFixed(2)}%</span>`):'&mdash;';
    return `<tr class="hover:bg-gray-50">
      <td class="p-2 border-b text-gray-500">${m.month}</td>
      <td class="p-2 border-b font-semibold">${m.signal||'&mdash;'}</td>
      <td class="p-2 border-b text-center ${cls}">${icon}</td>
      <td class="p-2 border-b text-center">${ret}</td>
      <td class="p-2 border-b text-center font-mono">${m.score!=null?m.score.toFixed(1):'&mdash;'}</td>
      <td class="p-2 border-b text-center">${bandBadge(m.band)}</td>
    </tr>`;
  }).join('');
  document.getElementById('modalBody').innerHTML=`
    <div class="grid grid-cols-3 gap-3 mb-4">
      <div class="bg-indigo-50 rounded-xl p-3 text-center">
        <div class="text-2xl font-black ${hitClass(r.hit_pct)}">${r.hit_pct!=null?r.hit_pct.toFixed(1)+'%':'&mdash;'}</div>
        <div class="text-xs text-gray-500 mt-1">Hit Rate</div>
      </div>
      <div class="bg-gray-50 rounded-xl p-3 text-center">
        <div class="text-2xl font-black text-gray-700">${r.signals}</div>
        <div class="text-xs text-gray-500 mt-1">Signals</div>
      </div>
      <div class="bg-gray-50 rounded-xl p-3 text-center">
        <div class="text-2xl font-black text-gray-700">${r.avg_score!=null?r.avg_score.toFixed(1):'&mdash;'}</div>
        <div class="text-xs text-gray-500 mt-1">Avg Score</div>
      </div>
    </div>
    <div class="mb-4">${bandBadge(r.band)}</div>
    <div class="overflow-x-auto">
      <table class="w-full text-sm border-collapse">
        <thead><tr class="bg-gray-100 text-xs uppercase text-gray-500">
          <th class="p-2 text-left border-b">Month</th>
          <th class="p-2 border-b">Signal</th>
          <th class="p-2 border-b">Result</th>
          <th class="p-2 border-b">Return</th>
          <th class="p-2 border-b">Score</th>
          <th class="p-2 border-b">Band</th>
        </tr></thead>
        <tbody>${mrows}</tbody>
      </table>
    </div>`;
  const bd=document.getElementById('modalBackdrop');
  bd.classList.remove('hidden'); bd.classList.add('flex');
}
function closeModal(){
  const bd=document.getElementById('modalBackdrop');
  bd.classList.add('hidden'); bd.classList.remove('flex');
}

// Excel download (SheetJS) ----------------------------------------------------
function downloadExcel(){
  const wb=XLSX.utils.book_new();
  // Sheet 1: Ticker Summary
  const sh=['Ticker','Sector','Signals','Correct','Hit %','Neutral','Avg Score','Band','Outcome'];
  const sr=TICKER_ROWS.map(r=>[r.ticker,r.sector,r.signals,r.correct,
    r.hit_pct!=null?r.hit_pct:null,r.neutral,r.avg_score!=null?r.avg_score:null,r.band,r.outcome]);
  const ws1=XLSX.utils.aoa_to_sheet([sh,...sr]);
  ws1['!cols']=[8,20,8,8,8,8,10,16,10].map(w=>{return{wch:w}});
  XLSX.utils.book_append_sheet(wb,ws1,'Ticker Summary');
  // Sheet 2: Monthly Detail
  const dh=['Ticker','Sector','Month','Signal','Result','Return %','Score','Band'];
  const dr=[];
  TICKER_ROWS.forEach(r=>r.monthly.forEach(m=>dr.push([
    r.ticker,r.sector,m.month,m.signal||'neutral',
    m.correct===true?'Correct':m.correct===false?'Wrong':'Neutral',
    m.return_pct,m.score,m.band
  ])));
  const ws2=XLSX.utils.aoa_to_sheet([dh,...dr]);
  ws2['!cols']=[8,20,14,10,10,10,8,16].map(w=>{return{wch:w}});
  XLSX.utils.book_append_sheet(wb,ws2,'Monthly Detail');
  // Sheet 3: Confusion Matrices
  const ch=['Sector','Accuracy%','Precision%','Recall%','F1%','Specificity%','Abstention%','TP','FP','TN','FN','Signals','Neutral'];
  const cr=SECTOR_SUM.map(s=>[s.name,s.accuracy,s.precision,s.recall,s.f1,s.specificity,s.abstention,s.tp,s.fp,s.tn,s.fn,s.signals,s.neutral]);
  cr.push(['OVERALL',OVERALL.accuracy_pct,OVERALL.precision_pct,OVERALL.recall_pct,OVERALL.f1_pct,
    OVERALL.specificity_pct,OVERALL.abstention_rate_pct,OVERALL.TP,OVERALL.FP,OVERALL.TN,OVERALL.FN,
    OVERALL.directional_signals,OVERALL.neutral_count]);
  const ws3=XLSX.utils.aoa_to_sheet([ch,...cr]);
  ws3['!cols']=ch.map(()=>{return{wch:14}});
  XLSX.utils.book_append_sheet(wb,ws3,'Confusion Matrices');
  XLSX.writeFile(wb,'backtest_report.xlsx');
}

// CSV download ----------------------------------------------------------------
function downloadCSV(){
  const hdr=['Ticker','Sector','Month','Signal','Result','Return %','Score','Band'];
  const dr=[];
  TICKER_ROWS.forEach(r=>r.monthly.forEach(m=>dr.push([
    r.ticker,r.sector,m.month,m.signal||'neutral',
    m.correct===true?'Correct':m.correct===false?'Wrong':'Neutral',
    m.return_pct,m.score,m.band
  ].join(','))));
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([[hdr.join(','),...dr].join('\n')],{type:'text/csv'}));
  a.download='backtest_report.csv'; document.body.appendChild(a); a.click(); document.body.removeChild(a);
}

// Charts ----------------------------------------------------------------------
const sLabels=SECTOR_SUM.map(s=>s.name);
const sColors=SECTOR_SUM.map(s=>s.color);

new Chart(document.getElementById('sectorBarChart'),{
  type:'bar',
  data:{labels:sLabels,datasets:[
    {label:'Accuracy %',data:SECTOR_SUM.map(s=>s.accuracy),backgroundColor:sColors.map(c=>c+'cc'),borderColor:sColors,borderWidth:2},
    {label:'F1 %',      data:SECTOR_SUM.map(s=>s.f1),      backgroundColor:sColors.map(c=>c+'33'),borderColor:sColors,borderWidth:2},
  ]},
  options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{position:'top',labels:{font:{size:11}}}},
    scales:{y:{min:0,max:100,ticks:{callback:v=>v+'%'}}}}
});

new Chart(document.getElementById('doughnutChart'),{
  type:'doughnut',
  data:{labels:['TP','FP','TN','FN','Neutral'],datasets:[{
    data:[OVERALL.TP,OVERALL.FP,OVERALL.TN,OVERALL.FN,OVERALL.neutral_count],
    backgroundColor:['#22c55e','#ef4444','#3b82f6','#f97316','#cbd5e1'],borderWidth:1
  }]},
  options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{position:'bottom',labels:{font:{size:10},boxWidth:10}}}}
});

new Chart(document.getElementById('abstentionChart'),{
  type:'bar',
  data:{labels:sLabels,datasets:[{
    label:'Abstention %',data:SECTOR_SUM.map(s=>s.abstention),
    backgroundColor:'#c7d2fe',borderColor:'#6366f1',borderWidth:2
  }]},
  options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:false}},scales:{x:{min:0,max:100,ticks:{callback:v=>v+'%'}}}}
});

new Chart(document.getElementById('scatterChart'),{
  type:'scatter',
  data:{datasets:SECTOR_SUM.map(s=>{return{
    label:s.name,data:[{x:s.recall,y:s.precision}],
    backgroundColor:s.color+'cc',pointRadius:14,pointHoverRadius:17
  }})},
  options:{responsive:true,maintainAspectRatio:false,
    plugins:{
      legend:{position:'right',labels:{font:{size:11}}},
      tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label} \u2014 P:${ctx.parsed.y?.toFixed(1)}%  R:${ctx.parsed.x?.toFixed(1)}%`}}
    },
    scales:{
      x:{title:{display:true,text:'Recall %'},min:0,max:110,ticks:{callback:v=>v+'%'}},
      y:{title:{display:true,text:'Precision %'},min:0,max:110,ticks:{callback:v=>v+'%'}}
    }}
});
</script>
</body>
</html>"""

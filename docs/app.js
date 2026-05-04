// ── Sector name lookup ────────────────────────────────────────────────────
const SECTOR_NAMES = {
  "A01": "Crop & animal production",   "A02": "Forestry & logging",
  "A03": "Fishing & aquaculture",      "B05": "Coal mining",
  "B06": "Oil & gas extraction",       "B07": "Metal ore mining",
  "B08": "Other mining & quarrying",   "B09": "Mining support services",
  "C10T12": "Food, beverages & tobacco","C13T15": "Textiles, apparel & leather",
  "C16": "Wood & wood products",       "C17_18": "Paper & printing",
  "C19": "Coke & refined petroleum",   "C20": "Chemicals",
  "C21": "Pharmaceuticals",            "C22": "Rubber & plastics",
  "C23": "Non-metallic mineral products","C24A": "Basic metals (ferrous)",
  "C24B": "Basic metals (non-ferrous)","C25": "Fabricated metal products",
  "C26": "Computer & electronic products","C27": "Electrical equipment",
  "C28": "Machinery & equipment",      "C29": "Motor vehicles",
  "C301": "Ships & boats",             "C302T309": "Other transport equipment",
  "C31T33": "Furniture & other manufacturing",
  "D": "Electricity & gas",   "E": "Water supply & waste",
  "F": "Construction",         "G": "Wholesale & retail trade",
  "H49": "Land transport",    "H50": "Water transport",
  "H51": "Air transport",     "H52": "Warehousing & logistics",
  "H53": "Postal & courier",  "I": "Accommodation & food services",
  "J58T60": "Publishing & broadcasting","J61": "Telecommunications",
  "J62_63": "IT & computer services",  "K": "Financial & insurance",
  "L": "Real estate",          "M": "Professional & scientific services",
  "N": "Administrative & support services","O": "Public administration",
  "P": "Education",            "Q": "Health & social work",
  "R": "Arts & entertainment", "S": "Other services"
};

// ── ICIO-to-NACE crosswalk (aligned with Src/utils/constants.py) ──────────
const ICIO_TO_NACE = {
  "A01":"A","A02":"A","A03":"A",
  "B05":"B","B06":"B","B07":"B","B08":"B","B09":"B",
  "C10T12":"C10-C12","C13T15":"C13-C15",
  "C16":"C16-C18","C17_18":"C16-C18",
  "C19":"C19","C20":"C20","C21":"C21",
  "C22":"C22-C23","C23":"C22-C23",
  "C24A":"C24-C25","C24B":"C24-C25","C25":"C24-C25",
  "C26":"C26","C27":"C27","C28":"C28",
  "C29":"C29-C30","C301":"C29-C30","C302T309":"C29-C30",
  "C31T33":"C31-C33",
  "D":"D","E":"E","F":"F","G":"G",
  "H49":"H49","H50":"H50","H51":"H51","H52":"H52","H53":"H53",
  "I":"I","J58T60":"J58-J60","J61":"J61","J62_63":"J62-J63",
  "K":"K","L":"L","M":"M","N":"N","O":"O","P":"P","Q":"Q","R":"R","S":"S"
};

const YEARS = [2016,2017,2018,2019,2020,2021];
const DATA_ROOT_CANDIDATES = ["../data/processed","data/processed","/data/processed"];

let proxy       = "contribution"; // "contribution" | "depth"
let centrality  = "pagerank";     // "pagerank" | "betweenness" | "in_strength" | "out_strength"
let scale       = "raw";          // "raw" | "norm"
let currentYear = "avg";
let allData      = {};
let charts       = {};
let dataReady    = false;
let globalBounds = {}; // { colName: {min, max} } — fixed across all years
let currentView = "rankings";

const CENTRALITY_LABELS = {
  pagerank:     "PageRank",
  betweenness:  "Betweenness",
  in_strength:  "In-strength",
  out_strength: "Out-strength",
};

function sectorName(icio) { return SECTOR_NAMES[icio] || icio; }


function roundAxisBound(value, mode) {
  if (!isFinite(value) || value === 0) return 0;
  const magnitude = 10 ** Math.floor(Math.log10(Math.abs(value)));
  const scaled = value / magnitude;
  const rounded = mode === "min"
    ? Math.floor(scaled * 2) / 2
    : Math.ceil(scaled * 2) / 2;
  return rounded * magnitude;
}

function computeAxisBounds(values, {padRatio = 0.12, symmetric = false} = {}) {
  if (!values.length) return null;
  let min = Math.min(...values);
  let max = Math.max(...values);

  if (symmetric) {
    const limit = Math.max(Math.abs(min), Math.abs(max));
    min = -limit;
    max = limit;
  }

  const span = Math.max(max - min, Math.abs(max), 1);
  const pad = span * padRatio;
  min -= pad;
  max += pad;

  if (symmetric) {
    const limit = Math.max(Math.abs(min), Math.abs(max));
    min = -limit;
    max = limit;
  }

  return {
    min: roundAxisBound(min, "min"),
    max: roundAxisBound(max, "max"),
  };
}

function computeGlobalBounds() {
  const AXIS_COLS = [
    "pagerank", "betweenness", "in_strength", "out_strength",
    "pagerank_norm", "betweenness_norm", "in_strength_norm", "out_strength_norm",
    "dig_contribution", "dig_depth",
    "dig_contribution_norm", "dig_depth_norm",
  ];

  globalBounds = {};
  AXIS_COLS.forEach((col) => {
    const vals = YEARS.flatMap((y) =>
      (allData[y] || []).map((r) => r[col]).filter((v) => v != null && !isNaN(v))
    );
    if (!vals.length) return;
    globalBounds[col] = computeAxisBounds(vals, {
      symmetric: col.endsWith("_norm"),
      padRatio: col.endsWith("_norm") ? 0.14 : 0.08,
    });
  });
}

function fmt(v, decimals = 3) {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toFixed(decimals);
}

// ── CSV loading ───────────────────────────────────────────────────────────

function loadCSV(path) {
  return new Promise((resolve, reject) => {
    Papa.parse(path, {
      download: true, header: true, dynamicTyping: true, skipEmptyLines: true,
      complete: (r) => resolve(r.data),
      error: () => reject(new Error(`Failed: ${path}`))
    });
  });
}

async function loadCSVFromCandidates(fileName) {
  let lastError = null;
  for (const root of DATA_ROOT_CANDIDATES) {
    try {
      const rows = await loadCSV(`${root}/${fileName}`);
      if (Array.isArray(rows) && rows.length > 0) return rows;
      lastError = new Error(`Empty: ${root}/${fileName}`);
    } catch (e) { lastError = e; }
  }
  throw lastError || new Error(`Failed to load ${fileName}`);
}

function mergeYear(cent, dig) {
  const digByNace = {};
  dig.forEach((d) => { if (d.nace_r2_code) digByNace[String(d.nace_r2_code).trim()] = d; });
  return cent.map((c) => {
    const icio = String(c.icio_code || "").trim();
    const nace = ICIO_TO_NACE[icio] || null;
    const d    = nace ? (digByNace[nace] || {}) : {};
    return {
      icio_code: icio, sector_name: sectorName(icio), nace_r2_code: nace,
      pagerank: c.pagerank ?? null, pagerank_norm: c.pagerank_norm ?? null,
      betweenness: c.betweenness ?? null, betweenness_norm: c.betweenness_norm ?? null,
      in_strength: c.in_strength ?? null, in_strength_norm: c.in_strength_norm ?? null,
      out_strength: c.out_strength ?? null, out_strength_norm: c.out_strength_norm ?? null,
      dig_contribution: d.dig_contribution ?? null,
      dig_contribution_norm: d.dig_contribution_norm ?? null,
      dig_depth: d.dig_depth ?? null,
      dig_depth_norm: d.dig_depth_norm ?? null
    };
  }).filter((r) => r.icio_code);
}

// ── Statistics ────────────────────────────────────────────────────────────

function spearman(xs, ys) {
  const pairs = xs.map((x,i) => ({x,y:ys[i]}))
    .filter((p) => p.x != null && p.y != null && !isNaN(p.x) && !isNaN(p.y));
  const n = pairs.length;
  if (n < 4) return {r:NaN, lo:NaN, hi:NaN, n};
  const rankArr = (arr) => {
    const sorted = [...arr].map((v,i) => ({v,i})).sort((a,b) => a.v-b.v);
    const ranks  = new Array(n);
    sorted.forEach((item,ri) => { ranks[item.i] = ri+1; });
    return ranks;
  };
  const px = pairs.map((p) => p.x), py = pairs.map((p) => p.y);
  const rx = rankArr(px),           ry = rankArr(py);
  const mx = rx.reduce((a,b)=>a+b,0)/n, my = ry.reduce((a,b)=>a+b,0)/n;
  let num=0, dx2=0, dy2=0;
  for (let i=0;i<n;i++) {
    num += (rx[i]-mx)*(ry[i]-my);
    dx2 += (rx[i]-mx)**2;
    dy2 += (ry[i]-my)**2;
  }
  const r  = num/Math.sqrt(dx2*dy2);
  const zr = Math.atanh(Math.max(-0.9999, Math.min(0.9999, r)));
  const se = 1/Math.sqrt(n-3);
  return {r, lo:Math.tanh(zr-1.96*se), hi:Math.tanh(zr+1.96*se), n};
}

// Spearman is rank-based: invariant to monotone transforms. Raw and
// normalised inputs yield identical r. We compute on demand so that the
// centrality selector can change which column is used as the x-axis.
function buildCorrData(centCol) {
  return {
    contribution: YEARS.map((y) => {
      const rows = allData[y] || [];
      return {year:y, ...spearman(rows.map((r)=>r[centCol]), rows.map((r)=>r.dig_contribution))};
    }),
    depth: YEARS.map((y) => {
      const rows = allData[y] || [];
      return {year:y, ...spearman(rows.map((r)=>r[centCol]), rows.map((r)=>r.dig_depth))};
    }),
  };
}

// Threshold is 0 because _norm columns are z-scores: 0 = global mean.
function assignQ(pr, dig) {
  if (pr >= 0 && dig >= 0) return "HH";
  if (pr >= 0 && dig <  0) return "HL";
  if (pr <  0 && dig >= 0) return "LH";
  return "LL";
}

const Q_COL = {HH:"#0D5C4A", HL:"#1A567A", LH:"#5A9E52", LL:"#A07840"};
const Q_LABEL = {
  HH:"High centrality / High digital", HL:"High centrality / Low digital",
  LH:"Low centrality / High digital",  LL:"Low centrality / Low digital"
};

// ── Helpers to pick the right column based on scale toggle ───────────────

function col(metric) {
  // metric = "dig_contribution" | "dig_depth" | "pagerank"
  return scale === "norm" ? `${metric}_norm` : metric;
}
function colLabel(metric) {
  const names = {dig_contribution:"Digital contribution", dig_depth:"Digital depth", pagerank:"PageRank"};
  return `${names[metric] || metric}${scale === "norm" ? " (norm.)" : " (raw)"}`;
}
// Quadrant always uses globally norm. norm so 0.5 threshold is meaningful
function qcol(metric) { return `${metric}_norm`; }

// ── Data loading ──────────────────────────────────────────────────────────

async function loadAll() {
  try {
    if (window.DASHBOARD_BUNDLE && typeof window.DASHBOARD_BUNDLE === "object") {
      allData = Object.fromEntries(
        Object.entries(window.DASHBOARD_BUNDLE).map(([y,rows]) => [Number(y), rows])
      );
      Object.values(allData).forEach((rows) =>
        rows.forEach((r) => { if (!r.sector_name) r.sector_name = sectorName(r.icio_code); })
      );
      const sample = allData[2021] || [];
      if (!sample.length) throw new Error("Bundled data is empty.");
      computeGlobalBounds();
      dataReady = true;
      const withDig = sample.filter((r) => r.dig_contribution_norm != null).length;
      document.getElementById("status").style.display = "none";
      document.getElementById("load-msg").textContent =
        `${sample.length} sectors · ${withDig} with digitalisation data`;
      showView("rankings");
      document.getElementById("year-sel").value = "avg";
      renderAll();
      return;
    }

    await Promise.all(YEARS.map(async (y) => {
      const [cent,dig] = await Promise.all([
        loadCSVFromCandidates(`centrality_${y}.csv`),
        loadCSVFromCandidates(`digitalisation_${y}.csv`)
      ]);
      allData[y] = mergeYear(cent, dig);
    }));

    const sample = allData[2021] || [];
    if (!sample.length) throw new Error("Merge produced 0 rows.");
    const withDig = sample.filter((r) => r.dig_contribution_norm != null).length;
    if (!withDig) throw new Error(
      `No digitalisation values matched.\nSample ICIO: ` +
      `${[...new Set(sample.slice(0,6).map((r)=>r.icio_code))].join(", ")}`
    );

    computeGlobalBounds();
    dataReady = true;
    document.getElementById("status").style.display = "none";
    document.getElementById("load-msg").textContent =
      `${sample.length} sectors · ${withDig} with digitalisation data`;
    showView("rankings");
    renderAll();
  } catch (e) {
    document.getElementById("status").textContent =
      `Error loading data:\n${e.message}\n\n` +
      "Start a local server from project root:\n  python -m http.server 8000\n" +
      "then open http://localhost:8000/dashboard/index.html";
    document.getElementById("status").className = "error";
    document.getElementById("load-msg").textContent = "Error";
    console.error(e);
    window.allData = allData;
  }
}

// ── KPI strip ─────────────────────────────────────────────────────────────

function renderKPIs(year) {
  const el = document.getElementById("kpi-strip");
  if (!el) return;
  const rows = allData[year] || [];

  if (currentView === "rankings") {
    const kpiRows = year === "avg" ? avgRows() : rows;
    const withC = kpiRows.filter((r) => r.dig_contribution != null);
    const withD = kpiRows.filter((r) => r.dig_depth != null);
    const topC  = withC.length ? withC.reduce((a,b) => b.dig_contribution > a.dig_contribution ? b : a) : null;
    const topD  = withD.length ? withD.reduce((a,b) => b.dig_depth > a.dig_depth ? b : a) : null;
    el.innerHTML = `
      <div class="kpi-card"><div class="kpi-value">${kpiRows.length}</div><div class="kpi-label">Sectors in panel</div></div>
      <div class="kpi-card"><div class="kpi-value">${withC.length}</div><div class="kpi-label">With contribution data</div></div>
      <div class="kpi-card"><div class="kpi-value">${withD.length}</div><div class="kpi-label">With depth data</div></div>
      <div class="kpi-card"><div class="kpi-value kpi-code">${topC?.icio_code||"—"}</div><div class="kpi-label">Top contribution — ${topC?.sector_name||""}</div></div>
      <div class="kpi-card"><div class="kpi-value kpi-code">${topD?.icio_code||"—"}</div><div class="kpi-label">Top depth — ${topD?.sector_name||""}</div></div>`;

  } else if (currentView === "correlation") {
    el.innerHTML = "";

  } else if (currentView === "quadrant") {
    const qc = proxy==="contribution" ? "dig_contribution_norm" : "dig_depth_norm";
    const centCol = `${centrality}_norm`;
    const valid = rows.filter((r) => r[centCol]!=null && r[qc]!=null);
    const counts = {HH:0, HL:0, LH:0, LL:0};
    valid.forEach((r) => { counts[assignQ(r[centCol], r[qc])]++; });
    el.innerHTML = Object.entries(counts).map(([q,n]) => `
      <div class="kpi-card kpi-quad kpi-${q.toLowerCase()}">
        <div class="kpi-value">${n}</div>
        <div class="kpi-label">${Q_LABEL[q]}</div>
      </div>`).join("");

  } else if (currentView === "table") {
    const top = rows[0];
    el.innerHTML = `
      <div class="kpi-card"><div class="kpi-value">${rows.length}</div><div class="kpi-label">Sectors</div></div>
      <div class="kpi-card"><div class="kpi-value kpi-code">${top?.icio_code||"—"}</div><div class="kpi-label">Highest PageRank — ${top?.sector_name||""}</div></div>`;
  }
}

// ── Chart helpers ─────────────────────────────────────────────────────────

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

Chart.register({
  id: "zeroline",
  afterDraw(chart) {
    if (!chart.options._showZero) return;
    const {ctx, chartArea, scales} = chart;
    if (!scales.y) return;
    const y0 = scales.y.getPixelForValue(0);
    if (y0 < chartArea.top || y0 > chartArea.bottom) return;
    ctx.save();
    ctx.strokeStyle = "rgba(80,80,80,0.3)"; ctx.lineWidth = 1; ctx.setLineDash([5,4]);
    ctx.beginPath(); ctx.moveTo(chartArea.left, y0); ctx.lineTo(chartArea.right, y0); ctx.stroke();
    ctx.restore();
  }
});

Chart.register({
  id: "quadBg",
  beforeDraw(chart) {
    if (!chart.options._isQuad) return;
    const {ctx, chartArea, scales} = chart;
    if (!scales.x || !scales.y) return;
    const mx = scales.x.getPixelForValue(0), my = scales.y.getPixelForValue(0);
    const {left, right, top, bottom} = chartArea;
    [[mx,top,right-mx,my-top,"#0D5C4A14"],[left,top,mx-left,my-top,"#1A567A14"],
     [mx,my,right-mx,bottom-my,"#5A9E5214"],[left,my,mx-left,bottom-my,"#A0784014"]]
      .forEach(([x,y,w,h,c]) => { ctx.save(); ctx.fillStyle=c; ctx.fillRect(x,y,w,h); ctx.restore(); });
    ctx.save();
    ctx.strokeStyle="rgba(80,80,80,0.22)"; ctx.lineWidth=1; ctx.setLineDash([5,4]);
    ctx.beginPath(); ctx.moveTo(mx,top); ctx.lineTo(mx,bottom); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(left,my); ctx.lineTo(right,my); ctx.stroke();
    ctx.restore();
    ctx.save();
    ctx.font="bold 11px DM Sans,sans-serif"; ctx.fillStyle="rgba(80,80,80,0.38)";
    ctx.fillText("HH",mx+8,top+18); ctx.fillText("HL",left+8,top+18);
    ctx.fillText("LH",mx+8,bottom-8); ctx.fillText("LL",left+8,bottom-8);
    ctx.restore();
  }
});

Chart.register({
  id: "sectorLabels",
  afterDatasetsDraw(chart) {
    if (!chart.options._isQuad) return;
    const {ctx} = chart;
    chart.data.datasets.forEach((ds,di) => {
      chart.getDatasetMeta(di).data.forEach((pt,i) => {
        const point = ds.data[i];
        const lbl = point?.showLabel ? point.label : null;
        if (!lbl) return;
        ctx.save();
        ctx.font = "600 10px DM Sans, sans-serif";
        ctx.lineWidth = 3;
        ctx.strokeStyle = "rgba(255,255,255,0.92)";
        ctx.fillStyle = "rgba(10,20,18,0.88)";
        const dx = point.labelDx ?? 8;
        const dy = point.labelDy ?? -8;
        ctx.strokeText(lbl, pt.x + dx, pt.y + dy);
        ctx.fillText(lbl, pt.x + dx, pt.y + dy);
        ctx.restore();
      });
    });
  }
});

// ── Render: bar charts ────────────────────────────────────────────────────

function makeBarChart(canvasId, top10, lbl, color, axis = {}) {
  destroyChart(canvasId);
  const canvas = document.getElementById(canvasId);
  canvas.style.height = "380px";  // pin height before Chart.js takes over
  charts[canvasId] = new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: top10.map((r) => r.icio_code),
      datasets: [{
        label: lbl,
        data: top10.map((r) => +Number(r._val).toFixed(4)),
        backgroundColor: `${color}66`, borderColor: color, borderWidth: 1.5, borderRadius: 3,
        borderSkipped: false
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { right: 8 } },
      animation: { duration: 500, easing: "easeOutQuart" },
      plugins: {
        legend: {display: false},
        title: {
          display: true, text: lbl,
          font: {size:13, family:"DM Sans", weight:"500"},
          color: "#0B1E1A", padding: {bottom:12}
        },
        tooltip: {
          callbacks: {
            title: (items) => `${top10[items[0].dataIndex]?.icio_code} — ${top10[items[0].dataIndex]?.sector_name||""}`,
            label: (c) => ` ${lbl}: ${c.raw.toFixed(4)}`
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          min: axis.min ?? 0,
          max: axis.max ?? undefined,
          border: { display: true, color: "#2A5A52", width: 2 },
          grid: { color: "#C0D8D4", lineWidth: 1, drawTicks: true },
          ticks: { font: {size:11}, color: "#2A4A44", maxTicksLimit: 6 }
        },
        y: {
          border: { display: true, color: "#2A5A52", width: 2 },
          grid: { display: false },
          ticks: { font: {size:11, family:"monospace"}, color: "#2A4A44", padding: 4 }
        }
      }
    }
  });
}

function avgRows() {
  // Average each metric across all years per sector, using raw values.
  const bySector = {};
  YEARS.forEach((y) => {
    (allData[y] || []).forEach((r) => {
      if (!bySector[r.icio_code]) bySector[r.icio_code] = {icio_code: r.icio_code, sector_name: r.sector_name, _counts: {}, _sums: {}};
      const s = bySector[r.icio_code];
      ["dig_contribution","dig_contribution_norm","dig_depth","dig_depth_norm"].forEach((m) => {
        if (r[m] != null && !isNaN(r[m])) {
          s._sums[m] = (s._sums[m] || 0) + r[m];
          s._counts[m] = (s._counts[m] || 0) + 1;
        }
      });
    });
  });
  return Object.values(bySector).map((s) => {
    const out = {icio_code: s.icio_code, sector_name: s.sector_name};
    Object.keys(s._sums).forEach((m) => { out[m] = s._sums[m] / s._counts[m]; });
    return out;
  });
}

function renderBars(year) {
  const isAvg = year === "avg";
  const rows = isAvg ? avgRows() : (allData[year] || []);
  const yearLbl = isAvg ? "2016–2021 avg" : String(year);

  [
    ["contribution","dig_contribution","Digital contribution","#0D5C4A"],
    ["depth",       "dig_depth",       "Digital depth",       "#1A7A64"]
  ].forEach(([p, metric, baseLabel, color]) => {
    const c = col(metric);
    const lbl = `${colLabel(metric)}${isAvg ? " — avg" : ""}`;
    const valid = rows.filter((r) => r[c] != null && !isNaN(r[c]));
    const top10 = [...valid].sort((a,b) => b[c]-a[c]).slice(0,10)
      .map((r) => ({...r, _val: r[c]}));
    makeBarChart(`bar-${p}`, top10, lbl, color, {
      min: 0,
      max: metric === "dig_contribution" && scale === "raw" ? 2.5 : globalBounds[c]?.max
    });
  });
  document.getElementById("bar-sub").textContent =
    `${scale==="norm"?"z-score normalised":"Unscaled raw"} values · ${yearLbl} · top 10 by each proxy`;
}

// ── Render: correlation charts ────────────────────────────────────────────

// Four centrality measures, each with a distinct colour.
const CENT_LINE_COLORS = {
  pagerank:     "#0D5C4A",
  betweenness:  "#3D9E82",
  in_strength:  "#1A567A",
  out_strength: "#A07840",
};

function renderCorrelations() {
  // One chart per proxy (contribution / depth).
  // Each chart has 4 lines — one per centrality measure.
  [["contribution","Digital contribution"],["depth","Digital depth"]].forEach(([p, baseLabel]) => {
    destroyChart(`corr-${p}`);
    const canvas = document.getElementById(`corr-${p}`);
    canvas.style.height = "260px";

    // Build one dataset per centrality measure.
    const datasets = Object.entries(CENTRALITY_LABELS).map(([cent, centLbl]) => {
      const data = buildCorrData(cent)[p] || [];
      const rs   = data.map((d) => isNaN(d.r) ? null : +d.r.toFixed(3));
      const color = CENT_LINE_COLORS[cent];
      return {
        label: centLbl,
        data: rs,
        borderColor: color,
        backgroundColor: color,
        pointRadius: 4, pointHoverRadius: 6,
        borderWidth: 2, tension: 0.3, fill: false,
      };
    });

    charts[`corr-${p}`] = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: { labels: YEARS, datasets },
      options: {
        _showZero: true,
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: "bottom",
            labels: { boxWidth: 12, font: {size:11}, padding: 14 } },
          title: {
            display: true, text: `Correlation vs ${baseLabel}`,
            font: {size:13, family:"DM Sans", weight:"500"},
            color: "#0B1E1A", padding: {bottom:10}
          },
          tooltip: {
            callbacks: {
              label: (c) => {
                const r = c.raw;
                if (r == null) return null;
                const sig = Math.abs(r) >= 0.30 ? " ✓" : " n.s.";
                return ` ${c.dataset.label}: ${r}${sig}`;
              }
            }
          }
        },
        scales: {
          x: { grid:{color:"#C0D8D4"}, ticks:{font:{size:11}} },
          y: { min:-1, max:1, grid:{color:"#C0D8D4"}, ticks:{font:{size:11}, stepSize:0.5},
               border:{display:true, color:"#2A5A52", width:2} }
        }
      }
    });
  });
}

// ── Render: quadrant scatter ──────────────────────────────────────────────

function renderQuadrant(year, p) {
  // _norm columns are global z-scores (mean=0, std=1 across all 6 years ×
  // 49 sectors). Threshold = 0 means above/below the global mean.
  const qc      = p==="contribution" ? "dig_contribution_norm" : "dig_depth_norm";
  const digLbl  = p==="contribution" ? "Digital contribution (z-score)" : "Digital depth (z-score)";
  const centCol = `${centrality}_norm`;
  const centLbl = `${CENTRALITY_LABELS[centrality]} (z-score)`;

  const rows = (allData[year]||[]).filter((r)=>r[centCol]!=null && r[qc]!=null);
  destroyChart("quad-chart");

  const canvas = document.getElementById("quad-chart");
  canvas.style.height = "720px";
  canvas.style.width  = "";

  // Use global bounds (fixed across all years) so the axis scale is stable
  const xMin = globalBounds[qc]?.min ?? -4;
  const xMax = globalBounds[qc]?.max ??  4;
  const yMin = globalBounds[centCol]?.min ?? -4;
  const yMax = globalBounds[centCol]?.max ??  4;

  const labelOffsets = [
    {dx: 8, dy: -8},
    {dx: 8, dy: 14},
    {dx: -34, dy: -8},
    {dx: 10, dy: 24},
    {dx: -42, dy: 12},
    {dx: -26, dy: 24},
  ];
  const datasets = ["HH","HL","LH","LL"].map((q) => {
    const quadRows = rows
      .filter((r)=>assignQ(r[centCol], r[qc])===q)
      .map((r) => ({
        x:+r[qc].toFixed(4),
        y:+r[centCol].toFixed(4),
        label:r.icio_code,
        name:r.sector_name,
        prominence: Math.hypot(r[qc], r[centCol]),
      }));

    const labeledCodes = new Set(
      [...quadRows]
        .sort((a, b) => b.prominence - a.prominence)
        .slice(0, Math.min(6, quadRows.length))
        .map((r) => r.label)
    );

    return {
      label: Q_LABEL[q],
      data: quadRows.map((r, idx) => {
        const offset = labelOffsets[idx % labelOffsets.length];
        return {
          ...r,
          showLabel: labeledCodes.has(r.label) || r.prominence >= 1.35,
          labelDx: offset.dx,
          labelDy: offset.dy,
        };
      }),
    backgroundColor:`${Q_COL[q]}CC`,
    borderColor:"#FFFFFF",
    pointBorderColor:Q_COL[q],
    borderWidth:2.2,
    pointRadius:6,
    pointHoverRadius:9,
    pointHitRadius:12,
    pointHoverBorderWidth:3,
    pointStyle:"circle"
    };
  });

  charts["quad-chart"] = new Chart(canvas.getContext("2d"), {
    type:"scatter", data:{datasets},
    options: {
      _isQuad: true, responsive: true, maintainAspectRatio: false,
      animation: { duration: 400, easing: "easeOutQuart" },
      interaction: { mode: "nearest", intersect: true, axis: "xy" },
      plugins: {
        legend: {display:false},
        tooltip: {
          callbacks: {
            title: (items) => `${items[0].raw.label} - ${items[0].raw.name || ""}`,
            label: (c) => [`Code: ${c.raw.label}`, `Digital (norm.): ${c.raw.x}`, `${CENTRALITY_LABELS[centrality]} (norm.): ${c.raw.y}`]
          }
        }
      },
      scales: {
        x: {min:xMin, max:xMax, title:{display:true, text:digLbl,  font:{size:12}, color:"#5F5E5A"}, grid:{color:"#D4E4E018"}, ticks:{font:{size:11}}},
        y: {min:yMin, max:yMax, title:{display:true, text:centLbl, font:{size:12}, color:"#5F5E5A"}, grid:{color:"#D4E4E018"}, ticks:{font:{size:11}}}
      }
    }
  });

  document.getElementById("quad-sub").textContent =
    `Split at z = 0 (global mean) · ${year} · y-axis: ${CENTRALITY_LABELS[centrality]} · x-axis: ${digLbl}`;
}

// ── Render: sector data table ─────────────────────────────────────────────

function renderTable(year) {
  const rows  = (allData[year]||[]).slice()
    .sort((a,b)=>(b.pagerank??-Infinity)-(a.pagerank??-Infinity));
  const tbody = document.getElementById("tbl-body");
  if (!tbody) return;

  const c_cont = col("dig_contribution");
  const c_dep  = col("dig_depth");
  const c_pr   = col("pagerank");

  const c_ins = scale === "norm" ? "in_strength_norm"  : "in_strength";
  const c_out = scale === "norm" ? "out_strength_norm" : "out_strength";

  tbody.innerHTML = rows.map((r,i) => {
    const qC = (r.pagerank_norm!=null && r.dig_contribution_norm!=null)
      ? assignQ(r.pagerank_norm, r.dig_contribution_norm) : null;
    const qD = (r.pagerank_norm!=null && r.dig_depth_norm!=null)
      ? assignQ(r.pagerank_norm, r.dig_depth_norm) : null;
    const dot = (q) => q
      ? `<span class="q-dot-sm" style="background:${Q_COL[q]}"></span>`
      : "";
    return `<tr>
      <td class="tbl-rank">${i+1}</td>
      <td class="tbl-code">${r.icio_code}</td>
      <td class="tbl-name">${r.sector_name||""}</td>
      <td class="tbl-num">${fmt(r.pagerank, 6)}</td>
      <td class="tbl-num">${fmt(r.pagerank_norm)}</td>
      <td class="tbl-num">${fmt(r[c_ins], 4)}</td>
      <td class="tbl-num">${fmt(r.in_strength_norm, 3)}</td>
      <td class="tbl-num">${fmt(r[c_out], 4)}</td>
      <td class="tbl-num">${fmt(r.out_strength_norm, 3)}</td>
      <td class="tbl-num">${fmt(r[c_cont], 4)}</td>
      <td class="tbl-num">${fmt(r[c_dep],  4)}</td>
      <td class="tbl-quad">${dot(qC)}${qC||"—"}</td>
      <td class="tbl-quad">${dot(qD)}${qD||"—"}</td>
    </tr>`;
  }).join("");

  document.getElementById("tbl-sub").textContent =
    `Sorted by raw PageRank · ${year} · metrics shown: ${scale==="norm"?"normalised":"raw"} · quadrants use globally normalised values`;
}

// ── View routing ──────────────────────────────────────────────────────────

// Controls shown per view:
//   Rankings:    Year ✓  Proxy ✗  Scale ✓
//   Correlation: Year ✗  Proxy ✓  Scale ✗  (Spearman is rank-invariant)
//   Quadrant:    Year ✓  Proxy ✓  Scale ✗  (always globally norm. norm)
//   Table:       Year ✓  Proxy ✗  Scale ✓

const CTRL_VISIBILITY = {
  rankings:    {year:true,  proxy:false, centrality:false, scale:true },
  quadrant:    {year:true,  proxy:true,  centrality:true,  scale:false},
  correlation: {year:false, proxy:false, centrality:false, scale:false},
  table:       {year:true,  proxy:false, centrality:false, scale:true },
};

function showView(v) {
  document.querySelectorAll(".view").forEach((el)=>el.classList.remove("active"));
  document.getElementById(`view-${v}`).classList.add("active");
  currentView = v;
  const vis = CTRL_VISIBILITY[v];
  document.getElementById("ctrl-year").style.display       = vis.year       ? "" : "none";
  document.getElementById("ctrl-proxy").style.display      = vis.proxy      ? "" : "none";
  document.getElementById("ctrl-centrality").style.display = vis.centrality ? "" : "none";
  document.getElementById("ctrl-scale").style.display      = vis.scale      ? "" : "none";
  // "Average" year option only available in views that support it
  const vis2 = CTRL_VISIBILITY[v];
  const avgAllowed = v === "rankings" || (vis2 && vis2.avgOk);
  const optAvg = document.getElementById("opt-avg");
  if (optAvg) optAvg.style.display = avgAllowed ? "" : "none";
  // Reset to 2021 when switching to a view that doesn't support avg
  if (!avgAllowed && currentYear === "avg") {
    currentYear = 2021;
    document.getElementById("year-sel").value = "2021";
  }
}

function switchView(v, btn) {
  document.querySelectorAll("nav button").forEach((b)=>b.classList.remove("active"));
  btn.classList.add("active");
  showView(v);
  if (dataReady) renderAll();
}

function onYearChange() {
  const v = document.getElementById("year-sel").value;
  currentYear = v === "avg" ? "avg" : parseInt(v, 10);
  if (dataReady) renderAll();
}

function setProxy(p) {
  proxy = p;
  document.getElementById("pill-contribution").classList.toggle("active", p==="contribution");
  document.getElementById("pill-depth").classList.toggle("active", p==="depth");
  if (dataReady) renderAll();
}

function setScale(s) {
  scale = s;
  document.getElementById("pill-raw").classList.toggle("active",  s==="raw");
  document.getElementById("pill-norm").classList.toggle("active", s==="norm");
  if (dataReady) renderAll();
}

function setCentrality(c) {
  centrality = c;
  ["pagerank","betweenness","in_strength","out_strength"].forEach((id) =>
    document.getElementById(`pill-${id}`).classList.toggle("active", id===c)
  );
  if (dataReady) renderAll();
}

function renderAll() {
  renderKPIs(currentYear);
  if (currentView==="rankings")    renderBars(currentYear);
  if (currentView==="quadrant")    renderQuadrant(currentYear, proxy);
  if (currentView==="correlation") renderCorrelations();
  if (currentView==="table")       renderTable(currentYear);
}

window.switchView    = switchView;
window.onYearChange  = onYearChange;
window.setProxy      = setProxy;
window.setScale      = setScale;
window.setCentrality = setCentrality;
window.allData       = allData;

loadAll();

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
let scale       = "raw";          // "raw" | "norm"
let currentYear = 2021;
let allData     = {};
let corrData    = {};
let charts      = {};
let dataReady   = false;
let currentView = "rankings";

function sectorName(icio) { return SECTOR_NAMES[icio] || icio; }

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

function computeCorrelations() {
  // Spearman is rank-based: invariant to monotone transforms such as
  // min-max normalization. Raw and normalised inputs yield identical r.
  corrData = {contribution:[], depth:[]};
  YEARS.forEach((y) => {
    const rows = allData[y] || [];
    corrData.contribution.push({year:y,
      ...spearman(rows.map((r)=>r.pagerank), rows.map((r)=>r.dig_contribution))});
    corrData.depth.push({year:y,
      ...spearman(rows.map((r)=>r.pagerank), rows.map((r)=>r.dig_depth))});
  });
}

// Threshold is 0 because _norm columns are z-scores: 0 = global mean.
function assignQ(pr, dig) {
  if (pr >= 0 && dig >= 0) return "HH";
  if (pr >= 0 && dig <  0) return "HL";
  if (pr <  0 && dig >= 0) return "LH";
  return "LL";
}

const Q_COL = {HH:"#1D9E75", HL:"#D85A30", LH:"#378ADD", LL:"#BA7517"};
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
      computeCorrelations();
      dataReady = true;
      const withDig = sample.filter((r) => r.dig_contribution_norm != null).length;
      document.getElementById("status").style.display = "none";
      document.getElementById("load-msg").textContent =
        `${sample.length} sectors · ${withDig} with digitalisation data`;
      showView("rankings");
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

    computeCorrelations();
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
    const withC = rows.filter((r) => r.dig_contribution != null);
    const withD = rows.filter((r) => r.dig_depth != null);
    const topC  = withC.length ? withC.reduce((a,b) => b.dig_contribution > a.dig_contribution ? b : a) : null;
    const topD  = withD.length ? withD.reduce((a,b) => b.dig_depth > a.dig_depth ? b : a) : null;
    el.innerHTML = `
      <div class="kpi-card"><div class="kpi-value">${rows.length}</div><div class="kpi-label">Sectors in panel</div></div>
      <div class="kpi-card"><div class="kpi-value">${withC.length}</div><div class="kpi-label">With contribution data</div></div>
      <div class="kpi-card"><div class="kpi-value">${withD.length}</div><div class="kpi-label">With depth data</div></div>
      <div class="kpi-card"><div class="kpi-value kpi-code">${topC?.icio_code||"—"}</div><div class="kpi-label">Top contribution — ${topC?.sector_name||""}</div></div>
      <div class="kpi-card"><div class="kpi-value kpi-code">${topD?.icio_code||"—"}</div><div class="kpi-label">Top depth — ${topD?.sector_name||""}</div></div>`;

  } else if (currentView === "correlation") {
    const cy = corrData.contribution.find((d)=>d.year===year) || {};
    const dy = corrData.depth.find((d)=>d.year===year) || {};
    const arrow = (r) => isNaN(r) ? "" : r>0.05 ? " ↑" : r<-0.05 ? " ↓" : " →";
    // Critical |r| ≈ 0.30 for n=44 at α=0.05 (two-tailed, Fisher z-test)
    const sig = (r,n) => {
      if (isNaN(r)||n==null) return "";
      const crit = 0.3; // approximate for n≈44
      return Math.abs(r) >= crit ? " ✓" : " (n.s.)";
    };
    el.innerHTML = `
      <div class="kpi-card"><div class="kpi-value">${fmt(cy.r)}${arrow(cy.r)}${sig(cy.r,cy.n)}</div><div class="kpi-label">r — contribution vs PageRank (${year})</div></div>
      <div class="kpi-card"><div class="kpi-value">${fmt(dy.r)}${arrow(dy.r)}${sig(dy.r,dy.n)}</div><div class="kpi-label">r — depth vs PageRank (${year})</div></div>
      <div class="kpi-card"><div class="kpi-value">[${fmt(cy.lo)}, ${fmt(cy.hi)}]</div><div class="kpi-label">95% CI — contribution</div></div>
      <div class="kpi-card"><div class="kpi-value">[${fmt(dy.lo)}, ${fmt(dy.hi)}]</div><div class="kpi-label">95% CI — depth</div></div>
      <div class="kpi-card"><div class="kpi-value">${cy.n??""} / ${dy.n??""}</div><div class="kpi-label">n (contribution / depth)</div></div>`;

  } else if (currentView === "quadrant") {
    const qc = proxy==="contribution" ? "dig_contribution_norm" : "dig_depth_norm";
    const valid = rows.filter((r) => r.pagerank_norm!=null && r[qc]!=null);
    const counts = {HH:0, HL:0, LH:0, LL:0};
    valid.forEach((r) => { counts[assignQ(r.pagerank_norm, r[qc])]++; });
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
    [[mx,top,right-mx,my-top,"#1D9E7512"],[left,top,mx-left,my-top,"#D85A3012"],
     [mx,my,right-mx,bottom-my,"#378ADD12"],[left,my,mx-left,bottom-my,"#BA751712"]]
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
        const lbl = ds.data[i]?.label;
        if (!lbl) return;
        ctx.save(); ctx.font="8px monospace"; ctx.fillStyle="rgba(15,27,45,0.62)";
        ctx.fillText(lbl, pt.x+5, pt.y-4); ctx.restore();
      });
    });
  }
});

// ── Render: bar charts ────────────────────────────────────────────────────

function renderBars(year) {
  const rows = allData[year] || [];
  [
    ["contribution","dig_contribution","Digital contribution","#185FA5"],
    ["depth",       "dig_depth",       "Digital depth",       "#1D9E75"]
  ].forEach(([p, metric, baseLabel, color]) => {
    destroyChart(`bar-${p}`);
    const c = col(metric);
    const lbl = colLabel(metric);
    const valid = rows.filter((r) => r[c] != null && !isNaN(r[c]));
    // Sort descending: highest at top of horizontal bar chart
    const top10 = [...valid].sort((a,b) => b[c]-a[c]).slice(0,10);

    charts[`bar-${p}`] = new Chart(document.getElementById(`bar-${p}`).getContext("2d"), {
      type: "bar",
      data: {
        labels: top10.map((r) => r.icio_code),
        datasets: [{
          label: lbl,
          data: top10.map((r) => +Number(r[c]).toFixed(4)),
          backgroundColor: `${color}44`, borderColor: color, borderWidth: 1.5, borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: {
          legend: {display: false},
          title: {
            display: true, text: lbl,
            font: {size:13, family:"DM Sans", weight:"500"},
            color: "#0F1B2D", padding: {bottom:12}
          },
          tooltip: {
            callbacks: {
              title: (items) => sectorName(top10[items[0].dataIndex]?.icio_code),
              label: (c) => `${lbl}: ${c.raw.toFixed(4)}`
            }
          }
        },
        scales: {
          x: {grid:{color:"#EAE8E0"}, ticks:{font:{size:11}}},
          y: {grid:{display:false}, ticks:{font:{size:11, family:"monospace"}}}
        }
      }
    });
  });
  document.getElementById("bar-sub").textContent =
    `${scale==="norm"?"Normalised (0–1 within year)":"Unscaled raw"} values · ${year} · top 10 by each proxy`;
}

// ── Render: correlation charts ────────────────────────────────────────────

function renderCorrelations() {
  [["contribution","Digital contribution"],["depth","Digital depth"]].forEach(([p,baseLabel]) => {
    destroyChart(`corr-${p}`);
    const data   = corrData[p] || [];
    const years  = data.map((d)=>d.year);
    const rs     = data.map((d)=>isNaN(d.r)  ? null : +d.r.toFixed(3));
    const los    = data.map((d)=>isNaN(d.lo) ? null : +d.lo.toFixed(3));
    const his    = data.map((d)=>isNaN(d.hi) ? null : +d.hi.toFixed(3));
    const isActive   = p===proxy;
    const lineColor  = isActive ? "#185FA5" : "#CCCCCC";
    const fillColor  = isActive ? "#185FA520" : "#CCCCCC18";

    charts[`corr-${p}`] = new Chart(document.getElementById(`corr-${p}`).getContext("2d"), {
      type: "line",
      data: {
        labels: years,
        datasets: [
          {label:"CI upper", data:his, borderColor:"transparent", backgroundColor:fillColor, pointRadius:0, fill:"+1", tension:0.3, order:3},
          {label:"CI lower", data:los, borderColor:"transparent", backgroundColor:fillColor, pointRadius:0, fill:false, tension:0.3, order:4},
          {label:"Spearman r", data:rs, borderColor:lineColor, backgroundColor:lineColor, pointRadius:5, pointHoverRadius:7, borderWidth:2, tension:0.3, fill:false, order:1}
        ]
      },
      options: {
        _showZero: true,
        responsive: true,
        plugins: {
          legend: {display:false},
          title: {
            display: true, text: `PageRank vs ${baseLabel}`,
            font: {size:13, family:"DM Sans", weight: isActive?"600":"400"},
            color: isActive?"#0F1B2D":"#AAAAAA", padding:{bottom:12}
          },
          tooltip: {
            filter: (item) => item.datasetIndex===2,
            callbacks: {
              label: (c) => {
                const i = c.dataIndex;
                const sig = Math.abs(rs[i]) >= 0.30 ? " ✓ sig." : " n.s.";
                return [`r = ${rs[i]}${sig}`, `95% CI [${los[i]}, ${his[i]}]`, `n = ${data[i].n}`];
              }
            }
          }
        },
        scales: {
          x: {grid:{color:"#EAE8E0"}, ticks:{font:{size:11}}},
          y: {min:-1, max:1, grid:{color:"#EAE8E0"}, ticks:{font:{size:11}, stepSize:0.5}}
        }
      }
    });
  });
}

// ── Render: quadrant scatter ──────────────────────────────────────────────

function renderQuadrant(year, p) {
  // _norm columns are global z-scores (mean=0, std=1 across all 6 years ×
  // 49 sectors). Threshold = 0 means above/below the global mean, which is
  // a natural and year-comparable split.
  const qc  = p==="contribution" ? "dig_contribution_norm" : "dig_depth_norm";
  const lbl = p==="contribution" ? "Digital contribution (z-score)"
                                 : "Digital depth (z-score)";
  const rows = (allData[year]||[]).filter((r)=>r.pagerank_norm!=null && r[qc]!=null);
  destroyChart("quad-chart");

  const datasets = ["HH","HL","LH","LL"].map((q) => ({
    label: Q_LABEL[q],
    data: rows.filter((r)=>assignQ(r.pagerank_norm, r[qc])===q)
      .map((r) => ({x:+r[qc].toFixed(4), y:+r.pagerank_norm.toFixed(4), label:r.icio_code, name:r.sector_name})),
    backgroundColor:`${Q_COL[q]}BB`, borderColor:Q_COL[q],
    borderWidth:1, pointRadius:7, pointHoverRadius:9
  }));

  charts["quad-chart"] = new Chart(document.getElementById("quad-chart").getContext("2d"), {
    type:"scatter", data:{datasets},
    options: {
      _isQuad: true, responsive: true,
      plugins: {
        legend: {display:false},
        tooltip: {
          callbacks: {
            title: (items) => items[0].raw.name||items[0].raw.label,
            label: (c) => [`Code: ${c.raw.label}`, `Digital (norm.): ${c.raw.x}`, `PageRank (norm.): ${c.raw.y}`]
          }
        }
      },
      scales: {
        x: {title:{display:true, text:lbl, font:{size:12}, color:"#5F5E5A"}, grid:{color:"#EAE8E018"}, ticks:{font:{size:11}}},
        y: {title:{display:true, text:"PageRank (z-score)", font:{size:12}, color:"#5F5E5A"}, grid:{color:"#EAE8E018"}, ticks:{font:{size:11}}}
      }
    }
  });

  document.getElementById("quad-sub").textContent =
    `Fixed 0.5 threshold · ${year} · ${lbl} · hover for details`;
}

// ── Render: sector data table ─────────────────────────────────────────────

function renderTable(year) {
  const rows  = (allData[year]||[]).slice().sort((a,b)=>(b.pagerank??-Infinity)-(a.pagerank??-Infinity));
  const tbody = document.getElementById("tbl-body");
  if (!tbody) return;

  const c_cont = col("dig_contribution");
  const c_dep  = col("dig_depth");
  const c_pr   = col("pagerank");

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
      <td class="tbl-num">${fmt(r[c_cont], 4)}</td>
      <td class="tbl-num">${fmt(r[c_dep],  4)}</td>
      <td class="tbl-quad">${dot(qC)}${qC||"—"}</td>
      <td class="tbl-quad">${dot(qD)}${qD||"—"}</td>
    </tr>`;
  }).join("");

  document.getElementById("tbl-sub").textContent =
    `Sorted by raw PageRank · ${year} · metrics shown: ${scale==="norm"?"normalised (globally norm.)":"raw"} · quadrants always use globally norm. norm`;
}

// ── View routing ──────────────────────────────────────────────────────────

// Controls shown per view:
//   Rankings:    Year ✓  Proxy ✗  Scale ✓
//   Correlation: Year ✗  Proxy ✓  Scale ✗  (Spearman is rank-invariant)
//   Quadrant:    Year ✓  Proxy ✓  Scale ✗  (always globally norm. norm)
//   Table:       Year ✓  Proxy ✗  Scale ✓

const CTRL_VISIBILITY = {
  rankings:    {year:true,  proxy:false, scale:true },
  correlation: {year:false, proxy:true,  scale:false},
  quadrant:    {year:true,  proxy:true,  scale:false},
  table:       {year:true,  proxy:false, scale:true }
};

function showView(v) {
  document.querySelectorAll(".view").forEach((el)=>el.classList.remove("active"));
  document.getElementById(`view-${v}`).classList.add("active");
  currentView = v;
  const vis = CTRL_VISIBILITY[v];
  document.getElementById("ctrl-year").style.display  = vis.year  ? "" : "none";
  document.getElementById("ctrl-proxy").style.display = vis.proxy ? "" : "none";
  document.getElementById("ctrl-scale").style.display = vis.scale ? "" : "none";
}

function switchView(v, btn) {
  document.querySelectorAll("nav button").forEach((b)=>b.classList.remove("active"));
  btn.classList.add("active");
  showView(v);
  if (dataReady) renderAll();
}

function onYearChange() {
  currentYear = parseInt(document.getElementById("year-sel").value, 10);
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

function renderAll() {
  renderKPIs(currentYear);
  if (currentView==="rankings")    renderBars(currentYear);
  if (currentView==="correlation") renderCorrelations();
  if (currentView==="quadrant")    renderQuadrant(currentYear, proxy);
  if (currentView==="table")       renderTable(currentYear);
}

window.switchView   = switchView;
window.onYearChange = onYearChange;
window.setProxy     = setProxy;
window.setScale     = setScale;
window.allData      = allData;
window.corrData     = corrData;

loadAll();

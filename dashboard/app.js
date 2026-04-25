// ICIO-to-NACE crosswalk aligned with Src/utils/constants.py
const ICIO_TO_NACE = {
  "A01": "A",
  "A02": "A",
  "A03": "A",
  "B05": "B",
  "B06": "B",
  "B07": "B",
  "B08": "B",
  "B09": "B",
  "C10T12": "C10-C12",
  "C13T15": "C13-C15",
  "C16": "C16-C18",
  "C17_18": "C16-C18",
  "C19": "C19",
  "C20": "C20",
  "C21": "C21",
  "C22": "C22-C23",
  "C23": "C22-C23",
  "C24A": "C24-C25",
  "C24B": "C24-C25",
  "C25": "C24-C25",
  "C26": "C26",
  "C27": "C27",
  "C28": "C28",
  "C29": "C29-C30",
  "C301": "C29-C30",
  "C302T309": "C29-C30",
  "C31T33": "C31-C33",
  "D": "D",
  "E": "E",
  "F": "F",
  "G": "G",
  "H49": "H49",
  "H50": "H50",
  "H51": "H51",
  "H52": "H52",
  "H53": "H53",
  "I": "I",
  "J58T60": "J58-J60",
  "J61": "J61",
  "J62_63": "J62-J63",
  "K": "K",
  "L": "L",
  "M": "M",
  "N": "N",
  "O": "O",
  "P": "P",
  "Q": "Q",
  "R": "R",
  "S": "S"
};

const YEARS = [2016, 2017, 2018, 2019, 2020, 2021];
const DATA_ROOT_CANDIDATES = ["../data/processed", "data/processed", "/data/processed"];

let proxy = "ict";
let currentYear = 2021;
let allData = {};
let corrData = {};
let charts = {};
let dataReady = false;
let currentView = "rankings";

function loadCSV(path) {
  return new Promise((resolve, reject) => {
    Papa.parse(path, {
      download: true,
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (result) => resolve(result.data),
      error: () => reject(new Error(`Failed: ${path}`))
    });
  });
}

async function loadCSVFromCandidates(fileName) {
  let lastError = null;

  for (const root of DATA_ROOT_CANDIDATES) {
    const path = `${root}/${fileName}`;
    try {
      const rows = await loadCSV(path);
      if (Array.isArray(rows) && rows.length > 0) {
        return rows;
      }
      lastError = new Error(`Empty CSV: ${path}`);
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error(`Failed to load ${fileName}`);
}

function mergeYear(cent, dig) {
  const digByNace = {};
  dig.forEach((d) => {
    if (d.nace_r2_code) {
      digByNace[String(d.nace_r2_code).trim()] = d;
    }
  });

  return cent
    .map((c) => {
      const icio = String(c.icio_code || "").trim();
      const nace = ICIO_TO_NACE[icio] || null;
      const d = nace ? (digByNace[nace] || {}) : {};
      return {
        icio_code: icio,
        nace_r2_code: nace,
        pagerank_norm: c.pagerank_norm ?? null,
        pagerank: c.pagerank ?? null,
        ict_share: d.ict_share ?? null,
        ict_share_norm: d.ict_share_norm ?? null,
        dig_intensity: d.dig_intensity ?? null,
        dig_intensity_norm: d.dig_intensity_norm ?? null
      };
    })
    .filter((r) => r.icio_code);
}

function spearman(xs, ys) {
  const pairs = xs
    .map((x, i) => ({ x, y: ys[i] }))
    .filter((p) => p.x != null && p.y != null && !isNaN(p.x) && !isNaN(p.y));

  const n = pairs.length;
  if (n < 4) {
    return { r: NaN, lo: NaN, hi: NaN, n };
  }

  const rankArr = (arr) => {
    const sorted = [...arr].map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v);
    const ranks = new Array(n);
    sorted.forEach((item, rankIndex) => {
      ranks[item.i] = rankIndex + 1;
    });
    return ranks;
  };

  const px = pairs.map((p) => p.x);
  const py = pairs.map((p) => p.y);
  const rx = rankArr(px);
  const ry = rankArr(py);

  const mx = rx.reduce((a, b) => a + b, 0) / n;
  const my = ry.reduce((a, b) => a + b, 0) / n;

  let num = 0;
  let dx2 = 0;
  let dy2 = 0;

  for (let i = 0; i < n; i += 1) {
    num += (rx[i] - mx) * (ry[i] - my);
    dx2 += (rx[i] - mx) ** 2;
    dy2 += (ry[i] - my) ** 2;
  }

  const r = num / Math.sqrt(dx2 * dy2);
  const zr = Math.atanh(Math.max(-0.9999, Math.min(0.9999, r)));
  const se = 1 / Math.sqrt(n - 3);

  return {
    r,
    lo: Math.tanh(zr - 1.96 * se),
    hi: Math.tanh(zr + 1.96 * se),
    n
  };
}

function computeCorrelations() {
  corrData = { ict: [], dig: [] };
  YEARS.forEach((y) => {
    const rows = allData[y] || [];
    const ci = spearman(
      rows.map((r) => r.pagerank_norm),
      rows.map((r) => r.ict_share_norm)
    );
    const cd = spearman(
      rows.map((r) => r.pagerank_norm),
      rows.map((r) => r.dig_intensity_norm)
    );
    corrData.ict.push({ year: y, ...ci });
    corrData.dig.push({ year: y, ...cd });
  });
}

function assignQ(pr, dig) {
  if (pr >= 0.5 && dig >= 0.5) {
    return "HH";
  }
  if (pr >= 0.5 && dig < 0.5) {
    return "HL";
  }
  if (pr < 0.5 && dig >= 0.5) {
    return "LH";
  }
  return "LL";
}

const Q_COL = { HH: "#1D9E75", HL: "#D85A30", LH: "#378ADD", LL: "#BA7517" };

async function loadAll() {
  try {
    if (window.DASHBOARD_BUNDLE && typeof window.DASHBOARD_BUNDLE === "object") {
      allData = Object.fromEntries(
        Object.entries(window.DASHBOARD_BUNDLE).map(([year, rows]) => [Number(year), rows])
      );

      const sample = allData[2021] || [];
      const withDig = sample.filter((r) => r.ict_share_norm != null).length;
      if (sample.length === 0) {
        throw new Error("Bundled data is empty.");
      }

      computeCorrelations();
      dataReady = true;
      document.getElementById("status").style.display = "none";
      document.getElementById("load-msg").textContent =
        `${sample.length} sectors - ${withDig} with digitalisation data (offline bundle)`;
      showView("rankings");
      renderAll();
      return;
    }

    await Promise.all(
      YEARS.map(async (y) => {
        const [cent, dig] = await Promise.all([
          loadCSVFromCandidates(`centrality_${y}.csv`),
          loadCSVFromCandidates(`digitalisation_${y}.csv`)
        ]);
        allData[y] = mergeYear(cent, dig);
      })
    );

    const sample = allData[2021] || [];
    const withDig = sample.filter((r) => r.ict_share_norm != null).length;

    if (sample.length === 0) {
      throw new Error("Merge produced 0 rows - check ICIO codes in centrality CSVs.");
    }

    if (withDig === 0) {
      const icios = [...new Set(sample.slice(0, 8).map((r) => r.icio_code))].join(", ");
      const naces = [...new Set((allData[2021] || []).slice(0, 8).map((r) => r.nace_r2_code))].join(", ");
      throw new Error(
        `Centrality loaded (${sample.length} rows) but no digitalisation values matched.\n` +
          `Sample ICIO codes: ${icios}\n` +
          `Mapped NACE codes: ${naces}\n\n` +
          "Check that the nace_r2_code values in your digitalisation CSVs match the crosswalk keys above.\n" +
          "Open the console and run: allData[2021].slice(0,5) to inspect the merged rows."
      );
    }

    computeCorrelations();
    dataReady = true;
    document.getElementById("status").style.display = "none";
    document.getElementById("load-msg").textContent = `${sample.length} sectors - ${withDig} with digitalisation data`;
    showView("rankings");
    renderAll();
  } catch (e) {
    document.getElementById("status").textContent =
      `Error:\n${e.message}\n\n` +
      "Start a web server from project root (python -m http.server 8000) and open /dashboard/index.html.";
    document.getElementById("status").className = "error";
    document.getElementById("load-msg").textContent = "Error";
    console.error(e);
    window.allData = allData;
  }
}

function destroyChart(id) {
  if (charts[id]) {
    charts[id].destroy();
    delete charts[id];
  }
}

Chart.register({
  id: "zeroline",
  afterDraw(chart) {
    if (!chart.options._showZero) {
      return;
    }
    const { ctx, chartArea, scales } = chart;
    if (!scales.y) {
      return;
    }
    const y0 = scales.y.getPixelForValue(0);
    if (y0 < chartArea.top || y0 > chartArea.bottom) {
      return;
    }
    ctx.save();
    ctx.strokeStyle = "rgba(80,80,80,0.35)";
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(chartArea.left, y0);
    ctx.lineTo(chartArea.right, y0);
    ctx.stroke();
    ctx.restore();
  }
});

Chart.register({
  id: "quadBg",
  beforeDraw(chart) {
    if (!chart.options._isQuad) {
      return;
    }

    const { ctx, chartArea, scales } = chart;
    if (!scales.x || !scales.y) {
      return;
    }

    const mx = scales.x.getPixelForValue(0.5);
    const my = scales.y.getPixelForValue(0.5);
    const { left, right, top, bottom } = chartArea;

    [
      [mx, top, right - mx, my - top, "#1D9E7510"],
      [left, top, mx - left, my - top, "#D85A3010"],
      [mx, my, right - mx, bottom - my, "#378ADD10"],
      [left, my, mx - left, bottom - my, "#BA751710"]
    ].forEach(([x, y, w, h, c]) => {
      ctx.save();
      ctx.fillStyle = c;
      ctx.fillRect(x, y, w, h);
      ctx.restore();
    });

    ctx.save();
    ctx.strokeStyle = "rgba(80,80,80,0.25)";
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 4]);
    ctx.beginPath();
    ctx.moveTo(mx, top);
    ctx.lineTo(mx, bottom);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(left, my);
    ctx.lineTo(right, my);
    ctx.stroke();
    ctx.restore();

    ctx.save();
    ctx.font = "11px DM Sans,sans-serif";
    ctx.fillStyle = "rgba(80,80,80,0.45)";
    ctx.fillText("HH", mx + 6, top + 16);
    ctx.fillText("HL", left + 6, top + 16);
    ctx.fillText("LH", mx + 6, bottom - 6);
    ctx.fillText("LL", left + 6, bottom - 6);
    ctx.restore();
  }
});

Chart.register({
  id: "sectorLabels",
  afterDatasetsDraw(chart) {
    if (!chart.options._isQuad) {
      return;
    }
    const { ctx } = chart;
    chart.data.datasets.forEach((ds, di) => {
      chart.getDatasetMeta(di).data.forEach((pt, i) => {
        const lbl = ds.data[i]?.label;
        if (!lbl) {
          return;
        }
        ctx.save();
        ctx.font = "8px monospace";
        ctx.fillStyle = "rgba(15,27,45,0.7)";
        ctx.fillText(lbl, pt.x + 5, pt.y - 4);
        ctx.restore();
      });
    });
  }
});

function renderBars(year) {
  const rows = allData[year] || [];
  [
    ["ict", "ict_share", "ICT capital share"],
    ["dig", "dig_intensity", "Digital intensity"]
  ].forEach(([p, col, lbl]) => {
    destroyChart(`bar-${p}`);
    const valid = rows.filter((r) => r[col] != null && !isNaN(r[col]));
    const top10 = [...valid]
      .sort((a, b) => b[col] - a[col])
      .slice(0, 10)
      .reverse();

    charts[`bar-${p}`] = new Chart(document.getElementById(`bar-${p}`).getContext("2d"), {
      type: "bar",
      data: {
        labels: top10.map((r) => r.icio_code),
        datasets: [
          {
            label: lbl,
            data: top10.map((r) => +r[col].toFixed(4)),
            backgroundColor: "#185FA560",
            borderColor: "#185FA5",
            borderWidth: 1,
            borderRadius: 3
          }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: lbl,
            font: { size: 13, family: "DM Sans" },
            color: "#0F1B2D",
            padding: { bottom: 12 }
          },
          tooltip: {
            callbacks: {
              label: (c) => `${c.raw.toFixed(4)}`
            }
          }
        },
        scales: {
          x: { grid: { color: "#EAE8E0" }, ticks: { font: { size: 11 } } },
          y: { grid: { display: false }, ticks: { font: { size: 11, family: "monospace" } } }
        }
      }
    });
  });

  document.getElementById("bar-sub").textContent = `Unscaled raw values - year ${year} - top 10 sectors by each proxy`;
}

function renderCorrelations() {
  [["ict", "ICT capital share"], ["dig", "Digital intensity"]].forEach(([p, lbl]) => {
    destroyChart(`corr-${p}`);
    const data = corrData[p] || [];
    const years = data.map((d) => d.year);
    const rs = data.map((d) => (isNaN(d.r) ? null : +d.r.toFixed(3)));
    const los = data.map((d) => (isNaN(d.lo) ? null : +d.lo.toFixed(3)));
    const his = data.map((d) => (isNaN(d.hi) ? null : +d.hi.toFixed(3)));

    charts[`corr-${p}`] = new Chart(document.getElementById(`corr-${p}`).getContext("2d"), {
      type: "line",
      data: {
        labels: years,
        datasets: [
          {
            label: "CI upper",
            data: his,
            borderColor: "transparent",
            backgroundColor: "#185FA520",
            pointRadius: 0,
            fill: "+1",
            tension: 0.3,
            order: 3
          },
          {
            label: "CI lower",
            data: los,
            borderColor: "transparent",
            backgroundColor: "#185FA520",
            pointRadius: 0,
            fill: false,
            tension: 0.3,
            order: 4
          },
          {
            label: "Spearman r",
            data: rs,
            borderColor: "#185FA5",
            backgroundColor: "#185FA5",
            pointRadius: 5,
            pointHoverRadius: 7,
            borderWidth: 2,
            tension: 0.3,
            fill: false,
            order: 1
          }
        ]
      },
      options: {
        _showZero: true,
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: `PageRank vs ${lbl}`,
            font: { size: 13, family: "DM Sans" },
            color: "#0F1B2D",
            padding: { bottom: 12 }
          },
          tooltip: {
            filter: (item) => item.datasetIndex === 2,
            callbacks: {
              label: (c) => {
                const i = c.dataIndex;
                return [`r = ${rs[i]}`, `95% CI [${los[i]}, ${his[i]}]`, `n = ${data[i].n}`];
              }
            }
          }
        },
        scales: {
          x: { grid: { color: "#EAE8E0" }, ticks: { font: { size: 11 } } },
          y: { min: -1, max: 1, grid: { color: "#EAE8E0" }, ticks: { font: { size: 11 }, stepSize: 0.5 } }
        }
      }
    });
  });
}

function renderQuadrant(year, p) {
  const col = p === "ict" ? "ict_share_norm" : "dig_intensity_norm";
  const lbl = p === "ict" ? "ICT capital share (norm.)" : "Digital intensity (norm.)";
  const rows = (allData[year] || []).filter((r) => r.pagerank_norm != null && r[col] != null);

  destroyChart("quad-chart");

  const datasets = ["HH", "HL", "LH", "LL"].map((q) => ({
    label: q,
    data: rows
      .filter((r) => assignQ(r.pagerank_norm, r[col]) === q)
      .map((r) => ({ x: +r[col].toFixed(4), y: +r.pagerank_norm.toFixed(4), label: r.icio_code })),
    backgroundColor: `${Q_COL[q]}BB`,
    borderColor: Q_COL[q],
    borderWidth: 1,
    pointRadius: 6,
    pointHoverRadius: 8
  }));

  charts["quad-chart"] = new Chart(document.getElementById("quad-chart").getContext("2d"), {
    type: "scatter",
    data: { datasets },
    options: {
      _isQuad: true,
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (c) => `${c.raw.label}  |  ${p === "ict" ? "ICT" : "DIG"}: ${c.raw.x}  |  PR: ${c.raw.y}`
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: lbl, font: { size: 12 }, color: "#5F5E5A" },
          min: -0.02,
          max: 1.02,
          grid: { color: "#EAE8E015" },
          ticks: { font: { size: 11 }, stepSize: 0.25 }
        },
        y: {
          title: { display: true, text: "PageRank (norm.)", font: { size: 12 }, color: "#5F5E5A" },
          min: -0.02,
          max: 1.02,
          grid: { color: "#EAE8E015" },
          ticks: { font: { size: 11 }, stepSize: 0.25 }
        }
      }
    }
  });

  document.getElementById("quad-sub").textContent = `Fixed threshold 0.5 - year ${year} - ${lbl}`;
}

function showView(v) {
  document.querySelectorAll(".view").forEach((el) => el.classList.remove("active"));
  document.getElementById(`view-${v}`).classList.add("active");
  currentView = v;

  const yrSel = document.getElementById("year-sel");
  const pg = document.querySelector(".pill-group");
  const pl = document.getElementById("proxy-label");

  yrSel.style.opacity = v === "correlation" ? "0.35" : "1";
  yrSel.style.pointerEvents = v === "correlation" ? "none" : "";
  pg.style.opacity = v === "rankings" ? "0.35" : "1";
  pg.style.pointerEvents = v === "rankings" ? "none" : "";
  pl.style.opacity = v === "rankings" ? "0.35" : "1";
}

function switchView(v, btn) {
  document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  showView(v);
  if (dataReady) {
    renderAll();
  }
}

function onYearChange() {
  currentYear = parseInt(document.getElementById("year-sel").value, 10);
  if (dataReady) {
    renderAll();
  }
}

function setProxy(p) {
  proxy = p;
  document.getElementById("pill-ict").classList.toggle("active", p === "ict");
  document.getElementById("pill-dig").classList.toggle("active", p === "dig");
  if (dataReady) {
    renderAll();
  }
}

function renderAll() {
  if (currentView === "rankings") {
    renderBars(currentYear);
  }
  if (currentView === "correlation") {
    renderCorrelations();
  }
  if (currentView === "quadrant") {
    renderQuadrant(currentYear, proxy);
  }
}

window.switchView = switchView;
window.onYearChange = onYearChange;
window.setProxy = setProxy;
window.allData = allData;
window.corrData = corrData;

loadAll();

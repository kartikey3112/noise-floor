// Draws the Noisefloor report from the JSON embedded in index.html.
// Tables are plain HTML; the two charts use Chart.js. Every chart has a table twin.
"use strict";

const data = JSON.parse(document.getElementById("report-data").textContent);

// ---------- small helpers ----------

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const seriesColor = (index) => css(`--series-${(index % 8) + 1}`);
const pct = (x) => (x == null ? "–" : `${Math.round(x * 100)}%`);
const secs = (x) => (x == null ? "–" : `${x.toFixed(2)} s`);
const fmt = (n) => Number(n).toLocaleString("en");
const shortDate = (iso) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en", { month: "short", day: "numeric", timeZone: "UTC" });

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child == null) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// columns: [{label, value: row => text|Node, num?: true}]
function fillTable(id, columns, rows) {
  const table = document.getElementById(id);
  table.replaceChildren(
    el("thead", {}, el("tr", {}, columns.map((c) => el("th", c.num ? { class: "num", scope: "col" } : { scope: "col" }, c.label)))),
    el("tbody", {}, rows.map((row) =>
      el("tr", {}, columns.map((c) => el("td", c.num ? { class: "num" } : {}, c.value(row)))))),
  );
}

const testCell = (name, colorIndex) =>
  el("span", {},
    colorIndex == null ? null : el("span", { class: "swatch", style: `background:${seriesColor(colorIndex)}` }),
    el("span", { class: "test-name" }, name));

// ---------- header and tiles ----------

function renderSummary() {
  const o = data.overview;
  document.getElementById("meta").textContent =
    `${fmt(o.builds)} builds of ${fmt(o.commits)} commits · ${fmt(o.tests)} tests · ` +
    `${fmt(o.executions)} test executions · simulated ${o.simulated_from} to ${o.simulated_to} · ` +
    `data as of ${o.data_as_of}`;

  const tile = (label, value, sub) =>
    el("div", { class: "tile" }, el("div", { class: "label" }, label), el("div", { class: "value" }, value), el("div", { class: "sub" }, sub));
  document.getElementById("tiles").replaceChildren(
    tile("Flaky tests", fmt(o.flaky_tests), `of ${fmt(o.tests)} tests`),
    tile("Sustained regressions", fmt(o.sustained_regressions), `in ${fmt(o.regressed_tests)} tests`),
    tile("Runtime spikes", fmt(o.runtime_spikes), "short-lived, shown separately"),
    tile("Answer key", `${o.answer_key_matched} of ${o.answer_key_total}`, "demo tests detected as designed"),
  );

  const suiteNames = { unit: "backend unit", api: "API", demo: "demo" };
  const suiteOrder = ["unit", "api", "demo"];
  const rank = (s) => (suiteOrder.includes(s.suite_name) ? suiteOrder.indexOf(s.suite_name) : 99);
  document.getElementById("suite-counts").textContent = [...data.suites]
    .sort((a, b) => rank(a) - rank(b))
    .map((s) => `${fmt(s.tests)} ${suiteNames[s.suite_name] || s.suite_name} tests`)
    .join(", ")
    .replace(/, ([^,]*)$/, " and $1");
}

// ---------- tables ----------

const flakyColor = new Map(data.flaky_series.map((s, i) => [s.test_key, i]));
const slowColor = new Map(data.slow_series.map((s, i) => [s.test_key, i]));

function renderTables() {
  fillTable("flaky-table", [
    { label: "Test", value: (r) => el("span", {}, testCell(r.test_name, flakyColor.get(r.test_key)),
        r.designed_cause ? el("div", { class: "cause" }, `Designed: ${r.designed_cause}`) : null) },
    { label: "Suite", value: (r) => el("span", { class: "tag" }, r.suite_name) },
    { label: "Flip rate (30 d)", num: true, value: (r) => `${pct(r.flip_rate_30d)} (${r.flips_30d}/${r.pairs_30d})` },
    { label: "Fail rate", num: true, value: (r) => `${pct(r.fail_rate)} (${r.fails}/${r.runs})` },
    { label: "Commits with pass and fail", num: true, value: (r) => `${r.divergent_commits} of ${r.commits_run_on}` },
  ], data.flaky);

  const sustained = data.regressions.filter((r) => r.episode_kind === "sustained");
  const spikes = data.regressions.filter((r) => r.episode_kind === "spike");
  const regressionColumns = [
    { label: "Test", value: (r) => testCell(r.test_name, slowColor.get(r.test_key)) },
    { label: "Suite", value: (r) => el("span", { class: "tag" }, r.suite_name) },
    { label: "Started", value: (r) => el("span", {}, `build #${r.onset_build} · `, el("code", {}, r.onset_commit),
        r.subject ? el("div", { class: "cause" }, r.subject) : null) },
    { label: "Normal", num: true, value: (r) => secs(r.baseline_s) },
    { label: "Then", num: true, value: (r) => `${secs(r.onset_s)} (${r.ratio}×)` },
    { label: "Slow runs in a row", num: true, value: (r) => r.flagged_runs },
  ];
  fillTable("sustained-table", regressionColumns, sustained);
  fillTable("spikes-table", regressionColumns, spikes);
  document.getElementById("spikes-summary").textContent =
    `Runtime spikes: ${spikes.length} short-lived slow runs (show)`;

  fillTable("key-table", [
    { label: "Demo test", value: (r) => el("span", { class: "test-name" }, r.test_name) },
    { label: "Designed as", value: (r) => el("span", {}, r.designed_as,
        r.designed_cause ? el("div", { class: "cause" }, r.designed_cause) : null) },
    { label: "Fail rate: designed / observed", num: true, value: (r) =>
        r.designed_as === "slows_down" ? "–" : `${pct(r.designed_fail_rate)} / ${pct(r.observed_fail_rate)}` },
    { label: "Found", value: (r) =>
        r.is_flaky ? `flaky on ${r.divergent_commits} commits`
        : r.has_regressed ? el("span", {}, "slowed down at ", el("code", {}, r.found_commit))
        : "stable" },
    { label: "Match", value: (r) => r.detected_as_designed
        ? el("span", { class: "ok" }, "✓ as designed")
        : el("span", { class: "miss" }, "✗ missed") },
  ], data.answer_key);
}

// ---------- charts ----------

const charts = [];

function baseOptions(yTitle, yFormat) {
  const ink2 = css("--ink-2"), muted = css("--muted"), grid = css("--grid");
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { position: "bottom", labels: { color: ink2, usePointStyle: true, pointStyle: "line", boxWidth: 18 } },
      tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${yFormat(ctx.parsed.y)}` } },
    },
    scales: {
      x: { grid: { color: grid }, border: { color: css("--axis") }, ticks: { color: muted, maxRotation: 0, autoSkipPadding: 14 } },
      y: { grid: { color: grid }, border: { display: false }, ticks: { color: muted, callback: yFormat },
           title: { display: true, text: yTitle, color: muted } },
    },
  };
}

const line = (label, points, color) => ({
  label, data: points, borderColor: color, backgroundColor: color,
  borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, tension: 0, spanGaps: false,
});

// A window with only a pair or two of runs makes a single flip read as 100%, so the chart
// skips those days. The table under it still lists every day.
const MIN_PAIRS_TO_PLOT = 10;

function flipChart() {
  const days = [...new Set(data.flip_trend.map((p) => p.day))].sort();
  const byTest = new Map();
  for (const p of data.flip_trend) {
    if (p.pairs_in_window >= MIN_PAIRS_TO_PLOT) byTest.set(`${p.test_key}|${p.day}`, p.flip_rate);
  }
  const datasets = data.flaky_series.map((s, i) =>
    line(s.test_name, days.map((d) => byTest.get(`${s.test_key}|${d}`) ?? null), seriesColor(i)));
  const options = baseOptions("Flip rate", (v) => `${Math.round(v * 100)}%`);
  options.scales.y.min = 0;
  options.scales.y.max = 1;
  return new Chart(document.getElementById("flip-chart"), {
    type: "line", data: { labels: days.map(shortDate), datasets }, options,
  });
}

// Draws a thin vertical line and the short SHA at the first build of each commit.
const commitMarkers = {
  id: "commitMarkers",
  afterDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    ctx.save();
    ctx.strokeStyle = css("--axis");
    ctx.fillStyle = css("--muted");
    ctx.lineWidth = 1;
    ctx.font = "11px system-ui, sans-serif";
    for (const commit of data.commits) {
      const x = scales.x.getPixelForValue(chart.data.labels.indexOf(`#${commit.first_build}`));
      if (!Number.isFinite(x)) continue;
      ctx.beginPath();
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
      ctx.fillText(commit.short_sha, x + 4, chartArea.top + 11);
    }
    ctx.restore();
  },
};

function durationChart() {
  const builds = [...new Set(data.durations.map((p) => p.build_number))].sort((a, b) => a - b);
  const byTest = new Map();
  for (const p of data.durations) byTest.set(`${p.test_key}|${p.build_number}`, p.duration_s);
  const datasets = data.slow_series.map((s, i) =>
    line(s.test_name, builds.map((b) => byTest.get(`${s.test_key}|${b}`) ?? null), seriesColor(i)));
  const options = baseOptions("Seconds", (v) => `${Number(v).toFixed(1)} s`);
  options.scales.y.min = 0;
  options.layout = { padding: { top: 4 } };
  return new Chart(document.getElementById("duration-chart"), {
    type: "line", data: { labels: builds.map((b) => `#${b}`), datasets }, options, plugins: [commitMarkers],
  });
}

function renderChartTables() {
  const days = [...new Set(data.flip_trend.map((p) => p.day))].sort();
  const flip = new Map(data.flip_trend.map((p) => [`${p.test_key}|${p.day}`, p]));
  const flipCell = (p) => (p ? `${pct(p.flip_rate)} (${p.flips_in_window}/${p.pairs_in_window})` : "–");
  fillTable("flip-table", [
    { label: "Day", value: (d) => d },
    ...data.flaky_series.map((s) => ({ label: s.test_name, num: true, value: (d) => flipCell(flip.get(`${s.test_key}|${d}`)) })),
  ], days);

  const builds = [...new Set(data.durations.map((p) => p.build_number))].sort((a, b) => a - b);
  const dur = new Map(data.durations.map((p) => [`${p.test_key}|${p.build_number}`, p.duration_s]));
  fillTable("duration-table", [
    { label: "Build", value: (b) => `#${b}` },
    ...data.slow_series.map((s) => ({ label: s.test_name, num: true, value: (b) => secs(dur.get(`${s.test_key}|${b}`)) })),
  ], builds);
}

function renderCharts() {
  while (charts.length) charts.pop().destroy();
  if (typeof Chart === "undefined") return; // the tables still show every number
  charts.push(flipChart(), durationChart());
}

// ---------- start ----------

renderSummary();
renderTables();
renderChartTables();
renderCharts();
// Redraw the charts in the other palette when the system theme changes.
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  renderTables();
  renderCharts();
});

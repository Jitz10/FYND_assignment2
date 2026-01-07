const API_BASE = window.location.origin;
const WS_URL = API_BASE.replace(/^http/, "ws") + "/ws/analytics";

const websiteEl = document.getElementById("website");
const productEl = document.getElementById("product");
const classificationEl = document.getElementById("classification");
const apiStatusEl = document.getElementById("api-status");
const wsStatusEl = document.getElementById("ws-status");

const metricTotal = document.getElementById("metric-total");
const metricAvg = document.getElementById("metric-avg");
const metricTopClass = document.getElementById("metric-top-class");
const metricTopSite = document.getElementById("metric-top-site");

const classificationList = document.getElementById("classification-list");
const websiteList = document.getElementById("website-list");
const productList = document.getElementById("product-list");
const latestReviews = document.getElementById("latest-reviews");
const chartClassificationEl = document.getElementById("chart-classification");
const chartWebsiteEl = document.getElementById("chart-website");
const chartProductEl = document.getElementById("chart-product");
const wordCloudEl = document.getElementById("word-cloud");
const insightTextEl = document.getElementById("insight-text");
const insightActionsEl = document.getElementById("insight-actions");
const insightUpdatedEl = document.getElementById("insight-updated");

const CATALOG = {
  "alpha-shop": ["alpha-phone", "alpha-case", "alpha-charge"],
  "beta-store": ["beta-laptop", "beta-mouse", "beta-bag"],
  "gamma-mart": ["gamma-watch", "gamma-band", "gamma-scale"],
};

function populateWebsites() {
  websiteEl.innerHTML = '<option value="">All websites</option>' +
    Object.keys(CATALOG).map((w) => `<option value="${w}">${w}</option>`).join("");
}

function populateProducts(website) {
  const products = website ? (CATALOG[website] || []) : Object.values(CATALOG).flat();
  productEl.innerHTML = '<option value="">All products</option>' +
    products.map((p) => `<option value="${p}">${p}</option>`).join("");
}

function setApiStatus(ok) {
  if (ok) {
    apiStatusEl.textContent = "API: online";
    apiStatusEl.classList.remove("bad");
    apiStatusEl.classList.add("good");
  } else {
    apiStatusEl.textContent = "API: offline";
    apiStatusEl.classList.remove("good");
    apiStatusEl.classList.add("bad");
  }
}

function setWsStatus(text, cls) {
  wsStatusEl.textContent = `WebSocket: ${text}`;
  wsStatusEl.classList.remove("good", "bad", "warn");
  if (cls) wsStatusEl.classList.add(cls);
}

function buildQuery() {
  const params = new URLSearchParams();
  if (websiteEl.value) params.set("website", websiteEl.value);
  if (productEl.value) params.set("product", productEl.value);
  if (classificationEl.value) params.set("classification", classificationEl.value);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function fetchSummary() {
  try {
    const res = await fetch(`${API_BASE}/analytics/summary${buildQuery()}`);
    setApiStatus(res.ok);
    if (!res.ok) throw new Error("Request failed");
    const data = await res.json();
    renderSummary(data);
  } catch (err) {
    console.error(err);
  }
}

async function fetchInsights() {
  try {
    const res = await fetch(`${API_BASE}/analytics/insights${buildQuery()}`);
    if (!res.ok) return;
    const data = await res.json();
    renderInsights(data);
  } catch (err) {
    console.error(err);
  }
}

function renderSummary(data) {
  metricTotal.textContent = data.total_reviews ?? 0;
  metricAvg.textContent = (data.avg_rating ?? 0).toFixed(2);

  const classEntries = Object.entries(data.classification_counts || {});
  classEntries.sort((a, b) => b[1] - a[1]);
  metricTopClass.textContent = classEntries[0]?.[0] || "—";

  renderChart(chartClassificationEl, classEntries.map((c) => c[0]), classEntries.map((c) => c[1]), {
    label: "Classification",
    type: "doughnut",
  });

  classificationList.innerHTML = classEntries
    .map(([name, count]) =>
      `<div class="list-row"><div><div class="list-label">${escapeHtml(name)}</div></div><div class="list-meta">${count}</div></div>`
    )
    .join("") || emptyState("No data");

  const topSite = (data.website_breakdown || [])[0];
  metricTopSite.textContent = topSite ? `${topSite.website} (${topSite.count})` : "—";

  renderChart(
    chartWebsiteEl,
    (data.website_breakdown || []).map((i) => i.website || "(unknown)"),
    (data.website_breakdown || []).map((i) => i.count || 0),
    { label: "Websites", type: "bar", horizontal: true }
  );

  websiteList.innerHTML = (data.website_breakdown || [])
    .map((item) =>
      `<div class="list-row"><div class="list-label">${escapeHtml(item.website || "(unknown)")}</div><div class="list-meta">${item.count} • avg ${Number(item.avg_rating || 0).toFixed(2)}</div></div>`
    )
    .join("") || emptyState("No websites");

  productList.innerHTML = (data.product_breakdown || [])
    .map((item) =>
      `<div class="list-row"><div class="list-label">${escapeHtml(item.product || "(unknown)")}</div><div class="list-meta">${item.count} • avg ${Number(item.avg_rating || 0).toFixed(2)}</div></div>`
    )
    .join("") || emptyState("No products");

  renderChart(
    chartProductEl,
    (data.product_breakdown || []).map((i) => i.product || "(unknown)"),
    (data.product_breakdown || []).map((i) => i.count || 0),
    { label: "Products", type: "bar", horizontal: false }
  );

  latestReviews.innerHTML = (data.latest_reviews || [])
    .map((r) => {
      const created = r.created_at ? new Date(r.created_at).toLocaleString() : "";
      return `<div class="review-card">
        <div class="badges">
          <span class="badge">${escapeHtml(String(r.rating ?? ""))}/5</span>
          <span class="badge">${escapeHtml(r.classification || "")}</span>
        </div>
        <div class="list-label">${escapeHtml(r.website || "")} • ${escapeHtml(r.product || "")}</div>
        <div class="list-meta">${escapeHtml(r.feedback || "")}</div>
        <div class="list-meta">${escapeHtml(created)}</div>
      </div>`;
    })
    .join("") || emptyState("No recent reviews");

  renderWordCloud(data.latest_reviews || []);
  // Refresh insights (cached server-side) alongside summary updates
  fetchInsights();
}

function emptyState(text) {
  return `<div class="list-row"><div class="list-label">${escapeHtml(text)}</div></div>`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function connectWebSocket() {
  try {
    const ws = new WebSocket(WS_URL);
    setWsStatus("connecting", "warn");

    ws.onopen = () => setWsStatus("connected", "good");
    ws.onclose = () => setWsStatus("disconnected", "bad");
    ws.onerror = () => setWsStatus("error", "bad");
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "analytics_snapshot" && msg.summary) {
          // If filters are applied, fetch filtered view; else use snapshot directly.
          if (websiteEl.value || productEl.value || classificationEl.value) {
            fetchSummary();
          } else {
            renderSummary(msg.summary);
          }
        }
      } catch (err) {
        console.error("WS parse error", err);
      }
    };
  } catch (err) {
    console.error("WS error", err);
    setWsStatus("error", "bad");
  }
}

websiteEl.addEventListener("change", (e) => {
  populateProducts(e.target.value);
  fetchSummary();
  fetchInsights();
});

productEl.addEventListener("change", () => {
  fetchSummary();
  fetchInsights();
});
classificationEl.addEventListener("change", () => {
  fetchSummary();
  fetchInsights();
});

populateWebsites();
populateProducts("");
fetchSummary();
fetchInsights();
connectWebSocket();

// Auto-refresh to keep data current without manual clicks
const AUTO_REFRESH_MS = 15000; // 15s
setInterval(fetchSummary, AUTO_REFRESH_MS);
setInterval(fetchInsights, AUTO_REFRESH_MS);

// Simple chart cache to avoid recreating Chart instances
const charts = new Map();

function renderChart(canvas, labels, values, opts = {}) {
  if (!canvas || typeof Chart === "undefined") return;
  const type = opts.type || "bar";
  const ctx = canvas.getContext("2d");
  const existing = charts.get(canvas);
  const colors = [
    "#22d3ee",
    "#4ade80",
    "#fbbf24",
    "#a78bfa",
    "#f87171",
    "#38bdf8",
    "#f472b6",
  ];
  const datasetColor = (i) => colors[i % colors.length];

  const baseDataset = {
    label: opts.label || "",
    data: values,
    backgroundColor: (type === "doughnut" || type === "polarArea")
      ? labels.map((_, i) => datasetColor(i))
      : "rgba(34, 211, 238, 0.6)",
    borderColor: (type === "doughnut" || type === "polarArea")
      ? labels.map((_, i) => datasetColor(i))
      : "rgba(34, 211, 238, 1)",
    borderWidth: type === "line" ? 2 : 1,
    fill: type === "line" ? false : true,
    tension: type === "line" ? 0.35 : 0,
  };

  const datasets = opts.datasets && Array.isArray(opts.datasets) && opts.datasets.length
    ? opts.datasets
    : [baseDataset];

  const config = {
    type,
    data: {
      labels,
      datasets,
    },
    options: {
      plugins: {
        legend: {
          display: opts.showLegend !== undefined
            ? opts.showLegend
            : (["doughnut", "polarArea"].includes(type) || datasets.length > 1),
        },
      },
      scales: ["doughnut", "polarArea"].includes(type) ? {} : {
        x: { beginAtZero: true, ticks: { precision: 0 } },
        y: { beginAtZero: true, ticks: { precision: 0 } },
      },
      responsive: true,
      maintainAspectRatio: false,
    },
  };

  if (opts.horizontal && config.type === "bar") {
    config.options.indexAxis = "y";
  }
  if (existing) {
    existing.config.type = config.type;
    existing.data.labels = labels;
    existing.data.datasets = config.data.datasets;
    existing.options = config.options;
    existing.update();
    return;
  }
  const chart = new Chart(ctx, config);
  charts.set(canvas, chart);
}

function renderWordCloud(reviews) {
  if (!wordCloudEl) return;
  const text = reviews.map((r) => r.feedback || "").join(" ").toLowerCase();
  if (!text.trim()) {
    wordCloudEl.innerHTML = emptyState("No words");
    return;
  }
  const stop = new Set(["the","and","a","to","of","it","is","in","for","on","with","this","that","was","i","we","you","they","at","as","had","have","has","be","are"]);
  const counts = {};
  text.split(/[^a-z0-9']+/).filter(Boolean).forEach((w) => {
    if (w.length < 3 || stop.has(w)) return;
    counts[w] = (counts[w] || 0) + 1;
  });
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 30);
  if (!entries.length) {
    wordCloudEl.innerHTML = emptyState("No words");
    return;
  }
  const max = entries[0][1];
  wordCloudEl.innerHTML = entries
    .map(([word, count]) => {
      const scale = 0.6 + 0.4 * (count / max);
      const size = Math.round(12 + 14 * scale);
      return `<span style="font-size:${size}px">${escapeHtml(word)}</span>`;
    })
    .join(" ");
}

function renderInsights(data) {
  if (!data) return;
  insightTextEl.textContent = data.summary || "—";
  insightUpdatedEl.textContent = data.generated_at ? `Updated ${new Date(data.generated_at).toLocaleString()}` : "—";
  const actions = Array.isArray(data.recommendations) ? data.recommendations : [];
  insightActionsEl.innerHTML = actions.map((a) => `<li>${escapeHtml(String(a))}</li>`).join("") || "<li>—</li>";
}

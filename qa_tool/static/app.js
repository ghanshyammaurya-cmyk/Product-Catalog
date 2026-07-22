const state = {
  summary: null,
  environments: [],
  runs: [],
  testData: { columns: [], rows: [], multiline_columns: [] },
  activeRunId: null,
  logOffset: 0,
  logTimer: null,
  dataEditIndex: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch (_) {}
    throw new Error(message);
  }
  return response.json();
}

function toast(message, type = "") {
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.textContent = message;
  $("#toasts").append(node);
  setTimeout(() => node.remove(), 4500);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function statusClass(status) {
  return ["passed", "failed", "error", "running", "queued", "cancelled"].includes(status)
    ? status : "neutral";
}

function setPage(page) {
  $$(".page").forEach(node => node.classList.toggle("active", node.id === `page-${page}`));
  $$(".nav-item").forEach(node => node.classList.toggle("active", node.dataset.page === page));
  const titles = {
    dashboard: "Automation Dashboard",
    runs: "Test Runs & Reports",
    data: "Excel Test Data",
    environments: "Execution Environments",
  };
  $("#pageTitle").textContent = titles[page] || titles.dashboard;
  $(".sidebar").classList.remove("open");
  if (page === "runs") loadRuns();
  if (page === "data") loadTestData();
  if (page === "environments") loadEnvironments();
}

async function loadSummary() {
  try {
    const summary = await api("/api/summary");
    state.summary = summary;
    $("#metricProducts").textContent = summary.enabled_products;
    $("#metricRuns").textContent = summary.total_runs;
    $("#metricPassed").textContent = summary.passed_runs;
    $("#metricFailed").textContent = summary.failed_runs;
    renderRecentRuns(summary.recent_runs);
    if (summary.active_run) {
      startLogPolling(summary.active_run.id);
    } else if (state.activeRunId) {
      await refreshRun(state.activeRunId);
    }
  } catch (error) {
    toast(`Could not load dashboard: ${error.message}`, "error");
  }
}

function renderRecentRuns(runs) {
  const root = $("#recentRuns");
  if (!runs.length) {
    root.innerHTML = `<p class="muted">No dashboard runs yet. Launch your first automation.</p>`;
    return;
  }
  root.innerHTML = runs.map(run => `
    <div class="run-row">
      <div class="run-name"><strong>${escapeHtml(run.suite.toUpperCase())} · ${escapeHtml(run.environment.toUpperCase())}</strong>
        <span>${escapeHtml(run.test_id || "All enabled tests")} · ${formatDate(run.created_at)}</span></div>
      <span class="status ${statusClass(run.status)}">${escapeHtml(run.status.toUpperCase())}</span>
      <button class="table-action" data-view-run="${escapeHtml(run.id)}">Open</button>
    </div>`).join("");
}

async function loadEnvironments() {
  try {
    const data = await api("/api/environments");
    state.environments = data.environments;
    $("#environmentMini").innerHTML = data.environments.map(env => `
      <div class="environment-mini-row"><div><span class="env-dot ${env.color}"></span><strong>${escapeHtml(env.label)}</strong></div>
      <small>${env.warnings.length ? `${env.warnings.length} warning` : "Configured"}</small></div>`).join("");
    $("#environmentCards").innerHTML = data.environments.map(env => `
      <article class="environment-card">
        <div class="environment-card-head"><h3>${escapeHtml(env.label)}</h3><span class="status ${env.id === "live" ? "passed" : "running"}">${escapeHtml(env.framework_name.toUpperCase())}</span></div>
        <dl><dt>Base URL</dt><dd>${escapeHtml(env.base_url || "Not configured")}</dd>
          <dt>Edge Catalog</dt><dd>${escapeHtml(env.edge_catalog_url || "Not configured")}</dd>
          <dt>Partner Spotlight</dt><dd>${escapeHtml(env.partner_spotlight_url || "Not configured")}</dd></dl>
        ${env.warnings.map(w => `<div class="warning">${escapeHtml(w)}</div>`).join("")}
      </article>`).join("");
  } catch (error) {
    toast(`Could not load environments: ${error.message}`, "error");
  }
}

async function loadRuns() {
  try {
    const data = await api("/api/runs");
    state.runs = data.runs;
    $("#runsTable").innerHTML = data.runs.length ? data.runs.map(run => `
      <tr><td><strong>${escapeHtml(run.id)}</strong>${run.test_id ? `<br><span class="muted">${escapeHtml(run.test_id)}</span>` : ""}</td>
      <td>${escapeHtml(run.environment.toUpperCase())}</td><td>${escapeHtml(run.suite)}</td><td>${escapeHtml(run.browser)}</td>
      <td>${formatDate(run.started_at || run.created_at)}</td>
      <td><span class="status ${statusClass(run.status)}">${escapeHtml(run.status.toUpperCase())}</span></td>
      <td><button class="table-action" data-view-run="${escapeHtml(run.id)}">View</button></td></tr>`).join("")
      : `<tr><td colspan="7" class="muted">No runs yet.</td></tr>`;
    if (data.active) startLogPolling(data.active.id);
  } catch (error) {
    toast(`Could not load runs: ${error.message}`, "error");
  }
}

async function showRun(runId) {
  setPage("runs");
  try {
    const run = await api(`/api/runs/${runId}`);
    $("#runDetail").classList.remove("hidden");
    $("#detailTitle").textContent = `${run.suite.toUpperCase()} · ${run.id}`;
    $("#detailStatus").className = `status ${statusClass(run.status)}`;
    $("#detailStatus").textContent = run.status.toUpperCase();
    $("#detailMeta").innerHTML = [
      ["Environment", run.environment.toUpperCase()],
      ["Browser", run.browser],
      ["Test filter", run.test_id || "All enabled"],
      ["Started", formatDate(run.started_at)],
      ["Finished", formatDate(run.finished_at)],
    ].map(([label, value]) => `<div class="detail-item"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`).join("");
    $("#artifactList").innerHTML = run.artifacts.length ? run.artifacts.map(file =>
      `<a class="artifact" href="${escapeHtml(file.url)}" ${file.viewable ? 'target="_blank"' : 'download'}>⇩ ${escapeHtml(file.name)} <small>${formatBytes(file.size)}</small></a>`
    ).join("") : `<span class="muted">Artifacts become available when execution finishes.</span>`;
    const log = await api(`/api/runs/${runId}/log`);
    $("#detailConsole").textContent = log.content || "No console output available.";
  } catch (error) {
    toast(`Could not open run: ${error.message}`, "error");
  }
}

function openModal(id) { $(`#${id}`).classList.remove("hidden"); }
function closeModal(id) { $(`#${id}`).classList.add("hidden"); }

async function startRun(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    environment: form.get("environment"),
    suite: form.get("suite"),
    browser: form.get("browser"),
    test_id: String(form.get("test_id") || "").trim(),
    slow_mo: Number(form.get("slow_mo") || 500),
    headed: form.get("headed") === "on",
  };
  try {
    const run = await api("/api/runs", { method: "POST", body: JSON.stringify(payload) });
    closeModal("runModal");
    toast(`Run ${run.id} started`, "success");
    state.logOffset = 0;
    $("#liveConsole").textContent = "";
    startLogPolling(run.id);
    setPage("dashboard");
    await loadSummary();
  } catch (error) {
    toast(`Could not start run: ${error.message}`, "error");
  }
}

function startLogPolling(runId) {
  if (state.activeRunId !== runId) {
    state.activeRunId = runId;
    state.logOffset = 0;
    $("#liveConsole").textContent = "";
  }
  clearInterval(state.logTimer);
  pollRun();
  state.logTimer = setInterval(pollRun, 1800);
}

async function pollRun() {
  if (!state.activeRunId) return;
  try {
    const [run, log] = await Promise.all([
      api(`/api/runs/${state.activeRunId}`),
      api(`/api/runs/${state.activeRunId}/log?offset=${state.logOffset}`),
    ]);
    state.logOffset = log.offset;
    if (log.content) {
      const consoleNode = $("#liveConsole");
      consoleNode.textContent += log.content;
      consoleNode.scrollTop = consoleNode.scrollHeight;
    }
    $("#consoleTitle").textContent = `${run.suite.toUpperCase()} · ${run.environment.toUpperCase()} · ${run.id}`;
    $("#consoleStatus").className = `status ${statusClass(run.status)}`;
    $("#consoleStatus").textContent = run.status.toUpperCase();
    $("#cancelRun").classList.toggle("hidden", !["queued", "running"].includes(run.status));
    if (!["queued", "running"].includes(run.status)) {
      clearInterval(state.logTimer);
      state.logTimer = null;
      state.activeRunId = null;
      toast(run.message, run.status === "passed" ? "success" : "error");
      await Promise.all([loadSummary(), loadRuns()]);
    }
  } catch (_) {}
}

async function refreshRun(runId) {
  try {
    const run = await api(`/api/runs/${runId}`);
    if (!["queued", "running"].includes(run.status)) {
      state.activeRunId = null;
      clearInterval(state.logTimer);
    }
  } catch (_) {}
}

async function cancelActiveRun() {
  if (!state.activeRunId || !confirm("Cancel this test run and all Playwright browser processes?")) return;
  try {
    await api(`/api/runs/${state.activeRunId}/cancel`, { method: "POST" });
    toast("Cancellation requested", "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function loadTestData() {
  try {
    state.testData = await api("/api/test-data");
    renderTestData();
  } catch (error) {
    toast(`Could not load test data: ${error.message}`, "error");
  }
}

function filteredRows() {
  const term = $("#dataSearch").value.toLowerCase().trim();
  const enabled = $("#dataEnabledFilter").value;
  return state.testData.rows.map((row, index) => ({ row, index })).filter(({ row }) => {
    const searchable = [row.test_id, row.ticket_number, row.partner_name, row.product_name].join(" ").toLowerCase();
    const termMatch = !term || searchable.includes(term);
    const enabledMatch = enabled === "all" || (enabled === "enabled" ? row.enabled : !row.enabled);
    return termMatch && enabledMatch;
  });
}

function renderTestData() {
  const rows = filteredRows();
  const enabledCount = state.testData.rows.filter(row => row.enabled).length;
  $("#dataSummary").textContent = `${state.testData.rows.length} products · ${enabledCount} enabled`;
  $("#dataTable").innerHTML = rows.length ? rows.map(({ row, index }) => `
    <tr><td><input class="data-toggle" type="checkbox" ${row.enabled ? "checked" : ""} data-toggle-row="${index}" aria-label="Enable ${escapeHtml(row.test_id)}"></td>
    <td><strong>${escapeHtml(row.test_id)}</strong></td><td>${escapeHtml(row.ticket_number)}</td>
    <td>${escapeHtml(row.partner_name)}</td>
    <td class="product-cell"><strong>${escapeHtml(row.product_name)}</strong><span>${escapeHtml(row.search_term)}</span></td>
    <td><span class="status ${row.product_type === "system" ? "cancelled" : "running"}">${escapeHtml(String(row.product_type).toUpperCase())}</span></td>
    <td><button class="table-action" data-edit-row="${index}">Edit</button> <button class="table-action" data-delete-row="${index}">Delete</button></td></tr>`
  ).join("") : `<tr><td colspan="7" class="muted">No matching test data.</td></tr>`;
}

function openDataEditor(index = null) {
  state.dataEditIndex = index;
  const isNew = index === null;
  const row = isNew ? Object.fromEntries(state.testData.columns.map(column => [column, ""])) : state.testData.rows[index];
  if (isNew) {
    row.enabled = true;
    row.validate_pdf = false;
    row.test_id = nextTestId();
  }
  $("#dataModalTitle").textContent = isNew ? "Add product test data" : `Edit ${row.test_id}`;
  const multiline = new Set(state.testData.multiline_columns);
  $("#dataFields").innerHTML = state.testData.columns.map(column => {
    const value = row[column] ?? "";
    const wide = multiline.has(column) ? "wide" : "";
    if (["enabled", "validate_pdf"].includes(column)) {
      return `<label class="${wide}">${escapeHtml(column)}<select name="${escapeHtml(column)}"><option value="true" ${value ? "selected" : ""}>True</option><option value="false" ${!value ? "selected" : ""}>False</option></select></label>`;
    }
    if (column === "product_type") {
      return `<label>${escapeHtml(column)}<select name="${column}"><option value="application" ${value === "application" ? "selected" : ""}>Application</option><option value="system" ${value === "system" ? "selected" : ""}>System</option></select></label>`;
    }
    if (multiline.has(column)) {
      return `<label class="wide">${escapeHtml(column)}<textarea name="${escapeHtml(column)}">${escapeHtml(value)}</textarea></label>`;
    }
    return `<label class="${wide}">${escapeHtml(column)}<input name="${escapeHtml(column)}" value="${escapeHtml(value)}"></label>`;
  }).join("");
  openModal("dataModal");
}

function nextTestId() {
  const numbers = state.testData.rows.map(row => Number(String(row.test_id).replace(/\D/g, ""))).filter(Number.isFinite);
  return `PS-${String((Math.max(0, ...numbers) + 1)).padStart(3, "0")}`;
}

function applyDataRow(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const row = {};
  state.testData.columns.forEach(column => {
    const value = form.get(column);
    row[column] = ["enabled", "validate_pdf"].includes(column) ? value === "true" : String(value ?? "");
  });
  if (state.dataEditIndex === null) state.testData.rows.push(row);
  else state.testData.rows[state.dataEditIndex] = row;
  closeModal("dataModal");
  renderTestData();
  toast("Row updated locally. Click Save changes to write Excel.");
}

async function saveTestData() {
  try {
    const result = await api("/api/test-data", { method: "PUT", body: JSON.stringify({ rows: state.testData.rows }) });
    toast(`${result.message} Backup: ${result.backup}`, "success");
    await loadTestData();
  } catch (error) {
    toast(`Could not save Excel: ${error.message}`, "error");
  }
}

document.addEventListener("click", event => {
  const nav = event.target.closest("[data-page]");
  if (nav) setPage(nav.dataset.page);
  const pageLink = event.target.closest("[data-page-link]");
  if (pageLink) setPage(pageLink.dataset.pageLink);
  if (event.target.closest('[data-action="new-run"]')) openModal("runModal");
  const close = event.target.closest("[data-close]");
  if (close) closeModal(close.dataset.close);
  const viewRun = event.target.closest("[data-view-run]");
  if (viewRun) showRun(viewRun.dataset.viewRun);
  const editRow = event.target.closest("[data-edit-row]");
  if (editRow) openDataEditor(Number(editRow.dataset.editRow));
  const deleteRow = event.target.closest("[data-delete-row]");
  if (deleteRow && confirm("Delete this test-data row? Changes are not written until Save changes.")) {
    state.testData.rows.splice(Number(deleteRow.dataset.deleteRow), 1);
    renderTestData();
  }
  const toggle = event.target.closest("[data-toggle-row]");
  if (toggle) {
    state.testData.rows[Number(toggle.dataset.toggleRow)].enabled = toggle.checked;
    renderTestData();
  }
});

$("#runForm").addEventListener("submit", startRun);
$("#dataForm").addEventListener("submit", applyDataRow);
$("#cancelRun").addEventListener("click", cancelActiveRun);
$("#saveData").addEventListener("click", saveTestData);
$("#addDataRow").addEventListener("click", () => openDataEditor());
$("#enableAll").addEventListener("click", () => { state.testData.rows.forEach(row => row.enabled = true); renderTestData(); });
$("#disableAll").addEventListener("click", () => { state.testData.rows.forEach(row => row.enabled = false); renderTestData(); });
$("#dataSearch").addEventListener("input", renderTestData);
$("#dataEnabledFilter").addEventListener("change", renderTestData);
$("#refreshButton").addEventListener("click", () => Promise.all([loadSummary(), loadRuns(), loadEnvironments()]));
$("#mobileMenu").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
$$('input[name="environment"]').forEach(input => input.addEventListener("change", () => {
  $("#liveWarning").classList.toggle("hidden", input.value !== "live" || !input.checked);
}));
$$(".modal-backdrop").forEach(backdrop => backdrop.addEventListener("click", event => {
  if (event.target === backdrop) closeModal(backdrop.id);
}));

async function initialize() {
  try {
    await api("/api/health");
    $("#serviceStatus").textContent = "Connected";
  } catch (_) {
    $("#serviceStatus").textContent = "Unavailable";
  }
  await Promise.all([loadSummary(), loadRuns(), loadEnvironments()]);
}

initialize();

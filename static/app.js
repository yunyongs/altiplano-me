/* AR Workflow Dashboard – client-side logic */

// ── Language Toggle / Cambio de Idioma ───────────────────────────────────────
// Stores preference in localStorage and switches html[lang] attribute.
// Elements with class "lang-es" or "lang-en" are shown/hidden via CSS.

function getLang() {
  return document.documentElement.lang || "es";
}

function setLang(lang) {
  lang = lang === "en" ? "en" : "es";
  document.documentElement.lang = lang;
  localStorage.setItem("ar_lang", lang);
  // Update toggle buttons
  var btns = document.querySelectorAll("#langToggle .lang-btn");
  for (var i = 0; i < btns.length; i++) {
    btns[i].classList.toggle("active", btns[i].getAttribute("data-lang") === lang);
  }
  // Update <option> elements with data-es/data-en attributes
  var opts = document.querySelectorAll("option[data-es][data-en]");
  for (var j = 0; j < opts.length; j++) {
    opts[j].textContent = opts[j].getAttribute("data-" + lang) || opts[j].getAttribute("data-es");
  }
  // Update title attributes (data-title-es / data-title-en)
  var titles = document.querySelectorAll("[data-title-es][data-title-en]");
  for (var k = 0; k < titles.length; k++) {
    titles[k].title = titles[k].getAttribute("data-title-" + lang) || titles[k].getAttribute("data-title-es");
  }
  // Update aria-label attributes (data-aria-es / data-aria-en)
  var arias = document.querySelectorAll("[data-aria-es][data-aria-en]");
  for (var m = 0; m < arias.length; m++) {
    arias[m].setAttribute("aria-label",
      arias[m].getAttribute("data-aria-" + lang) || arias[m].getAttribute("data-aria-es"));
  }
}

// Restore language preference on load
(function() {
  var saved = localStorage.getItem("ar_lang");
  if (saved === "en" || saved === "es") {
    document.documentElement.lang = saved;
    // Defer button update until DOM is ready
    document.addEventListener("DOMContentLoaded", function() { setLang(saved); });
  }
})();

/**
 * Build a bilingual HTML string. Only the active language is visible.
 * Usage: i18n("Texto español", "English text")
 * Returns: '<span class="lang-es">Texto español</span><span class="lang-en">English text</span>'
 */
function i18n(es, en) {
  return '<span class="lang-es">' + escapeHtml(es) + '</span>' +
         '<span class="lang-en">' + escapeHtml(en || es) + '</span>';
}

/** Same as i18n but without HTML escaping (for trusted HTML content). */
function i18nRaw(es, en) {
  return '<span class="lang-es">' + es + '</span>' +
         '<span class="lang-en">' + (en || es) + '</span>';
}

// ── Help Modal / Modal de Ayuda ────────────────────────────────────────────
// Clicking the ? icon on any [data-help-es] element opens a bilingual modal.
// Al hacer clic en el ícono ? de cualquier elemento [data-help-es] abre un modal bilingüe.

document.addEventListener("click", function(e) {
  const el = e.target.closest("[data-help-es]");
  if (!el) return;
  // Determine click position vs the ::after pseudo-element bounding area.
  // We trigger the modal when clicking the right-most 28px of the element
  // (where the ? badge is rendered by CSS ::after).
  // ES: Detectar si el clic fue sobre el ícono ? (últimos 28px del elemento).
  const rect = el.getBoundingClientRect();
  const isHelpClick = e.clientX >= rect.right - 28;
  if (!isHelpClick) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  const es = el.dataset.helpEs || "";
  const en = el.dataset.helpEn || "";
  document.getElementById("helpModalEs").textContent = es;
  document.getElementById("helpModalEn").textContent = en || "—";
  document.getElementById("helpModalOverlay").classList.add("open");
}, true);

function closeHelpModal(e) {
  if (e && e.target !== document.getElementById("helpModalOverlay")) return;
  document.getElementById("helpModalOverlay").classList.remove("open");
}

document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") document.getElementById("helpModalOverlay").classList.remove("open");
});
// ──────────────────────────────────────────────────────────────────────────

/** Escape a string for safe innerHTML insertion. */
function escapeHtml(s) {
  if (typeof s !== "string") return String(s);
  var d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

/** Get local auth token from the meta tag injected by the server. */
function _localToken() {
  var m = document.querySelector('meta[name="local-token"]');
  return m ? m.content : "";
}

/** Display a path truncated to last N segments, with full path in title. */
function displayPath(fullPath, segments) {
  segments = segments || 3;
  if (!fullPath) return "";
  var parts = fullPath.replace(/\\/g, "/").split("/");
  var short = parts.length > segments
    ? "…/" + parts.slice(-segments).join("/")
    : fullPath;
  return '<span title="' + escapeHtml(fullPath) + '">' + escapeHtml(short) + "</span>";
}

const logEl = document.getElementById("log");
let logCount = 0;

// State
let sheetData = null;
let attachmentsData = null;
let c2GrantType = "";
let c2Contrato = "";
let filteredRowNumbers = null; // row numbers currently visible in the table

// ── Last-clicked sidebar button highlight ──
function markLastClicked(btnEl) {
  if (!btnEl) return;
  // Clear previous button highlight
  document.querySelectorAll(".sb-btn.last-clicked").forEach(function(el) {
    el.classList.remove("last-clicked");
  });
  btnEl.classList.add("last-clicked");

  // Highlight parent Paso section header
  document.querySelectorAll(".sb-sec-hd.active").forEach(function(el) {
    el.classList.remove("active");
  });
  var section = btnEl.closest(".sb-sec");
  if (section) {
    var hd = section.querySelector(".sb-sec-hd");
    if (hd) hd.classList.add("active");
  }
}
// Auto-attach: any sb-btn click inside sidebar
(function initLastClicked() {
  var sb = document.getElementById("sidebar");
  if (!sb) return;
  sb.addEventListener("click", function(e) {
    var btn = e.target.closest(".sb-btn");
    if (btn) markLastClicked(btn);
  });
})();

// ── Execution indicator (log bar spinner) ──
let _execCount = 0;
function execStart() {
  _execCount++;
  var el = document.getElementById("logExecIndicator");
  if (el) el.classList.remove("hidden");
}
function execEnd() {
  _execCount = Math.max(0, _execCount - 1);
  if (_execCount === 0) {
    var el = document.getElementById("logExecIndicator");
    if (el) el.classList.add("hidden");
  }
}

// Pagination state
let currentPage = 1;
let pageSize = 100;

// Cache: { C1: { data, ts }, C2: { data, ts }, C3: { data, ts } }
const sheetCache = {};
const CACHE_TTL = 60 * 60 * 1000; // 1 hour

// ── Cache patching ────────────────────────────────────────────────────
// EN: Merge server-returned patches into local cache instead of re-fetching.
// ES: Fusionar parches del servidor en la caché local en lugar de recargar.
// patches: [{rowId, cells: {colName: value, ...}}, ...]

function patchSheetCache(patches) {
  if (!patches || !patches.length || !sheetData) return;
  const byId = {};
  patches.forEach(function (p) { byId[p.rowId] = p.cells; });
  sheetData.rows.forEach(function (r) {
    const patch = byId[r.id];
    if (patch) {
      for (var col in patch) {
        r.cells[col] = patch[col];
      }
    }
  });
  // Update cache entry
  var comp = document.getElementById("component").value;
  if (sheetCache[comp]) {
    sheetCache[comp].data = sheetData;
    sheetCache[comp].ts = Date.now();
  }
  renderSheetTable();
  renderSummary();
  saveSessionState();
}

// ── Session persistence ───────────────────────────────────────────────
// EN: Save/restore working state across page refreshes (sessionStorage).
// ES: Guardar/restaurar estado de trabajo al refrescar la página.

function saveSessionState() {
  try {
    var destFolderField = document.getElementById("destFolder");
    const state = {
      component: document.getElementById("component").value,
      c2GrantType: c2GrantType,
      c2Contrato: c2Contrato,
      filterTipos: getMsValues("filterTipo"),
      filterContratos: getMsValues("filterContrato"),
      filterTrimestres: getMsValues("filterTrimestre"),
      rowStart: document.getElementById("rowStart").value,
      rowEnd: document.getElementById("rowEnd").value,
      destFolderMode: getDestFolderMode(),
      destFolder: destFolderField ? destFolderField.value : "",
      workQuarter: getWorkQuarter(),
      ts: Date.now(),
    };
    sessionStorage.setItem("arSessionState", JSON.stringify(state));
    // Save only the active component's sheet cache (sessionStorage ~5MB limit)
    const comp = state.component;
    if (sheetCache[comp] && (Date.now() - sheetCache[comp].ts) < CACHE_TTL) {
      sessionStorage.setItem("arSheetCache", JSON.stringify({ [comp]: sheetCache[comp] }));
    }
  } catch (_) { /* sessionStorage full or unavailable */ }
}

function restoreSessionState() {
  try {
    const raw = sessionStorage.getItem("arSessionState");
    if (!raw) return false;
    const state = JSON.parse(raw);
    // Reject if older than cache TTL
    if (Date.now() - state.ts > CACHE_TTL) {
      sessionStorage.removeItem("arSessionState");
      sessionStorage.removeItem("arSheetCache");
      return false;
    }
    // Restore component selection
    if (state.component) {
      document.getElementById("component").value = state.component;
    }
    // Restore row range — but never restore a rowEnd smaller than config default
    if (state.rowStart) document.getElementById("rowStart").value = state.rowStart;
    if (state.rowEnd) {
      var cfgEnd = parseInt(window.APP_CONFIG && window.APP_CONFIG.ROW_END) || 9999;
      var savedEnd = parseInt(state.rowEnd) || cfgEnd;
      document.getElementById("rowEnd").value = Math.max(savedEnd, cfgEnd);
    }
    // Restore C2 filter state (legacy vars + multi-select arrays)
    c2GrantType = state.c2GrantType || "";
    c2Contrato = state.c2Contrato || "";
    // Store multi-select arrays temporarily for post-populate restore
    window._restoreFilterTipos = state.filterTipos || [];
    window._restoreFilterContratos = state.filterContratos || [];
    window._restoreFilterTrimestres = state.filterTrimestres || [];
    window._restoreDestFolderMode = state.destFolderMode || "auto";
    window._restoreDestFolderValue = state.destFolder || "";
    window._restoreWorkQuarter = state.workQuarter || "";
    // Restore sheet cache
    const cacheRaw = sessionStorage.getItem("arSheetCache");
    if (cacheRaw) {
      const cached = JSON.parse(cacheRaw);
      for (const k in cached) {
        if (cached[k] && (Date.now() - cached[k].ts) < CACHE_TTL) {
          sheetCache[k] = cached[k];
        }
      }
    }
    // Restore active sheet data from cache
    const comp = state.component || "C1";
    if (sheetCache[comp]) {
      sheetData = sheetCache[comp].data;
      // EN: Invalidate cached data if rows array is smaller than totalRows
      //     (stale cache from when rowEnd was limited)
      // ES: Invalidar caché si el array de filas es menor que totalRows
      if (sheetData && sheetData.rows && sheetData.totalRows
          && sheetData.rows.length < sheetData.totalRows) {
        sheetData = null;
        delete sheetCache[comp];
        sessionStorage.removeItem("arSheetCache");
        return false;
      }
    }
    return !!sheetData;
  } catch (_) {
    return false;
  }
}

// EN: Auto-save state before page unload
// ES: Guardar estado automáticamente antes de cerrar/recargar la página
window.addEventListener("beforeunload", saveSessionState);

// ── Shapefile helpers ──────────────────────────────────────────────────

// EN: AbE abbreviations used in shapefile ZIP filenames (e.g. SAF_23.60 ha.zip)
// ES: Abreviaciones AbE usadas en nombres de ZIP shapefiles
var _ABE_ZIP_KEYWORDS = /sueloyagua|aguaysuelo|anual|peren|silvo|plant|forestal|produ|prote|bnp|refor|saf|cs/i;

function isShapefileZip(name) {
  const n = name.toLowerCase();
  if (!n.endsWith(".zip")) return false;
  // Direct shape/area/geometry keywords — always match even inside anexo names
  if (/shp|shape|area|\u00e1rea|puntos|poligonos|pol\u00edgonos/.test(n)) return true;
  // AbE keyword detection (e.g. SAF_perennes_y_anuales.zip, anexo_saf.zip)
  if (_ABE_ZIP_KEYWORDS.test(n.replace(/\.zip$/, ""))) return true;
  // Exclude generic anexo files that didn't match
  return false;
}

function rowHasShapefile(row) {
  return (row.attachments || []).some((a) => isShapefileZip(a.name));
}

// ── Layout: Sidebar ────────────────────────────────────────────────────

function toggleSidebar() {
  const s = document.getElementById("sidebar");
  s.classList.toggle("collapsed");
  try { localStorage.setItem("arSbCollapsed", s.classList.contains("collapsed")); } catch (_) {}
}

function expandSidebar() {
  document.getElementById("sidebar").classList.remove("collapsed");
}

/* ── Pencil nav: Switch between views / Cambiar entre vistas ── */
function navigateTo(viewId) {
  // 1. Show controls area, hide empty state
  var area = document.getElementById("pasoControlsArea");
  if (!area) return;
  area.classList.remove("hidden");
  var empty = document.getElementById("emptyState");
  if (empty) empty.classList.add("hidden");

  // 2. Deactivate all views, activate requested
  area.querySelectorAll(".paso-view").forEach(function(v) {
    v.classList.remove("active");
  });
  var view = document.getElementById("view" + viewId);
  if (view) view.classList.add("active");

  // 3. Update sidebar active highlight
  document.querySelectorAll(".sb-sec-hd").forEach(function(h) {
    h.classList.remove("active");
  });
  var activeHd = document.querySelector(".sb-sec-hd[data-view='" + viewId + "']");
  if (activeHd) activeHd.classList.add("active");

  // 4. Persist last view
  try { localStorage.setItem("arCurrentView", viewId); } catch (_) {}
}

/* Sidebar filter sync — mirrors sidebar checkboxes to main filter-bar and triggers onFilterChange */
function syncSbCheckbox(mainId, sbEl) {
  const main = document.getElementById(mainId);
  if (main) main.checked = sbEl.checked;
  if (typeof onFilterChange === "function") onFilterChange();
}
function syncSbFilter(filterName, sbEl) {
  // Sync sidebar checkbox → content-area hidden filter
  const mainDd = document.querySelector('.ms-dropdown[data-filter="' + filterName + '"]');
  if (mainDd) {
    const mainCb = mainDd.querySelector('input[value="' + sbEl.value + '"]');
    if (mainCb) mainCb.checked = sbEl.checked;
  }
  if (typeof onFilterChange === "function") onFilterChange();
}
// Sync content-area filter state → sidebar filter checkboxes
function syncMainToSidebar() {
  ["tipo", "contrato", "trimestre"].forEach(function(name) {
    var mainVals = getMsValues(
      name === "tipo" ? "filterTipo" :
      name === "contrato" ? "filterContrato" : "filterTrimestre"
    );
    var sbId = name === "tipo" ? "sbFilterTipo" :
               name === "contrato" ? "sbFilterContrato" : "sbFilterTrimestre";
    var sbEl = document.getElementById(sbId);
    if (!sbEl) return;
    sbEl.querySelectorAll(".sb-ms-menu input[type=checkbox]").forEach(function(cb) {
      cb.checked = mainVals.indexOf(cb.value) !== -1;
    });
  });
  // Update sidebar toggle labels
  updateSbToggleLabel("sbFilterTipo", "Tipo");
  updateSbToggleLabel("sbFilterContrato", "Nº Contrato");
  updateSbToggleLabel("sbFilterTrimestre", "Trimestre");
}
function updateSbToggleLabel(sbId, defaultLabel) {
  var el = document.getElementById(sbId);
  if (!el) return;
  var btn = el.querySelector(".sb-ms-toggle");
  if (!btn) return;
  var vals = [];
  el.querySelectorAll(".sb-ms-menu input:checked").forEach(function(cb) { vals.push(cb.value); });
  if (vals.length === 0) {
    btn.innerHTML = defaultLabel + ' <span class="sb-ms-arrow">▾</span>';
    btn.classList.remove("active");
  } else if (vals.length === 1) {
    btn.innerHTML = vals[0] + ' <span class="sb-ms-arrow">▾</span>';
    btn.classList.add("active");
  } else {
    btn.innerHTML = defaultLabel + " (" + vals.length + ") " + '<span class="sb-ms-arrow">▾</span>';
    btn.classList.add("active");
  }
}
function toggleSbMsDropdown(btn) {
  const dd = btn.closest(".sb-ms-dropdown");
  document.querySelectorAll(".sb-ms-dropdown.open").forEach(d => { if (d !== dd) d.classList.remove("open"); });
  dd.classList.toggle("open");
}
document.addEventListener("click", function(e) {
  if (!e.target.closest(".sb-ms-dropdown")) {
    document.querySelectorAll(".sb-ms-dropdown.open").forEach(d => d.classList.remove("open"));
  }
});

/* Paso 2: Agent / Manual mode toggle */
function setPaso2Mode(mode) {
  const pairs = [
    ["agentSection", "manualSection"],
    ["agentSectionMain", "manualSectionMain"],
  ];
  const btnAgent = document.getElementById("btnModeAgent");
  const btnManual = document.getElementById("btnModeManual");
  pairs.forEach(([aId, mId]) => {
    const a = document.getElementById(aId);
    const m = document.getElementById(mId);
    if (a) a.style.display = mode === "agent" ? "" : "none";
    if (m) m.style.display = mode === "manual" ? "" : "none";
  });
  if (mode === "agent") {
    btnAgent.classList.add("active");
    btnManual.classList.remove("active");
  } else {
    btnAgent.classList.remove("active");
    btnManual.classList.add("active");
  }
}

// Restore sidebar state on load
(function restoreSidebar() {
  try {
    if (localStorage.getItem("arSbCollapsed") === "true") {
      document.getElementById("sidebar").classList.add("collapsed");
    }
    const w = localStorage.getItem("arSbWidth");
    if (w) document.getElementById("sidebar").style.width = w + "px";
  } catch (_) {}
})();

// Restore last viewed panel on load
(function restoreLastView() {
  try {
    var saved = localStorage.getItem("arCurrentView");
    if (saved) {
      document.addEventListener("DOMContentLoaded", function() {
        navigateTo(saved);
      });
    }
  } catch (_) {}
})();

// ── Layout: Resize sidebar ─────────────────────────────────────────────

(function initResizeHandle() {
  const handle  = document.getElementById("resizeHandle");
  const sidebar = document.getElementById("sidebar");
  if (!handle || !sidebar) return;

  let dragging = false;
  let startX   = 0;
  let startW   = 0;

  handle.addEventListener("mousedown", (e) => {
    if (sidebar.classList.contains("collapsed")) return;
    dragging = true;
    startX   = e.clientX;
    startW   = sidebar.getBoundingClientRect().width;
    handle.classList.add("is-dragging");
    sidebar.classList.add("resizing");
    document.body.style.userSelect = "none";
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const newW = Math.max(180, Math.min(500, startW + e.clientX - startX));
    sidebar.style.width = newW + "px";
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    handle.classList.remove("is-dragging");
    sidebar.classList.remove("resizing");
    document.body.style.userSelect = "";
    try { localStorage.setItem("arSbWidth", parseInt(sidebar.style.width)); } catch (_) {}
  });
})();

// ── Layout: Log layer ──────────────────────────────────────────────────

function toggleLog() {
  const layer = document.getElementById("logLayer");
  if (layer.classList.contains("collapsed")) {
    // Expand: remove collapsed, then restore saved inline height (if any)
    layer.classList.remove("collapsed");
    try {
      var saved = parseInt(sessionStorage.getItem("logH"), 10);
      if (saved && saved >= 80) layer.style.height = saved + "px";
    } catch (_) {}
  } else {
    // Collapse: MUST clear inline style first so CSS rule takes effect
    layer.style.height = "";
    layer.classList.add("collapsed");
  }
  try { sessionStorage.setItem("arLogCollapsed", layer.classList.contains("collapsed") ? "1" : "0"); } catch (_) {}
}

// ── Logging (Spanish) ──────────────────────────────────────────────────

/**
 * Log a message to the activity log.
 * msg can be a string (shown as-is) or {es: "...", en: "..."} for bilingual.
 */
function log(msg, cls) {
  const entry = document.createElement("div");
  entry.className = "log-entry" + (cls ? " log-" + cls : "");
  const ts = new Date().toLocaleTimeString("es", { hour12: false });
  var content;
  if (msg && typeof msg === "object" && (msg.es || msg.en)) {
    content = i18n(msg.es || "", msg.en || "");
  } else {
    content = escapeHtml(msg);
  }
  entry.innerHTML =
    '<span class="log-ts">[' + escapeHtml(ts) + "]</span>" +
    '<span class="log-msg">' + content + "</span>";
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;

  logCount++;
  document.getElementById("logCount").textContent = logCount;

  // Auto-expand log panel when a new entry arrives
  var logLayer = document.getElementById("logLayer");
  if (logLayer && logLayer.classList.contains("collapsed")) {
    logLayer.classList.remove("collapsed");
    try {
      var savedH = parseInt(sessionStorage.getItem("logH"), 10);
      if (savedH && savedH >= 80) logLayer.style.height = savedH + "px";
    } catch (_) {}
  }

  const pulse = document.getElementById("logPulse");
  if (pulse) {
    pulse.classList.add("active");
    setTimeout(() => pulse.classList.remove("active"), 1400);
  }
}

// EN: Log entry with raw HTML content (for diagnostic details with buttons)
// ES: Entrada de log con HTML (para diagnósticos con botones)
/**
 * Log raw HTML to the activity log.
 * htmlContent can be a string or {es: "...", en: "..."} for bilingual HTML.
 */
function logHtml(htmlContent, cls) {
  const entry = document.createElement("div");
  entry.className = "log-entry" + (cls ? " log-" + cls : "");
  const ts = new Date().toLocaleTimeString("es", { hour12: false });
  var content;
  if (htmlContent && typeof htmlContent === "object" && (htmlContent.es || htmlContent.en)) {
    content = i18nRaw(htmlContent.es || "", htmlContent.en || "");
  } else {
    content = htmlContent;
  }
  entry.innerHTML =
    '<span class="log-ts">[' + escapeHtml(ts) + "]</span>" +
    '<span class="log-msg log-msg-rich">' + content + "</span>";
  logEl.appendChild(entry);
  logEl.scrollTop = logEl.scrollHeight;
  logCount++;
  document.getElementById("logCount").textContent = logCount;
  // Auto-expand log panel on new entry
  var logLayer2 = document.getElementById("logLayer");
  if (logLayer2 && logLayer2.classList.contains("collapsed")) {
    logLayer2.classList.remove("collapsed");
    try {
      var savedH2 = parseInt(sessionStorage.getItem("logH"), 10);
      if (savedH2 && savedH2 >= 80) logLayer2.style.height = savedH2 + "px";
    } catch (_) {}
  }
  const pulse = document.getElementById("logPulse");
  if (pulse) {
    pulse.classList.add("active");
    setTimeout(() => pulse.classList.remove("active"), 1400);
  }
}

function clearLog() {
  logEl.innerHTML = "";
  logCount = 0;
  document.getElementById("logCount").textContent = "0";
}

function downloadLog() {
  const entries = logEl.querySelectorAll(".log-entry");
  if (!entries.length) {
    log("No hay registros para descargar. / No log entries to download.", "warn");
    return;
  }
  let text = "=== Altiplano Resiliente — Registro de Actividad ===\n";
  text += "Fecha / Date: " + new Date().toLocaleString("es") + "\n";
  text += "Componente: " + (document.getElementById("componentSelect")?.value || "-") + "\n";
  text += "=".repeat(52) + "\n\n";
  entries.forEach((entry) => {
    const ts = entry.querySelector(".log-ts")?.textContent || "";
    const msg = entry.querySelector(".log-msg")?.textContent || "";
    text += ts + " " + msg + "\n";
  });
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ar_log_" + new Date().toISOString().slice(0, 10) + ".txt";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ══ S3: Toast / Friendly notification ════════════════════════════════════

function showToast(data, fallbackMsg) {
  // data can be a structured backend error or a simple string
  // ES: Muestra una notificación al usuario / EN: Shows a notification to the user
  const isStructured = data && data.title;

  const toast = document.createElement("div");
  toast.className = "toast toast-" + (isStructured ? data.severity : "error");

  if (isStructured) {
    toast.innerHTML =
      '<div class="toast-header">' +
        '<span class="toast-icon">' + getToastIcon(data.severity) + "</span>" +
        "<strong class=\"toast-title\">" + escapeHtml(data.title) + "</strong>" +
        '<button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>' +
      "</div>" +
      '<div class="toast-body">' +
        '<p class="toast-message">' + escapeHtml(data.message) + "</p>" +
        (data.action
          ? '<p class="toast-action"><strong>Qué hacer:</strong> ' + escapeHtml(data.action) + "</p>"
          // ES: "Qué hacer:" / EN: "What to do:"
          : "") +
      "</div>";
  } else {
    toast.innerHTML =
      '<div class="toast-header">' +
        '<span class="toast-icon">' + getToastIcon("error") + "</span>" +
        "<strong class=\"toast-title\">Error</strong>" +
        '<button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>' +
      "</div>" +
      '<div class="toast-body">' +
        '<p class="toast-message">' +
          escapeHtml(fallbackMsg || "Ocurrió un error inesperado.") +
          // ES: "Ocurrió un error inesperado." / EN: "An unexpected error occurred."
        "</p>" +
      "</div>";
  }

  // Append to container — create it if missing
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  container.appendChild(toast);

  // Entrance animation
  requestAnimationFrame(() => toast.classList.add("show"));

  // Auto-remove: 5s for warnings, 8s for errors
  const duration = (isStructured && data.severity === "warn") ? 5000 : 8000;
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function showSuccessToast(message) {
  // ES: Muestra una notificación de éxito / EN: Shows a success notification
  showToast({ title: "Listo", message: message, severity: "ok" });
  // ES: "Listo" / EN: "Done"
}

function getToastIcon(severity) {
  switch (severity) {
    case "ok":    return "✓";
    case "warn":  return "⚠";
    case "error": return "✕";
    default:      return "ℹ";
  }
}

// ═════════════════════════════════════════════════════════════════════════

// ── Params ─────────────────────────────────────────────────────────────

function getParams() {
  const p = {
    component: document.getElementById("component").value,
    rowStart: parseInt(document.getElementById("rowStart").value) || 1,
    rowEnd:   parseInt(document.getElementById("rowEnd").value)   || (sheetData ? sheetData.totalRows : 9999),
  };
  // EN: Send active filters so server can pre-filter before returning rows
  // ES: Enviar filtros activos para que el servidor filtre antes de devolver filas
  const trimestres = getMsValues("filterTrimestre");
  if (trimestres.length > 0) p.filterTrimestres = trimestres;
  if (p.component === "C2") {
    if (c2GrantType) p.c2GrantType = c2GrantType;
    if (c2Contrato) p.c2Contrato = c2Contrato;
    const tipos = getMsValues("filterTipo");
    if (tipos.length > 0) p.filterTipos = tipos;
    const contratos = getMsValues("filterContrato");
    if (contratos.length > 0) p.filterContratos = contratos;
  }
  return p;
}

// ── API helper ─────────────────────────────────────────────────────────

async function api(path, body, _retryCount) {
  var maxRetries = 1;
  var attempt = _retryCount || 0;
  log("Llamando a " + path + " …");
  execStart();
  try {
    var controller = new AbortController();
    var timeoutId = setTimeout(function() { controller.abort(); }, 120000);
    var resp = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Local-Token": _localToken() },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const data = await resp.json();
    if (!resp.ok) {
      // S3: Show structured toast if backend returned friendly_error, else fallback
      if (data.title) {
        showToast(data);
        log(data.title + ": " + data.message, "err");
      } else {
        showToast(null, data.error || resp.statusText);
        log("Error: " + (data.error || resp.statusText), "err");
      }
      return null;
    }
    return data;
  } catch (e) {
    if (attempt < maxRetries) {
      log("Reintentando " + path + " (intento " + (attempt + 2) + ") … / Retrying…", "warn");
      execEnd();
      return api(path, body, attempt + 1);
    }
    // ES: "No se pudo conectar..." / EN: "Could not connect to server"
    showToast(null, "No se pudo conectar con el servidor. ¿Está run.bat ejecutándose?");
    log("Error de red: " + e.message, "err");
    return null;
  } finally {
    execEnd();
  }
}

async function apiGet(path) {
  log("Consultando " + path + " …");
  try {
    const resp = await fetch(path, { headers: { "X-Local-Token": _localToken() } });
    const data = await resp.json();
    if (!resp.ok) {
      if (data.title) {
        showToast(data);
        log(data.title + ": " + (data.message || ""), "err");
      } else {
        showToast(null, data.error || resp.statusText);
        log("Error: " + (data.error || resp.statusText), "err");
      }
      return null;
    }
    return data;
  } catch (e) {
    showToast(null, "No se pudo conectar / Could not connect");
    log("Error de red: " + e.message, "err");
    return null;
  }
}

// ── Panel helpers ──────────────────────────────────────────────────────

const RESULT_PANELS = [
  "paso0Panel",
  "summaryPanel",
  "sheetPreview",
  "codeSelectionPanel",
  "attachmentsList",
  "downloadResult",
  "scriptOutput",
  "scriptRunner",
  "reportResult",
  "pbiPanel",
  "cleaningComparePanel",
];

function show(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("hidden");
  updateEmptyState();
  if (id === "downloadResult") showRightSidebarIfContent();
  if (id === "paso0Panel") openRsbSection("rsb-diag");
}

function hide(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
  updateEmptyState();
}

function disable(id, val) {
  const el = document.getElementById(id);
  if (el) el.disabled = val;
}

function updateEmptyState() {
  const anyVisible = RESULT_PANELS.some((id) => {
    const el = document.getElementById(id);
    return el && !el.classList.contains("hidden");
  });
  const es = document.getElementById("emptyState");
  if (es) es.style.display = anyVisible ? "none" : "";
}

// ── Workflow steps ─────────────────────────────────────────────────────

const WORKFLOW_STEPS = [
  "btnLoad",
  "btnCodes",
  "btnReview",
  "btnAttach",
  "btnBatchDL",
];

let _currentStep = 0;

function setWorkflowStep(n) {
  _currentStep = n;
  WORKFLOW_STEPS.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("step-active", "step-done");
    const old = el.querySelector(".step-num");
    if (old) old.remove();

    if (i < n) {
      el.classList.add("step-done");
    } else if (i === n) {
      el.classList.add("step-active");
      const badge = document.createElement("span");
      badge.className = "step-num";
      badge.textContent = n + 1;
      el.prepend(badge);
    }
  });
}

function advanceStep() {
  const next = _currentStep + 1;
  if (next < WORKFLOW_STEPS.length) setWorkflowStep(next);
}

// ── Init: load config ──────────────────────────────────────────────────

(async function initConfig() {
  try {
    const resp = await fetch("/api/config");
    const cfg  = await resp.json();

    document.getElementById("cfgC1").textContent = cfg.SHEET_C1 || "—";
    document.getElementById("cfgC2").textContent = cfg.SHEET_C2 || "—";
    document.getElementById("cfgC3").textContent = cfg.SHEET_C3 || "—";

    const ts = document.getElementById("tokenStatus");
    if (cfg.has_token) {
      ts.textContent = "Conectado";
      ts.className = "badge badge-green";
    } else {
      ts.textContent = "Sin token";
      ts.className = "badge badge-red";
    }

    if (cfg.DEFAULT_COMPONENT)
      document.getElementById("component").value = cfg.DEFAULT_COMPONENT;
    if (cfg.ROW_START)
      document.getElementById("rowStart").value = cfg.ROW_START;
    if (cfg.ROW_END)
      document.getElementById("rowEnd").value = cfg.ROW_END;
    if (cfg.CSVPOINT_TO_GDB) {
      const gdb = document.getElementById("gdbPath");
      if (gdb && !gdb.value) gdb.value = cfg.CSVPOINT_TO_GDB;
    }

    // EN: Pre-fill all folder inputs from .env defaults
    // ES: Pre-llenar todos los campos de carpeta con valores de .env
    window._envFolders = {
      FOLDER_C1: cfg.FOLDER_C1 || "",
      FOLDER_C2: cfg.FOLDER_C2 || "",
      FOLDER_C3: cfg.FOLDER_C3 || "",
      SMARTSHEET_ATTACH_DIR: cfg.SMARTSHEET_ATTACH_DIR || "",
      SMARTSHEET_DATA_DIR: cfg.SMARTSHEET_DATA_DIR || "",
      EXCEL_DB_DIR: cfg.EXCEL_DB_DIR || "",
      CSVPOINT_TO_GDB: cfg.CSVPOINT_TO_GDB || "",
      WORKSPACE_PATH: cfg.WORKSPACE_PATH || "",
      APRX: cfg.APRX || "",
    };

    // Restore saved working state before syncing UI mirrors.
    // / Restaurar estado guardado antes de sincronizar los espejos de UI.
    const restoredSheet = restoreSessionState();

    // Restore folder mode/manual override for the restored component.
    // / Restaurar modo manual/automático según el componente restaurado.
    restoreDestFolderState();
    updateDestFolderFromEnv();

    // EN: Populate quarter dropdowns with previous 2 + current + next 1 quarter.
    // ES: Poblar los desplegables con 2 trimestres previos + actual + siguiente.
    populateQuarterDropdown(window._restoreWorkQuarter || "");

    // EN: Pre-populate filter visibility (Trimestre always, Tipo/Contrato for C2)
    // ES: Pre-llenar visibilidad de filtros (Trimestre siempre, Tipo/Contrato para C2)
    populateFilterMenus();

    // EN: Pre-fill Paso 3 csvPath from SMARTSHEET_DATA_DIR
    if (cfg.SMARTSHEET_DATA_DIR) {
      const csv = document.getElementById("csvPath");
      if (csv && !csv.value) csv.value = cfg.SMARTSHEET_DATA_DIR;
    }

    // EN: Pre-fill Paso 4 gdbFullPath from CSVPOINT_TO_GDB
    if (cfg.CSVPOINT_TO_GDB) {
      const gf = document.getElementById("gdbFullPath");
      if (gf && !gf.value) gf.value = cfg.CSVPOINT_TO_GDB;
    }
    // EN: Pre-fill Paso 4 exportFolder from WORKSPACE_PATH
    if (cfg.WORKSPACE_PATH) {
      const ef = document.getElementById("exportFolder");
      if (ef && !ef.value) ef.value = cfg.WORKSPACE_PATH;
    }
    // EN: Pre-fill Paso 3 excelPath from EXCEL_DB_DIR
    if (cfg.EXCEL_DB_DIR) {
      const ep = document.getElementById("excelPath");
      if (ep && !ep.value) ep.value = cfg.EXCEL_DB_DIR;
    }

    log("Configuración cargada.", "ok");
    setWorkflowStep(0);
    restorePipelineProgress(); // S2: restore progress bar from localStorage
    restoreWizardState();     // S1: restore wizard mode and progress
    // Restore agent loop state from server
    AgentController.restore();

    // EN: Restore sheet data and working state from session (survives page refresh)
    // ES: Restaurar datos de hoja y estado de trabajo de la sesión (sobrevive recarga)
    if (restoredSheet) {
      // Populate filter menus from restored data, then restore checkbox selections
      populateFilterMenus();
      // Restore multi-select checkbox states
      function restoreMsCheckboxes(containerId, values) {
        if (!values || !values.length) return;
        var vSet = new Set(values);
        var el = document.getElementById(containerId);
        if (!el) return;
        el.querySelectorAll(".ms-menu input[type=checkbox]").forEach(function(cb) {
          cb.checked = vSet.has(cb.value);
        });
      }
      restoreMsCheckboxes("filterTipo", window._restoreFilterTipos);
      restoreMsCheckboxes("filterContrato", window._restoreFilterContratos);
      restoreMsCheckboxes("filterTrimestre", window._restoreFilterTrimestres);
      // Sync legacy vars from restored multi-select state
      onFilterChange();
      updateDestFolderFromEnv();
      // Populate comment month filter from restored data
      const months = new Set();
      sheetData.rows.forEach(function(r) {
        if (r.comment && r.comment.date) months.add(r.comment.date.substring(0, 7));
      });
      const cmSel = document.getElementById("filterCommentMonth");
      cmSel.innerHTML = '<option value="">Comentario: todos</option>';
      Array.from(months).sort().reverse().forEach(function(m) {
        cmSel.innerHTML += '<option value="' + m + '">' + m + '</option>';
      });
      // Render restored sheet
      document.getElementById("topbarSheet").textContent = sheetData.name || "—";
      document.getElementById("topbarMeta").textContent =
        sheetData.totalRows + " filas · " + document.getElementById("component").value;
      show("sheetPreview");
      renderSheetTable();
      renderSummary();
      updateFilterBanner();
      log(
        "Hoja restaurada: " + sheetData.name + " (" + sheetData.totalRows +
          " filas). / Sheet restored from session.",
        "ok"
      );
    }
  } catch (e) {
    log("Error al cargar configuración: " + e.message, "err");
  }
})();

// ══════════════════════════════════════════════════════════════════════
// PASO 1 – Smartsheet
// ══════════════════════════════════════════════════════════════════════

async function loadSheet(forceRefresh) {
  const p = getParams();
  const comp = p.component;

  // Use cache if available, not expired, and filters match
  const cached = sheetCache[comp];
  const cacheKey = JSON.stringify({ comp: comp, filterTrimestres: p.filterTrimestres || [], filterTipos: p.filterTipos || [], filterContratos: p.filterContratos || [] });
  if (!forceRefresh && cached && (Date.now() - cached.ts) < CACHE_TTL
      && cached.filterKey === cacheKey) {
    sheetData = cached.data;
    log("Hoja " + comp + " desde caché (" + sheetData.totalRows + " filas).", "ok");
  } else {
    // Clear server-side cache when forcing refresh
    if (forceRefresh) {
      await api("/api/smartsheet/cache/clear", { component: comp });
      delete sheetCache[comp];
    }
    disable("btnLoad", true);
    // EN: Do NOT send rowStart/rowEnd to the load endpoint — load ALL rows.
    //     Row range is only for operations (generate codes, update review, etc.).
    // ES: NO enviar rowStart/rowEnd al endpoint de carga — cargar TODAS las filas.
    //     El rango de filas es solo para operaciones (generar códigos, etc.).
    var loadParams = Object.assign({}, p);
    delete loadParams.rowStart;
    delete loadParams.rowEnd;
    const data = await api("/api/smartsheet/load", { ...loadParams, force_refresh: forceRefresh });
    disable("btnLoad", false);
    if (!data) return;

    sheetData = data;
    sheetCache[comp] = { data: data, ts: Date.now(), filterKey: cacheKey };
    if (data.filteredRows !== undefined && data.filteredRows !== data.totalRows) {
      log("Hoja cargada: " + data.name + " — " + data.filteredRows + " filas mostradas de " + data.totalRows + " total.", "ok");
    } else {
      log("Hoja cargada: " + data.name + " (" + data.totalRows + " filas totales).", "ok");
    }
  }

  // Populate comment month filter
  const months = new Set();
  sheetData.rows.forEach(function(r) {
    if (r.comment && r.comment.date) months.add(r.comment.date.substring(0, 7));
  });
  const cmSel = document.getElementById("filterCommentMonth");
  cmSel.innerHTML = '<option value="">Comentario: todos</option>';
  Array.from(months).sort().reverse().forEach(function(m) {
    cmSel.innerHTML += '<option value="' + m + '">' + m + '</option>';
  });

  document.getElementById("topbarSheet").textContent = sheetData.name || "—";
  document.getElementById("topbarMeta").textContent =
    sheetData.totalRows + " filas · " + comp;

  // Only reset row range if user hasn't specified one
  if (!p.rowStart || p.rowStart === 1) {
    document.getElementById("rowEnd").value = sheetData.totalRows;
  }

  show("sheetPreview");
  updateC2FilterVisibility();
  renderSheetTable();
  renderSummary();
  updateFilterBanner();
  // S2: pipeline progress hooks
  updatePipelineStep(1, "success");
  updatePipelineStep("1b", "active");
  // EN: Persist state so page refresh restores this view
  // ES: Persistir estado para que al refrescar se restaure esta vista
  saveSessionState();
}

async function loadComments() {
  const p = getParams();
  const data = await api("/api/smartsheet/comments", { component: p.component });
  if (!data || !data.comments) return;
  // Merge comments into sheetData
  sheetData.rows.forEach(function(r) {
    if (data.comments[r.id]) {
      r.comment = data.comments[r.id];
    }
  });
  // Update comment month filter options
  const months = new Set();
  sheetData.rows.forEach(function(r) {
    if (r.comment && r.comment.date) months.add(r.comment.date.substring(0, 7));
  });
  const cmSel = document.getElementById("filterCommentMonth");
  cmSel.innerHTML = '<option value="">Comentario: todos</option>';
  Array.from(months).sort().reverse().forEach(function(m) {
    cmSel.innerHTML += '<option value="' + m + '">' + m + '</option>';
  });
  patchSheetCache([]);  // triggers re-render + cache save
  log("Comentarios cargados / Comments loaded", "ok");
}

function applyOpRange() {
  const s = parseInt(document.getElementById("rowStart").value) || 1;
  const e = parseInt(document.getElementById("rowEnd").value) || (sheetData ? sheetData.totalRows : 1);
  document.getElementById("opRangeCount").textContent =
    "Filas " + s + "–" + e + " (vista y operaciones)";
  log("Rango de operación: filas " + s + " a " + e + ".", "info");
  // EN: Row range now also filters the table view — re-render
  // ES: El rango ahora también filtra la vista — re-renderizar
  if (sheetData) renderSheetTable();
}

// ── C2 Filters ─────────────────────────────────────────────────────────

// ── Multi-select dropdown filter system ──────────────────────────────

// EN: Toggle a multi-select dropdown open/closed; close others
// ES: Abrir/cerrar un desplegable multi-selección; cerrar los demás
function toggleMsDropdown(btn) {
  const dd = btn.closest(".ms-dropdown");
  const wasOpen = dd.classList.contains("open");
  // Close all dropdowns
  document.querySelectorAll(".ms-dropdown.open").forEach((d) => d.classList.remove("open"));
  if (!wasOpen) dd.classList.add("open");
}

// EN: Close dropdowns when clicking outside
// ES: Cerrar desplegables al hacer clic fuera
document.addEventListener("click", function(e) {
  if (!e.target.closest(".ms-dropdown")) {
    document.querySelectorAll(".ms-dropdown.open").forEach((d) => d.classList.remove("open"));
  }
});

// ── Bad-date detection & fix ─────────────────────────────────────────────────
// EN: Spanish month abbreviation map for parsing text dates like "8-ago-25"
// ES: Mapa de abreviaturas de meses en español para parsear fechas de texto
var _MONTH_ES = {
  "ene": "01", "feb": "02", "mar": "03", "abr": "04",
  "may": "05", "jun": "06", "jul": "07", "ago": "08",
  "sep": "09", "oct": "10", "nov": "11", "dic": "12"
};

// EN: Detect if a date value is stored as incorrect text (e.g. "8-ago-25", "15 nov 24")
// ES: Detectar si un valor de fecha está almacenado como texto incorrecto
function _isBadDate(val) {
  if (!val) return false;
  var s = String(val).trim().toLowerCase();
  // Already ISO format (YYYY-MM-DD) → good
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return false;
  // Matches patterns like "8-ago-25", "15-nov-24", "8 ago 25", "15/ago/25"
  if (/^\d{1,2}[\s\-\/]+[a-záéíóú]{3,}[\s\-\/]+\d{2,4}$/i.test(s)) return true;
  // Day-month-year numeric with slashes like "08/08/25"
  if (/^\d{1,2}\/\d{1,2}\/\d{2,4}$/.test(s)) return true;
  return false;
}

// EN: Parse a bad-date string into ISO format (YYYY-MM-DD)
// ES: Convertir una fecha de texto incorrecto a formato ISO
function _parseBadDate(val) {
  if (!val) return null;
  var s = String(val).trim().toLowerCase();
  // Try Spanish month abbreviations: "8-ago-25", "15 nov 2024"
  var m = s.match(/^(\d{1,2})[\s\-\/]+([a-záéíóú]{3,})[\s\-\/]+(\d{2,4})$/i);
  if (m) {
    var day = m[1].padStart(2, "0");
    var monthStr = m[2].substring(0, 3);
    var month = _MONTH_ES[monthStr];
    if (!month) return null;
    var year = m[3];
    if (year.length === 2) year = (parseInt(year) > 50 ? "19" : "20") + year;
    return year + "-" + month + "-" + day;
  }
  // Try DD/MM/YY or DD/MM/YYYY
  var m2 = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/);
  if (m2) {
    var day2 = m2[1].padStart(2, "0");
    var month2 = m2[2].padStart(2, "0");
    var year2 = m2[3];
    if (year2.length === 2) year2 = (parseInt(year2) > 50 ? "19" : "20") + year2;
    return year2 + "-" + month2 + "-" + day2;
  }
  return null;
}

// EN: Fix bad dates on the server (Smartsheet update)
// ES: Corregir fechas incorrectas en el servidor (actualización en Smartsheet)
async function fixBadDates() {
  if (!sheetData) return;
  // EN: Only scan rows visible in the current filtered view
  // ES: Solo escanear filas visibles en la vista filtrada actual
  var visibleSet = (filteredRowNumbers && filteredRowNumbers.length > 0)
    ? new Set(filteredRowNumbers) : null;
  var badRows = [];
  sheetData.rows.forEach(function(r) {
    if (visibleSet && !visibleSet.has(r.rowNumber)) return;
    var fecha = r.cells["FECHA DE LA ACTIVIDAD"];
    if (_isBadDate(fecha)) {
      var fixed = _parseBadDate(fecha);
      if (fixed) {
        badRows.push({ rowId: r.id, rowNumber: r.rowNumber, original: fecha, fixed: fixed });
      }
    }
  });
  if (badRows.length === 0) {
    log("No se encontraron fechas con formato incorrecto. / No bad-format dates found.", "ok");
    return;
  }
  var msg = badRows.length + " fecha(s) por corregir. Ejemplos:\n";
  badRows.slice(0, 5).forEach(function(b) {
    msg += "  Fila " + b.rowNumber + ": \"" + b.original + "\" → " + b.fixed + "\n";
  });
  if (!confirm(msg + "\n¿Corregir en Smartsheet? / Fix in Smartsheet?")) return;

  disable("btnFixDates", true);
  var p = getParams();
  var data = await api("/api/smartsheet/fix-dates", {
    component: p.component,
    fixes: badRows.map(function(b) { return { rowId: b.rowId, date: b.fixed }; }),
  });
  disable("btnFixDates", false);
  if (!data) return;
  log("Fechas corregidas: " + data.updated + " de " + badRows.length + " / Dates fixed: " + data.updated + " of " + badRows.length, "ok");
  // Patch local cache
  if (data.patches) patchSheetCache(data.patches);
}

// ── Right Sidebar (Results Panel) ────────────────────────────────────────────
// EN: Toggle right sidebar open/collapsed
// ES: Alternar barra lateral derecha abierta/colapsada
function toggleRightSidebar() {
  var rsb = document.getElementById("rightSidebar");
  if (rsb) {
    rsb.classList.toggle("collapsed");
    localStorage.setItem("rightSidebarCollapsed", rsb.classList.contains("collapsed") ? "1" : "0");
  }
}

// EN: Toggle an accordion section inside the right sidebar
// ES: Alternar una sección de acordeón dentro de la barra lateral derecha
function toggleRsbAccordion(id) {
  var el = document.getElementById(id);
  if (el) el.classList.toggle("collapsed");
}

// EN: Open right sidebar and expand a specific accordion section
// ES: Abrir barra lateral derecha y expandir una sección de acordeón específica
function openRsbSection(accordionId) {
  var rsb = document.getElementById("rightSidebar");
  var empty = document.getElementById("rsb-empty");
  if (rsb) {
    rsb.classList.remove("collapsed");
    localStorage.setItem("rightSidebarCollapsed", "0");
  }
  if (empty) empty.style.display = "none";
  var section = document.getElementById(accordionId);
  if (section) section.classList.remove("collapsed");
  // EN: Show notification dot on tab strip when results are available
  var dot = document.getElementById("rsbTabDot");
  if (dot) dot.classList.add("visible");
}

// EN: Show right sidebar when download results become available
// ES: Mostrar barra lateral derecha cuando hay resultados de descarga
function showRightSidebarIfContent() {
  openRsbSection("rsb-download");
}

// EN: Init right sidebar state from localStorage
// ES: Inicializar estado de barra lateral derecha desde localStorage
(function initRightSidebar() {
  var rsb = document.getElementById("rightSidebar");
  if (!rsb) return;
  var stored = localStorage.getItem("rightSidebarCollapsed");
  // Default: collapsed
  if (stored !== "0") {
    rsb.classList.add("collapsed");
  }
  // Restore saved width / Restaurar ancho guardado
  var savedW = localStorage.getItem("rightSidebarWidth");
  if (savedW) rsb.style.width = savedW;
})();

// EN: Drag-to-resize right sidebar
// ES: Arrastrar para redimensionar la barra lateral derecha
(function initRsbResize() {
  var handle = document.getElementById("rsbResizeHandle");
  var rsb = document.getElementById("rightSidebar");
  if (!handle || !rsb) return;

  var startX, startW;
  function onMouseDown(e) {
    if (rsb.classList.contains("collapsed")) return;
    e.preventDefault();
    startX = e.clientX;
    startW = rsb.offsetWidth;
    rsb.classList.add("resizing");
    handle.classList.add("active");
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }
  function onMouseMove(e) {
    var delta = startX - e.clientX; // drag left = wider
    var newW = Math.max(280, Math.min(window.innerWidth * 0.6, startW + delta));
    rsb.style.width = newW + "px";
  }
  function onMouseUp() {
    rsb.classList.remove("resizing");
    handle.classList.remove("active");
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    localStorage.setItem("rightSidebarWidth", rsb.style.width);
  }
  handle.addEventListener("mousedown", onMouseDown);
})();

// EN: Get selected values from a multi-select dropdown
// ES: Obtener valores seleccionados de un desplegable multi-selección
function getMsValues(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return [];
  return Array.from(el.querySelectorAll(".ms-menu input:checked")).map((cb) => cb.value);
}

// EN: Update the toggle button text to reflect selected values
// ES: Actualizar el texto del botón para reflejar los valores seleccionados
function updateMsToggleLabel(containerId, defaultLabel) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const btn = el.querySelector(".ms-toggle");
  const vals = getMsValues(containerId);
  if (vals.length === 0) {
    btn.textContent = defaultLabel + " ▾";
    btn.classList.remove("active");
  } else if (vals.length === 1) {
    btn.textContent = vals[0] + " ▾";
    btn.classList.add("active");
  } else {
    btn.textContent = vals.length + " sel. ▾";
    btn.classList.add("active");
  }
}

// EN: Central handler for any filter change — updates labels, syncs legacy vars, re-renders
// ES: Manejador central para cualquier cambio de filtro — actualiza etiquetas, sincroniza variables, re-renderiza
function onFilterChange() {
  currentPage = 1;
  const comp = document.getElementById("component").value;

  // Sync legacy c2GrantType / c2Contrato variables from multi-select state
  if (comp === "C2") {
    const tipos = getMsValues("filterTipo");
    c2GrantType = tipos.length === 1 ? tipos[0] : "";

    // EN: Re-populate contrato menu filtered by selected tipos
    // ES: Re-llenar menú de contrato filtrado por tipos seleccionados
    populateFilterMenus();

    const contratos = getMsValues("filterContrato");
    c2Contrato = contratos.length === 1 ? contratos[0] : "";
  } else {
    c2GrantType = "";
    c2Contrato = "";
  }

  // Update toggle labels (content-area + sidebar)
  updateMsToggleLabel("filterTipo", "Tipo");
  updateMsToggleLabel("filterContrato", "Nº Contrato");
  updateMsToggleLabel("filterTrimestre", "Trimestre");
  updateMsToggleLabel("filterHectareas", "Hectáreas");
  updateMsToggleLabel("filterCalidadSIG", "Calidad SIG");
  syncMainToSidebar();

  // Show/hide fix-dates button when bad-date filter is active
  const badDateChecked = document.getElementById("filterBadDate").checked;
  const btnFix = document.getElementById("btnFixDates");
  if (btnFix) btnFix.classList.toggle("hidden", !badDateChecked);

  // Show/hide clear button
  const codigoInput = document.getElementById("filterCodigo");
  const codigoVal = codigoInput ? codigoInput.value.trim() : "";
  const hasAny = c2GrantType || c2Contrato ||
    getMsValues("filterTipo").length > 0 ||
    getMsValues("filterContrato").length > 0 ||
    getMsValues("filterTrimestre").length > 0 ||
    getMsValues("filterHectareas").length > 0 ||
    getMsValues("filterCalidadSIG").length > 0 ||
    document.getElementById("filterMissingCode").checked ||
    document.getElementById("filterHasShapefile").checked ||
    badDateChecked ||
    codigoVal ||
    document.getElementById("filterCommentMonth").value;
  const clearBtn = document.getElementById("btnClearFilters");
  if (clearBtn) clearBtn.classList.toggle("hidden", !hasAny);

  // Show/hide fill-down bar
  const fdBar = document.getElementById("c2FillDownBar");
  if (fdBar) fdBar.classList.toggle("hidden", comp !== "C2");
  const fdBtn = document.getElementById("btnC2ApplyFillDown");
  if (fdBtn) fdBtn.disabled = !sheetData;
  const sbFdBtn = document.getElementById("btnSbC2FillDown");
  if (sbFdBtn) sbFdBtn.classList.toggle("hidden", comp !== "C2");

  renderSheetTable();
  renderSummary();
  saveSessionState();
}

// EN: Generate static quarter list for Trimestre pre-population (2023-Q1 → current+1 year Q4)
// ES: Generar lista estática de trimestres para pre-llenar el filtro (2023-Q1 → año actual+1 Q4)
function _staticQuarters() {
  var quarters = [];
  var endYear = new Date().getFullYear() + 1;
  for (var y = 2023; y <= endYear; y++) {
    for (var q = 1; q <= 4; q++) {
      quarters.push(y + "-Q" + q);
    }
  }
  return quarters;
}

// EN: Populate Trimestre filter menus with the given list of values (preserves selections)
// ES: Llenar menús de filtro Trimestre con la lista dada (preserva selecciones)
function _populateTrimestreMenus(values) {
  var prevSelTrimestres = getMsValues("filterTrimestre");
  // Content-area hidden menu
  var tMenu = document.getElementById("filterTrimestreMenu");
  if (tMenu) {
    tMenu.innerHTML = "";
    values.forEach(function(t) {
      var lbl = document.createElement("label");
      lbl.className = "ms-option";
      var checked = prevSelTrimestres.indexOf(t) !== -1 ? " checked" : "";
      lbl.innerHTML = '<input type="checkbox" value="' + t + '"' + checked + ' onchange="onFilterChange()"> ' + t;
      tMenu.appendChild(lbl);
    });
  }
  // Sidebar menu
  var sbTMenu = document.getElementById("sbFilterTrimestreMenu");
  if (sbTMenu) {
    sbTMenu.innerHTML = "";
    values.forEach(function(t) {
      var lbl = document.createElement("label");
      lbl.className = "sb-ms-option";
      var checked = prevSelTrimestres.indexOf(t) !== -1 ? " checked" : "";
      lbl.innerHTML = '<input type="checkbox" value="' + t + '"' + checked + ' onchange="syncSbFilter(\'trimestre\',this)"> ' + t;
      sbTMenu.appendChild(lbl);
    });
  }
}

// EN: Populate C2 multi-select filter menus and Trimestre (all components)
// ES: Llenar los menús de filtro multi-selección C2 y Trimestre (todos los componentes)
function populateFilterMenus() {
  const comp = document.getElementById("component").value;

  // ── Visibility: Tipo & Contrato are C2-only, Trimestre is always visible ──
  ["filterTipo", "filterContrato"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("hidden", comp !== "C2");
  });
  ["sbFilterTipo", "sbFilterContrato"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("hidden", comp !== "C2");
  });
  // Trimestre always visible (content-area + sidebar)
  var ftEl = document.getElementById("filterTrimestre");
  if (ftEl) ftEl.classList.remove("hidden");
  var sbftEl = document.getElementById("sbFilterTrimestre");
  if (sbftEl) sbftEl.classList.remove("hidden");

  const fdBar = document.getElementById("c2FillDownBar");
  if (fdBar) fdBar.classList.toggle("hidden", comp !== "C2");
  const sbFdBtn = document.getElementById("btnSbC2FillDown");
  if (sbFdBtn) sbFdBtn.classList.toggle("hidden", comp !== "C2");

  // ── Pre-populate Trimestre with static quarters when no data yet ──
  if (!sheetData) {
    _populateTrimestreMenus(_staticQuarters());
    if (comp !== "C2") {
      c2GrantType = "";
      c2Contrato = "";
    }
    syncMainToSidebar();
    return;
  }

  // ── Data-dependent population ──
  if (comp !== "C2") {
    c2GrantType = "";
    c2Contrato = "";
  }

  // Collect unique values from data
  const contratos = new Set();
  const trimestres = new Set();
  sheetData.rows.forEach((r) => {
    const c = r.cells["NÚMERO DE CONTRATO"] || "";
    if (c) contratos.add(c);
    const t = r.cells["TRIMESTRE QUE REPORTA"] || "";
    if (t) trimestres.add(t);
  });

  // Populate Trimestre from actual data (merged with static so pre-selections survive)
  var trimestreList = Array.from(trimestres).sort();
  if (trimestreList.length === 0) trimestreList = _staticQuarters();
  _populateTrimestreMenus(trimestreList);

  if (comp !== "C2") {
    syncMainToSidebar();
    return;
  }

  // EN: Filter contratos by selected grant types (PPD/PMD).
  //     If one or more tipos are selected, only show contratos containing
  //     the selected tipo string (e.g. "PPD" → only AR-PPD-*).
  // ES: Filtrar contratos por tipos seleccionados (PPD/PMD).
  const selTipos = getMsValues("filterTipo");
  var filteredContratos = Array.from(contratos);
  if (selTipos.length > 0) {
    filteredContratos = filteredContratos.filter(function(c) {
      return selTipos.some(function(t) { return c.toUpperCase().indexOf(t.toUpperCase()) !== -1; });
    });
  }

  // Populate Contrato menu (preserve existing selections when possible)
  var prevSelected = getMsValues("filterContrato");
  const cMenu = document.getElementById("filterContratoMenu");
  if (cMenu) {
    cMenu.innerHTML = "";
    filteredContratos.sort().forEach((c) => {
      const lbl = document.createElement("label");
      lbl.className = "ms-option";
      var checked = prevSelected.indexOf(c) !== -1 ? " checked" : "";
      lbl.innerHTML = '<input type="checkbox" value="' + c + '"' + checked + ' onchange="onFilterChange()"> ' + c;
      cMenu.appendChild(lbl);
    });
  }

  // Populate sidebar Contrato menu (mirror of content-area)
  const sbCMenu = document.getElementById("sbFilterContratoMenu");
  if (sbCMenu) {
    sbCMenu.innerHTML = "";
    filteredContratos.sort().forEach(function(c) {
      var lbl = document.createElement("label");
      lbl.className = "sb-ms-option";
      var checked = prevSelected.indexOf(c) !== -1 ? " checked" : "";
      lbl.innerHTML = '<input type="checkbox" value="' + c + '"' + checked + ' onchange="syncSbFilter(\'contrato\',this)"> ' + c;
      sbCMenu.appendChild(lbl);
    });
  }

  // Sync sidebar checkboxes and labels
  syncMainToSidebar();
}

// EN: Show/hide C2 filters and populate menus (called when component or data changes)
// ES: Mostrar/ocultar filtros C2 y llenar menús (se llama cuando cambia el componente o los datos)
function updateC2FilterVisibility() {
  populateFilterMenus();
}

// EN: Legacy compatibility — called from session restore
function populateC2Contratos() { populateFilterMenus(); }

// EN: Clear all filters and refresh the view
// ES: Limpiar todos los filtros y actualizar la vista
function clearAllFilters() {
  currentPage = 1;
  c2GrantType = "";
  c2Contrato = "";
  // Uncheck all multi-select checkboxes (content-area + sidebar)
  document.querySelectorAll(".ms-menu input:checked, .sb-ms-menu input:checked").forEach((cb) => { cb.checked = false; });
  // Reset simple filters
  document.getElementById("filterMissingCode").checked = false;
  document.getElementById("filterHasShapefile").checked = false;
  document.getElementById("filterBadDate").checked = false;
  document.getElementById("filterCommentMonth").value = "";
  var codigoClr = document.getElementById("filterCodigo");
  if (codigoClr) codigoClr.value = "";
  // Reset sidebar simple filters
  var sbMC = document.getElementById("sbFilterMissingCode"); if (sbMC) sbMC.checked = false;
  var sbHS = document.getElementById("sbFilterHasShapefile"); if (sbHS) sbHS.checked = false;
  var sbBD = document.getElementById("sbFilterBadDate"); if (sbBD) sbBD.checked = false;
  // Reset row range to full sheet
  if (sheetData) {
    document.getElementById("rowStart").value = 1;
    document.getElementById("rowEnd").value   = sheetData.totalRows || sheetData.rows.length;
    var orc = document.getElementById("opRangeCount");
    if (orc) orc.textContent = "";
  }
  // Hide fix-dates button
  const btnFix = document.getElementById("btnFixDates");
  if (btnFix) btnFix.classList.add("hidden");
  // Update labels (content-area + sidebar)
  updateMsToggleLabel("filterTipo", "Tipo");
  updateMsToggleLabel("filterContrato", "Nº Contrato");
  updateMsToggleLabel("filterTrimestre", "Trimestre");
  updateMsToggleLabel("filterHectareas", "Hectáreas");
  updateMsToggleLabel("filterCalidadSIG", "Calidad SIG");
  syncMainToSidebar();
  // Hide clear button
  const clearBtn = document.getElementById("btnClearFilters");
  if (clearBtn) clearBtn.classList.add("hidden");

  populateFilterMenus();
  renderSheetTable();
  renderSummary();
  saveSessionState();
}

// EN: Kept for compatibility — banner no longer exists; no-op
function updateFilterBanner() {}

// ── Pagination ───────────────────────────────────────────────────────────────

function changePage(delta) {
  var totalPages = pageSize > 0 ? (Math.ceil(filteredRowNumbers.length / pageSize) || 1) : 1;
  currentPage = Math.max(1, Math.min(currentPage + delta, totalPages));
  renderSheetTable();
}

function changePageSize() {
  var sel = document.getElementById("pageSize");
  pageSize = parseInt(sel.value, 10);
  currentPage = 1;
  renderSheetTable();
}

async function c2ApplyFillDown() {
  if (!sheetData) return;
  const p = getParams();
  disable("btnC2ApplyFillDown", true);

  const data = await api("/api/smartsheet/fill-down", {
    component: p.component,
    rowStart: p.rowStart,
    rowEnd: p.rowEnd,
    columns: ["ORGANIZACIÓN", "TRIMESTRE QUE REPORTA"],
    c2GrantType: c2GrantType,
    c2Contrato: c2Contrato,
  });

  disable("btnC2ApplyFillDown", false);
  if (!data) return;
  log("Relleno guardado: " + data.updated + " celdas actualizadas.", "ok");
  patchSheetCache(data.patches || []);
}

function renderSheetTable() {
  if (!sheetData) return;

  const p           = getParams();
  const missingOnly = document.getElementById("filterMissingCode").checked;
  const shapeOnly   = document.getElementById("filterHasShapefile").checked;
  const commentMonth = document.getElementById("filterCommentMonth").value;
  const badDateOnly  = document.getElementById("filterBadDate").checked;
  const selHectareas = getMsValues("filterHectareas");
  const selCalidadSIG = getMsValues("filterCalidadSIG");

  const isC2 = p.component === "C2";

  const COLS = isC2
    ? [
        "NÚMERO DE CONTRATO",
        "ORGANIZACIÓN",
        "TRIMESTRE QUE REPORTA",
        "FECHA DE LA ACTIVIDAD",
        "CÓDIGO DE LA ACTIVIDAD",
        "Calidad SIG",
        "ACCIONES DE RESTAURACIÓN AbE",
        "TOTAL DE HECTÁREAS",
      ].filter((c) => sheetData.columns.includes(c))
    : [
        "FECHA DE LA ACTIVIDAD",
        "CÓDIGO DE LA ACTIVIDAD",
        "NOMBRE DE QUIEN REPORTA",
        "Calidad SIG",
        "ACCIONES DE RESTAURACIÓN AbE",
        "TOTAL DE HECTÁREAS",
      ].filter((c) => sheetData.columns.includes(c));

  let rows = sheetData.rows.slice();
  const totalRows = rows.length;

  // Row range: limit display to rows within [rowStart, rowEnd] (inclusive)
  // EN: "Aplicar rango" filters both display and operations
  // ES: "Aplicar rango" filtra tanto la vista como las operaciones
  const rrStart = parseInt(document.getElementById("rowStart").value) || 1;
  const rrEnd   = parseInt(document.getElementById("rowEnd").value)   || sheetData.totalRows || rows.length;
  rows = rows.filter((r) => r.rowNumber >= rrStart && r.rowNumber <= rrEnd);

  // C2 multi-select filters: Tipo, Contrato
  if (isC2) {
    const selTipos = getMsValues("filterTipo");
    const selContratos = getMsValues("filterContrato");

    if (selContratos.length > 0) {
      const cSet = new Set(selContratos);
      rows = rows.filter((r) => cSet.has(r.cells["NÚMERO DE CONTRATO"] || ""));
    } else if (selTipos.length > 0) {
      rows = rows.filter((r) => {
        const contrato = r.cells["NÚMERO DE CONTRATO"] || "";
        return selTipos.some((t) => contrato.includes(t));
      });
    }
  }
  // Trimestre filter: all components
  const selTrimestres = getMsValues("filterTrimestre");
  if (selTrimestres.length > 0) {
    const tSet = new Set(selTrimestres);
    rows = rows.filter((r) => tSet.has(r.cells["TRIMESTRE QUE REPORTA"] || ""));
  }

  if (missingOnly) {
    // Find rows missing code (with fecha), plus the first row of each
    // (NÚMERO DE CONTRATO + TRIMESTRE QUE REPORTA) group that contains missing-code rows
    const missingRows = rows.filter((r) => r.cells["FECHA DE LA ACTIVIDAD"] && !r.cells["CÓDIGO DE LA ACTIVIDAD"]);

    // Collect the (contrato, trimestre) groups that have missing-code rows
    const groupsNeeded = new Set();
    let mc_lastContrato = "", mc_lastTrimestre = "";
    missingRows.forEach((r) => {
      const c = r.cells["NÚMERO DE CONTRATO"] || "";
      if (c) mc_lastContrato = c;
      const t = r.cells["TRIMESTRE QUE REPORTA"] || "";
      if (t) mc_lastTrimestre = t;
      if (mc_lastContrato && mc_lastTrimestre) groupsNeeded.add(mc_lastContrato + "|" + mc_lastTrimestre);
    });

    // Find the first row of each needed group
    const groupFirstRows = new Set();
    let g_lastContrato = "", g_lastTrimestre = "", g_prevKey = "";
    rows.forEach((r) => {
      const c = r.cells["NÚMERO DE CONTRATO"] || "";
      if (c) g_lastContrato = c;
      const t = r.cells["TRIMESTRE QUE REPORTA"] || "";
      if (t) g_lastTrimestre = t;
      const key = g_lastContrato + "|" + g_lastTrimestre;
      if (key !== g_prevKey && groupsNeeded.has(key)) {
        groupFirstRows.add(r.rowNumber);
        g_prevKey = key;
      }
    });

    const missingRowNums = new Set(missingRows.map((r) => r.rowNumber));
    rows = rows.filter((r) => missingRowNums.has(r.rowNumber) || groupFirstRows.has(r.rowNumber));
  }
  // EN: "Con shapefile" and "Hectáreas" filters combine as OR —
  //     a row passes if it matches EITHER condition (when both are active).
  //     Other filters remain AND conditions.
  // ES: Los filtros "Con shapefile" y "Hectáreas" se combinan con OR —
  //     una fila pasa si cumple CUALQUIERA de las dos condiciones.
  //     Los demás filtros siguen siendo AND.
  const haFilterActive = selHectareas.length > 0 && selHectareas.length < 2;
  const haWantValue = haFilterActive && selHectareas.includes("con_valor");

  if (shapeOnly && haFilterActive) {
    // OR combination: keep rows that match shapefile OR hectáreas condition
    // EN: For C2 in OR mode, check individual row shapefile (no group expansion)
    //     so only summary rows with SHP pass via shapefile; child rows pass via hectáreas.
    // ES: Para C2 en modo OR, verificar shapefile en cada fila individual (sin expansión de grupo)
    //     así solo filas resumen con SHP pasan por shapefile; filas hijas pasan por hectáreas.
    rows = rows.filter((r) => {
      // Hectáreas condition
      const ha = parseFloat(r.cells["TOTAL DE HECTÁREAS"]);
      const hasHaVal = !isNaN(ha) && ha > 0;
      const passHa = haWantValue ? hasHaVal : !hasHaVal;
      // Shapefile condition — individual row check (works for both C2 and non-C2)
      const passShape = rowHasShapefile(r);
      return passShape || passHa;
    });
  } else if (shapeOnly) {
    if (isC2) {
      const shapeRows = rows.filter((r) => rowHasShapefile(r));
      const shapeGroups = new Set();
      let sf_lastContrato = "", sf_lastTrimestre = "";
      shapeRows.forEach((r) => {
        const c = r.cells["NÚMERO DE CONTRATO"] || "";
        if (c) sf_lastContrato = c;
        const t = r.cells["TRIMESTRE QUE REPORTA"] || "";
        if (t) sf_lastTrimestre = t;
        if (sf_lastContrato && sf_lastTrimestre) shapeGroups.add(sf_lastContrato + "|" + sf_lastTrimestre);
      });
      let eff_contrato = "", eff_trimestre = "";
      rows = rows.filter((r) => {
        const c = r.cells["NÚMERO DE CONTRATO"] || "";
        if (c) eff_contrato = c;
        const t = r.cells["TRIMESTRE QUE REPORTA"] || "";
        if (t) eff_trimestre = t;
        return shapeGroups.has(eff_contrato + "|" + eff_trimestre);
      });
    } else {
      rows = rows.filter((r) => rowHasShapefile(r));
    }
  } else if (haFilterActive) {
    rows = rows.filter((r) => {
      const ha = parseFloat(r.cells["TOTAL DE HECTÁREAS"]);
      const hasVal = !isNaN(ha) && ha > 0;
      return haWantValue ? hasVal : !hasVal;
    });
  }
  if (commentMonth) {
    if (sheetData.rows.every(function(r) { return !r.comment; })) {
      log("Primero cargue los comentarios / Load comments first", "warn");
    }
    rows = rows.filter((r) => r.comment && r.comment.date && r.comment.date.startsWith(commentMonth));
  }

  // EN: Calidad SIG multi-select filter
  // ES: Filtro multi-selección de Calidad SIG
  if (selCalidadSIG.length > 0) {
    const sigSet = new Set(selCalidadSIG);
    rows = rows.filter((r) => {
      const val = r.cells["Calidad SIG"];
      const normalized = (val == null || val === "") ? "" : String(val);
      return sigSet.has(normalized);
    });
  }

  // EN: Bad date filter — show rows where FECHA DE LA ACTIVIDAD is a text string, not ISO date
  // ES: Filtro de fecha errónea — muestra filas donde la fecha está almacenada como texto
  if (badDateOnly) {
    rows = rows.filter((r) => _isBadDate(r.cells["FECHA DE LA ACTIVIDAD"]));
  }

  // EN: Código search — case-insensitive substring match on CÓDIGO DE LA ACTIVIDAD
  // ES: Búsqueda por código — coincidencia parcial sin distinguir mayúsculas en CÓDIGO DE LA ACTIVIDAD
  const codigoEl = document.getElementById("filterCodigo");
  const codigoQ = codigoEl ? codigoEl.value.trim().toLowerCase() : "";
  if (codigoQ) {
    rows = rows.filter((r) => {
      const v = r.cells["CÓDIGO DE LA ACTIVIDAD"];
      return v != null && String(v).toLowerCase().includes(codigoQ);
    });
  }

  // Store filtered row numbers so listAttachments/batchDownload operate on visible rows only
  filteredRowNumbers = rows.map((r) => r.rowNumber);

  // EN: Batch-select set for diagnose table (UI-only, cleared after download)
  // ES: Conjunto de selección batch para tabla diagnose (solo UI, se limpia tras descarga)

  // ── Summary card update (removed — stats now only in summaryPanel) ──

  // ── Pagination ───────────────────────────────────────────────────────
  var displayRows = rows;
  var paginationBar = document.getElementById("paginationBar");
  if (pageSize > 0 && rows.length > pageSize) {
    var totalPages = Math.ceil(rows.length / pageSize);
    currentPage = Math.max(1, Math.min(currentPage, totalPages));
    var start = (currentPage - 1) * pageSize;
    displayRows = rows.slice(start, start + pageSize);
    document.getElementById("pageInfo").textContent = "Página " + currentPage + " de " + totalPages;
    paginationBar.style.display = "";
    document.getElementById("btnPrevPage").disabled = (currentPage <= 1);
    document.getElementById("btnNextPage").disabled = (currentPage >= totalPages);
  } else {
    paginationBar.style.display = "none";
  }

  let html = "<table><thead><tr><th>#</th><th>Forma</th>";
  COLS.forEach((c) => (html += "<th>" + c + "</th>"));
  html += "<th>Comentario</th>";
  html += "</tr></thead><tbody>";

  let fillLastContrato = "";
  let fillLastOrg = "";
  let fillLastTrimestre = "";

  displayRows.forEach((r) => {
    const missingCode = !r.cells["CÓDIGO DE LA ACTIVIDAD"];
    const hasShape    = rowHasShapefile(r);
    const hasFecha    = !!r.cells["FECHA DE LA ACTIVIDAD"];

    // Reset fill-down state when NÚMERO DE CONTRATO changes
    if (isC2) {
      const contrato = r.cells["NÚMERO DE CONTRATO"] || "";
      if (contrato && contrato !== fillLastContrato) {
        fillLastContrato = contrato;
        fillLastOrg = "";
        fillLastTrimestre = "";
      }
    }

    const isGroupHeader = missingOnly && !missingCode;
    const rowClass = isGroupHeader ? "row-group-header" : (missingCode ? "row-missing-code" : "");
    html += '<tr data-row="' + r.rowNumber + '"' + (rowClass ? ' class="' + rowClass + '"' : "") + ">";
    html += "<td>" + r.rowNumber + "</td>";
    html +=
      "<td>" +
      (hasShape ? '<span class="tag tag-shape">SHP</span>' : "") +
      "</td>";
    COLS.forEach((c) => {
      let val = r.cells[c] != null ? r.cells[c] : "";
      let cellClass = "";

      if (isC2 && c === "ORGANIZACIÓN") {
        if (val) { fillLastOrg = val; }
        else if (fillLastOrg && hasFecha) { val = fillLastOrg; cellClass = " cell-filled"; }
      }
      if (isC2 && c === "TRIMESTRE QUE REPORTA") {
        if (val) { fillLastTrimestre = val; }
        else if (fillLastTrimestre && hasFecha) { val = fillLastTrimestre; cellClass = " cell-filled"; }
      }

      const isMissingCol = c === "CÓDIGO DE LA ACTIVIDAD" && !val;
      if (isMissingCol) cellClass = " cell-missing";
      // Highlight bad-date cells
      if (c === "FECHA DE LA ACTIVIDAD" && _isBadDate(val)) cellClass += " cell-bad-date";
      html +=
        "<td" + (cellClass ? ' class="' + cellClass.trim() + '"' : "") + ">" +
        (isMissingCol ? "—" : val) +
        "</td>";
    });
    const cmt = r.comment;
    if (cmt) {
      html += '<td class="cell-comments">' +
        '<span class="comment-author">' + cmt.author + '</span> ' +
        '<span class="comment-date">' + cmt.date + '</span>: ' +
        cmt.text + "</td>";
    } else {
      html += "<td></td>";
    }
    html += "</tr>";
  });

  html += "</tbody></table>";

  document.getElementById("sheetPreviewContent").innerHTML = html;
  document.getElementById("filterCount").textContent =
    "Mostrando " +
    (pageSize > 0 && rows.length > pageSize ? displayRows.length + " de " + rows.length : rows.length) +
    " de " +
    totalRows +
    " filas";
}

// EN: Highlight a specific row in the Smartsheet table by row number.
// ES: Resaltar una fila específica en la tabla de Smartsheet por número de fila.
function highlightSmartsheetRow(rowNumber) {
  // Remove any previous highlight / Quitar resaltado previo
  document.querySelectorAll(".ss-highlight").forEach(function(el) {
    el.classList.remove("ss-highlight");
  });
  var table = document.getElementById("sheetPreviewContent");
  if (!table) return;
  var tr = table.querySelector('tr[data-row="' + rowNumber + '"]');
  if (tr) {
    tr.classList.add("ss-highlight");
    tr.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

async function generateCodes() {
  log("Generar Códigos: iniciando… / starting…", "info");
  try {
  if (!sheetData) {
    log("Cargando datos de la hoja primero…", "warn");
    await loadSheet();
    if (!sheetData) return;
  }

  const p = getParams();
  let filteredRows = sheetData.rows.filter(
    (r) => r.rowNumber >= p.rowStart && r.rowNumber <= p.rowEnd
  );
  log("Generar Códigos: " + filteredRows.length + " filas en rango " + p.rowStart + "–" + p.rowEnd, "info");
  // EN: Respect data view filters — only process visible rows
  // ES: Respetar filtros del visor de datos — solo procesar filas visibles
  if (filteredRowNumbers && filteredRowNumbers.length > 0) {
    var visibleSet = new Set(filteredRowNumbers);
    filteredRows = filteredRows.filter(function(r) { return visibleSet.has(r.rowNumber); });
    log("Generar Códigos: tras filtro visible = " + filteredRows.length + " filas", "info");
  }
  if (p.component === "C2" && c2Contrato) {
    filteredRows = filteredRows.filter((r) => (r.cells["NÚMERO DE CONTRATO"] || "") === c2Contrato);
    log("Generar Códigos: tras c2Contrato='" + c2Contrato + "' = " + filteredRows.length + " filas", "info");
  } else if (p.component === "C2" && c2GrantType) {
    filteredRows = filteredRows.filter((r) => {
      const contrato = r.cells["NÚMERO DE CONTRATO"] || "";
      return contrato.includes(c2GrantType);
    });
    log("Generar Códigos: tras c2GrantType='" + c2GrantType + "' = " + filteredRows.length + " filas", "info");
  }
  // EN: who field is required for code generation (ORGANIZACIÓN for C2, NOMBRE DE QUIEN REPORTA for C1/C3)
  // ES: El campo "quién" es obligatorio para generar códigos
  const whoCol = p.component === "C2" ? "ORGANIZACIÓN" : "NOMBRE DE QUIEN REPORTA";
  const allMissing = filteredRows.filter(
    (r) => r.cells["FECHA DE LA ACTIVIDAD"] && !r.cells["CÓDIGO DE LA ACTIVIDAD"]
  );
  const missingWho = allMissing.filter((r) => !r.cells[whoCol]);
  const candidates = allMissing.filter((r) => r.cells[whoCol]);
  log("Generar Códigos: allMissing=" + allMissing.length + ", candidates=" + candidates.length + ", missingWho=" + missingWho.length + " (whoCol='" + whoCol + "')", "info");

  if (candidates.length === 0 && missingWho.length === 0) {
    log("No hay filas sin código en el rango seleccionado.", "ok");
    return;
  }
  // EN: If rows are missing the who column, check if fill-down can resolve them
  // ES: Si faltan datos en la columna "quién", verificar si se pueden rellenar desde arriba
  const skipFD = window._skipFillDownCheck;
  window._skipFillDownCheck = false;
  if (missingWho.length > 0 && !skipFD) {
    const preview = await api("/api/smartsheet/fill-down-preview", {
      ...p,
      columns: [whoCol],
    });
    if (preview && preview.total_fillable > 0) {
      // Show fill-down confirmation panel
      let fdHtml = '<p class="hint" style="margin-bottom:10px">' +
        '<strong>' + missingWho.length + '</strong> fila(s) sin "' + whoCol +
        '", pero <strong>' + preview.total_fillable +
        '</strong> puede(n) rellenarse desde la fila superior del mismo grupo de contrato.' +
        ' / ' + missingWho.length + ' row(s) missing "' + whoCol +
        '", but <strong>' + preview.total_fillable +
        '</strong> can be filled from the upper row in the same contract group.</p>';
      fdHtml += '<div class="code-select-list">';
      (preview.fillable || []).forEach((f) => {
        fdHtml += '<div class="code-select-item">' +
          '<span class="code-row-num">#' + f.rowNumber + '</span>' +
          '<span class="code-row-info">' + f.column + ' ← <strong>' + f.value + '</strong></span>' +
          '</div>';
      });
      fdHtml += '</div>';
      if (preview.unfillable > 0) {
        fdHtml += '<p class="hint" style="margin-top:8px;color:var(--ar-blue-dark)">' +
          preview.unfillable + ' celda(s) vacía(s) no tienen valor superior para copiar.' +
          ' / ' + preview.unfillable + ' empty cell(s) have no upper value to copy from.</p>';
      }
      document.getElementById("fillDownContent").innerHTML = fdHtml;
      // Store context for the fill-down callback
      window._fillDownCtx = { params: p, whoCol: whoCol, columns: [whoCol] };
      show("fillDownPanel");
      document.getElementById("fillDownPanel").scrollIntoView({ behavior: "smooth" });
      return; // Wait for user confirmation via executeFillDown() or skipFillDown()
    }
    // Not fillable — warn and continue with whatever candidates exist
    if (candidates.length === 0) {
      log(
        missingWho.length + " fila(s) sin código encontrada(s), pero faltan datos en \"" +
          whoCol + "\" y no hay valor superior para copiar. Complete ese campo manualmente. / " +
          missingWho.length + " row(s) missing code found, but \"" +
          whoCol + "\" is empty and no upper value to fill from. Fill that column manually.",
        "warn"
      );
      return;
    }
    log(
      missingWho.length + " fila(s) omitida(s) por falta de \"" + whoCol +
        "\" (sin valor superior para rellenar). / " +
        missingWho.length + " row(s) skipped — missing \"" + whoCol + "\" (no upper value).",
      "warn"
    );
  }
  // EN: Handle skip-fill-down case: warn about missing rows
  if (skipFD && missingWho.length > 0) {
    if (candidates.length === 0) {
      log(
        missingWho.length + " fila(s) sin \"" + whoCol + "\". No hay candidatos válidos. / " +
          missingWho.length + " row(s) missing \"" + whoCol + "\". No valid candidates.",
        "warn"
      );
      return;
    }
    log(
      missingWho.length + " fila(s) omitida(s) por falta de \"" + whoCol + "\". / " +
        missingWho.length + " row(s) skipped — missing \"" + whoCol + "\".",
      "warn"
    );
  }

  let html =
    '<p class="hint" style="margin-bottom:10px">' +
    candidates.length +
    " filas sin código. Selecciona las que deseas actualizar:</p>" +
    '<div class="code-select-list">';

  candidates.forEach((r) => {
    const date     = r.cells["FECHA DE LA ACTIVIDAD"] || "";
    const who      = r.cells["NOMBRE DE QUIEN REPORTA"] ||
                     r.cells["ORGANIZACIÓN"] || "";
    const hasShape = rowHasShapefile(r);
    html +=
      '<label class="code-select-item">' +
      '<input type="checkbox" class="code-row-cb" value="' + r.id + '" checked>' +
      '<span class="code-row-num">#' + r.rowNumber + "</span>" +
      '<span class="code-row-info">' +
      date +
      (who ? " · " + who : "") +
      "</span>" +
      (hasShape ? ' <span class="tag tag-shape">ZIP</span>' : "") +
      "</label>";
  });
  html += "</div>";

  document.getElementById("codeSelectionContent").innerHTML = html;
  show("codeSelectionPanel");
  document
    .getElementById("codeSelectionPanel")
    .scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    log("Generar Códigos: ERROR — " + (err && err.message ? err.message : err), "err");
    console.error("generateCodes error:", err);
  }
}

function selectAllCodes(val) {
  document
    .querySelectorAll(".code-row-cb")
    .forEach((cb) => (cb.checked = val));
}

// EN: Execute fill-down, reload sheet, then re-run generateCodes
// ES: Ejecutar rellenado, recargar hoja, y reiniciar generación de códigos
async function executeFillDown() {
  const ctx = window._fillDownCtx;
  if (!ctx) return;
  disable("btnFillDown", true);
  log("Rellenando celdas vacías… / Filling empty cells…", "info");
  const data = await api("/api/smartsheet/fill-down", {
    ...ctx.params,
    columns: ctx.columns,
  });
  disable("btnFillDown", false);
  hide("fillDownPanel");
  window._fillDownCtx = null;
  if (!data) return;
  log(
    data.updated + " celda(s) rellenada(s). / " +
      data.updated + " cell(s) filled.",
    "ok"
  );
  // Patch local cache with filled values, then re-run generateCodes
  patchSheetCache(data.patches || []);
  await generateCodes();
}

function skipFillDown() {
  hide("fillDownPanel");
  const ctx = window._fillDownCtx;
  window._fillDownCtx = null;
  if (ctx) {
    log(
      "Rellenado omitido. Las filas sin \"" + ctx.whoCol +
        "\" no se incluirán en la generación. / " +
        "Fill-down skipped. Rows missing \"" + ctx.whoCol +
        "\" will not be included in code generation.",
      "warn"
    );
  }
  // Re-run generateCodes — this time missingWho will still exist but we need
  // to show code selection for whatever candidates are valid.
  // Set a flag to skip the fill-down check on re-entry
  window._skipFillDownCheck = true;
  generateCodes();
}

async function applySelectedCodes() {
  const selected = Array.from(
    document.querySelectorAll(".code-row-cb:checked")
  ).map((cb) => parseInt(cb.value, 10));

  if (selected.length === 0) {
    log("Ninguna fila seleccionada.", "warn");
    return;
  }

  disable("btnApplyCodes", true);
  const p    = getParams();
  const data = await api("/api/smartsheet/generate-codes", {
    ...p,
    rowIds: selected,
  });
  disable("btnApplyCodes", false);
  if (!data) return;

  // EN: Show generation result with diagnostics for skipped rows
  // ES: Mostrar resultado con diagnósticos de filas omitidas
  const sk = data.skipped || {};
  let msg = "Códigos generados para " + data.generated + " de " + selected.length + " filas seleccionadas.";
  if (data.generated === 0 && (sk.missing_who || sk.missing_date || sk.already_has_code)) {
    const parts = [];
    if (sk.missing_who)      parts.push(sk.missing_who + " sin \"" + (data.who_column || "?") + "\"");
    if (sk.missing_date)     parts.push(sk.missing_date + " sin fecha");
    if (sk.already_has_code) parts.push(sk.already_has_code + " ya tienen código");
    msg += " Razón: " + parts.join(", ") + ".";
  } else if (sk.missing_who || sk.missing_date) {
    const parts = [];
    if (sk.missing_who)  parts.push(sk.missing_who + " sin \"" + (data.who_column || "?") + "\"");
    if (sk.missing_date) parts.push(sk.missing_date + " sin fecha");
    msg += " (" + parts.join(", ") + " omitida(s))";
  }
  log(msg, data.generated > 0 ? "ok" : "warn");
  hide("codeSelectionPanel");
  patchSheetCache(data.patches || []);
  advanceStep();
}

async function updateReview() {
  disable("btnReview", true);
  const p    = getParams();
  // EN: Send filtered row numbers so backend only updates visible rows
  // ES: Enviar números de fila filtrados para que el backend solo actualice filas visibles
  if (filteredRowNumbers && filteredRowNumbers.length > 0) {
    p.rowNumbers = filteredRowNumbers;
  }
  const data = await api("/api/smartsheet/update-review", p);
  disable("btnReview", false);
  if (!data) return;

  log(
    "Revisión actualizada: " +
      data.updated +
      " filas cambiadas" +
      (data.espera != null
        ? " (" + data.espera + " → Espera, " + data.si + " → Sí)"
        : "") +
      ".",
    data.updated > 0 ? "ok" : "warn"
  );

  // EN: Show diagnostics when no changes were made
  // ES: Mostrar diagnóstico cuando no hubo cambios
  var d = data.diagnostics;
  if (d) {
    var lines = [];
    lines.push("Diagnóstico / Diagnostics: " + d.totalRows + " filas evaluadas");
    if (d.noCode > 0) {
      var noCodeMsg = "· " + d.noCode + " sin CÓDIGO DE LA ACTIVIDAD";
      if (d.noCodeCleared > 0)
        noCodeMsg += " (" + d.noCodeCleared + " Calidad SIG → null)";
      else
        noCodeMsg += " (omitidas / skipped)";
      lines.push(noCodeMsg);
    }
    if (d.manualRating > 0)
      lines.push("· " + d.manualRating + " con calificación manual (Rojo/Amarillo/Verde, preservadas)");
    if (d.alreadyCorrect > 0) {
      var detail = [];
      if (d.alreadyDetail && d.alreadyDetail["Espera"])
        detail.push(d.alreadyDetail["Espera"] + " Espera");
      if (d.alreadyDetail && d.alreadyDetail["Sí"])
        detail.push(d.alreadyDetail["Sí"] + " Sí");
      lines.push("· " + d.alreadyCorrect + " ya tienen el valor correcto" +
        (detail.length ? " (" + detail.join(", ") + ")" : ""));
    }
    if (d.withShapefile > 0)
      lines.push("· " + d.withShapefile + " filas con shapefile ZIP adjunto");

    var html = escapeHtml(lines.join("\n")).replace(/\n/g, "<br>");

    // EN: If rows with codes exist (beyond those already correct), offer bulk override buttons
    // ES: Si hay filas con código (más allá de las ya correctas), ofrecer botones de cambio masivo
    if (d.withShapefile > 0 || d.evaluated - d.noCode - d.alreadyCorrect > 0) {
      html += '<div style="margin-top:6px;font-size:12px;">' +
        '<span style="margin-right:4px;">Cambiar Calidad SIG de filas con código a:</span>' +
        '<button class="log-action-btn" onclick="setCalidadBulk(\'Espera\')">Espera</button> ' +
        '<button class="log-action-btn" onclick="setCalidadBulk(\'Sí\')">Sí</button> ' +
        '<button class="log-action-btn" onclick="setCalidadBulk(\'\')">Limpiar / Clear</button>' +
        '</div>';
    }
    logHtml(html, "info");
  }

  patchSheetCache(data.patches || []);
  advanceStep();
}

// EN: Bulk-set Calidad SIG for rows with activity code
// ES: Cambiar Calidad SIG masivamente para filas con código de actividad
async function setCalidadBulk(value) {
  const p = getParams();
  p.value = value;
  p.target = "all";
  // EN: Send currently visible row numbers so backend only updates filtered rows
  // ES: Enviar números de fila visibles para que el backend solo actualice filas filtradas
  if (filteredRowNumbers && filteredRowNumbers.length > 0) {
    p.rowNumbers = filteredRowNumbers;
  }
  log("Actualizando Calidad SIG → " + (value || "(vacío)") + " en filas con código …");
  const data = await api("/api/smartsheet/set-calidad", p);
  if (!data) return;
  log(
    "Calidad SIG actualizada: " + data.updated + " filas → " + (data.value || "(vacío)") + ".",
    data.updated > 0 ? "ok" : "warn"
  );
  // EN: Show diagnostics when no changes were made
  // ES: Mostrar diagnóstico cuando no hubo cambios
  var d = data.diagnostics;
  if (d && data.updated === 0) {
    var lines = [];
    lines.push("Diagnóstico / Diagnostics: " + d.totalRows + " filas evaluadas");
    if (d.noCode > 0)
      lines.push("· " + d.noCode + " sin CÓDIGO DE LA ACTIVIDAD (omitidas / skipped)");
    if (d.noShapefile > 0)
      lines.push("· " + d.noShapefile + " sin shapefile ZIP adjunto (omitidas / skipped)");
    if (d.alreadyCorrect > 0)
      lines.push("· " + d.alreadyCorrect + " ya tienen el valor " + (data.value || "(vacío)"));
    log(lines.join("\n"), "info");
  }
  patchSheetCache(data.patches || []);
  // Refresh table to show updated values
  renderSheetTable();
  renderSummary();
}

async function listAttachments() {
  disable("btnAttach", true);
  const p    = getParams();
  // EN: Send filtered row numbers so backend only returns attachments for visible rows
  // ES: Enviar números de fila filtrados para que el backend solo devuelva adjuntos de filas visibles
  if (filteredRowNumbers) p.rowNumbers = filteredRowNumbers;
  const data = await api("/api/smartsheet/attachments", p);
  disable("btnAttach", false);
  if (!data) return;

  attachmentsData = data;
  let html  = "";
  let total = 0;

  var container = document.getElementById("attachmentsContent");
  if (!data.rows || data.rows.length === 0) {
    container.innerHTML =
      '<p class="hint">No se encontraron adjuntos en el rango seleccionado.</p>';
  } else {
    container.innerHTML = "";
    data.rows.forEach((r) => {
      var rowDiv = document.createElement("div");
      rowDiv.className = "att-row";
      var rowNum = document.createElement("span");
      rowNum.className = "att-row-num";
      rowNum.textContent = "Fila " + r.rowNumber;
      rowDiv.appendChild(rowNum);
      r.attachments.forEach((a) => {
        var isShape = isShapefileZip(a.name);
        var nameSpan = document.createElement("span");
        nameSpan.className = "att-link" + (isShape ? " is-shape" : "");
        nameSpan.textContent = (isShape ? "⬡ " : "") + a.name;
        rowDiv.appendChild(nameSpan);
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn-sm download-btn";
        btn.textContent = "Descargar";
        btn.addEventListener("click", (function(sid, aid, aname) {
          return function() { downloadAtt(sid, aid, aname); };
        })(data.sheetId, a.id, a.name));
        rowDiv.appendChild(btn);
        total++;
      });
      container.appendChild(rowDiv);
    });
  }
  show("attachmentsList");
  log("Se encontraron " + total + " archivo(s) adjunto(s).", "ok");
  advanceStep();
}

// ══════════════════════════════════════════════════════════════════════
// PASO 1b – Descarga
// ══════════════════════════════════════════════════════════════════════

function normalizeQuarterGroupName(value) {
  return (value || "").trim().replace(/^T(?=\d{4}_Q[1-4]$)/, "");
}

function refreshWorkQuarterInfo(selectedValue) {
  var normalized = normalizeQuarterGroupName(selectedValue);
  var es = normalized
    ? "ArcGIS Pro usará los grupos " + normalized + ", " + normalized + "_point y " + normalized + "_polygon."
    : "Seleccione el trimestre antes del componente. El batch ubicará shapefiles en los grupos de ArcGIS Pro del trimestre elegido.";
  var en = normalized
    ? "ArcGIS Pro will use the groups " + normalized + ", " + normalized + "_point, and " + normalized + "_polygon."
    : "Select the quarter before the component. Batch placement will target the ArcGIS Pro groups for the chosen quarter.";

  ["workQuarterInfo", "sbWorkQuarterInfo"].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = i18n(es, en);
  });
}

function setWorkQuarterValue(value, options) {
  var config = options || {};
  var main = document.getElementById("workQuarter");
  var sidebar = document.getElementById("sbWorkQuarter");
  var chosen = (value || "").trim();

  if (main) {
    main.value = chosen;
    chosen = main.value || "";
  }
  if (sidebar) sidebar.value = chosen;

  refreshWorkQuarterInfo(chosen);
  if (!config.skipSave) saveSessionState();
  return chosen;
}

function handleWorkQuarterChange() {
  var main = document.getElementById("workQuarter");
  setWorkQuarterValue(main ? main.value : "");
}

function syncWorkQuarterFromSidebar() {
  var sidebar = document.getElementById("sbWorkQuarter");
  setWorkQuarterValue(sidebar ? sidebar.value : "");
}

// EN: Populate work-quarter dropdowns with previous 2 + current + next 1 quarter.
// ES: Poblar los desplegables de trimestre con 2 previos + actual + 1 siguiente.
function populateQuarterDropdown(preferredValue) {
  const selects = [
    document.getElementById("workQuarter"),
    document.getElementById("sbWorkQuarter")
  ].filter(Boolean);
  if (!selects.length) return;

  const monthRanges = { 1: "Ene–Mar", 2: "Abr–Jun", 3: "Jul–Sep", 4: "Oct–Dic" };
  const today = new Date();
  const currentYear = today.getFullYear();
  const currentQuarter = Math.floor(today.getMonth() / 3) + 1;
  const offsets = [-2, -1, 0, 1];

  const options = offsets.map(function(offset) {
    let year = currentYear;
    let quarter = currentQuarter + offset;
    while (quarter < 1) {
      quarter += 4;
      year -= 1;
    }
    while (quarter > 4) {
      quarter -= 4;
      year += 1;
    }
    return {
      value: "T" + year + "_Q" + quarter,
      label: year + " T" + quarter + " (" + monthRanges[quarter] + ")"
    };
  });

  selects.forEach(function(sel) {
    sel.innerHTML = "";
    var blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "(sin trimestre)";
    sel.appendChild(blank);
    options.forEach(function(item) {
      var opt = document.createElement("option");
      opt.value = item.value;
      opt.textContent = item.label;
      sel.appendChild(opt);
    });
  });

  var preferred = (preferredValue || "").trim();
  var chosen = options[2] ? options[2].value : "";
  if (preferred && options.some(function(item) { return item.value === preferred; })) {
    chosen = preferred;
  }
  setWorkQuarterValue(chosen, { skipSave: true });
}

function getWorkQuarter() {
  const sel = document.getElementById("workQuarter");
  return sel ? sel.value.trim() : "";
}

function getDestFolderMode() {
  var manualRadio = document.getElementById("destFolderModeManual");
  return manualRadio && manualRadio.checked ? "manual" : "auto";
}

function getEnvDestFolder(component) {
  if (!window._envFolders) return "";
  var selectedComponent = component || document.getElementById("component").value;
  return window._envFolders["FOLDER_" + selectedComponent]
    || window._envFolders.SMARTSHEET_ATTACH_DIR
    || "";
}

function refreshDestFolderUi() {
  var destFolderField = document.getElementById("destFolder");
  var destFolderHint = document.getElementById("destFolderHint");
  var destFolderAutoPath = document.getElementById("destFolderAutoPath");
  if (!destFolderField) return;

  var selectedComponent = document.getElementById("component").value;
  var isManualMode = getDestFolderMode() === "manual";
  var autoFolder = getEnvDestFolder(selectedComponent);

  destFolderField.readOnly = !isManualMode;
  destFolderField.classList.toggle("is-readonly", !isManualMode);

  if (destFolderHint) {
    destFolderHint.textContent = isManualMode
      ? "Ingrese una ruta manual. Debe estar dentro de una carpeta permitida en .env."
      : "Usa la ruta configurada en .env para el componente seleccionado.";
  }
  if (destFolderAutoPath) {
    destFolderAutoPath.textContent = autoFolder
      ? "Ruta automática: " + autoFolder
      : "Ruta automática: no configurada en .env";
  }
  // Mirror to sidebar path display
  var sbPath = document.getElementById("sbDestFolderPath");
  if (sbPath) {
    sbPath.textContent = autoFolder ? ".env: " + autoFolder : "(.env no configurada)";
  }
  // Keep sidebar folder input in sync (only if user hasn't typed a custom value)
  var sbFolder = document.getElementById("sbDestFolder");
  if (sbFolder && !sbFolder.matches(":focus")) {
    var effectiveVal = isManualMode ? destFolderField.value : "";
    sbFolder.value = effectiveVal;
    sbFolder.placeholder = autoFolder || "(automático desde .env)";
  }
  // Keep sidebar component selector in sync
  var sbComp = document.getElementById("sbComponent");
  if (sbComp && sbComp.value !== selectedComponent) {
    sbComp.value = selectedComponent;
  }
}

function setDestFolderMode(mode, options) {
  var config = options || {};
  var normalizedMode = mode === "manual" ? "manual" : "auto";
  var autoRadio = document.getElementById("destFolderModeAuto");
  var manualRadio = document.getElementById("destFolderModeManual");
  var destFolderField = document.getElementById("destFolder");
  if (!destFolderField) return;

  if (autoRadio) autoRadio.checked = normalizedMode === "auto";
  if (manualRadio) manualRadio.checked = normalizedMode === "manual";

  if (normalizedMode === "auto") {
    destFolderField.value = getEnvDestFolder();
    destFolderField.dataset.userModified = "";
  } else if (destFolderField.value.trim()) {
    destFolderField.dataset.userModified = "1";
  }

  refreshDestFolderUi();
  if (!config.skipSave) saveSessionState();
}

function restoreDestFolderState() {
  var restoredMode = window._restoreDestFolderMode || "auto";
  var restoredValue = window._restoreDestFolderValue || "";
  var destFolderField = document.getElementById("destFolder");
  if (!destFolderField) return;

  setDestFolderMode(restoredMode, { skipSave: true });
  if (restoredMode === "manual" && restoredValue) {
    destFolderField.value = restoredValue;
    destFolderField.dataset.userModified = "1";
  }
  refreshDestFolderUi();
}

// Sync sidebar component selector → hidden #component + update folders
function syncComponentFromSidebar() {
  var sb = document.getElementById("sbComponent");
  var main = document.getElementById("component");
  if (sb && main) {
    main.value = sb.value;
  }
  updateDestFolderFromEnv();
  // EN: Update filter visibility for new component (Tipo/Contrato C2-only, Trimestre always)
  // ES: Actualizar visibilidad de filtros para nuevo componente
  populateFilterMenus();
}

// Sync sidebar dest-folder input → hidden #destFolder
function syncDestFolderFromSidebar() {
  var sbInput = document.getElementById("sbDestFolder");
  var mainInput = document.getElementById("destFolder");
  if (!sbInput || !mainInput) return;
  var val = sbInput.value.trim();
  if (val) {
    // User override — switch to manual mode
    setDestFolderMode("manual", { skipSave: true });
    mainInput.value = val;
    mainInput.dataset.userModified = "1";
  } else {
    // Cleared — revert to .env default
    setDestFolderMode("auto", { skipSave: true });
    mainInput.value = getEnvDestFolder();
    mainInput.dataset.userModified = "";
  }
  refreshDestFolderUi();
  saveSessionState();
}

function updateDestFolderFromEnv() {
  if (!window._envFolders) return;
  var destFolderField = document.getElementById("destFolder");
  if (!destFolderField) return;

  if (getDestFolderMode() === "manual") {
    refreshDestFolderUi();
    saveSessionState();
    return;
  }

  destFolderField.value = getEnvDestFolder();
  destFolderField.dataset.userModified = "";
  refreshDestFolderUi();
  saveSessionState();
}

function handleDestFolderInput() {
  var destFolderField = document.getElementById("destFolder");
  if (!destFolderField) return;
  if (getDestFolderMode() !== "manual") {
    setDestFolderMode("manual", { skipSave: true });
  }
  destFolderField.dataset.userModified = destFolderField.value.trim() ? "1" : "";
  saveSessionState();
}

function getDestFolder() {
  return document.getElementById("destFolder").value.trim() || "";
}

async function exportCSV() {
  disable("btnExportCSV", true);
  const p = getParams();
  p.destFolder = getDestFolder();
  const data = await api("/api/smartsheet/export-csv", p);
  disable("btnExportCSV", false);
  if (!data) return;

  log("CSV exportado: " + data.file + " (" + data.rows + " filas).", "ok");
  document.getElementById("downloadContent").innerHTML =
    "<p>Guardado en: <code>" + displayPath(data.path) + "</code></p>";
  show("downloadResult");
  document.getElementById("csvPath").value = data.path;
  advanceStep();
}

async function downloadAtt(sheetId, attId, name) {
  log("Descargando " + name + " …");
  const data = await api("/api/smartsheet/download-attachment", {
    sheetId,
    attachmentId: attId,
    destFolder: getDestFolder(),
  });
  if (!data) return;
  log("Descargado: " + data.downloaded + " (" + data.size + " bytes).", "ok");
}


async function batchDownload(forceResume) {
  disable("btnBatchDL", true);
  const p = getParams();
  if (filteredRowNumbers) p.rowNumbers = filteredRowNumbers;
  p.destFolder = getDestFolder();

  // If the operator has selected specific rows via the diagnose batch checkboxes,
  // narrow the download to only those rows (overrides the row-range filter).
  // ES: Si el operador seleccionó filas en diagnose, descarga solo esas filas.
  if (_batchSelectedIds.size > 0) {
    var batchRows = [];
    var batchRowSet = new Set();
    _batchSelectedIds.forEach(function(itemId) {
      // C2 individual child row selection (e.g. "C2_child_1109")
      if (itemId.startsWith("C2_child_")) {
        var rn = parseInt(itemId.replace("C2_child_", ""));
        if (!isNaN(rn) && !batchRowSet.has(rn)) { batchRowSet.add(rn); batchRows.push(rn); }
        return;
      }
      var item = AgentController.items.find(function(i) { return i.id === itemId; });
      if (!item) return;
      if (item.rowNumber != null && !batchRowSet.has(item.rowNumber)) {
        batchRowSet.add(item.rowNumber); batchRows.push(item.rowNumber);
      }
      // C2 groups: also include all child row numbers so every SHP row is downloaded
      // ES: Grupos C2: incluir todos los números de fila hijas para descargar todos los SHP
      if (item.child_rows) {
        item.child_rows.forEach(function(cr) {
          if (cr.rowNumber != null && !batchRowSet.has(cr.rowNumber)) {
            batchRowSet.add(cr.rowNumber); batchRows.push(cr.rowNumber);
          }
        });
      }
    });
    if (batchRows.length > 0) {
      p.rowNumbers = batchRows;
      log("[P1-a] Descarga batch limitada a " + batchRows.length + " filas seleccionadas / Batch limited to " + batchRows.length + " selected rows.");
    }
  }
  const q = getWorkQuarter();
  if (!q) {
    log({es: "Seleccione un trimestre de trabajo antes de descargar.", en: "Select a work quarter before downloading."}, "warn");
    disable("btnBatchDL", false);
    return;
  }
  p.quarter = q;

  // EN: Check for existing checkpoint unless explicitly starting fresh
  // ES: Verificar checkpoint existente a menos que se inicie desde cero
  if (!forceResume && forceResume !== false) {
    const ckpt = await api("/api/smartsheet/batch-checkpoint", {
      destFolder: p.destFolder, quarter: p.quarter || "", component: p.component,
    });
    if (ckpt && ckpt.exists) {
      log(
        "Descarga interrumpida detectada: " + ckpt.completed + "/" + ckpt.total +
        " archivos completados. / Interrupted download detected.",
        "warn"
      );
      logHtml(
        '<button class="log-action-btn" onclick="batchDownload(true)">Reanudar / Resume</button> ' +
        '<button class="log-action-btn" onclick="batchDownload(false)">Reiniciar / Restart</button>',
        "warn"
      );
      disable("btnBatchDL", false);
      return;
    }
  }

  if (forceResume === true) {
    p.resume = true;
    log("Reanudando descarga… / Resuming download…");
  }

  const data = await api("/api/smartsheet/batch-download", p);
  disable("btnBatchDL", false);
  if (!data) return;

  // EN: Build summary line showing resumed/skipped info
  // ES: Línea de resumen con info de reanudación
  let summary = "Batch download: " + data.downloaded + " archivos, " + data.valid + " válidos";
  if (data.skipped > 0) {
    summary += ", " + data.skipped + " omitidos (ya descargados / already downloaded)";
  }
  summary += ".";
  log(summary, data.valid === data.downloaded ? "ok" : "warn");
  if (data.dest_folder) {
    log("Guardado en / Saved to: " + data.dest_folder, "ok");
  }

  // Auto-clear diagnose batch selections after successful download
  // ES: Limpiar selecciones batch de diagnose después de descarga exitosa
  if (_batchSelectedIds.size > 0) {
    _clearAllBatchSelections();
    log("[P1-a] Selecciones batch limpiadas. / Batch selections cleared.");
  }

  let html = "<h4>Resultados de Descarga Batch</h4><table><thead><tr>" +
    "<th>Archivo</th><th>Fila</th><th>Estado</th><th>Shapefiles</th></tr></thead><tbody>";
  (data.results || []).forEach((r) => {
    html += "<tr><td>" + escapeHtml(r.name) + "</td><td>" + escapeHtml(r.row || "-") + "</td>" +
      '<td class="' + (r.ok ? "cell-ok" : "cell-err") + '">' +
      (r.ok ? "OK" : "Error") + "</td>" +
      "<td>" + (r.shapefiles || []).map(escapeHtml).join(", ") + "</td></tr>";
  });
  html += "</tbody></table>";

  // EN: Show ABE validation warnings if any
  // ES: Mostrar advertencias de validación AbE si las hay
  if (data.abe_warnings && data.abe_warnings.length > 0) {
    html += '<div class="abe-warnings" style="margin-top:1rem;padding:0.75rem 1rem;' +
      'border-left:4px solid var(--ar-warning,#e6a817);background:var(--ar-warning-bg,#fef9e7);">';
    html += '<h4 style="margin:0 0 0.5rem">&#9888; Valores AbE no v\u00e1lidos en Smartsheet / Invalid AbE values in Smartsheet (' +
      data.abe_warnings.length + ')</h4>';
    html += '<table style="width:100%;font-size:0.9em"><thead><tr>' +
      '<th>Fila / Row</th><th>Identificador</th><th>Valor AbE actual / Current AbE</th>' +
      '<th>Acci\u00f3n / Action</th></tr></thead><tbody>';
    data.abe_warnings.forEach(function(w) {
      html += '<tr><td><strong>' + escapeHtml(String(w.row)) + '</strong></td>' +
        '<td>' + escapeHtml(w.identifier || '') + '</td>' +
        '<td class="text-error">' + escapeHtml(w.abe_value || '(vac\u00edo)') + '</td>' +
        '<td>Corregir en Smartsheet / Fix in Smartsheet</td></tr>';
    });
    html += '</tbody></table></div>';
    log("AbE: " + data.abe_warnings.length + " fila(s) con valores no v\u00e1lidos \u2014 corregir en Smartsheet / " +
        data.abe_warnings.length + " row(s) with invalid values \u2014 fix in Smartsheet", "warn");
  }

  document.getElementById("downloadContent").innerHTML = html;
  show("downloadResult");
  updatePipelineStep("1b", "success");
  updatePipelineStep(3, "active");

  // EN: Collect shapefile folders from batch results for ArcPy add-to-map
  // ES: Recopilar carpetas de shapefiles de los resultados para agregar al mapa
  var batchShpFolders = [];
  (data.results || []).forEach(function(r) {
    if (r.ok && r.folder && batchShpFolders.indexOf(r.folder) === -1) {
      batchShpFolders.push(r.folder);
    }
  });
  window._lastBatchShpFolders = batchShpFolders;

  // EN: If valid shapefiles were downloaded, show button to generate ArcPy map-add script
  // ES: Si se descargaron shapefiles válidos, mostrar botón para generar script ArcPy
  if (data.valid > 0) {
    logHtml(
      '<button class="log-action-btn" onclick="runAddToMapScript()">' +
      'Ejecutar: Agregar al mapa ArcGIS Pro / Run: Add to ArcGIS Pro map</button> ' +
      '<button class="log-action-btn btn-outline" onclick="genAddToMapScript()">' +
      'Ver script / View script</button>',
      "ok"
    );
  }
}


async function runAddToMapScript() {
  // EN: Show warning about ArcGIS Pro before executing
  // ES: Mostrar advertencia sobre ArcGIS Pro antes de ejecutar
  logHtml(
    '<div class="log-arcpro-warning">' +
    '<strong>IMPORTANTE / IMPORTANT:</strong><br>' +
    'ArcGIS Pro debe estar cerrado para agregar shapefiles al mapa.<br>' +
    'ArcGIS Pro must be closed to add shapefiles to the map.<br><br>' +
    'Si tiene trabajo sin guardar en ArcGIS Pro, <strong>guarde y cierre manualmente</strong> antes de continuar.<br>' +
    'If you have unsaved work in ArcGIS Pro, <strong>save and close manually</strong> before proceeding.<br><br>' +
    '<em>Al confirmar, el sistema cerrara ArcGIS Pro automaticamente.</em><br>' +
    '<em>Upon confirmation, the system will close ArcGIS Pro automatically.</em><br><br>' +
    '<button class="log-action-btn btn-danger" onclick="confirmRunAddToMap()">' +
    'Confirmar: Cerrar Pro y ejecutar / Confirm: Close Pro & run</button> ' +
    '<button class="log-action-btn btn-outline" onclick="genAddToMapScript()">' +
    'Solo ver script / View script only</button>' +
    '</div>',
    "warn"
  );
}

async function confirmRunAddToMap() {
  // EN: Close ArcGIS Pro, then execute ArcPy script
  // ES: Cerrar ArcGIS Pro, luego ejecutar script ArcPy

  // EN: Disable all ArcPy action buttons to prevent duplicate runs
  // ES: Desactivar todos los botones ArcPy para evitar ejecuciones duplicadas
  document.querySelectorAll('.log-arcpro-warning button').forEach(function(b) { b.disabled = true; });

  log("Cerrando ArcGIS Pro... / Closing ArcGIS Pro...");
  var closeResult = await api("/api/arcpy/close-pro", {});
  if (!closeResult) return;
  if (closeResult.wasRunning) {
    log({es: "ArcGIS Pro cerrado.", en: "ArcGIS Pro closed."}, "ok");
  } else {
    log({es: "ArcGIS Pro no estaba abierto.", en: "ArcGIS Pro was not open."}, "info");
  }

  var p = {
    destFolder: getDestFolder(),
    quarter: getWorkQuarter() || "",
    component: document.getElementById("component").value,
  };
  // EN: Pass specific folders from last batch download if available
  // ES: Pasar carpetas específicas del último batch download si están disponibles
  if (window._lastBatchShpFolders && window._lastBatchShpFolders.length > 0) {
    p.shpFolders = window._lastBatchShpFolders;
  }
  log({es: "Ejecutando script ArcPy...", en: "Running ArcPy script..."});
  var result = await api("/api/arcpy/run-add-to-map", p);
  if (!result) return;
  if (result.ok) {
    log({es: "Shapefiles agregados al mapa ArcGIS Pro exitosamente.", en: "Shapefiles added to ArcGIS Pro map successfully."}, "ok");
    if (result.stdout) {
      log(result.stdout);
      // Check for CdgActvdd no-match review warning
      if (result.stdout.indexOf("REVIEW NEEDED") >= 0) {
        var reviewBlock = result.stdout.substring(result.stdout.indexOf("REVIEW NEEDED"), result.stdout.indexOf("REVIEW NEEDED") + 500);
        var ssMatch = reviewBlock.match(/Smartsheet: (https:\/\/[^\s]+)/);
        var ssLink = ssMatch ? ssMatch[1] : "";
        var rowMatch = reviewBlock.match(/SummaryRow: (\d+)/);
        var rowNum = rowMatch ? rowMatch[1] : "";
        log({es: "⚠ CdgActvdd sin coincidencia — requiere revisión manual", en: "⚠ CdgActvdd no match — manual review needed"}, "warn");
        if (ssLink || rowNum) {
          var linkHtml = '';
          if (ssLink) linkHtml += '<a href="' + escapeHtml(ssLink) + '" target="_blank" style="color:#e8a500;text-decoration:underline;font-weight:bold">Abrir Smartsheet ↗</a>';
          if (rowNum) linkHtml += (ssLink ? ' ' : '') + '<a href="javascript:void(0)" onclick="highlightSmartsheetRow(' + rowNum + ')" style="color:#e8a500;text-decoration:underline;font-weight:bold">' + i18nRaw('→ Ir a fila ' + rowNum, '→ Go to row ' + rowNum) + '</a>';
          logHtml(linkHtml);
        }
      }
    }
    // EN: Offer to reopen ArcGIS Pro
    // ES: Ofrecer reabrir ArcGIS Pro
    logHtml(
      '<button class="log-action-btn" onclick="reopenArcGISPro()">' +
      i18nRaw('Reabrir ArcGIS Pro', 'Reopen ArcGIS Pro') + '</button> ' +
      '<span style="font-size:12px;opacity:0.7;">' +
      i18nRaw('(o continuar con mas filas antes de reabrir)', '(or continue with more rows before reopening)') + '</span>',
      "ok"
    );
  } else {
    log({es: "Error al ejecutar script ArcPy.", en: "Error running ArcPy script."}, "err");
    if (result.stderr) {
      log(result.stderr, "err");
    }
    if (result.stdout) {
      log(result.stdout, "warn");
    }
    // EN: Show the script so user can copy and run manually
    // ES: Mostrar el script para que el usuario lo copie y ejecute manualmente
    if (result.script) {
      logHtml(
        '<button class="log-action-btn btn-outline" onclick="genAddToMapScript()">' +
        'Ver script para ejecucion manual / View script for manual execution</button>',
        "warn"
      );
    }
  }
}

async function reopenArcGISPro() {
  log("Abriendo ArcGIS Pro... / Opening ArcGIS Pro...");
  var result = await api("/api/arcpy/open-pro", {});
  if (result && result.ok) {
    log("ArcGIS Pro abierto. / ArcGIS Pro opened.", "ok");
  } else {
    log("No se pudo abrir ArcGIS Pro. / Could not open ArcGIS Pro.", "err");
  }
}

async function genAddToMapScript() {
  // EN: Generate ArcPy script to add downloaded shapefiles into ArcGIS Pro map group layers
  // ES: Generar script ArcPy para agregar shapefiles descargados a group layers del mapa
  var p = {
    destFolder: getDestFolder(),
    quarter: getWorkQuarter() || "",
    component: document.getElementById("component").value,
  };
  // EN: Pass specific folders from last batch download if available
  // ES: Pasar carpetas específicas del último batch download si están disponibles
  if (window._lastBatchShpFolders && window._lastBatchShpFolders.length > 0) {
    p.shpFolders = window._lastBatchShpFolders;
  }
  var result = await api("/api/smartsheet/add-to-map-script", p);
  if (!result) return;
  log("Script generado: " + result.folders + " carpeta(s) con shapefiles. / Script generated: " + result.folders + " folder(s) with shapefiles.", "ok");
  showScriptModal(result.script, "PASO 1b: Agregar shapefiles al mapa / Add shapefiles to map");
}


// ── Mostrar script en modal / Show script in modal ───────────────────
function showScriptModal(scriptText, title) {
  let modal = document.getElementById("scriptModal");
  if (!modal) {
    modal = document.createElement("div");
    modal.id = "scriptModal";
    modal.className = "script-modal-overlay";
    modal.innerHTML = `
      <div class="script-modal">
        <div class="script-modal-hd">
          <h3 id="scriptModalTitle" class="script-modal-title"></h3>
          <button class="script-modal-close" onclick="closeScriptModal()" aria-label="Cerrar / Close">✕</button>
        </div>
        <div class="script-modal-body">
          <div class="script-modal-actions">
            <button class="btn-sm btn-outline" onclick="copyScriptToClipboard()">
              📋 Copiar / Copy
            </button>
            <button class="btn-sm btn-outline" onclick="downloadScript()">
              ⬇ Descargar / Download
            </button>
          </div>
          <pre id="scriptModalCode" class="script-code"></pre>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }
  document.getElementById("scriptModalTitle").textContent = title || "Script ArcPy";
  document.getElementById("scriptModalCode").textContent = scriptText;
  modal._scriptText = scriptText;
  modal.classList.remove("hidden");
  modal.style.display = "flex";
}

function closeScriptModal() {
  const modal = document.getElementById("scriptModal");
  if (modal) modal.style.display = "none";
}

async function copyScriptToClipboard() {
  const modal = document.getElementById("scriptModal");
  if (!modal) return;
  try {
    await navigator.clipboard.writeText(modal._scriptText || "");
    log("Script copiado al portapapeles. / Script copied to clipboard.", "ok");
  } catch {
    log("No se pudo copiar. Use Ctrl+A en el cuadro de texto. / Could not copy. Use Ctrl+A in the text box.", "warn");
  }
}

function downloadScript() {
  const modal = document.getElementById("scriptModal");
  if (!modal || !modal._scriptText) return;
  const blob = new Blob([modal._scriptText], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "validate_shp_cdgactvdd.py";
  a.click();
}

// ══════════════════════════════════════════════════════════════════════
// PASO 3 – ArcPy Scripts
// ══════════════════════════════════════════════════════════════════════

function getArcPyParams() {
  return {
    gdb:              document.getElementById("gdbPath").value.trim(),
    csvPath:          document.getElementById("csvPath").value.trim(),
    component:        document.getElementById("component").value,
    currentQt:        (document.getElementById("currentQt") || {}).value || "",
    officialPolygon:  (document.getElementById("officialPolygon") || {}).value || "AR_Oficial_poligono_GTM",
    officialPoint:    (document.getElementById("officialPoint") || {}).value || "AR_Oficial_punto_GTM",
    baseMicroMuni:    (document.getElementById("baseMicroMuni") || {}).value || "BASE_Micro_MUNI",
    smartsheetTable:  (document.getElementById("smartsheetTable") || {}).value || "ssheet",
    currentFC:        (document.getElementById("currentFC") || {}).value || "",
    trimesterFC:      (document.getElementById("trimesterFC") || {}).value || "",
    outputFC:         (document.getElementById("outputFC") || {}).value || "",
    featureClass:     (document.getElementById("outputFC") || {}).value || "",
    excelPath:        (document.getElementById("excelPath") || {}).value || "",
    portalUrl:        (document.getElementById("portalUrl") || {}).value || "",
    itemId:           (document.getElementById("itemId") || {}).value || "",
    gdbFullPath:      (document.getElementById("gdbFullPath") || {}).value || "",
    exportFolder:     (document.getElementById("exportFolder") || {}).value || "",
  };
}

async function genScript(step) {
  const data = await api("/api/arcpy/generate-script", {
    step,
    params: getArcPyParams(),
  });
  if (!data) return;
  document.getElementById("scriptContent").textContent = data.script;
  show("scriptOutput");
  log("Script '" + step + "' generado.", "ok");
}

// genScriptForRunner: calls existing genScript logic but returns the text
// instead of displaying in #scriptOutput — used by S4 Script Runner
// ES: Genera el script y devuelve el texto sin mostrarlo en #scriptOutput
async function genScriptForRunner(scriptType) {
  const data = await api("/api/arcpy/generate-script", {
    step: scriptType,
    params: getArcPyParams(),
  });
  if (!data) return null;
  log("Script '" + scriptType + "' generado para runner.", "ok");
  return data.script;
}

function copyScript() {
  const text = document.getElementById("scriptContent").textContent;
  navigator.clipboard
    .writeText(text)
    .then(() => log("Script copiado al portapapeles.", "ok"))
    .catch(() => {
      const ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      log("Script copiado al portapapeles.", "ok");
    });
}

// ── PASO 4 — Verificación 3 Fuentes / 3-Way Verification (G6) ────────

async function run3WayVerify() {
  // ES: Ejecuta verificación SS vs GIS en el servidor y muestra resultados.
  // EN: Runs server-side SS vs GIS comparison and shows results.
  disable("btn3WayVerify", true);
  log("Ejecutando verificación 3 fuentes… / Running 3-way verification…");

  const gisInput = document.getElementById("verify3wayGisRecords");
  let gis_records = [];
  if (gisInput && gisInput.value.trim()) {
    try {
      gis_records = JSON.parse(gisInput.value.trim());
    } catch {
      log("JSON de registros GIS inválido. Deje vacío para omitir comparación GIS. / Invalid GIS records JSON.", "warn");
      disable("btn3WayVerify", false);
      return;
    }
  }

  const p = getParams();
  const data = await api("/api/verify/3way", {
    component:   p.component,
    rowStart:    p.rowStart,
    rowEnd:      p.rowEnd,
    gis_records,
  });
  disable("btn3WayVerify", false);
  if (!data) return;

  render3WayReport(data);
  log("Verificación completada. / Verification complete.", "ok");
}

async function gen3WayScript() {
  // ES: Genera script arcpy completo (SS + GIS + AGOL) para ArcGIS Pro.
  // EN: Generates full arcpy script (SS + GIS + AGOL) for ArcGIS Pro.
  disable("btn3WayScript", true);
  log("Generando script 3-way… / Generating 3-way script…");

  const ssCsvPath   = (document.getElementById("verify3waySsCsv")    || {}).value?.trim() || "";
  const gisGdbPath  = (document.getElementById("verify3wayGdbPath")  || {}).value?.trim() || "";
  const gisFcName   = (document.getElementById("verify3wayFcName")   || {}).value?.trim() || "AR_Oficial_poligono_GTM";
  const agolUrl     = (document.getElementById("verify3wayAgolUrl")  || {}).value?.trim() || "";

  const data = await api("/api/verify/3way/script", {
    ss_csv_path:  ssCsvPath,
    gis_gdb_path: gisGdbPath,
    gis_fc_name:  gisFcName,
    agol_url:     agolUrl,
  });
  disable("btn3WayScript", false);
  if (!data) return;

  log("Script 3-way generado. Pegue en ArcGIS Pro Python window. / Paste into ArcGIS Pro Python window.", "ok");
  showScriptModal(data.script, "Verificación 3 Fuentes / 3-Way Verification");
}

function render3WayReport(data) {
  // ES: Renderiza tabla de comparación SS ↔ GIS ↔ AGOL.
  // EN: Renders SS ↔ GIS ↔ AGOL comparison table.
  const ss  = data.ss  || {};
  const gis = data.gis || {};

  const statusColor = data.status === "ok" ? "var(--ar-green)" :
                      data.status === "warning" ? "#f59e0b" : "var(--color-error, #dc2626)";
  const statusLabel = data.status === "ok" ? "✅ Fuentes coinciden / Sources match" :
                      data.status === "warning" ? "⚠️ Advertencias / Warnings" :
                      "❌ Errores / Errors";

  let html = `<div class="three-way-report">
    <div class="kpi-gauge" style="border-left:4px solid ${statusColor}; padding:10px; margin-bottom:12px">
      <span style="font-size:14px; font-weight:700; color:${statusColor}">${statusLabel}</span>
    </div>
    <table class="cc-table" style="width:100%; border-collapse:collapse; font-size:12px">
      <thead>
        <tr style="background:var(--ar-blue); color:#fff">
          <th style="padding:6px 8px; text-align:left">Métrica / Metric</th>
          <th style="padding:6px 8px; text-align:right">Smartsheet</th>
          <th style="padding:6px 8px; text-align:right">GIS</th>
        </tr>
      </thead>
      <tbody>
        <tr style="background:var(--ar-blue-light)">
          <td style="padding:5px 8px">Registros / Records</td>
          <td style="padding:5px 8px; text-align:right">${ss.count ?? "—"}</td>
          <td style="padding:5px 8px; text-align:right; color:${ss.count === gis.count ? "var(--ar-green)" : "var(--color-error,#dc2626)"}">${gis.count ?? "—"}</td>
        </tr>
        <tr>
          <td style="padding:5px 8px">Área total (ha)</td>
          <td style="padding:5px 8px; text-align:right">${(ss.area_total ?? 0).toFixed(2)}</td>
          <td style="padding:5px 8px; text-align:right; color:${data.area_delta <= 0.1 ? "var(--ar-green)" : data.area_delta <= 1.0 ? "#f59e0b" : "var(--color-error,#dc2626)"}">${(gis.area_total ?? 0).toFixed(2)} <small>(Δ${(data.area_delta ?? 0).toFixed(2)})</small></td>
        </tr>
      </tbody>
    </table>`;

  if ((data.ss_only || []).length > 0) {
    html += `<div style="margin-top:10px; padding:8px; background:#fee2e2; border-radius:4px; font-size:12px">
      <strong>❌ En SS pero no en GIS (${data.ss_only.length}):</strong><br>
      ${data.ss_only.slice(0, 15).join(", ")}${data.ss_only.length > 15 ? "…" : ""}
    </div>`;
  }
  if ((data.gis_only || []).length > 0) {
    html += `<div style="margin-top:6px; padding:8px; background:#fef3c7; border-radius:4px; font-size:12px">
      <strong>⚠️ En GIS pero no en SS (${data.gis_only.length}):</strong><br>
      ${data.gis_only.slice(0, 15).join(", ")}${data.gis_only.length > 15 ? "…" : ""}
    </div>`;
  }
  html += "</div>";

  let panel = document.getElementById("threeWayResult");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "threeWayResult";
    panel.className = "panel";
    const main = document.getElementById("mainContent");
    if (main) main.appendChild(panel);
  }
  panel.innerHTML = '<div class="panel-hd"><h3 class="panel-title">Verificación 3 Fuentes / 3-Way Verification</h3></div>' +
    '<div class="panel-bd">' + html + '</div>';
  panel.classList.remove("hidden");
  updateEmptyState();
}

// ══════════════════════════════════════════════════════════════════════
// PASO 5 – Excel Master
// ══════════════════════════════════════════════════════════════════════

async function generateExcelMaster() {
  disable("btnExcelMaster", true);
  const data = await api("/api/paso5/generate-excel", {
    destFolder: getDestFolder(),
  });
  disable("btnExcelMaster", false);
  if (!data) return;

  log("Excel maestro generado: " + data.file, "ok");
  document.getElementById("downloadContent").innerHTML =
    "<p>Excel guardado en: <code>" + displayPath(data.path) + "</code></p>" +
    "<p>Hojas: " + (data.sheets || []).map(escapeHtml).join(", ") + "</p>";
  show("downloadResult");
}

// ══════════════════════════════════════════════════════════════════════
// PASO 5b – Recepción M&E Dafne (G11 + G7)
// ══════════════════════════════════════════════════════════════════════

function _dafneFilePath() {
  return (document.getElementById("dafneFilePath") || {}).value || "";
}
function _dafneBasePath() {
  return (document.getElementById("dafneBasePath") || {}).value || "";
}
function _dafneQuarter() {
  return (document.getElementById("dafneQuarter") || {}).value || "";
}

async function dafneValidate() {
  // ES: Valida hojas requeridas en Tbl_Integrado.xlsx / EN: Validate required sheets
  var filePath = _dafneFilePath().trim();
  var resultEl = document.getElementById("dafneValidResult");
  if (!resultEl) return;
  if (!filePath) {
    resultEl.style.display = "block";
    resultEl.innerHTML = '<span style="color:var(--ar-blue,#003f6e)">⚠ Ingrese la ruta del archivo / Enter file path</span>';
    return;
  }
  resultEl.style.display = "block";
  resultEl.innerHTML = '<span class="text-info">Validando… / Validating…</span>';
  var data = await api("/api/dafne/validate", { file_path: filePath });
  if (!data) { resultEl.innerHTML = '<span class="text-error">❌ Error de servidor / Server error</span>'; return; }

  if (data.error) {
    resultEl.innerHTML = '<span class="text-error">❌ ' + escapeHtml(data.error) + '</span>';
    return;
  }
  if (data.valid) {
    var foundStr = (data.found_sheets || []).map(escapeHtml).join(", ");
    resultEl.innerHTML = '<span style="color:var(--ar-green,#70b62c)">✅ Archivo válido / Valid file</span>' +
      (data.warnings && data.warnings.length ? '<br><span style="color:var(--ar-blue,#003f6e)">⚠ ' + data.warnings.map(escapeHtml).join("; ") + '</span>' : '') +
      '<br><small style="color:var(--text-2,#666)">Hojas: ' + foundStr + '</small>';
  } else {
    var missing = (data.missing_sheets || []).map(escapeHtml).join(", ");
    resultEl.innerHTML = '<span class="text-error">❌ Hojas faltantes / Missing sheets: ' + missing + '</span>';
  }
}

async function dafneCheckStatus() {
  // ES: Verifica si Tbl_Integrado.xlsx existe en el BasePath / EN: Check file in BasePath
  var basePath = _dafneBasePath().trim();
  var statusBar = document.getElementById("dafneStatusBar");
  if (!statusBar) return;
  if (!basePath) {
    statusBar.innerHTML = '<span style="color:var(--ar-blue,#003f6e)">⚠ Ingrese BasePath / Enter BasePath</span>';
    return;
  }
  statusBar.innerHTML = '<span class="text-info">Verificando… / Checking…</span>';
  var data = await apiGet("/api/dafne/status?base_path=" + encodeURIComponent(basePath));
  if (!data) { statusBar.innerHTML = '<span class="text-error">❌ Error / Error</span>'; return; }

  if (data.exists) {
    statusBar.innerHTML =
      '<span style="color:var(--ar-green,#70b62c)">✅ Archivo presente / File present</span>' +
      '<br><small style="color:var(--text-2,#666)">' + escapeHtml(data.modified_at || "") +
      " — " + escapeHtml(String(data.size_kb || 0)) + " KB</small>";
  } else {
    statusBar.innerHTML = '<span style="color:var(--ar-blue,#003f6e)">— Sin archivo / No file in BasePath</span>';
  }
}

async function dafneReceive() {
  // ES: Valida + coloca + registra historial / EN: Validate + place + record history
  var filePath = _dafneFilePath().trim();
  var basePath = _dafneBasePath().trim();
  var quarter  = _dafneQuarter().trim();
  var resultEl = document.getElementById("dafneReceiveResult");
  if (!resultEl) return;

  if (!filePath || !basePath || !quarter) {
    resultEl.style.display = "block";
    resultEl.innerHTML = '<span style="color:var(--ar-blue,#003f6e)">⚠ Complete todos los campos / Fill all fields</span>';
    return;
  }

  disable("btnDafneReceive", true);
  resultEl.style.display = "block";
  resultEl.innerHTML = '<span style="color:var(--text-2,#666)">Procesando… / Processing…</span>';

  var data = await api("/api/dafne/receive", {
    file_path: filePath,
    quarter: quarter,
    base_path: basePath,
    metadata: {},
  });
  disable("btnDafneReceive", false);
  if (!data) { resultEl.innerHTML = '<span class="text-error">❌ Error de servidor / Server error</span>'; return; }

  if (data.success) {
    var dest = (data.placement || {}).dest || "";
    var backup = (data.placement || {}).backup || "";
    resultEl.innerHTML =
      '<span style="color:var(--ar-green,#70b62c)">✅ Archivo colocado / File placed</span>' +
      '<br><small style="color:var(--text-2,#666)">→ ' + displayPath(dest) + '</small>' +
      (backup ? '<br><small style="color:var(--text-2,#666)">Backup: ' + displayPath(backup) + '</small>' : '');
    log("Tbl_Integrado.xlsx colocado en BasePath (" + quarter + ")", "ok");
    // ES: Actualizar estado del BasePath / EN: Refresh BasePath status
    dafneCheckStatus();
  } else {
    var errMsg = "";
    if (data.validation && !data.validation.valid) {
      errMsg = "Validación fallida / Validation failed: " +
        (data.validation.missing_sheets || []).map(escapeHtml).join(", ");
    } else if (data.placement && data.placement.error) {
      errMsg = escapeHtml(data.placement.error);
    } else {
      errMsg = "Error desconocido / Unknown error";
    }
    resultEl.innerHTML = '<span class="text-error">❌ ' + errMsg + '</span>';
  }
}

async function dafneLoadHistory() {
  // ES: Carga historial de recepciones del trimestre / EN: Load reception history for quarter
  var quarter = _dafneQuarter().trim();
  var tableEl = document.getElementById("dafneHistoryTable");
  if (!tableEl) return;
  if (!quarter) {
    tableEl.innerHTML = '<span style="color:var(--ar-blue,#003f6e)">⚠ Ingrese un trimestre / Enter a quarter</span>';
    return;
  }
  tableEl.innerHTML = '<span style="color:var(--text-2,#666)">Cargando… / Loading…</span>';
  var rows = await apiGet("/api/dafne/history?quarter=" + encodeURIComponent(quarter));
  if (!rows) { tableEl.innerHTML = '<span class="text-error">❌ Error</span>'; return; }
  if (!rows.length) {
    tableEl.innerHTML = '<span class="text-info">Sin recepciones registradas / No receptions recorded</span>';
    return;
  }
  var html = '<table style="width:100%;border-collapse:collapse;font-size:11px">';
  html += '<thead><tr style="background:var(--ar-blue-light,#e0ecf5)">';
  html += '<th style="padding:3px 6px;text-align:left">Fecha/Date</th>';
  html += '<th style="padding:3px 6px;text-align:left">Archivo/File</th>';
  html += '<th style="padding:3px 6px;text-align:center">Válido</th>';
  html += '<th style="padding:3px 6px;text-align:center">Colocado</th>';
  html += '</tr></thead><tbody>';
  rows.forEach(function(r, i) {
    var bg = i % 2 === 0 ? "" : "background:var(--bg-alt,#f9f9f9)";
    var validIcon = r.valid ? "✅" : "❌";
    var placedIcon = r.placed ? "✅" : "❌";
    html += '<tr style="' + bg + '">';
    html += '<td style="padding:3px 6px">' + escapeHtml((r.received_at || "").substring(0, 16)) + '</td>';
    html += '<td style="padding:3px 6px;word-break:break-all">' + displayPath(r.filename || r.file_path || "") + '</td>';
    html += '<td style="padding:3px 6px;text-align:center">' + validIcon + '</td>';
    html += '<td style="padding:3px 6px;text-align:center">' + placedIcon + '</td>';
    html += '</tr>';
  });
  html += '</tbody></table>';
  tableEl.innerHTML = html;
}

// ══════════════════════════════════════════════════════════════════════
// PASO 7 – Documentación
// ══════════════════════════════════════════════════════════════════════

async function viewErrorReport() {
  const data = await apiGet("/api/paso7/error-report");
  if (!data) return;

  log("Reporte de errores generado.", "ok");
  let html = '<h4>Reporte de Errores</h4>';
  html += '<p>Generado: ' + escapeHtml(data.generated_at || '-') + '</p>';
  html += '<p>Errores del pipeline: ' + (data.pipeline_errors || []).length + '</p>';
  html += '<p>Advertencias: ' + (data.pipeline_warnings || []).length + '</p>';


  const errs = data.pipeline_errors || [];
  if (errs.length > 0) {
    html += '<h4>Errores Recientes</h4><ul>';
    errs.slice(-10).forEach((e) => { html += '<li>' + escapeHtml(e) + '</li>'; });
    html += '</ul>';
  }

  showReportPanel(html);
}

async function viewDataSummary() {
  const data = await apiGet("/api/paso7/data-summary");
  if (!data) return;

  log("Resumen de datos generado.", "ok");
  let html = '<h4>Resumen de Datos</h4>';
  html += '<p>Generado: ' + escapeHtml(data.generated_at || '-') + '</p>';

  (data.sections || []).forEach((sec) => {
    html += '<h4>' + escapeHtml(sec.title) + '</h4>';
    const c = sec.content || {};
    html += '<table><tbody>';
    Object.entries(c).forEach(([k, v]) => {
      if (typeof v === 'object' && v !== null) {
        html += '<tr><td><strong>' + escapeHtml(k) + '</strong></td><td><pre>' + escapeHtml(JSON.stringify(v, null, 2)) + '</pre></td></tr>';
      } else {
        html += '<tr><td>' + escapeHtml(k) + '</td><td>' + escapeHtml(String(v)) + '</td></tr>';
      }
    });
    html += '</tbody></table>';
  });

  showReportPanel(html);
}

function showReportPanel(html) {
  let panel = document.getElementById("reportResult");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "reportResult";
    panel.className = "panel";
    const main = document.getElementById("mainContent");
    main.appendChild(panel);
  }
  panel.innerHTML = '<div class="panel-hd"><h3 class="panel-title">Reporte</h3></div>' +
    '<div class="panel-bd">' + html + '</div>';
  panel.classList.remove("hidden");
  updateEmptyState();
}

// ══════════════════════════════════════════════════════════════════════
// Orquestador
// ══════════════════════════════════════════════════════════════════════

const PASO_NAMES = {
  1: "Smartsheet",
  3: "ArcPy",
  4: "AGOL",
  5: "Excel Master",
  6: "Power BI",
  7: "Documentación",
};

async function startPipeline() {
  disable("btnPipeline", true);
  const data = await api("/api/orchestrator/start", {});
  disable("btnPipeline", false);
  if (!data) return;

  log("Pipeline iniciado.", "ok");
  renderOrchProgress(data);
}

async function refreshOrchStatus() {
  const data = await apiGet("/api/orchestrator/status");
  if (!data) return;
  renderOrchProgress(data);
}

async function advancePaso(paso) {
  const data = await api("/api/orchestrator/advance", { paso });
  if (!data) return;
  log("Paso " + paso + " completado.", "ok");
  renderOrchProgress(data);
}

async function retryPaso(paso) {
  const data = await api("/api/orchestrator/retry", { paso });
  if (!data) return;
  log("Reintentando paso " + paso + "…", "ok");
  renderOrchProgress(data);
}

function renderOrchProgress(state) {
  const container = document.getElementById("orchProgress");
  if (!container) return;

  const pasoStatus = state.paso_status || {};
  let html = '<div class="orch-steps">';

  for (let i = 1; i <= 7; i++) {
    const status = pasoStatus[String(i)] || "pending";
    const name = PASO_NAMES[i] || ("Paso " + i);
    let statusCls = "orch-step-" + status.replace("awaiting_manual", "awaiting");
    let statusIcon = "";
    let actions = "";

    switch (status) {
      case "success":
        statusIcon = '<span class="orch-icon orch-icon-ok">&#10003;</span>';
        break;
      case "error":
        statusIcon = '<span class="orch-icon orch-icon-err">&#10007;</span>';
        actions = '<button class="btn-sm" onclick="retryPaso(' + i + ')">Reintentar</button>';
        break;
      case "awaiting_manual":
        statusIcon = '<span class="orch-icon orch-icon-wait">&#9679;</span>';
        actions = '<button class="btn-sm btn-primary" onclick="advancePaso(' + i + ')">Confirmar</button>';
        break;
      case "running":
        statusIcon = '<span class="orch-icon orch-icon-run">&#8635;</span>';
        break;
      default:
        statusIcon = '<span class="orch-icon orch-icon-pending">&#9675;</span>';
    }

    html += '<div class="orch-step ' + statusCls + '">';
    html += statusIcon;
    html += '<span class="orch-step-name">' + i + '. ' + name + '</span>';
    html += '<span class="orch-step-status">' + status + '</span>';
    if (actions) html += '<div class="orch-step-actions">' + actions + '</div>';
    html += '</div>';
  }
  html += '</div>';

  // Overall status
  const pipeline = state.pipeline_status || "idle";
  html += '<div class="orch-overall">Estado: <strong>' + pipeline + '</strong></div>';

  container.innerHTML = html;
}

// ── Path Settings ──────────────────────────────────────────────────────────
const PATH_FIELD_MAP = {
  FOLDER_C1: "ps_FOLDER_C1",
  FOLDER_C2: "ps_FOLDER_C2",
  FOLDER_C3: "ps_FOLDER_C3",
  SMARTSHEET_DATA_DIR: "ps_SMARTSHEET_DATA_DIR",
  SMARTSHEET_ATTACH_DIR: "ps_SMARTSHEET_ATTACH_DIR",
  EXCEL_DB_DIR: "ps_EXCEL_DB_DIR",
  APRX: "ps_APRX",
  WORKSPACE_PATH: "ps_WORKSPACE_PATH",
  CSVPOINT_TO_GDB: "ps_CSVPOINT_TO_GDB",
  AR_MAP_NAME: "ps_AR_MAP_NAME",
  ARCPY_PYTHON: "ps_ARCPY_PYTHON",
  ARCGIS_PRO_VERSION: "ps_ARCGIS_PRO_VERSION",
};

async function showPathSettings() {
  try {
    const res = await fetch("/api/config/paths", { headers: { "X-Local-Token": _localToken() } });
    const data = await res.json();
    for (const [key, elId] of Object.entries(PATH_FIELD_MAP)) {
      const el = document.getElementById(elId);
      if (el && data[key]) el.value = data[key];
    }
  } catch (e) {
    log("[paths] Error cargando rutas: " + e.message, "error");
  }
  showOnly("pathSettingsPanel");
  document.getElementById("pathSettingsMsg").textContent = "";
}

async function savePathSettings() {
  const btn = document.getElementById("btnSavePaths");
  btn.disabled = true;
  btn.textContent = "Guardando...";
  const msg = document.getElementById("pathSettingsMsg");

  const payload = {};
  for (const [key, elId] of Object.entries(PATH_FIELD_MAP)) {
    const el = document.getElementById(elId);
    if (el) payload[key] = el.value.trim();
  }

  try {
    const res = await fetch("/api/config/paths", {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-Local-Token": _localToken() },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    window._envFolders = window._envFolders || {};
    Object.keys(payload).forEach((key) => {
      window._envFolders[key] = payload[key];
    });
    updateDestFolderFromEnv();
    msg.className = "text-success";
    msg.textContent = "✓ Guardado correctamente en .env (" + data.saved.length + " variables)";
    log("[paths] Rutas guardadas en .env", "ok");
  } catch (e) {
    msg.className = "text-error";
    msg.textContent = "✗ Error: " + e.message;
    log("[paths] Error guardando rutas: " + e.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Guardar en .env";
  }
}

// ══════════════════════════════════════════════════════════════════════
// S2: Pipeline Progress Bar
// Barra de progreso central con 8 pasos del pipeline
// ══════════════════════════════════════════════════════════════════════

const PIPELINE_STEPS = [
  { id: 1,    short: "Datos",    full: "Recolección de datos" },
  { id: "1b", short: "Descarga", full: "Descarga y validación" },
  { id: 3,    short: "ArcPy",   full: "Procesamiento territorial" },
  { id: 4,    short: "AGOL",    full: "Publicación geoespacial" },
  { id: 5,    short: "Excel",   full: "Excel maestro" },
  { id: 6,    short: "PBI",     full: "Power BI" },
  { id: 7,    short: "Doc",     full: "Documentación" },
];

// Global state: status for each pipeline step
// Estados: "pending" | "active" | "awaiting" | "success" | "error" | "skipped"
let pipelineStatus = {};
(function initPipelineStatus() {
  PIPELINE_STEPS.forEach((s) => { pipelineStatus[String(s.id)] = "pending"; });
})();

function renderProgressBar() {
  const track = document.getElementById("ppTrack");
  if (!track) return;

  let html = "";
  PIPELINE_STEPS.forEach((step, idx) => {
    const sid = String(step.id);
    const status = pipelineStatus[sid] || "pending";
    const isLast = idx === PIPELINE_STEPS.length - 1;

    // Pill class
    let pillClass = "pp-step pp-step-" + status;
    const isPulse = status === "active" || status === "awaiting";
    if (isPulse) pillClass += " pulse";

    // Icon inside pill (only for success/error/skipped)
    let pillIcon = "";
    if (status === "success") pillIcon = '<span class="pp-step-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg></span>';
    if (status === "error")   pillIcon = '<span class="pp-step-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></span>';

    // Step label with number
    const stepLabel = (idx + 1) + " " + step.short;
    const subLabelKey = "ppSubLabel_" + sid;
    const subLabel = window[subLabelKey] || "";
    const titleText = step.full + (subLabel ? " — " + subLabel : "");

    html += '<div class="' + pillClass + '" onclick="onProgressStepClick(\'' + step.id + '\')" title="' + titleText + '">';
    html += pillIcon;
    html += '<span>' + stepLabel + '</span>';
    html += '</div>';

    // Chevron separator (not after last step)
    if (!isLast) {
      html += '<span class="pp-chevron"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></span>';
    }
  });

  track.innerHTML = html;
}

function updatePipelineStep(pasoId, status, subLabel) {
  // Guard: only run if S2 is initialized
  if (!pipelineStatus) return;
  const sid = String(pasoId);
  pipelineStatus[sid] = status;
  if (subLabel !== undefined) {
    window["ppSubLabel_" + sid] = subLabel;
  }
  renderProgressBar();
  savePipelineProgress();
}

function onProgressStepClick(pasoId) {
  // Placeholder: si wizardMode existe y está activo, navegar al paso (Chat F implementará esto)
  if (typeof wizardMode !== "undefined" && wizardMode) {
    if (typeof navigateWizardToPaso === "function") navigateWizardToPaso(pasoId);
  }
}

function savePipelineProgress() {
  try {
    localStorage.setItem("arPipelineStatus", JSON.stringify(pipelineStatus));
  } catch (_) {}
}

function restorePipelineProgress() {
  try {
    const saved = localStorage.getItem("arPipelineStatus");
    if (saved) {
      const parsed = JSON.parse(saved);
      // Only restore known steps
      PIPELINE_STEPS.forEach((s) => {
        const sid = String(s.id);
        if (parsed[sid]) pipelineStatus[sid] = parsed[sid];
      });
    }
  } catch (_) {}
  renderProgressBar();
}

// ══════════════════════════════════════════════════════════════════════
// S6: Summary Dashboard
// Muestra KPI cards y gráfico de distribución AbE al cargar la hoja.
// Shows KPI cards and AbE distribution chart when a sheet loads.
// ══════════════════════════════════════════════════════════════════════

function truncate(str, max) {
  // Trunca texto con '…' / Truncates text with ellipsis
  if (!str) return "";
  return str.length > max ? str.substring(0, max) + "…" : str;
}

// EN: Map of raw error ABE value → { count, codes[] }. Populated during renderSummary().
// ES: Mapa de valor AbE erróneo → { count, codes[] }. Se llena durante renderSummary().
var _abeErrorCodes = {};

// EN: Canonical ABE value set — exact strings that are valid in Smartsheet.
// ES: Conjunto de valores AbE canónicos — cadenas exactas válidas en Smartsheet.
var _ABE_CANONICAL_SET = new Set([
  "Sistema Agroforestal | Cultivos anuales",
  "Sistema Agroforestal | Cultivos perennes",
  "Sistema Silvopastoril",
  "Plantaciones Forestales",
  "Bosque Natural con Fines de Producción",
  "Bosque Natural con Fines de Protección",
  "Reforestación con Fines de Restauración",
  "Sistema Agroforestal | Conservación de suelo y agua",
]);

// EN: Normalised (no accents, lowercase) key → canonical display name.
// ES: Clave normalizada (sin acentos, minúsculas) → nombre canónico de visualización.
var _ABE_NORM_TO_CANONICAL = {
  "sistema agroforestal | cultivos anuales":              "Sistema Agroforestal | Cultivos anuales",
  "sistema agroforestal | cultivos perennes":             "Sistema Agroforestal | Cultivos perennes",
  "sistema silvopastoril":                                "Sistema Silvopastoril",
  "plantaciones forestales":                              "Plantaciones Forestales",
  "bosque natural con fines de produccion":               "Bosque Natural con Fines de Producción",
  "bosque natural con fines de proteccion":               "Bosque Natural con Fines de Protección",
  "reforestacion con fines de restauracion":              "Reforestación con Fines de Restauración",
  "sistema agroforestal | conservacion de suelo y agua":  "Sistema Agroforestal | Conservación de suelo y agua",
  // EN: Reversed order is NOT canonical — fixable to correct order / ES: Orden invertido NO es canónico
  "conservacion de suelo y agua | sistema agroforestal":  "Sistema Agroforestal | Conservación de suelo y agua",
  // EN: Common misspelling: "suelos" instead of "suelo y agua" / ES: Error frecuente: "suelos" en vez de "suelo y agua"
  "sistema agroforestal | conservacion de suelos":         "Sistema Agroforestal | Conservación de suelo y agua",
  "sistema agroforestal | conservacion de suelo":           "Sistema Agroforestal | Conservación de suelo y agua",
};

/**
 * EN: Classify a raw ABE string from Smartsheet:
 *   'ok'      → already a correct canonical value (show green)
 *   'fixable' → wrong accents/case/truncation we can auto-suggest a fix for (show orange)
 *   'error'   → completely unknown, requires human review (show red)
 * ES: Clasifica un valor AbE crudo de Smartsheet en ok / fixable / error.
 */
function classifyAbeValue(raw) {
  if (!raw) return { type: "ok" };
  // EN: Normalise whitespace (NBSP→space) and trim before matching
  // ES: Normalizar espacios en blanco (NBSP→espacio) y recortar antes de comparar
  var clean = raw.replace(/\u00a0/g, " ").trim();
  if (_ABE_CANONICAL_SET.has(clean)) return { type: "ok" };

  var norm = clean.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  // 1. Exact normalised match (accent/case variant of a canonical)
  if (_ABE_NORM_TO_CANONICAL[norm]) {
    var canon = _ABE_NORM_TO_CANONICAL[norm];
    return { type: "fixable", candidates: [canon] };
  }

  // 2. Prefix match for truncated values (require ≥25 normalised chars to avoid false positives)
  //    EN: canonical key starts with the normalised input
  //    ES: la clave canónica empieza con la entrada normalizada
  if (norm.length >= 25) {
    var found = [];
    for (var key in _ABE_NORM_TO_CANONICAL) {
      if (key.startsWith(norm)) {
        var c = _ABE_NORM_TO_CANONICAL[key];
        if (found.indexOf(c) === -1) found.push(c);
      }
    }
    if (found.length > 0) {
      // If suelo-y-agua match, add the sibling canonical too
      var hasSuelo = found.some(function(c) { return _ABE_SUELO_AGUA_PAIR.indexOf(c) !== -1; });
      if (hasSuelo) {
        _ABE_SUELO_AGUA_PAIR.forEach(function(c) {
          if (found.indexOf(c) === -1) found.push(c);
        });
      }
      return { type: "fixable", candidates: found };
    }
  }

  // 3. Unknown value — cannot auto-correct, requires human review
  return { type: "error" };
}

function summaryCard(value, label, sublabel, status) {
  // Genera HTML de una tarjeta KPI / Generates HTML for a KPI card
  // status: 'success' | 'warning' | 'error' | 'neutral'
  var cls = "summary-card summary-card--" + (status || "neutral");
  return (
    '<div class="' + cls + '">' +
      '<div class="summary-card-value">' + value + '</div>' +
      '<div class="summary-card-label">' + label + '</div>' +
      (sublabel ? '<div class="summary-card-sublabel">' + sublabel + '</div>' : '') +
    '</div>'
  );
}

function renderSummary() {
  // Calcula estadísticas y renderiza el panel resumen
  // Calculates statistics and renders the summary panel
  if (!sheetData || !sheetData.rows) return;

  // Apply C2 multi-select filters so summary reflects the same rows as the table
  // Aplica filtros multi-selección C2 para que el resumen refleje las mismas filas que la tabla
  var rows = sheetData.rows.slice();
  if (document.getElementById("component").value === "C2") {
    var selTipos = getMsValues("filterTipo");
    var selContratos = getMsValues("filterContrato");

    if (selContratos.length > 0) {
      var cSet = new Set(selContratos);
      rows = rows.filter(function(r) { return cSet.has(r.cells["NÚMERO DE CONTRATO"] || ""); });
    } else if (selTipos.length > 0) {
      rows = rows.filter(function(r) {
        var contrato = r.cells["NÚMERO DE CONTRATO"] || "";
        return selTipos.some(function(t) { return contrato.includes(t); });
      });
    }
  }
  // Trimestre filter: all components
  var selTrimestres = getMsValues("filterTrimestre");
  if (selTrimestres.length > 0) {
    var tSet = new Set(selTrimestres);
    rows = rows.filter(function(r) { return tSet.has(r.cells["TRIMESTRE QUE REPORTA"] || ""); });
  }

  // Apply the same additional filters as renderSheetTable
  // Aplica los mismos filtros adicionales que renderSheetTable
  var missingOnly  = document.getElementById("filterMissingCode").checked;
  var shapeOnly    = document.getElementById("filterHasShapefile").checked;
  var commentMonth = document.getElementById("filterCommentMonth").value;

  if (missingOnly) {
    var missingRows = rows.filter(function(r) {
      return r.cells["FECHA DE LA ACTIVIDAD"] && !r.cells["CÓDIGO DE LA ACTIVIDAD"];
    });
    var groupsNeeded = new Set();
    var mc_lastContrato = "", mc_lastTrimestre = "";
    missingRows.forEach(function(r) {
      var c = r.cells["NÚMERO DE CONTRATO"] || "";
      if (c) mc_lastContrato = c;
      var t = r.cells["TRIMESTRE QUE REPORTA"] || "";
      if (t) mc_lastTrimestre = t;
      if (mc_lastContrato && mc_lastTrimestre) groupsNeeded.add(mc_lastContrato + "|" + mc_lastTrimestre);
    });
    var groupFirstRows = new Set();
    var g_lastContrato = "", g_lastTrimestre = "", g_prevKey = "";
    rows.forEach(function(r) {
      var c = r.cells["NÚMERO DE CONTRATO"] || "";
      if (c) g_lastContrato = c;
      var t = r.cells["TRIMESTRE QUE REPORTA"] || "";
      if (t) g_lastTrimestre = t;
      var key = g_lastContrato + "|" + g_lastTrimestre;
      if (key !== g_prevKey && groupsNeeded.has(key)) {
        groupFirstRows.add(r.rowNumber);
        g_prevKey = key;
      }
    });
    var missingRowNums = new Set(missingRows.map(function(r) { return r.rowNumber; }));
    rows = rows.filter(function(r) { return missingRowNums.has(r.rowNumber) || groupFirstRows.has(r.rowNumber); });
  }
  // EN: "Con shapefile" and "Hectáreas" filters combine as OR (same as renderSheetTable).
  // ES: Los filtros "Con shapefile" y "Hectáreas" se combinan con OR.
  var selHectareas = getMsValues("filterHectareas");
  var haFilterActive = selHectareas.length > 0 && selHectareas.length < 2;
  var haWantValue = haFilterActive && selHectareas.includes("con_valor");
  var isC2Wiz = document.getElementById("component").value === "C2";

  if (shapeOnly && haFilterActive) {
    // EN: OR mode — individual row shapefile check (no C2 group expansion)
    // ES: Modo OR — verificar shapefile individual (sin expansión de grupo C2)
    rows = rows.filter(function(r) {
      var ha = parseFloat(r.cells["TOTAL DE HECTÁREAS"]);
      var hasHaVal = !isNaN(ha) && ha > 0;
      var passHa = haWantValue ? hasHaVal : !hasHaVal;
      var passShape = rowHasShapefile(r);
      return passShape || passHa;
    });
  } else if (shapeOnly) {
    if (isC2Wiz) {
      var shapeRows = rows.filter(function(r) { return rowHasShapefile(r); });
      var shapeGroups = new Set();
      var sf_lastContrato = "", sf_lastTrimestre = "";
      shapeRows.forEach(function(r) {
        var c = r.cells["NÚMERO DE CONTRATO"] || "";
        if (c) sf_lastContrato = c;
        var t = r.cells["TRIMESTRE QUE REPORTA"] || "";
        if (t) sf_lastTrimestre = t;
        if (sf_lastContrato && sf_lastTrimestre) shapeGroups.add(sf_lastContrato + "|" + sf_lastTrimestre);
      });
      var eff_contrato = "", eff_trimestre = "";
      rows = rows.filter(function(r) {
        var c = r.cells["NÚMERO DE CONTRATO"] || "";
        if (c) eff_contrato = c;
        var t = r.cells["TRIMESTRE QUE REPORTA"] || "";
        if (t) eff_trimestre = t;
        return shapeGroups.has(eff_contrato + "|" + eff_trimestre);
      });
    } else {
      rows = rows.filter(function(r) { return rowHasShapefile(r); });
    }
  } else if (haFilterActive) {
    rows = rows.filter(function(r) {
      var ha = parseFloat(r.cells["TOTAL DE HECTÁREAS"]);
      var hasVal = !isNaN(ha) && ha > 0;
      return haWantValue ? hasVal : !hasVal;
    });
  }
  if (commentMonth) rows = rows.filter(function(r) { return r.comment && r.comment.date && r.comment.date.startsWith(commentMonth); });

  // EN: Calidad SIG multi-select filter — match renderSheetTable logic
  // ES: Filtro multi-selección de Calidad SIG — coincide con la lógica de renderSheetTable
  var selCalidadSIG = getMsValues("filterCalidadSIG");
  if (selCalidadSIG.length > 0) {
    var sigSet = new Set(selCalidadSIG);
    rows = rows.filter(function(r) {
      var val = r.cells["Calidad SIG"];
      var normalized = (val == null || val === "") ? "" : String(val);
      return sigSet.has(normalized);
    });
  }

  // EN: Bad date filter — match renderSheetTable logic
  // ES: Filtro de fecha errónea — coincide con la lógica de renderSheetTable
  var badDateOnly = document.getElementById("filterBadDate").checked;
  if (badDateOnly) {
    rows = rows.filter(function(r) { return _isBadDate(r.cells["FECHA DE LA ACTIVIDAD"]); });
  }

  // EN: Código search — match renderSheetTable logic
  // ES: Búsqueda por código — coincide con la lógica de renderSheetTable
  var codigoElSum = document.getElementById("filterCodigo");
  var codigoQSum = codigoElSum ? codigoElSum.value.trim().toLowerCase() : "";
  if (codigoQSum) {
    rows = rows.filter(function(r) {
      var v = r.cells["CÓDIGO DE LA ACTIVIDAD"];
      return v != null && String(v).toLowerCase().indexOf(codigoQSum) !== -1;
    });
  }

  var cols = sheetData.columns || [];

  // Detectar columnas con nombres acentuados / Detect accented column names
  // Use case-insensitive normalized matching to handle encoding variants
  function findCol(candidates) {
    for (var i = 0; i < candidates.length; i++) {
      if (cols.includes(candidates[i])) return candidates[i];
    }
    // Fallback: substring match (handles accent encoding variants)
    var kws = candidates.map(function(c) { return c.toLowerCase().replace(/[^a-z0-9]/g, ""); });
    return cols.find(function(c) {
      var cn = c.toLowerCase().replace(/[^a-z0-9]/g, "");
      return kws.some(function(k) { return cn.indexOf(k.substring(0, 6)) !== -1; });
    }) || candidates[0];
  }

  var COL_CODE = findCol(["CÓDIGO DE LA ACTIVIDAD", "CODIGO DE LA ACTIVIDAD"]);
  var COL_HA   = findCol(["TOTAL DE HECTÁREAS", "TOTAL DE HECTAREAS", "HECTÁREAS", "HECTAREAS"]);
  var COL_ABE  = findCol(["ACCIONES DE RESTAURACIÓN AbE", "ACCIONES DE RESTAURACION AbE"]);

  var total       = rows.length;
  var withCode    = 0;
  var withoutCode = 0;
  var withDate    = 0;
  var hectareas   = 0;
  var withShape   = 0;
  var calidadSi   = 0;
  var calidadEspera = 0;
  var abeData     = {};  // { rawValue: { count: number, codes: string[] } }

  rows.forEach(function(r) {
    var code  = r.cells[COL_CODE];
    var fecha = r.cells["FECHA DE LA ACTIVIDAD"];
    var ha    = parseFloat(r.cells[COL_HA]);
    var cal   = r.cells["Calidad SIG"];
    var abe   = r.cells[COL_ABE];

    if (code)  withCode++;
    if (fecha) withDate++;
    if (fecha && !code) withoutCode++;
    if (code && !isNaN(ha)) hectareas += ha;
    if (rowHasShapefile(r)) withShape++;
    if (cal === "Sí" || cal === "Si") calidadSi++;
    if (cal === "Espera") calidadEspera++;
    // EN: Count raw values with associated codes / ES: Contar valores crudos con códigos asociados
    if (abe) {
      if (!abeData[abe]) abeData[abe] = { count: 0, codes: [] };
      abeData[abe].count++;
      if (code) abeData[abe].codes.push(String(code));
    }
  });

  // KPI de completitud / Completeness KPI: códigos vs filas con fecha
  var completitud = Math.round(withCode / Math.max(withDate, 1) * 100);
  var completitudStatus = completitud >= 90 ? "success" : (completitud >= 70 ? "warning" : "error");

  var shapePct = total > 0 ? Math.round(withShape / total * 100) : 0;
  var calPct   = total > 0 ? Math.round((calidadSi + calidadEspera) / total * 100) : 0;

  // Renderizar tarjetas / Render cards
  var grid = document.getElementById("summaryGrid");
  if (!grid) return;

  var commentCount = rows.filter(function(r) { return r.comment; }).length;

  var haStr = hectareas % 1 === 0
    ? hectareas.toLocaleString("es")
    : hectareas.toLocaleString("es", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  grid.innerHTML =
    summaryCard(total, "Actividades totales", null, "neutral") +
    summaryCard(haStr + " ha", "Total hectáreas", null, "neutral") +
    summaryCard(completitud + "%", "Completitud de códigos", "Meta: ≥90%", completitudStatus) +
    summaryCard(withoutCode, "Sin código (con fecha)", null, withoutCode === 0 ? "success" : "warning") +
    summaryCard(shapePct + "% (" + withShape + ")", "Con shapefile", null, shapePct > 80 ? "success" : "neutral") +
    summaryCard(calPct + "% (" + (calidadSi + calidadEspera) + ")", "Revisión SIG", "Calidad SIG asignada", calPct > 70 ? "success" : "neutral") +
    summaryCard(commentCount, "Con comentario", null, "neutral");

  // Gráfico de distribución AbE / AbE distribution bar chart
  var chartEl = document.getElementById("summaryChart");
  if (chartEl) {
    var sorted = Object.entries(abeData).sort(function(a, b) { return b[1].count - a[1].count; });
    var maxVal = sorted.length > 0 ? sorted[0][1].count : 1;

    if (sorted.length === 0) {
      chartEl.innerHTML = "";
    } else {
      // AbE chart wrapped in accordion / Gráfico AbE envuelto en acordeón
      // Default collapsed for compact layout / Colapsado por defecto para layout compacto
      var isOpen = (function() {
        try { return localStorage.getItem("arAbeOpen") === "true"; } catch(_) { return false; }
      })();
      var barsHtml = "";
      _abeErrorCodes = {};
      sorted.forEach(function(entry) {
        var raw   = entry[0];
        var info  = entry[1];
        var count = info.count;
        var pct   = Math.round(count / maxVal * 100);
        var cls   = classifyAbeValue(raw);

        var rowClass  = "abe-bar-row";
        var fillClass = "abe-bar-fill";
        var badge     = "";
        var clickAttr = "";

        if (cls.type === "fixable") {
          rowClass  += " abe-bar-row--fixable";
          fillClass += " abe-bar-fill--fixable";
          // EN: Store raw value in data attribute; click handled by delegated listener
          // ES: Almacenar valor crudo en atributo data; clic manejado por listener delegado
          var escaped = escapeHtml(raw).replace(/"/g, "&quot;");
          var candidatesJson = JSON.stringify(cls.candidates).replace(/"/g, "&quot;");
          clickAttr = ' data-abe-fixable="' + escaped + '" data-abe-candidates="' + candidatesJson + '" tabindex="0" role="button" title="Clic para corregir este valor en Smartsheet"';
          badge = ' <span class="abe-fix-badge">&#9888; Corregir</span>';
        } else if (cls.type === "error") {
          rowClass  += " abe-bar-row--error";
          fillClass += " abe-bar-fill--error";
          // EN: Store error codes for the error info dialog / ES: Guardar códigos erróneos para el diálogo de info
          _abeErrorCodes[raw] = info.codes.slice();
          var escapedErr = escapeHtml(raw).replace(/"/g, "&quot;");
          clickAttr = ' data-abe-error="' + escapedErr + '" tabindex="0" role="button" title="Clic para ver códigos afectados / Click to see affected codes"';
          badge = ' <span class="abe-error-badge">! Error</span>';
        }

        barsHtml +=
          '<div class="' + rowClass + '"' + clickAttr + '>' +
            '<div class="abe-bar-label" title="' + escapeHtml(raw) + '">' + escapeHtml(raw) + badge + '</div>' +
            '<div class="abe-bar-right">' +
              '<div class="abe-bar-track"><div class="' + fillClass + '" style="width:' + pct + '%"></div></div>' +
              '<div class="abe-bar-count">' + count + '</div>' +
            '</div>' +
          '</div>';
      });

      chartEl.innerHTML =
        '<button type="button" class="abe-accordion-hd" onclick="toggleAbeAccordion()" aria-expanded="' + isOpen + '">' +
          '<span class="abe-chart-title">Distribución de acciones AbE</span>' +
          '<svg class="abe-chevron' + (isOpen ? '' : ' collapsed') + '" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>' +
        '</button>' +
        '<div class="abe-accordion-body' + (isOpen ? '' : ' collapsed') + '">' + barsHtml + '</div>';

      // EN: Attach delegated click listener for fixable bars (avoids inline onclick with dynamic data)
      // ES: Agregar listener de clic delegado para barras corregibles (evita onclick inline con datos dinámicos)
      var body = chartEl.querySelector(".abe-accordion-body");
      if (body) {
        body.addEventListener("click", function(e) {
          var fixRow = e.target.closest("[data-abe-fixable]");
          if (fixRow) {
            var rawVal = fixRow.getAttribute("data-abe-fixable");
            var candidates = JSON.parse(fixRow.getAttribute("data-abe-candidates") || "[]");
            openAbeFixDialog(rawVal, candidates);
            return;
          }
          var errRow = e.target.closest("[data-abe-error]");
          if (errRow) {
            openAbeErrorDialog(errRow.getAttribute("data-abe-error"));
          }
        });
        body.addEventListener("keydown", function(e) {
          if (e.key !== "Enter" && e.key !== " ") return;
          var fixRow = e.target.closest("[data-abe-fixable]");
          if (fixRow) {
            var rawVal = fixRow.getAttribute("data-abe-fixable");
            var candidates = JSON.parse(fixRow.getAttribute("data-abe-candidates") || "[]");
            openAbeFixDialog(rawVal, candidates);
            return;
          }
          var errRow = e.target.closest("[data-abe-error]");
          if (errRow) {
            openAbeErrorDialog(errRow.getAttribute("data-abe-error"));
          }
        });
      }
    }
  }

  // Meta del panel: component + filter label + row count
  // Meta del panel: componente + etiqueta de filtro + conteo de filas
  var metaEl = document.getElementById("summaryMeta");
  if (metaEl) {
    var compEl = document.getElementById("component");
    var comp   = compEl ? compEl.value : "";
    var filterLabel = "";
    if (comp === "C2") {
      if (c2Contrato)       filterLabel = " · " + c2Contrato;
      else if (c2GrantType) filterLabel = " · " + (c2GrantType === "PPD" ? "Pequeña (PPD)" : "Mediana (PMD)");
    }
    metaEl.textContent = comp + filterLabel + " · " + total + " filas" +
      " · " + haStr + " ha · " + completitud + "% códigos · " + shapePct + "% SHP · " + calPct + "% SIG";
  }

  show("summaryPanel");
  // EN: Default summary accordion to collapsed for compact layout
  // ES: Acordeón de resumen colapsado por defecto para layout compacto
  var body = document.getElementById("summaryBody");
  var chevron = document.getElementById("summaryChevron");
  var toggle = document.getElementById("summaryToggle");
  if (body)    body.classList.add("collapsed");
  if (chevron) chevron.classList.add("collapsed");
  if (toggle)  toggle.setAttribute("aria-expanded", "false");

  log("[S6] Resumen: " + total + " actividades, " + completitud + "% completitud.", "ok");

  // EN: Update the stats row cards at the top of main content
  // ES: Actualizar las tarjetas de estadísticas en la parte superior del contenido principal
  updateStatsRow(total, withCode, hectareas, calidadSi + calidadEspera);
}

/**
 * updateStatsRow — Populates the 4 summary stat cards above the table.
 * EN: Shows total rows, rows with code, total hectares, and GIS quality count.
 * ES: Muestra total filas, filas con código, hectáreas totales y conteo calidad SIG.
 */
function updateStatsRow(total, withCode, hectareas, calidadGood) {
  var el = document.getElementById("statsRow");
  if (!el) return;

  var codePct = total > 0 ? (withCode / total * 100).toFixed(1) + "%" : "";
  var calPct  = total > 0 ? (calidadGood / total * 100).toFixed(1) + "%" : "";
  var haStr   = hectareas % 1 === 0
    ? hectareas.toLocaleString("es")
    : hectareas.toLocaleString("es", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

  document.getElementById("statTotalRows").textContent = total.toLocaleString("es");
  document.getElementById("statWithCode").textContent = withCode.toLocaleString("es");
  document.getElementById("statWithCodePct").textContent = codePct;
  document.getElementById("statHectares").textContent = haStr;
  document.getElementById("statCalidad").textContent = calidadGood.toLocaleString("es");
  document.getElementById("statCalidadPct").textContent = calPct;

  el.classList.remove("hidden");
}

// EN: Open the AbE fix dialog for a fixable bar — shows candidates as radio buttons.
// ES: Abrir el diálogo de corrección AbE para una barra corregible — muestra candidatos como radio buttons.
function openAbeFixDialog(rawVal, candidates) {
  var overlay = document.getElementById("abeFixOverlay");
  if (!overlay) return;

  // EN: Show current (wrong) value / ES: Mostrar valor actual (incorrecto)
  document.getElementById("abeFixCurrentVal").textContent = rawVal;

  // EN: Build radio options for each candidate canonical / ES: Construir opciones de radio para cada candidato
  var optionsEl = document.getElementById("abeFixOptions");
  optionsEl.innerHTML = "";
  candidates.forEach(function(canon, i) {
    var lbl = document.createElement("label");
    lbl.className = "abe-fix-option";
    var rb = document.createElement("input");
    rb.type = "radio";
    rb.name = "abeFixCandidate";
    rb.value = canon;
    if (i === 0) rb.checked = true;
    lbl.appendChild(rb);
    lbl.appendChild(document.createTextNode(" " + canon));
    optionsEl.appendChild(lbl);
  });

  // EN: Store the raw value being fixed for use in confirm / ES: Guardar el valor crudo que se corrige
  overlay.dataset.rawVal = rawVal;
  overlay.classList.add("open");
  // Focus first radio for accessibility
  var firstRb = optionsEl.querySelector("input[type=radio]");
  if (firstRb) firstRb.focus();
}

function closeAbeFixDialog(e) {
  if (e && e.target !== document.getElementById("abeFixOverlay")) return;
  var overlay = document.getElementById("abeFixOverlay");
  if (overlay) overlay.classList.remove("open");
}

async function confirmAbeFixDialog() {
  var overlay = document.getElementById("abeFixOverlay");
  if (!overlay) return;
  var rawVal = overlay.dataset.rawVal;
  var selected = overlay.querySelector("input[name=abeFixCandidate]:checked");
  if (!selected) return;
  var newVal = selected.value;

  overlay.classList.remove("open");

  var p = getParams();
  log("Corrigiendo \"" + rawVal + "\" → \"" + newVal + "\" en Smartsheet…", "info");
  try {
    var res = await fetch("/api/smartsheet/fix-abe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        component: p.component,
        old_value: rawVal,
        new_value: newVal,
      }),
    });
    var data = await res.json();
    if (!res.ok) {
      log("Error: " + (data.title || data.message || res.status), "error");
      return;
    }
    if (data.updated > 0) {
      log(data.updated + " fila(s) corregidas: \"" + rawVal + "\" → \"" + newVal + "\"", "ok");
      if (sheetData) await loadSheet();
    } else {
      log("No se encontraron filas con \"" + rawVal + "\" para corregir.", "warn");
    }
  } catch (ex) {
    log("Error de conexión al corregir AbE: " + ex.message, "error");
  }
}

// EN: Open error info dialog — shows affected CÓDIGO values so user can fix manually in Smartsheet.
// ES: Abrir diálogo de error AbE — muestra valores de CÓDIGO afectados para corrección manual.
function openAbeErrorDialog(rawVal) {
  var overlay = document.getElementById("abeErrorOverlay");
  if (!overlay) return;
  document.getElementById("abeErrorCurrentVal").textContent = rawVal;
  var listEl = document.getElementById("abeErrorCodeList");
  var codes = _abeErrorCodes[rawVal] || [];
  if (codes.length === 0) {
    listEl.innerHTML = '<p style="color:var(--text-3);font-size:12px;">No hay códigos asociados. / No associated codes.</p>';
  } else {
    // EN: Show codes as comma list, max 50 shown / ES: Mostrar códigos como lista, máx 50
    var shown = codes.slice(0, 50);
    var html = '<div class="abe-error-codes">';
    shown.forEach(function(c) {
      html += '<span class="abe-error-code-chip">' + escapeHtml(c) + '</span>';
    });
    if (codes.length > 50) {
      html += '<span class="abe-error-code-chip abe-error-code-more">… +' + (codes.length - 50) + ' más</span>';
    }
    html += '</div>';
    listEl.innerHTML = html;
  }
  overlay.classList.add("open");
}

function closeAbeErrorDialog(e) {
  if (e && e.target && e.target !== document.getElementById("abeErrorOverlay")) return;
  var overlay = document.getElementById("abeErrorOverlay");
  if (overlay) overlay.classList.remove("open");
}

document.addEventListener("keydown", function(e) {
  if (e.key === "Escape") {
    var o1 = document.getElementById("abeFixOverlay");
    if (o1) o1.classList.remove("open");
    var o2 = document.getElementById("abeErrorOverlay");
    if (o2) o2.classList.remove("open");
  }
});

function toggleAbeAccordion() {
  var chartEl = document.getElementById("summaryChart");
  if (!chartEl) return;
  var body    = chartEl.querySelector(".abe-accordion-body");
  var chevron = chartEl.querySelector(".abe-chevron");
  var btn     = chartEl.querySelector(".abe-accordion-hd");
  if (!body) return;
  var opening = body.classList.contains("collapsed");
  body.classList.toggle("collapsed");
  if (chevron) chevron.classList.toggle("collapsed");
  if (btn) btn.setAttribute("aria-expanded", opening);
  try { localStorage.setItem("arAbeOpen", opening); } catch(_) {}
}

function toggleSummaryAccordion() {
  // EN: Open/close the summary accordion — preserves KPI visibility without hiding panel
  // ES: Abrir/cerrar el acordeón de resumen — mantiene visibilidad KPI sin ocultar el panel
  var body    = document.getElementById("summaryBody");
  var chevron = document.getElementById("summaryChevron");
  var toggle  = document.getElementById("summaryToggle");
  if (!body) return;
  var isOpen = !body.classList.contains("collapsed");
  body.classList.toggle("collapsed", isOpen);
  if (chevron) chevron.classList.toggle("collapsed", isOpen);
  if (toggle)  toggle.setAttribute("aria-expanded", String(!isOpen));
}

// ══════════════════════════════════════════════════════════════════════
// PASO 1-a: AGOL vs Smartsheet Diagnostic / Diagnóstico AGOL vs Smartsheet
// EN: Compares AGOL Feature Layer (previous quarter) against Smartsheet
//     to categorize activities as verified-match, mismatch, or new.
// ES: Compara Feature Layer AGOL (trimestre anterior) contra Smartsheet
//     para categorizar actividades como verificado-coincide, discrepancia o nuevo.
// NOTE: Backend endpoints still use "paso0" names for backwards compatibility.
// ══════════════════════════════════════════════════════════════════════

// EN: Store the last paso0 request payload so CSV download can re-use it.
// ES: Guardar el payload del último paso0 para reutilizarlo en la descarga CSV.
var _paso0LastPayload = null;

// EN: Batch-select set for diagnose table — item IDs chosen for batch download.
// ES: Conjunto de selección batch para tabla diagnose — IDs seleccionados para descarga.
// UI-only: not persisted, cleared automatically after download completes.
var _batchSelectedIds = new Set();

// EN: Buttons to disable while P1-a diagnose is running (shape / write operations).
// ES: Botones a deshabilitar mientras P1-a diagnóstico está en ejecución.
var _DIAG_BLOCK_BTNS = [
  "btnBatchDL", "btnListAtt", "btnGenerate", "btnReview",
  "btnSetCalidad", "btnFixAbe", "btnFillDown",
  "btnC2ApplyFillDown",
];

// ══════════════════════════════════════════════════════════════════════
// Paso 1 Agent Loop Controller
// ES: Controlador del bucle agente para Paso 1
// ══════════════════════════════════════════════════════════════════════

var AgentController = {
  state: "idle",
  items: [],
  currentIndex: -1,
  pauseReason: null,
  component: null,
  quarter: null,
  destFolder: null,
  _abortFlag: false,
  _lastDiagnoseData: null,

  // ─── Init: build queue from diagnose results ──────────────
  async init(diagnoseData) {
    var comp = document.getElementById("component").value;
    var quarter = getWorkQuarter();
    var dest = getDestFolder();
    if (!dest) {
      log({es: "[Agent] Sin carpeta destino — configure Paso 1b", en: "[Agent] No dest folder — configure Step 1b"}, "warn");
      return;
    }
    this._lastDiagnoseData = diagnoseData;
    this.component = comp;
    this.quarter = quarter;
    this.destFolder = dest;

    var resp = await this._apiPost("/api/paso1-agent/init", {
      component: comp,
      quarter: quarter,
      destFolder: dest,
      diagnoseData: diagnoseData,
    });
    if (!resp || resp.error_code) {
      log({es: "[Agent] Error al inicializar", en: "[Agent] Init error"}, "err");
      return;
    }
    this.items = resp.items || [];
    this.currentIndex = -1;
    this.state = this.items.length > 0 ? "idle" : "done";
    this._showPanels();
    this._updateUI();
    log({es: "[Agent] Cola inicializada: " + this.items.length + " ítems pendientes", en: "[Agent] Queue initialized: " + this.items.length + " pending items"}, "ok");
  },

  // ─── Restore from server state (on page reload) ──────────
  async restore() {
    var dest = getDestFolder();
    if (!dest) return;
    try {
      var resp = await fetch("/api/paso1-agent/state?destFolder=" + encodeURIComponent(dest));
      var data = await resp.json();
      if (data && data.initialized) {
        this.items = data.items || [];
        this.component = data.component;
        this.quarter = data.quarter;
        this.destFolder = data.dest_folder;
        this.currentIndex = -1;
        var summary = data.summary || {};
        if (summary.pending === 0 && summary.in_progress === 0) {
          this.state = "done";
        } else {
          this.state = "idle";
        }
        this._showPanels();
        this._updateUI();
      }
    } catch (_) { /* ignore restore errors */ }
  },

  // ─── Sidebar toggle button (Start / Pause / Resume) ──────
  toggleAction: function() {
    if (this.state === "idle") { this.start(); }
    else if (this.state === "running") { this.pause("user_pause"); }
    else if (this.state === "paused") { this.resume(); }
  },

  // ─── Start ────────────────────────────────────────────────
  async start() {
    if (this.state !== "idle" && this.state !== "paused") return;
    // Verify quarter is set before starting
    var q = getWorkQuarter();
    if (!q) {
      log({es: "[Agent] Seleccione un trimestre de trabajo antes de iniciar el agente.", en: "[Agent] Select a work quarter before starting the agent."}, "warn");
      return;
    }
    this.quarter = q;
    this.state = "running";
    this._abortFlag = false;
    this._updateUI();
    log({es: "[Agent] Iniciando procesamiento", en: "[Agent] Starting processing"});
    await this._runLoop();
  },

  // ─── Pause ────────────────────────────────────────────────
  pause: function(reason) {
    if (this.state !== "running") return;
    this.state = "paused";
    this.pauseReason = reason || "user_pause";
    this._updateUI();
    log("[Agent] Pausado: " + this.pauseReason);
  },

  // ─── Resume ───────────────────────────────────────────────
  async resume() {
    if (this.state !== "paused") return;
    this.state = "running";
    this.pauseReason = null;
    this._hideManualPrompt();
    this._updateUI();
    log({es: "[Agent] Reanudando", en: "[Agent] Resuming"});
    await this._runLoop();
  },

  // ─── Skip current ────────────────────────────────────────
  async skipCurrent() {
    if (this.currentIndex < 0 || this.currentIndex >= this.items.length) return;
    var item = this.items[this.currentIndex];
    await this._markSkip(item, "user_skipped");
    log({es: "[Agent] Saltado: " + (item.code || "fila " + item.rowNumber), en: "[Agent] Skipped: " + (item.code || "row " + item.rowNumber)});
    if (this.state === "paused") {
      this._hideManualPrompt();
      this.state = "running";
      this._updateUI();
      await this._runLoop();
    }
  },

  // ─── Cancel ───────────────────────────────────────────────
  cancel: function() {
    this._abortFlag = true;
    this.state = "idle";
    this.currentIndex = -1;
    this._hideManualPrompt();
    this._updateUI();
    log({es: "[Agent] Cancelado", en: "[Agent] Cancelled"});
  },

  // ─── Main loop ────────────────────────────────────────────
  async _runLoop() {
    while (this.state === "running") {
      if (this._abortFlag) {
        this.state = "idle";
        this._updateUI();
        return;
      }
      var nextIdx = this._findNextPending();
      if (nextIdx < 0) {
        this.state = "done";
        this._updateUI();
        log({es: "[Agent] Todos los ítems procesados", en: "[Agent] All items processed"}, "ok");
        return;
      }
      this.currentIndex = nextIdx;
      var item = this.items[this.currentIndex];
      item.item_state = "in_progress";
      this._updateUI();

      await this.processOneItem(item);

      if (this.state === "paused") {
        return;
      }
    }
  },

  // ─── Process single item (5 steps) ───────────────────────
  async processOneItem(item) {
    var reached = item.step_reached;
    var isC2Group = this.component === "C2" && item.child_codes;
    var displayName = item.code || "row " + item.rowNumber;
    if (isC2Group && item.child_codes) {
      displayName = item.code + " (" + item.child_codes.length + " códigos)";
    }
    log("[Agent] Procesando: " + displayName +
        (reached ? " (retomando desde " + reached + ")" : ""));

    // ── Step A: Code check ──
    // C2 groups already have child codes from diagnose — skip code generation.
    // C1/C3: generate code if missing.
    if (!reached || reached === null) {
      if (isC2Group) {
        // C2: no code generation needed, child codes are pre-assigned
        if (!item.rowNumber) {
          log({es: "[Agent]   A: Sin fila resumen con SHP — saltando", en: "[Agent]   A: No summary row with SHP — skipping"}, "err");
          await this._markSkip(item, "no_summary_row");
          return;
        }
        log({es: "[Agent]   A: Grupo C2 con " + (item.child_codes || []).length + " códigos", en: "[Agent]   A: C2 group with " + (item.child_codes || []).length + " codes"}, "ok");
      } else if (!item.code) {
        log("[Agent]   A: Generando código / Generating code…");
        var codeResp = await this._apiPost("/api/smartsheet/generate-codes", {
          component: this.component,
          rowIds: [item.rowId],
        });
        if (!codeResp || codeResp._httpError) {
          log({es: "[Agent]   A: Error generando código — saltando", en: "[Agent]   A: Error generating code — skipping"}, "err");
          await this._markSkip(item, "code_gen_error");
          return;
        }
        if (codeResp.patches && codeResp.patches.length) {
          var patchCells = codeResp.patches[0].cells || {};
          var codeVal = Object.values(patchCells)[0] || "";
          if (codeVal) item.code = codeVal;
          log("[Agent]   A: Código generado: " + item.code, "ok");
        }
      }
      item.step_reached = "code_ok";
      this._updateUI();
    }
    if (this._abortFlag || this.state !== "running") return;

    // ── Step B: Shapefile download (with Excel fallback) ──
    // C2: downloads from the summary row (which has the SHP attachment).
    // C1/C3: downloads from the individual row.
    // ES: Si no hay SHP adjunto, intenta descargar el Excel de áreas como
    //     respaldo para luego convertirlo a un feature class de puntos.
    if (!reached || reached === "code_ok") {
      log("[Agent]   B: Descargando shapefile…");
      var dlResp = await this._apiPost("/api/smartsheet/batch-download", {
        component: this.component,
        rowNumbers: [item.rowNumber],
        destFolder: this.destFolder,
        quarter: this.quarter,
      });
      var shpFound = false;
      if (dlResp && dlResp.results && dlResp.results.length > 0) {
        var anyError = dlResp.results.find(function(r) { return r.error; });
        if (anyError) {
          log("[Agent]   B: Error descarga: " + anyError.error, "warn");
        } else {
          var shpCount = dlResp.results.reduce(function(s, r) {
            return s + (r.shapefiles ? r.shapefiles.length : 0);
          }, 0);
          if (shpCount > 0) {
            shpFound = true;
            log("[Agent]   B: Shapefile descargado (" + shpCount + " archivos)", "ok");
            if (dlResp.results[0] && dlResp.results[0].folder) {
              item._shpFolder = dlResp.results[0].folder;
            }
          }
        }
      } else if (!dlResp) {
        log({es: "[Agent]   B: Error de descarga — saltando", en: "[Agent]   B: Download error — skipping"}, "err");
        await this._markSkip(item, "download_error");
        return;
      }
      // Fallback: no shapefile found → try area Excel attachment
      // / Respaldo: si no hay shapefile, intentar Excel de áreas
      if (!shpFound) {
        log({es: "[Agent]   B: Sin shapefile — buscando Excel de áreas…", en: "[Agent]   B: No shapefile — looking for area Excel…"}, "warn");
        var xlResp = await this._apiPost("/api/smartsheet/excel-area-download", {
          component: this.component,
          rowNumbers: [item.rowNumber],
          destFolder: this.destFolder,
          quarter: this.quarter,
        });
        var xlOk = xlResp && xlResp.results && xlResp.results.some(function(r) { return r.ok; });
        if (xlOk) {
          var xlRes = xlResp.results.find(function(r) { return r.ok; });
          item._excelFolder = xlRes.folder;
          item._excelCdg = xlRes.code || item.code || "";
          log({es: "[Agent]   B: Excel de áreas descargado (" + (xlRes.files || []).length + " archivos)",
               en: "[Agent]   B: Area Excel downloaded (" + (xlRes.files || []).length + " files)"}, "ok");
        } else {
          log({es: "[Agent]   B: No se encontraron archivos adjuntos (ni SHP ni Excel)",
               en: "[Agent]   B: No attachments found (neither SHP nor Excel)"}, "warn");
        }
      }
      item.step_reached = "downloaded";
      this._updateUI();
    }
    if (this._abortFlag || this.state !== "running") return;

    // ── Step C: ArcPy execution (auto with manual fallback) ──
    // ES: Si hay carpeta de Excel pero no de SHP, ejecuta la conversión
    //     Excel→puntos en lugar del flujo normal de shapefiles.
    if (!reached || reached === "code_ok" || reached === "downloaded") {
      // Guard: if neither shapefile folder nor Excel folder is set, there
      // is nothing for ArcPy to process — skip this item so we don't
      // accidentally re-process unrelated recent folders.
      // / Salvaguarda: sin carpeta SHP ni Excel, omitir el ítem.
      if (!item._shpFolder && !item._excelFolder) {
        log({es: "[Agent]   C: Sin SHP ni Excel — omitiendo ítem",
             en: "[Agent]   C: No SHP nor Excel — skipping item"}, "warn");
        await this._markSkip(item, "no_source_attachment");
        return;
      }
      var useExcel = !item._shpFolder && !!item._excelFolder;
      if (useExcel) {
        log({es: "[Agent]   C: Ejecutando ArcPy (Excel→puntos)…",
             en: "[Agent]   C: Running ArcPy (Excel→points)…"});
      } else {
        log({es: "[Agent]   C: Ejecutando ArcPy…", en: "[Agent]   C: Running ArcPy…"});
      }
      try {
        var arcResp;
        if (useExcel) {
          arcResp = await this._apiPost("/api/arcpy/run-excel-to-point", {
            destFolder: this.destFolder,
            quarter: this.quarter,
            items: [{folder: item._excelFolder, cdg: item._excelCdg || item.code || ""}],
            lang: getLang(),
          });
        } else {
          arcResp = await this._apiPost("/api/arcpy/run-add-to-map", {
            destFolder: this.destFolder,
            quarter: this.quarter,
            component: this.component,
            shpFolders: item._shpFolder ? [item._shpFolder] : undefined,
            lang: getLang(),
          });
        }
        if (arcResp && arcResp.ok && arcResp.returncode === 0) {
          item.step_reached = "arcpy_done";
          var stdout = arcResp.stdout || "";
          log("[Agent]   C: ArcPy OK: " + stdout.substring(0, 200), "ok");
          // Check for CdgActvdd no-match review warning
          if (stdout.indexOf("REVIEW NEEDED") >= 0) {
            // Extract the review block from stdout
            var reviewStart = stdout.indexOf("REVIEW NEEDED");
            var reviewBlock = stdout.substring(reviewStart, reviewStart + 500);
            var ssMatch = reviewBlock.match(/Smartsheet: (https:\/\/[^\s]+)/);
            var ssLink = ssMatch ? ssMatch[1] : "";
            log({es: "[Agent]   ⚠ CdgActvdd sin coincidencia — requiere revisión manual", en: "[Agent]   ⚠ CdgActvdd no match — manual review needed"}, "warn");
            if (ssLink) {
              var rowNum = item.rowNumber || "";
              logHtml({es: '[Agent]   <a href="' + escapeHtml(ssLink) + '" target="_blank" style="color:#e8a500;text-decoration:underline">Abrir Smartsheet ↗</a>' +
                (rowNum ? ' <a href="javascript:void(0)" onclick="highlightSmartsheetRow(' + rowNum + ')" style="color:#e8a500;text-decoration:underline;margin-left:6px">→ Ir a fila ' + rowNum + '</a>' : ''),
                en: '[Agent]   <a href="' + escapeHtml(ssLink) + '" target="_blank" style="color:#e8a500;text-decoration:underline">Open Smartsheet ↗</a>' +
                (rowNum ? ' <a href="javascript:void(0)" onclick="highlightSmartsheetRow(' + rowNum + ')" style="color:#e8a500;text-decoration:underline;margin-left:6px">→ Go to row ' + rowNum + '</a>' : '')});
            }
          }
        } else {
          // ArcPy execution failed — fall back to manual
          log("[Agent]   C: ArcPy falló (rc=" + (arcResp && arcResp.returncode != null ? arcResp.returncode : "?") + "): " +
              ((arcResp && arcResp.stderr) || "").substring(0, 300), "warn");
          await this._fallbackManualArcPy(item);
          return; // pause was called inside fallback
        }
      } catch (err) {
        log({es: "[Agent]   C: Error de red ArcPy: " + err.message, en: "[Agent]   C: ArcPy network error: " + err.message}, "warn");
        await this._fallbackManualArcPy(item);
        return;
      }
      this._updateUI();
    }
    if (this._abortFlag || this.state !== "running") return;

    // ── Step D: Mark complete (after auto-exec or resume from arcgis_manual) ──
    if (reached === "arcpy_done" || reached === "script_ready") {
      log({es: "[Agent]   D: Marcando completado", en: "[Agent]   D: Marking complete"});
      await this._markComplete(item, "done");
      return;
    }
  },

  // ─── Utility: item state queries ─────────────────────────

  isItemDone: function(itemId) {
    var item = this.items.find(function(i) { return i.id === itemId; });
    return item && (item.item_state === "done" || item.item_state === "skipped");
  },

  onManualCheck: function(itemId, isDone) {
    if (!this.destFolder) return;
    var item = this.items.find(function(i) { return i.id === itemId; });
    if (isDone) {
      this._apiPost("/api/paso1-agent/mark-complete", {
        destFolder: this.destFolder,
        itemId: itemId,
        stepReached: "manual",
      });
      if (item) { item.item_state = "done"; item.step_reached = "manual"; }
    } else {
      this._apiPost("/api/paso1-agent/mark-pending", {
        destFolder: this.destFolder,
        itemId: itemId,
      });
      if (item) { item.item_state = "pending"; item.step_reached = null; }
    }
    _updateDoneRowVisual(itemId, isDone);
    this._updateUI();
  },

  _findNextPending: function() {
    for (var i = 0; i < this.items.length; i++) {
      if (this.items[i].item_state === "pending" ||
          this.items[i].item_state === "in_progress") {
        return i;
      }
    }
    return -1;
  },

  async _markComplete(item, step) {
    item.item_state = "done";
    item.step_reached = step;
    await this._apiPost("/api/paso1-agent/mark-complete", {
      destFolder: this.destFolder,
      itemId: item.id,
      stepReached: step,
    });
    this._updateUI();
  },

  async _markSkip(item, reason) {
    item.item_state = "skipped";
    item.step_reached = reason;
    await this._apiPost("/api/paso1-agent/mark-skip", {
      destFolder: this.destFolder,
      itemId: item.id,
      reason: reason,
    });
    this._updateUI();
  },

  async _fallbackManualArcPy(item) {
    try {
      var scriptResp = await this._apiPost("/api/smartsheet/add-to-map-script", {
        destFolder: this.destFolder,
        quarter: this.quarter,
        component: this.component,
        shpFolders: item._shpFolder ? [item._shpFolder] : undefined,
        lang: getLang(),
      });
      if (scriptResp && scriptResp.script) {
        this._copyToClipboard(scriptResp.script);
        log({es: "[Agent]   C: Script copiado al portapapeles", en: "[Agent]   C: Script copied to clipboard"}, "ok");
      }
    } catch (e) {
      log({es: "[Agent]   C: No se pudo generar script: " + e.message, en: "[Agent]   C: Could not generate fallback script: " + e.message}, "err");
    }
    item.step_reached = "script_ready";
    this._updateUI();
    this._showManualPrompt(
      "ArcPy automático falló. Ejecute el script en ArcGIS Pro Python window y luego presione Continuar.\n" +
      "Automatic ArcPy failed. Run the script in ArcGIS Pro Python window, then press Continue."
    );
    this.pause("arcgis_manual");
  },

  async _apiPost(url, body) {
    try {
      var controller = new AbortController();
      var timeoutId = setTimeout(function() { controller.abort(); }, 120000);
      var resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Local-Token": _localToken() },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return await resp.json();
    } catch (e) {
      log("[Agent] Error de red: " + e.message, "err");
      return null;
    }
  },

  _copyToClipboard: function(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(function() {
        log({es: "[Agent] No se pudo copiar al portapapeles", en: "[Agent] Could not copy to clipboard"}, "warn");
      });
    }
  },

  // ─── Show/hide panels ────────────────────────────────────
  _showPanels: function() {
    if (this.items.length === 0) { this._hidePanels(); return; }
    // Show sidebar agent section
    var sbSec = document.getElementById("agentSection");
    if (sbSec) sbSec.style.display = "";
    // Show right sidebar agent accordion and expand it
    var rsbAgent = document.getElementById("rsb-agent");
    if (rsbAgent) {
      rsbAgent.style.display = "";
      rsbAgent.classList.remove("collapsed");
    }
    // Open right sidebar if collapsed
    var rsb = document.getElementById("rightSidebar");
    if (rsb && rsb.classList.contains("collapsed")) {
      toggleRightSidebar();
    }
  },

  _hidePanels: function() {
    var sbSec = document.getElementById("agentSection");
    if (sbSec) sbSec.style.display = "none";
    var rsbAgent = document.getElementById("rsb-agent");
    if (rsbAgent) { rsbAgent.style.display = "none"; }
  },

  _showManualPrompt: function(msg) {
    var el = document.getElementById("agentManualPrompt");
    var msgEl = document.getElementById("agentManualMsg");
    if (el && msgEl) {
      msgEl.textContent = msg;
      el.classList.remove("hidden");
    }
  },

  _hideManualPrompt: function() {
    var el = document.getElementById("agentManualPrompt");
    if (el) el.classList.add("hidden");
  },

  // ─── Render item list in right sidebar ────────────────────
  _renderItemList: function() {
    var el = document.getElementById("agentItemList");
    if (!el || this.items.length === 0) return;
    var h = '<table><thead><tr><th>#</th><th>Código</th><th>Paso</th><th>Estado</th></tr></thead><tbody>';
    for (var i = 0; i < this.items.length; i++) {
      var it = this.items[i];
      var cls = it.item_state === "done" || it.item_state === "skipped"
        ? "agent-item-done"
        : (it.item_state === "in_progress" ? "agent-item-active" : "");
      var stateLabel = it.item_state === "done" ? "Hecho"
        : it.item_state === "skipped" ? "Saltado"
        : it.item_state === "in_progress" ? "En proceso"
        : "Pendiente";
      h += '<tr class="' + cls + '">' +
        '<td>' + it.rowNumber + '</td>' +
        '<td>' + escapeHtml(it.code || "—") + '</td>' +
        '<td>' + escapeHtml(it.step_reached || "—") + '</td>' +
        '<td>' + stateLabel + '</td></tr>';
    }
    h += '</tbody></table>';
    el.innerHTML = h;
  },

  // ─── Update UI (sidebar compact + right sidebar detail) ──
  _updateUI: function() {
    // ── Shared counters ──
    var done = 0, skipped = 0, total = this.items.length;
    for (var i = 0; i < this.items.length; i++) {
      if (this.items[i].item_state === "done") done++;
      if (this.items[i].item_state === "skipped") skipped++;
    }
    var completed = done + skipped;
    var pct = total > 0 ? Math.round(completed / total * 100) : 0;

    var labels = {
      idle: "Inactivo / Idle",
      running: "En ejecución / Running",
      paused: "Pausado / Paused",
      done: "Completado / Done",
      error: "Error"
    };

    // ── Sidebar compact ──
    var statusEl = document.getElementById("agentStatus");
    var labelEl = document.getElementById("agentStateLabel");
    var progEl = document.getElementById("agentProgress");
    var barEl = document.getElementById("agentProgressBar");
    if (labelEl) labelEl.textContent = labels[this.state] || this.state;
    if (progEl) progEl.textContent = completed + " / " + total;
    if (barEl) barEl.style.width = pct + "%";
    if (statusEl) statusEl.className = "agent-status agent-" + this.state;

    // Sidebar action button: change label/icon based on state
    var actionBtn = document.getElementById("btnAgentAction");
    var actionLabel = document.getElementById("agentActionLabel");
    var actionIcon = document.getElementById("agentActionIcon");
    if (actionBtn && actionLabel) {
      if (this.state === "idle" && total > 0 && completed < total) {
        actionBtn.disabled = false;
        actionLabel.textContent = "Iniciar Agente";
        if (actionIcon) actionIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"/>';
      } else if (this.state === "running") {
        actionBtn.disabled = false;
        actionLabel.textContent = "Pausar Agente";
        if (actionIcon) actionIcon.innerHTML = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
      } else if (this.state === "paused") {
        actionBtn.disabled = false;
        actionLabel.textContent = "Reanudar Agente";
        if (actionIcon) actionIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"/>';
      } else {
        actionBtn.disabled = true;
        actionLabel.textContent = this.state === "done" ? "Agente Completado" : "Iniciar Agente";
      }
    }

    // ── Right sidebar detail ──
    var badgeEl = document.getElementById("agentBadge");
    if (badgeEl) badgeEl.textContent = completed + "/" + total;

    var currentEl = document.getElementById("agentCurrentItem");
    var codeEl = document.getElementById("agentCurrentCode");
    var stepEl = document.getElementById("agentCurrentStep");
    if (currentEl) {
      if (this.state === "running" && this.currentIndex >= 0 && this.currentIndex < total) {
        var cur = this.items[this.currentIndex];
        if (codeEl) codeEl.textContent = cur.code || ("row " + cur.rowNumber);
        if (stepEl) stepEl.textContent = cur.step_reached || "starting";
        currentEl.classList.remove("hidden");
      } else {
        currentEl.classList.add("hidden");
      }
    }

    // Agent control buttons (now in left sidebar)
    var pauseOk = this.state === "running";
    var resumeOk = this.state === "paused";
    var skipOk = this.state === "running" || this.state === "paused";
    var cancelOk = this.state === "running" || this.state === "paused";
    this._enableButton("btnAgentPause", pauseOk);
    this._enableButton("btnAgentResume", resumeOk);
    this._enableButton("btnAgentSkip", skipOk);
    this._enableButton("btnAgentCancel", cancelOk);

    // Render item list in right sidebar
    this._renderItemList();

    // Update diagnosis panel checkboxes
    this.items.forEach(function(item) {
      var row = document.querySelector('tr[data-agent-item="' + item.id + '"]');
      if (row) {
        var chk = row.querySelector(".agent-chk");
        if (chk) {
          chk.checked = item.item_state === "done" || item.item_state === "skipped";
          chk.disabled = item.item_state === "done" || item.item_state === "skipped";
        }
      }
    });
  },

  _enableButton: function(id, enabled) {
    var btn = document.getElementById(id);
    if (btn) btn.disabled = !enabled;
  },
};

function _diagBannerShow() {
  var el = document.getElementById("diagBusyBanner");
  if (el) el.style.display = "";
  _DIAG_BLOCK_BTNS.forEach(function(id) { disable(id, true); });
}
function _diagBannerHide() {
  var el = document.getElementById("diagBusyBanner");
  if (el) el.style.display = "none";
  _DIAG_BLOCK_BTNS.forEach(function(id) { disable(id, false); });
}

/* ── AGOL Connection ──────────────────────────────────────────────────── */

function _agolUpdateUI(info) {
  var statusEl = document.getElementById("agolStatusLine");
  var connectBtn = document.getElementById("btnAgolConnect");
  var disconnectBtn = document.getElementById("btnAgolDisconnect");
  var panel = document.getElementById("agolConnectPanel");

  if (info && info.connected) {
    if (statusEl) statusEl.textContent =
      "\u2713 " + (info.username || "?") + " @ " + (info.org || "AGOL");
    if (statusEl) statusEl.style.color = "";
    if (statusEl) statusEl.classList.add("text-success");
    if (connectBtn) connectBtn.style.display = "none";
    if (disconnectBtn) disconnectBtn.style.display = "";
    if (panel) panel.style.borderColor = "var(--ar-green)";
  } else {
    if (statusEl) {
      statusEl.textContent = "No conectado a AGOL / Not connected";
      statusEl.style.color = "";
      statusEl.classList.remove("text-success");
    }
    if (connectBtn) connectBtn.style.display = "";
    if (disconnectBtn) disconnectBtn.style.display = "none";
    if (panel) panel.style.borderColor = "var(--ar-blue-light)";
  }
}

async function agolConnect() {
  var orgUrl = (document.getElementById("agolOrgUrl") || {}).value?.trim() || "";

  if (!orgUrl) {
    log("[AGOL] Ingrese URL de Organización / Enter Organization URL", "warn");
    return;
  }

  disable("btnAgolConnect", true);
  log("[AGOL] Iniciando OAuth… / Starting OAuth…");

  var data = await api("/api/agol/auth/start", { org_url: orgUrl });
  if (!data || !data.url) {
    log("[AGOL] Error al iniciar OAuth / OAuth start error", "error");
    disable("btnAgolConnect", false);
    return;
  }

  // Open popup for AGOL login
  var w = 600, h = 700;
  var left = (screen.width - w) / 2, top = (screen.height - h) / 2;
  var popup = window.open(data.url, "agolOAuth",
    "width=" + w + ",height=" + h + ",left=" + left + ",top=" + top +
    ",menubar=no,toolbar=no,status=no");

  // Listen for postMessage from the popup callback page
  function onMessage(ev) {
    if (ev.data && ev.data.agolConnected) {
      window.removeEventListener("message", onMessage);
      clearInterval(pollTimer);
      log("[AGOL] OAuth exitoso / OAuth successful");
      disable("btnAgolConnect", false);
      agolCheckStatus();
    }
  }
  window.addEventListener("message", onMessage);

  // Fallback: poll status in case postMessage fails (e.g. popup blocked)
  var pollTimer = setInterval(function() {
    if (popup && popup.closed) {
      clearInterval(pollTimer);
      window.removeEventListener("message", onMessage);
      disable("btnAgolConnect", false);
      agolCheckStatus();
    }
  }, 1000);
}

async function agolDisconnect() {
  var data = await api("/api/agol/disconnect", {});
  log("[AGOL] Desconectado / Disconnected");
  _agolUpdateUI(null);
}

async function agolCheckStatus() {
  try {
    var resp = await fetch("/api/agol/status");
    var info = await resp.json();
    // Pre-fill org URL from .env default if field is empty
    var orgEl = document.getElementById("agolOrgUrl");
    if (orgEl && !orgEl.value && info.env_org_url) orgEl.value = info.env_org_url;
    _agolUpdateUI(info);
  } catch (e) { /* ignore — server may not be ready */ }
}

// Check AGOL status on page load
document.addEventListener("DOMContentLoaded", function() {
  agolCheckStatus();
});

async function paso0Diagnose() {
  var p = getParams();
  disable("btnPaso0", true);
  _diagBannerShow();

  var polygonUrl = (document.getElementById("paso0PolygonUrl") || {}).value || "";
  var pointUrl = (document.getElementById("paso0PointUrl") || {}).value || "";
  var threshold = parseFloat((document.getElementById("paso0Threshold") || {}).value) || 5;

  log("[P1-a] Comparando AGOL (polígono+punto) vs Smartsheet para " + p.component + " (tolerancia=" + threshold + " ha) …");

  var payload = {
    component: p.component,
    rowStart: p.rowStart,
    rowEnd: p.rowEnd,
    ha_threshold: threshold,
  };
  if (filteredRowNumbers && filteredRowNumbers.length > 0) {
    payload.rowNumbers = filteredRowNumbers;
  }
  if (polygonUrl) payload.agol_polygon_url = polygonUrl;
  if (pointUrl) payload.agol_point_url = pointUrl;
  if (p.c2GrantType) payload.c2GrantType = p.c2GrantType;
  if (p.c2Contrato)  payload.c2Contrato  = p.c2Contrato;

  _paso0LastPayload = payload;

  var data = await api("/api/paso0/diagnose", payload);
  disable("btnPaso0", false);
  _diagBannerHide();
  if (!data) return;

  // Log diagnostic details
  var diag = data.diagnostics || {};
  log("[P1-a] Hoja: " + (diag.sheet_name || "?") +
      " | SS filas totales: " + (diag.sheet_total_rows || "?") +
      " | En rango: " + (diag.rows_in_range || "?") +
      " | Sin ha: " + (diag.skipped_no_ha || 0) +
      " | Vacías: " + (diag.skipped_empty || 0) +
      " | Analizadas: " + (diag.analyzed || "?") +
      (diag.ss_cache_hit ? " (SS caché)" : "") +
      (diag.agol_cache_hit ? " (AGOL caché)" : "") +
      (diag.agol_targeted ? " (AGOL dirigido: " + (diag.ss_target_codes_count || 0) + " códigos, " + (diag.agol_query_batches || 0) + " lotes)" : ""));
  var ls = diag.agol_layer_stats || {};
  log("[P1-a] AGOL: " + (diag.agol_features || 0) + " códigos (polígono=" + (ls.polygon || 0) + ", punto=" + (ls.point || 0) + ")");

  // Show sample codes for debugging code-format mismatches
  if (diag.ss_sample_codes && diag.ss_sample_codes.length) {
    log("[P1-a] SS sample: " + diag.ss_sample_codes.join(", "));
  }
  if (diag.agol_sample_codes && diag.agol_sample_codes.length) {
    log("[P1-a] AGOL sample: " + diag.agol_sample_codes.join(", "));
  }

  var s = data.summary || {};
  var cmp = data.comparison || {};
  log("[P1-a] Resultado: " +
      s.verified_match + " coinciden, " +
      s.verified_mismatch + " discrepancia, " +
      s.new_this_quarter + " nuevos este trimestre" +
      " | AGOL-only: " + (cmp.agol_only_count || 0));

  if (s.verified_mismatch > 0) {
    log("[P1-a] ATENCIÓN: " + s.verified_mismatch + " actividades con diferencia de hectáreas mayor a " + cmp.ha_threshold + " ha", "warn");
  }
  if (s.new_this_quarter > 0) {
    log("[P1-a] " + s.new_this_quarter + " actividades nuevas este trimestre (no están en AGOL)", "ok");
  }

  // Auto-init agent queue BEFORE rendering so done states are available for checkboxes
  // ES: Inicializar agente ANTES de renderizar para que los estados done estén disponibles
  if (data.groups && data.groups.length > 0 &&
      (s.verified_mismatch > 0 || s.new_this_quarter > 0)) {
    await AgentController.init(data);
  } else {
    AgentController._hidePanels();
  }

  renderPaso0(data);
  show("paso0Panel");
  log("[P1-a] Diagnóstico completo: " + s.verified_pct + "% verificado-coincide.", "ok");
}

function renderPaso0(data) {
  var s = data.summary;
  var cmp = data.comparison || {};
  var isC2 = data.component === "C2";

  // ── Summary cards ──
  var sumEl = document.getElementById("paso0Summary");
  if (sumEl) {
    var vPct = s.verified_pct;
    var vStatus = vPct >= 90 ? "success" : (vPct >= 60 ? "warning" : "error");
    sumEl.innerHTML =
      _p0Card(s.total_rows, "Actividades analizadas", "SS con hectáreas", "neutral") +
      _p0Card(s.verified_match, "Verificado-Coincide", "AGOL = SS (±" + cmp.ha_threshold + " ha)", "success") +
      _p0Card(s.verified_mismatch, "Verificado-Discrepancia", "En AGOL pero ha difiere", s.verified_mismatch === 0 ? "success" : "warning") +
      _p0Card(s.new_this_quarter, "Nuevos este trimestre", "Solo en SS, no en AGOL", s.new_this_quarter === 0 ? "neutral" : "error") +
      _p0Card(vPct + "%", "Verificación AGOL", null, vStatus);
  }

  // ── Comparison bar ──
  var compBar = document.getElementById("paso0CompBar");
  if (compBar) {
    compBar.style.display = "";
    var haHtml = '<div class="p0-gis-stats">' +
      '<span class="p0-gis-stat"><b>' + cmp.ss_total_ha + '</b> ha en Smartsheet</span>' +
      '<span class="p0-gis-stat"><b>' + cmp.agol_total_ha + '</b> ha en AGOL</span>' +
      '<span class="p0-gis-stat"><b>' + cmp.ss_total_codes + '</b> códigos SS</span>' +
      '<span class="p0-gis-stat"><b>' + cmp.agol_total_codes + '</b> códigos AGOL</span>' +
    '</div>';

    var agolOnlyHtml = "";
    if (cmp.agol_only_count > 0) {
      agolOnlyHtml =
        '<details class="p0-gis-details"><summary>' + cmp.agol_only_count + ' códigos solo en AGOL (no en SS filtrado)</summary>' +
        '<div class="p0-code-list">' + cmp.agol_only.map(function(c) { return '<code>' + escapeHtml(c) + '</code>'; }).join(" ") + '</div></details>';
    }

    compBar.innerHTML =
      '<div class="p0-gis-header">' +
        '<span class="p0-gis-title">Comparación AGOL vs Smartsheet</span>' +
        '<span class="p0-gis-pct ' + (s.verified_pct >= 90 ? "p0-gis-ok" : (s.verified_pct >= 60 ? "p0-gis-warn" : "p0-gis-err")) + '">' +
          s.verified_pct + '% verificado</span>' +
      '</div>' +
      haHtml + agolOnlyHtml;
  }

  // ── Group cards ──
  var groupsEl = document.getElementById("paso0Groups");
  if (!groupsEl) return;
  var html = "";
  var comp = data.component;

  data.groups.forEach(function(g) {
    var pct = g.verified_pct;
    var barClass = pct >= 90 ? "p0-bar-ok" : (pct >= 60 ? "p0-bar-warn" : "p0-bar-err");

    // Group header
    var headerLabel = "";
    if (isC2) {
      headerLabel = (g.grant_type ? '<span class="p0-badge p0-badge-' + (g.grant_type === "PPD" ? "ppd" : "pmd") + '">' + escapeHtml(g.grant_type) + '</span> ' : '') +
        '<strong>' + escapeHtml(g.contrato || "(sin contrato)") + '</strong>' +
        (g.quarter ? ' · <span class="p0-quarter">' + escapeHtml(g.quarter) + '</span>' : '');
    } else {
      headerLabel = escapeHtml(data.component);
    }

    html +=
      '<div class="p0-group">' +
        '<div class="p0-group-hd">' +
          '<div class="p0-group-label">' + headerLabel + '</div>' +
          '<div class="p0-group-stats">' +
            '<span>' + g.verified_match + '/' + g.total + ' verificadas</span>' +
            '<span class="p0-group-pct">' + pct + '%</span>' +
          '</div>' +
        '</div>' +
        '<div class="p0-progress-track"><div class="p0-progress-fill ' + barClass + '" style="width:' + pct + '%"></div></div>';

    // Status summary tags
    html += '<div class="p0-pending-cols">';
    if (g.verified_mismatch > 0) {
      html += '<span class="p0-col-tag">' + escapeHtml("Discrepancia") + ' <b>(' + g.verified_mismatch + ')</b></span>';
    }
    if (g["new"] > 0) {
      html += '<span class="p0-col-tag">' + escapeHtml("Nuevos") + ' <b>(' + g["new"] + ')</b></span>';
    }
    html += '<span class="p0-col-tag">SS ha: <b>' + g.ss_ha_total + '</b></span>';
    html += '<span class="p0-col-tag">AGOL ha: <b>' + g.agol_ha_total + '</b></span>';
    html += '</div>';

    // Detail rows (collapsible) — show mismatches and new rows
    var actionRows = g.rows.filter(function(r) { return r.cmp_status !== "verified_match"; });
    if (actionRows.length > 0) {
      if (isC2) {
        // C2: one agent item per GROUP — render a single row for the whole group
        var groupItemId = "C2_grp_" + (g.contrato || "").replace(/ /g, "_") + "_" + (g.quarter || "").replace(/ /g, "_");
        var isDone = AgentController.isItemDone(groupItemId);
        var batchChecked = _batchSelectedIds.has(groupItemId) ? ' checked' : '';
        var batchDisabled = isDone ? ' disabled' : '';
        var doneChecked = isDone ? ' checked' : '';
        var rowClass = isDone ? ' class="p0-row-done"' : '';
        var grpSsHa = actionRows.reduce(function(acc, r) { return acc + (r.ss_ha || 0); }, 0).toFixed(2);
        html +=
          '<details class="p0-row-details">' +
            '<summary>' + actionRows.length + ' filas requieren atención / rows need attention</summary>' +
            '<table class="p0-row-table"><thead><tr>' +
              '<th class="p0-chk-col" title="Seleccionar para batch / Select for batch">⬇</th>' +
              '<th class="p0-chk-col" title="Marcar completado / Mark done">✓</th>' +
              '<th>#</th><th>Contrato</th><th>SS ha</th><th>Estado</th>' +
            '</tr></thead><tbody>' +
            '<tr data-agent-item="' + escapeHtml(groupItemId) + '"' + rowClass + '>' +
              '<td class="p0-chk-col"><input type="checkbox" class="batch-chk" data-agent-id="' + escapeHtml(groupItemId) + '"' + batchChecked + batchDisabled + '></td>' +
              '<td class="p0-chk-col"><input type="checkbox" class="done-chk" data-agent-id="' + escapeHtml(groupItemId) + '"' + doneChecked + '></td>' +
              '<td>' + (g.summaryRowNumber || '—') + '</td>' +
              '<td>' + escapeHtml(g.contrato || "—") + '</td>' +
              '<td>' + grpSsHa + '</td>' +
              '<td>' + (isDone ? '<span class="p0-status-done">✓ Completado</span>' : '<span class="p0-status-pending">' + actionRows.length + ' filas</span>') + '</td>' +
            '</tr>' +
            '</tbody></table>' +
            '<details style="margin-top:4px"><summary style="font-size:11px;color:var(--text-3)">Ver filas individuales / View child rows (' + actionRows.length + ')</summary>' +
            '<table class="p0-row-table"><thead><tr>' +
              '<th class="p0-chk-col" title="Seleccionar para batch / Select for batch">⬇</th>' +
              '<th>#</th><th>Código</th><th>SS ha</th><th>AGOL ha</th><th>Diff</th><th>Estado</th></tr></thead><tbody>';
        actionRows.forEach(function(r) {
          var childItemId = 'C2_child_' + r.rowNumber;
          var childBatchChecked = _batchSelectedIds.has(childItemId) ? ' checked' : '';
          var childBatchDisabled = isDone ? ' disabled' : '';
          html += '<tr data-agent-item="' + escapeHtml(childItemId) + '">' +
            '<td class="p0-chk-col"><input type="checkbox" class="batch-chk" data-agent-id="' + escapeHtml(childItemId) + '"' + childBatchChecked + childBatchDisabled + '></td>' +
            '<td>' + r.rowNumber + '</td>' +
            '<td>' + escapeHtml(r.code || "—") + '</td>' +
            '<td>' + (r.ss_ha != null ? r.ss_ha : "—") + '</td>' +
            '<td>' + (r.agol_ha != null ? r.agol_ha : "—") + '</td>' +
            '<td>' + (r.ha_diff != null ? r.ha_diff : "—") + '</td>' +
            '<td>' + _p0CmpStatusLabel(r.cmp_status) + '</td></tr>';
        });
        html += '</tbody></table></details></details>';
      } else {
        // C1/C3: one agent item per row
        html +=
          '<details class="p0-row-details">' +
            '<summary>' + actionRows.length + ' filas requieren atención / rows need attention</summary>' +
            '<table class="p0-row-table"><thead><tr>' +
              '<th class="p0-chk-col" title="Seleccionar para batch / Select for batch">⬇</th>' +
              '<th class="p0-chk-col" title="Marcar completado / Mark done">✓</th>' +
              '<th>#</th><th>Código</th><th>Fecha</th><th>SS ha</th><th>AGOL ha</th><th>Diff</th><th>Estado</th>' +
            '</tr></thead><tbody>';
        actionRows.forEach(function(r) {
          var itemId = comp + "_row" + r.rowNumber;
          var isDone = AgentController.isItemDone(itemId);
          var batchChecked = _batchSelectedIds.has(itemId) ? ' checked' : '';
          var batchDisabled = isDone ? ' disabled' : '';
          var doneChecked = isDone ? ' checked' : '';
          var rowClass = isDone ? ' class="p0-row-done"' : '';
          var statusCell = isDone
            ? '<span class="p0-status-done">✓ Completado</span>'
            : _p0CmpStatusLabel(r.cmp_status);
          html += '<tr data-agent-item="' + escapeHtml(itemId) + '"' + rowClass + '>' +
            '<td class="p0-chk-col"><input type="checkbox" class="batch-chk" data-agent-id="' + escapeHtml(itemId) + '"' + batchChecked + batchDisabled + '></td>' +
            '<td class="p0-chk-col"><input type="checkbox" class="done-chk" data-agent-id="' + escapeHtml(itemId) + '"' + doneChecked + '></td>' +
            '<td>' + r.rowNumber + '</td>' +
            '<td>' + escapeHtml(r.code || "—") + '</td>' +
            '<td>' + escapeHtml(r.date || "—") + '</td>' +
            '<td>' + (r.ss_ha != null ? r.ss_ha : "—") + '</td>' +
            '<td>' + (r.agol_ha != null ? r.agol_ha : "—") + '</td>' +
            '<td>' + (r.ha_diff != null ? r.ha_diff : "—") + '</td>' +
            '<td>' + statusCell + '</td>' +
          '</tr>';
        });
        html += '</tbody></table></details>';
      }
    }

    // Also show verified matches (collapsed by default)
    var matchRows = g.rows.filter(function(r) { return r.cmp_status === "verified_match"; });
    if (matchRows.length > 0) {
      html +=
        '<details class="p0-row-details">' +
          '<summary class="p0-status-ok">' + matchRows.length + ' filas verificadas / verified rows</summary>' +
          '<table class="p0-row-table"><thead><tr>' +
            '<th>#</th><th>Código</th><th>SS ha</th><th>AGOL ha</th>' +
          '</tr></thead><tbody>';
      matchRows.forEach(function(r) {
        html += '<tr>' +
          '<td>' + r.rowNumber + '</td>' +
          '<td>' + escapeHtml(r.code || "—") + '</td>' +
          '<td>' + (r.ss_ha != null ? r.ss_ha : "—") + '</td>' +
          '<td>' + (r.agol_ha != null ? r.agol_ha : "—") + '</td>' +
        '</tr>';
      });
      html += '</tbody></table></details>';
    }

    html += '</div>'; // close p0-group
  });

  groupsEl.innerHTML = html;
}

function _p0Card(value, label, sub, status) {
  return '<div class="p0-card p0-card-' + status + '">' +
    '<div class="p0-card-value">' + value + '</div>' +
    '<div class="p0-card-label">' + escapeHtml(label) + '</div>' +
    (sub ? '<div class="p0-card-sub">' + escapeHtml(sub) + '</div>' : '') +
  '</div>';
}

function _p0CmpStatusLabel(status) {
  switch (status) {
    case "verified_match":    return '<span class="p0-status-ok">Verificado</span>';
    case "verified_mismatch": return '<span class="p0-status-review">Discrepancia ha</span>';
    case "new":               return '<span class="p0-status-pending">Nuevo este trimestre</span>';
    default:                  return '<span class="p0-status-pending">' + escapeHtml(status) + '</span>';
  }
}

function _updateDoneRowVisual(itemId, isDone) {
  var row = document.querySelector('[data-agent-item="' + itemId + '"]');
  if (!row) return;
  if (isDone) {
    row.classList.add("p0-row-done");
  } else {
    row.classList.remove("p0-row-done");
  }
  // Update batch checkbox: disable when done, uncheck and remove from set
  var batchChk = row.querySelector('.batch-chk');
  if (batchChk) {
    batchChk.disabled = isDone;
    if (isDone) {
      batchChk.checked = false;
      _batchSelectedIds.delete(itemId);
    }
  }
  // Update status cell (last <td>)
  var cells = row.querySelectorAll('td');
  var statusCell = cells[cells.length - 1];
  if (statusCell) {
    if (isDone) {
      statusCell.innerHTML = '<span class="p0-status-done">✓ Completado</span>';
    } else {
      var item = AgentController.items.find(function(i) { return i.id === itemId; });
      statusCell.innerHTML = item ? _p0CmpStatusLabel(item.cmp_status || "new") : "—";
    }
  }
  _updateBatchCounter();
}

function _updateBatchCounter() {
  var groupsEl = document.getElementById("paso0Groups");
  if (!groupsEl) return;
  var bar = document.getElementById("p0BatchBar");
  if (_batchSelectedIds.size === 0) {
    if (bar) bar.remove();
    return;
  }
  var n = _batchSelectedIds.size;
  var msg = n + ' seleccionada' + (n === 1 ? '' : 's') + ' para descarga / ' + n + ' selected for download';
  if (!bar) {
    bar = document.createElement("div");
    bar.id = "p0BatchBar";
    bar.className = "p0-batch-bar";
    groupsEl.insertBefore(bar, groupsEl.firstChild);
  }
  bar.innerHTML =
    '<span class="p0-batch-bar-count">' + escapeHtml(msg) + '</span>' +
    '<button class="p0-batch-bar-clear" onclick="_clearAllBatchSelections()">Limpiar / Clear</button>';
}

function _clearAllBatchSelections() {
  _batchSelectedIds.clear();
  document.querySelectorAll('.batch-chk').forEach(function(chk) { chk.checked = false; });
  _updateBatchCounter();
}

// EN: Download Paso 0 diagnostic results as CSV.
// ES: Descargar resultados del diagnóstico Paso 0 como CSV.
async function paso0DownloadCsv() {
  if (!_paso0LastPayload) {
    showToast(null, "Primero ejecute el diagnóstico / Run the diagnostic first");
    return;
  }
  log("[P0] Descargando CSV / Downloading CSV …");
  try {
    var resp = await fetch("/api/paso0/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(_paso0LastPayload),
    });
    if (!resp.ok) {
      var err = await resp.json().catch(function() { return {}; });
      showToast(err.title ? err : null, err.message || "Error al generar CSV");
      log("[P0] Error CSV: " + (err.message || resp.statusText), "err");
      return;
    }
    var blob = await resp.blob();
    var disposition = resp.headers.get("Content-Disposition") || "";
    var fnMatch = disposition.match(/filename="?([^"]+)"?/);
    var filename = fnMatch ? fnMatch[1] : "paso0_diagnostico.csv";
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    log("[P0] CSV descargado: " + filename, "ok");
  } catch (e) {
    log("[P0] Error de red al descargar CSV: " + e.message, "err");
  }
}

// ══════════════════════════════════════════════════════════════════════
// S4: Guided Script Runner
// ES: Corredor de scripts guiado para Pasos 3 y 4
// ══════════════════════════════════════════════════════════════════════

const PASO3_PHASES = [
  {
    name: "Preparación",
    // EN: Preparation
    description: "Importar datos y preparar las capas para el análisis.",
    scripts: [
      {
        id: "import",
        label: "Importar CSV a geodatabase",
        // EN: Import CSV to geodatabase
        description: "Convierte el archivo CSV exportado de Smartsheet en una tabla dentro de la geodatabase.",
        estimatedTime: "~1 minuto",
      },
      {
        id: "merge_field_mapping",
        label: "Unir capas (Merge)",
        // EN: Merge layers
        description: "Combina la capa del trimestre actual con la capa oficial anterior, mapeando los campos correctamente.",
        estimatedTime: "~2 minutos",
      },
      {
        id: "overlap_analysis",
        label: "Detectar solapamientos",
        // EN: Detect overlaps
        description: "Identifica áreas que se superponen entre polígonos. Esto es normal y se corrige en el siguiente paso.",
        estimatedTime: "~3 minutos",
      },
      {
        id: "overlap_pdf_report",
        label: "Reporte PDF de solapamientos",
        // EN: Overlap PDF Report
        description: "Genera un reporte PDF con la tabla de solapamientos detectados (AbE, componente, geometría, área).",
        // EN: "Generates a PDF report with the detected overlap table (AbE type, component, geometry, area)."
        estimatedTime: "~2 minutos",
      },
    ],
  },
  {
    name: "Limpieza de datos",
    // EN: Data cleanup
    description: "Corregir duplicados y solapamientos espaciales.",
    scripts: [
      {
        id: "duplicate_detection",
        label: "Detectar duplicados",
        // EN: Detect duplicates
        description: "Busca pol\u00edgonos id\u00e9nticos que podr\u00edan estar duplicados por error.",
        estimatedTime: "~1 minuto",
      },
      {
        id: "erase_pipeline",
        label: "Eliminar solapamientos (Erase)",
        // EN: Remove overlaps (Erase)
        description: "Recorta los pol\u00edgonos que se solapan para eliminar doble conteo de hect\u00e1reas.",
        estimatedTime: "~5 minutos",
      },
      {
        id: "spatial_join_micro",
        label: "Uni\u00f3n espacial con microcuencas",
        // EN: Spatial join with micro-watersheds
        description: "Asigna a cada pol\u00edgono la microcuenca donde se ubica (tratamiento o control).",
        estimatedTime: "~2 minutos",
      },
    ],
  },
  {
    name: "Integraci\u00f3n oficial",
    // EN: Official integration
    description: "Incorporar los datos validados a las capas oficiales del proyecto.",
    scripts: [
      {
        id: "incentive_validation",
        label: "Validar incentivos",
        // EN: Validate incentives
        description: "Verifica que las \u00e1reas de incentivos est\u00e1n correctamente clasificadas.",
        estimatedTime: "~1 minuto",
      },
      {
        id: "append_official",
        label: "Agregar a capa oficial (Append)",
        // EN: Append to official layer
        description: "Incorpora los datos del trimestre actual a la capa oficial acumulada del proyecto.",
        estimatedTime: "~3 minutos",
        warning: "Este paso modifica la capa oficial. Aseg\u00farese de que los pasos anteriores se completaron sin errores.",
        // EN: "This step modifies the official layer. Ensure previous steps completed without errors."
      },
      {
        id: "gis_vs_ss_comparison",
        label: "Comparar GIS vs Smartsheet",
        // EN: Compare GIS vs Smartsheet
        description: "Verifica que los c\u00f3digos de actividad en GIS coinciden con los de Smartsheet.",
        estimatedTime: "~1 minuto",
      },
    ],
  },
  {
    name: "Respaldo y exportaci\u00f3n",
    // EN: Backup and export
    description: "Crear copias de seguridad y exportar resultados.",
    scripts: [
      {
        id: "backup_cumulative",
        label: "Respaldo acumulativo",
        // EN: Cumulative backup
        description: "Crea una copia de seguridad de la capa oficial antes de cerrar el trimestre.",
        estimatedTime: "~2 minutos",
      },
      {
        id: "export_excel",
        label: "Exportar a Excel",
        // EN: Export to Excel
        description: "Exporta la tabla de atributos de la capa oficial a un archivo Excel.",
        estimatedTime: "~1 minuto",
      },
    ],
  },
];

const PASO4_PHASES = [
  {
    name: "Publicaci\u00f3n en l\u00ednea",
    // EN: Online publishing
    description: "Actualizar las capas compartidas en ArcGIS Online.",
    scripts: [
      {
        id: "update_wfl_point",
        label: "Actualizar capa de puntos",
        // EN: Update point layer
        description: "Sobrescribe la capa de puntos en ArcGIS Online con los datos actualizados.",
        estimatedTime: "~5 minutos",
        warning: "Requiere conexi\u00f3n a internet estable.",
        // EN: "Requires stable internet connection."
      },
      {
        id: "update_wfl_polygon",
        label: "Actualizar capa de pol\u00edgonos",
        // EN: Update polygon layer
        description: "Sobrescribe la capa de pol\u00edgonos en ArcGIS Online.",
        estimatedTime: "~5 minutos",
      },
      {
        id: "export_shapefiles",
        label: "Exportar shapefiles",
        // EN: Export shapefiles
        description: "Genera archivos shapefile para respaldo y distribuci\u00f3n.",
        estimatedTime: "~2 minutos",
      },
    ],
  },
];

// S4 state / Estado de S4
let srCurrentScript = 0;        // EN: flat index of current script
let srCompletedScripts = {};    // EN: { scriptId: true | "skipped" }
let srCurrentPasoPhases = null; // EN: PASO3_PHASES or PASO4_PHASES

function openScriptRunner(paso) {
  srCurrentScript = 0;
  srCompletedScripts = {};
  srCurrentPasoPhases = (paso === 3) ? PASO3_PHASES : PASO4_PHASES;

  // ES: T\u00edtulo del panel / EN: Panel title
  var titleEl = document.getElementById("scriptRunnerTitle");
  if (titleEl) titleEl.textContent =
    paso === 3 ? "Paso 3 \u2014 Procesamiento Territorial" : "Paso 4 \u2014 Publicaci\u00f3n AGOL";

  renderScriptRunner();
  show("scriptRunner");
}

function renderScriptRunner() {
  var container = document.getElementById("scriptRunnerContent");
  if (!container || !srCurrentPasoPhases) return;

  var allScripts = srCurrentPasoPhases.reduce(function(acc, p) { return acc.concat(p.scripts); }, []);
  var totalDone = Object.keys(srCompletedScripts).length;

  // ES: "X de Y completados" / EN: "X of Y completed"
  var progressEl = document.getElementById("scriptRunnerProgress");
  if (progressEl) progressEl.textContent = totalDone + " de " + allScripts.length + " completados";

  var html = "";
  var globalIdx = 0;

  srCurrentPasoPhases.forEach(function(phase) {
    var phaseDone = phase.scripts.every(function(s) { return !!srCompletedScripts[s.id]; });
    var phaseScriptIndices = phase.scripts.map(function(_, i) { return globalIdx + i; });
    var phaseActive = phaseScriptIndices.indexOf(srCurrentScript) !== -1;

    var phaseClass = "sr-phase" + (phaseDone ? " done" : "") + (phaseActive ? " active" : "");
    // ES: Estado de la fase / EN: Phase status text
    var statusText = phaseDone ? "\u2713 completada" : (phaseActive ? "en progreso" : "pendiente");

    html += '<div class="' + phaseClass + '">';
    html += '<div class="sr-phase-header">';
    html += '<span class="sr-phase-name">' + phase.name + '</span>';
    html += '<span class="sr-phase-status">' + statusText + '</span>';
    html += '</div>';
    if (phaseActive || phaseDone) {
      html += '<p class="sr-phase-desc">' + phase.description + '</p>';
    }
    html += '<div class="sr-scripts">';

    phase.scripts.forEach(function(script, scriptIdx) {
      var idx = globalIdx + scriptIdx;
      var isDone = !!srCompletedScripts[script.id];
      var isSkipped = srCompletedScripts[script.id] === "skipped";
      var isCurrent = (idx === srCurrentScript);

      var scriptClass = "sr-script" + (isDone ? " done" : "") + (isCurrent ? " current" : "");
      var statusIcon = isDone ? (isSkipped ? "\u2014" : "\u2713") : (isCurrent ? "\u25c9" : "\u25cb");

      html += '<div class="' + scriptClass + '">';
      html += '<div class="sr-script-header">';
      html += '<span class="sr-script-status">' + statusIcon + '</span>';
      html += '<span class="sr-script-label">' + script.label + '</span>';
      html += '<span class="sr-script-time">' + (script.estimatedTime || "") + '</span>';
      html += '</div>';

      if (isCurrent) {
        html += '<div class="sr-script-body">';
        html += '<p class="sr-script-desc">' + script.description + '</p>';

        if (script.warning) {
          html += '<div class="sr-warning"><strong>Importante:</strong> ' + script.warning + '</div>';
          // EN: "Important: ..."
        }

        html += '<div class="sr-script-actions">';
        html += '<button class="btn-primary" onclick="srGenerateAndShow(\'' + script.id + '\')">';
        html += 'Generar Script</button>';
        // EN: "Generate Script"
        html += '<button class="btn-sm" id="srCopyBtn" disabled onclick="srCopyScript()">Copiar al portapapeles</button>';
        // EN: "Copy to clipboard"
        html += '</div>';

        html += '<div id="srScriptPreview" class="sr-script-preview hidden">';
        html += '<pre id="srScriptCode" class="code-block"></pre>';
        html += '</div>';

        html += '<div class="sr-instructions">';
        html += '<strong>Instrucciones:</strong>';
        // EN: "Instructions:"
        html += '<ol>';
        html += '<li>Abra <strong>ArcGIS Pro</strong></li>';
        // EN: "Open ArcGIS Pro"
        html += '<li>Vaya a <strong>Vista \u2192 Python</strong></li>';
        // EN: "Go to View → Python"
        html += '<li>Pegue el script copiado y presione <strong>Enter</strong></li>';
        // EN: "Paste the copied script and press Enter"
        html += '<li>Espere a que termine (' + (script.estimatedTime || "unos minutos") + ')</li>';
        // EN: "Wait for completion"
        html += '</ol>';
        html += '</div>';

        html += '<div class="sr-confirm">';
        html += '<button class="btn-primary sr-confirm-btn" onclick="srConfirmScript(\'' + script.id + '\')">';
        html += '\u2713 Ya lo ejecut\u00e9, continuar</button>';
        // EN: "I ran it, continue"
        html += '<button class="btn-sm" onclick="srSkipScript(\'' + script.id + '\')">';
        html += 'Omitir este paso</button>';
        // EN: "Skip this step"
        html += '</div>';

        html += '</div>'; // sr-script-body
      }

      html += '</div>'; // sr-script
    });

    html += '</div>'; // sr-scripts
    html += '</div>'; // sr-phase
    globalIdx += phase.scripts.length;
  });

  container.innerHTML = html;

  // EN: Auto-scroll to current / ES: Desplazar al script actual
  var currentEl = container.querySelector(".sr-script.current");
  if (currentEl) currentEl.scrollIntoView({ behavior: "smooth", block: "center" });
}

async function srGenerateAndShow(scriptType) {
  // EN: Generate script and display inside runner panel (not in #scriptOutput)
  // ES: Genera el script y lo muestra en el runner, no en #scriptOutput
  var scriptText = await genScriptForRunner(scriptType);
  if (!scriptText) return;

  var codeEl = document.getElementById("srScriptCode");
  var previewEl = document.getElementById("srScriptPreview");
  var copyBtn = document.getElementById("srCopyBtn");

  if (codeEl) codeEl.textContent = scriptText;
  if (previewEl) previewEl.classList.remove("hidden");
  if (copyBtn) copyBtn.disabled = false;
}

function srCopyScript() {
  // EN: Copy the script shown in the runner / ES: Copiar el script del runner
  var codeEl = document.getElementById("srScriptCode");
  if (!codeEl) return;
  var text = codeEl.textContent;
  navigator.clipboard.writeText(text)
    .then(function() { log("Script copiado al portapapeles.", "ok"); })
    .catch(function() {
      var ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      log("Script copiado al portapapeles.", "ok");
    });
}

function srConfirmScript(scriptId) {
  // EN: Mark script done and advance / ES: Marcar completado y avanzar
  srCompletedScripts[scriptId] = true;
  srCurrentScript++;

  var allScripts = srCurrentPasoPhases.reduce(function(acc, p) { return acc.concat(p.scripts); }, []);
  var totalDone = Object.keys(srCompletedScripts).length;
  var pasoId = (srCurrentPasoPhases === PASO3_PHASES) ? 3 : 4;

  if (totalDone >= allScripts.length) {
    // EN: All done — mark paso as success / ES: Todo completado — marcar paso como exitoso
    updatePipelineStep(pasoId, "success");
    if (typeof showSuccessToast === "function") {
      showSuccessToast("Paso " + pasoId + " completado: todos los scripts ejecutados.");
      // EN: "Step X completed: all scripts executed."
    }
  } else {
    var nextScript = allScripts[srCurrentScript];
    var nextLabel = nextScript ? nextScript.label : "Completado";
    updatePipelineStep(pasoId, "awaiting", nextLabel + " (" + totalDone + "/" + allScripts.length + ")");
  }

  renderScriptRunner();
}

function srSkipScript(scriptId) {
  // EN: Skip script and advance / ES: Omitir script y avanzar
  srCompletedScripts[scriptId] = "skipped";
  srCurrentScript++;
  renderScriptRunner();
}

// ══════════════════════════════════════════════════════════════
// ══ S1: Wizard Mode (Modo Asistente)
// ══ Dependencies: S2 (updatePipelineStep), S4 (openScriptRunner)
// ══════════════════════════════════════════════════════════════

// ── State / Estado ──
let wizardMode = false;          // EN: true=wizard visible, false=expert(sidebar) mode
let wizardCurrentPaso = 0;       // EN: index in WIZARD_STEPS
let wizardSubStep = 0;           // EN: sub-step index within manual steps (3, 4, 6)
let wizardCompletedPasos = {};   // EN: { 1: true, "1b": true, 2: false, ... }
let simulationMode = false;      // EN: simulation mode — prevents write operations

// ── Step Definitions / Definición de pasos ──
const WIZARD_STEPS = [
  {
    id: 1,
    // ES: Recolección de Datos / EN: Data Collection
    title: "Recolección de Datos",
    subtitle: "Conectar con Smartsheet y descargar información",
    description: "En este paso descargamos los datos del trimestre actual desde Smartsheet: actividades reportadas, códigos y archivos shapefile.",
    actions: [
      { label: "Cargar datos de Smartsheet", fn: "loadSheet", required: true },
      { label: "Generar códigos faltantes", fn: "generateCodes", required: false },
      { label: "Actualizar revisión (shapefile)", fn: "updateReview", required: false }
    ],
    autoComplete: true,
    helpText: "Si el token aparece en rojo, contacte al administrador del sistema."
  },
  {
    id: "1b",
    // ES: Descarga y Validación / EN: Download and Validation
    title: "Descarga y Validación",
    subtitle: "Descargar archivos shapefile y exportar CSV",
    description: "Descargamos los archivos de formas (shapefiles) adjuntos en Smartsheet y exportamos los datos a CSV para ArcGIS.",
    actions: [
      { label: "Exportar datos a CSV", fn: "exportCSV", required: true },
      { label: "Descargar todos los shapefiles", fn: "batchDownload", required: true }
    ],
    autoComplete: false,
    helpText: "Los archivos se guardan en la carpeta configurada en 'Rutas Locales'."
  },
  {
    id: 3,
    // ES: Procesamiento Territorial / EN: Territorial Processing
    title: "Procesamiento Territorial",
    subtitle: "Ejecutar scripts en ArcGIS Pro",
    description: "Se generan scripts de Python que usted debe ejecutar en la ventana Python de ArcGIS Pro. El sistema los genera; usted solo copia y pega.",
    subSteps: [
      { label: "Importar CSV a GDB", scriptType: "import" },
      { label: "Unir capas (Merge)", scriptType: "merge_field_mapping" },
      { label: "Detectar solapamientos", scriptType: "overlap_analysis" },
      { label: "Detectar duplicados", scriptType: "duplicate_detection" },
      { label: "Eliminar solapamientos (Erase)", scriptType: "erase_pipeline" },
      { label: "Unión espacial (Microcuencas)", scriptType: "spatial_join_micro" },
      { label: "Validar incentivos", scriptType: "incentive_validation" },
      { label: "Agregar a capa oficial", scriptType: "append_official" },
      { label: "Comparar GIS vs Smartsheet", scriptType: "gis_vs_ss_comparison" },
      { label: "Respaldo acumulativo", scriptType: "backup_cumulative" },
      { label: "Exportar a Excel", scriptType: "export_excel" }
    ],
    isManual: true,
    helpText: "Abra ArcGIS Pro → Vista → Python. Pegue cada script y presione Enter."
  },
  {
    id: 4,
    // ES: Publicación en ArcGIS Online / EN: AGOL Publishing
    title: "Publicación en ArcGIS Online",
    subtitle: "Actualizar capas web compartidas",
    description: "Estos scripts actualizan las capas publicadas en ArcGIS Online para que el equipo pueda ver los datos actualizados en el mapa web.",
    subSteps: [
      { label: "Actualizar capa de puntos", scriptType: "update_wfl_point" },
      { label: "Actualizar capa de polígonos", scriptType: "update_wfl_polygon" },
      { label: "Exportar shapefiles", scriptType: "export_shapefiles" }
    ],
    isManual: true,
    helpText: "Requiere conexión a internet y credenciales de ArcGIS Online."
  },
  {
    id: 5,
    // ES: Excel Maestro / EN: Master Excel
    title: "Excel Maestro",
    subtitle: "Consolidar datos de los 3 componentes",
    description: "Genera un archivo Excel con una hoja por componente (C1, C2, C3) que consolida toda la información del trimestre.",
    actions: [
      { label: "Generar Excel Maestro", fn: "generateExcelMaster", required: true }
    ],
    autoComplete: true,
    helpText: "El archivo se guarda automáticamente en la carpeta configurada."
  },
  {
    id: 6,
    // ES: Dashboard Power BI / EN: Power BI Dashboard
    title: "Dashboard Power BI",
    subtitle: "Actualizar el modelo semántico de Power BI",
    description: "Abra Power BI Desktop con el proyecto .pbip, conecte por MCP y actualice las tablas del modelo semántico. El sistema le ayuda a verificar que todo esté configurado.",
    actions: [
      { label: "Verificar estado de PBI Desktop", fn: "pbiCheckStatus", required: true,
        helpText: "Comprueba si Power BI Desktop está corriendo y muestra el puerto de conexión." },
      { label: "Abrir PBI Desktop", fn: "pbiLaunch", required: false,
        helpText: "Lanza PBI Desktop con el archivo .pbip. Espera automáticamente a que el motor AS esté listo." }
    ],
    autoComplete: false,
    helpText: "Necesita Power BI Desktop instalado. La actualización de tablas se hace vía MCP desde VS Code Copilot."
  },
  {
    id: 7,
    // ES: Documentación y Respaldo / EN: Documentation and Backup
    title: "Documentación y Respaldo",
    subtitle: "Generar reportes y crear respaldo",
    description: "Crea un reporte de errores, un resumen de los datos procesados y una copia de respaldo de todos los archivos del trimestre.",
    actions: [
      { label: "Ver reporte de errores", fn: "viewErrorReport", required: false },
      { label: "Ver resumen de datos", fn: "viewDataSummary", required: false }
    ],
    autoComplete: false,
    helpText: "Revise el reporte de errores antes de dar por terminado el trimestre."
  }
];

// ── Mode Switch / Cambio de modo ──
function setMode(mode) {
  // EN: Switch between wizard and expert (sidebar) mode
  // ES: Cambia entre modo asistente y modo experto (barra lateral)
  wizardMode = (mode === "wizard");
  var sidebar = document.getElementById("sidebar");
  var resizeHandle = document.getElementById("resizeHandle");
  var wizardView = document.getElementById("wizardView");
  var btnWizard = document.getElementById("btnWizard");
  var btnExpert = document.getElementById("btnExpert");

  if (wizardMode) {
    sidebar.classList.add("hidden");
    if (resizeHandle) resizeHandle.classList.add("hidden");
    wizardView.classList.remove("hidden");
    btnWizard.classList.add("active");
    btnExpert.classList.remove("active");
    renderWizardStep();
  } else {
    sidebar.classList.remove("hidden");
    if (resizeHandle) resizeHandle.classList.remove("hidden");
    wizardView.classList.add("hidden");
    btnWizard.classList.remove("active");
    btnExpert.classList.add("active");
  }
  saveWizardState();
}

// ── Render current step / Renderizar paso actual ──
function renderWizardStep() {
  var step = WIZARD_STEPS[wizardCurrentPaso];
  var content = document.getElementById("wizardContent");
  if (!content) return;

  var stepIdx = wizardCurrentPaso + 1;
  var totalSteps = WIZARD_STEPS.length;
  var isCompleted = wizardCompletedPasos[step.id];

  var html = '<div class="wiz-step-card">';

  // Step header / Encabezado del paso
  html += '<div class="wiz-step-header">';
  html += '<span class="wiz-step-num">Paso ' + step.id + '</span>';
  html += '<span class="wiz-step-counter">' + stepIdx + ' / ' + totalSteps + '</span>';
  html += '<h2 class="wiz-step-title">' + step.title + '</h2>';
  html += '<p class="wiz-step-sub">' + step.subtitle + '</p>';
  html += '</div>';

  // Description / Descripción
  html += '<div class="wiz-step-desc"><p>' + step.description + '</p></div>';

  // Actions or sub-steps / Acciones o sub-pasos
  html += '<div class="wiz-step-body">';
  if (step.subSteps) {
    html += renderWizSubSteps(step);
  } else if (step.actions) {
    step.actions.forEach(function(action) {
      html += '<button class="wiz-action-btn' + (action.required ? ' required' : '') + '"';
      if (simulationMode && action.required) {
        // EN: In simulation mode, show preview but don't execute write actions
        // ES: En modo simulación, mostrar vista previa sin ejecutar acciones de escritura
        html += ' onclick="wizSimAction(\'' + action.label + '\')"';
      } else {
        html += ' onclick="' + action.fn + '(); wizMarkAction(\'' + action.fn + '\')"';
      }
      html += '>';
      html += action.label;
      if (action.required) html += ' <span class="wiz-required">✱</span>';
      html += '</button>';
      if (action.helpText) {
        html += '<p class="wiz-action-help">' + action.helpText + '</p>';
      }
    });
  }
  html += '</div>';

  // Help box / Cuadro de ayuda
  if (step.helpText) {
    html += '<div class="wiz-help-box"><strong>Ayuda:</strong> ' + step.helpText + '</div>';
  }

  html += '</div>'; // wiz-step-card

  content.innerHTML = html;

  // Update nav buttons / Actualizar botones de navegación
  var wizPrev = document.getElementById("wizPrev");
  var wizNext = document.getElementById("wizNext");
  if (wizPrev) wizPrev.disabled = (wizardCurrentPaso === 0);
  if (wizNext) {
    // EN: Last step shows "Finalizar" / ES: Último paso muestra "Finalizar"
    wizNext.textContent = (wizardCurrentPaso === WIZARD_STEPS.length - 1)
      ? "Finalizar ✓"
      : "Siguiente →";
  }

  saveWizardState();
}

// ── Render sub-steps (for manual steps 3, 4, 6) ──
function renderWizSubSteps(step) {
  // EN: For steps with ArcPy/PowerBI scripts, render a checklist with generate+copy+confirm
  // ES: Para pasos con scripts ArcPy/PowerBI, renderiza lista con generar+copiar+confirmar
  var html = '<div class="wiz-substeps">';
  step.subSteps.forEach(function(sub, i) {
    var isCurrent = (i === wizardSubStep);
    var isDone = (i < wizardSubStep);
    var cls = "wiz-substep" + (isCurrent ? " current" : "") + (isDone ? " done" : "");

    html += '<div class="' + cls + '">';
    html += '<div class="wiz-substep-hd">';
    html += '<span class="wiz-substep-num">' + (i + 1) + '/' + step.subSteps.length + '</span>';
    html += '<span class="wiz-substep-label">' + sub.label + '</span>';
    if (isDone) html += '<span class="wiz-check">✓</span>';
    html += '</div>';

    if (isCurrent) {
      html += '<div class="wiz-substep-body">';

      if (sub.action) {
        // EN: Action-based substep (e.g. pbiCheckStatus, pbiLaunch)
        // ES: Substep basado en acción (ej. verificar estado, abrir PBI)
        html += '<div class="wiz-substep-actions">';
        html += '<button class="btn-primary" onclick="' + sub.action + '()">' + sub.label + '</button>';
        html += '</div>';
        html += '<div class="wiz-substep-confirm" style="margin-top:.75rem">';
        html += '<p>¿Listo para continuar?</p>';
        html += '<button onclick="wizConfirmSubStep()" class="btn-primary wiz-confirm-btn">✓ Continuar</button>';
        html += '</div>';
      } else {
        // EN: Script-based substep (generate + copy + run in ArcGIS Pro)
        html += '<ol class="wiz-instructions">';
        html += '<li>Haga clic en <strong>Generar Script</strong></li>';
        html += '<li>Haga clic en <strong>Copiar al portapapeles</strong></li>';
        html += '<li>Abra <strong>ArcGIS Pro → Vista → Python</strong></li>';
        html += '<li>Pegue el script y presione <strong>Enter</strong></li>';
        html += '<li>Espere a que termine, luego haga clic en <strong>Ya lo ejecuté</strong></li>';
        html += '</ol>';

        html += '<div class="wiz-substep-actions">';
        html += '<button class="btn-primary" onclick="wizGenScript(\'' + sub.scriptType + '\')">Generar Script</button>';
        html += '<button class="btn-sm" id="wizCopyBtn" onclick="wizCopyScript()" disabled>Copiar al portapapeles</button>';
        html += '</div>';

        html += '<div id="wizScriptPreview" class="wiz-script-preview hidden">';
        html += '<pre id="wizScriptCode" class="code-block wiz-code"></pre>';
        html += '</div>';

        html += '<div class="wiz-substep-confirm">';
        html += '<p>¿Ya ejecutó este script en ArcGIS Pro?</p>';
        html += '<button onclick="wizConfirmSubStep()" class="btn-primary wiz-confirm-btn">✓ Ya lo ejecuté, continuar</button>';
        html += '</div>';
      }

      html += '</div>'; // wiz-substep-body
    }

    html += '</div>'; // wiz-substep
  });
  html += '</div>';
  return html;
}

// ── Navigation / Navegación ──
function wizardNext() {
  // EN: Advance to next step, mark current as completed
  // ES: Avanzar al siguiente paso, marcar el actual como completado
  if (wizardCurrentPaso < WIZARD_STEPS.length - 1) {
    wizardCompletedPasos[WIZARD_STEPS[wizardCurrentPaso].id] = true;
    var nextStep = WIZARD_STEPS[wizardCurrentPaso + 1];
    updatePipelineStep(nextStep.id, "active");
    wizardCurrentPaso++;
    wizardSubStep = 0;
    renderWizardStep();
  } else {
    // EN: Last step — show completion / ES: Último paso — mostrar pantalla final
    wizardCompletedPasos[WIZARD_STEPS[wizardCurrentPaso].id] = true;
    showWizardCompletion();
  }
  saveWizardState();
}

function wizardPrev() {
  // EN: Go back to previous step / ES: Retroceder al paso anterior
  if (wizardCurrentPaso > 0) {
    wizardCurrentPaso--;
    wizardSubStep = 0;
    renderWizardStep();
    saveWizardState();
  }
}

// ── Sub-step confirm / Confirmar sub-paso ──
function wizConfirmSubStep() {
  // EN: Mark sub-step done; if all done, advance to next wizard step
  // ES: Marcar sub-paso como hecho; si todos terminados, avanzar al siguiente paso
  var step = WIZARD_STEPS[wizardCurrentPaso];
  if (wizardSubStep < step.subSteps.length - 1) {
    wizardSubStep++;
    renderWizardStep();
  } else {
    // EN: All sub-steps completed — go to next paso
    // ES: Todos los sub-pasos completados — ir al siguiente paso
    wizardNext();
  }
  saveWizardState();
}

// ── Script generation inside wizard ──
async function wizGenScript(scriptType) {
  // EN: Generate script and display inside wizard (not in #scriptOutput)
  // ES: Genera el script y lo muestra dentro del asistente
  var scriptText = await genScriptForRunner(scriptType);
  if (!scriptText) return;

  var codeEl = document.getElementById("wizScriptCode");
  var previewEl = document.getElementById("wizScriptPreview");
  var copyBtn = document.getElementById("wizCopyBtn");

  if (codeEl) codeEl.textContent = scriptText;
  if (previewEl) previewEl.classList.remove("hidden");
  if (copyBtn) copyBtn.disabled = false;
}

function wizCopyScript() {
  // EN: Copy the script shown in wizard preview / ES: Copiar script del asistente
  var codeEl = document.getElementById("wizScriptCode");
  if (!codeEl) return;
  var text = codeEl.textContent;
  navigator.clipboard.writeText(text)
    .then(function() { log("Script copiado al portapapeles.", "ok"); })
    .catch(function() {
      var ta = document.createElement("textarea");
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      log("Script copiado al portapapeles.", "ok");
    });
}

// ── Mark action completion / Marcar acción completada ──
function wizMarkAction(fnName) {
  // EN: Placeholder — wizard can detect when an action button was clicked
  // ES: Marcador — el asistente detecta cuando se hizo clic en una acción
  log("Asistente: acción '" + fnName + "' ejecutada.", "ok");
  // EN: Log message: "Wizard: action executed."
}

function wizSimAction(label) {
  // EN: Simulation mode action — show toast instead of executing
  // ES: Acción en modo simulación — mostrar notificación en vez de ejecutar
  if (typeof showSuccessToast === "function") {
    showSuccessToast("Simulación: se ejecutaría '" + label + "'");
    // EN: "Simulation: would execute '{label}'"
  } else {
    log("Simulación: se ejecutaría '" + label + "'", "ok");
  }
}

// ── Completion screen / Pantalla de finalización ──
function showWizardCompletion() {
  // EN: Show final completion message with brand slogan
  // ES: Mostrar mensaje final con eslogan de la marca
  var content = document.getElementById("wizardContent");
  if (!content) return;

  content.innerHTML = [
    '<div class="wiz-complete">',
    '  <div class="wiz-complete-icon">✓</div>',
    '  <h2>Actualización completada</h2>',
    // EN: Update completed
    '  <p>Todos los pasos del pipeline se han ejecutado correctamente.</p>',
    // EN: All pipeline steps have been completed successfully.
    '  <p style="margin-top:8px">Los datos actualizados ya están disponibles en:</p>',
    // EN: Updated data is now available in:
    '  <ul class="wiz-complete-list">',
    '    <li>ArcGIS Online (mapa web)</li>',
    '    <li>Power BI (dashboard)</li>',
    '    <li>Excel Maestro (archivo local)</li>',
    '  </ul>',
    '  <p class="wiz-slogan">Cuencas conservadas | Comunidades productivas</p>',
    '  <button onclick="resetWizard()" class="btn-primary wiz-restart-btn">Iniciar nuevo ciclo</button>',
    // EN: Start new cycle
    '</div>'
  ].join("\n");

  // EN: Update nav / ES: Actualizar navegación
  var wizNext = document.getElementById("wizNext");
  var wizPrev = document.getElementById("wizPrev");
  if (wizNext) wizNext.disabled = true;
  if (wizPrev) wizPrev.disabled = false;

  // EN: Mark all steps done in progress bar / ES: Marcar todos los pasos como completados
  WIZARD_STEPS.forEach(function(s) {
    updatePipelineStep(s.id, "success");
  });
}

function navigateWizardToPaso(pasoId) {
  // EN: Navigate wizard to the step matching pasoId (called from progress bar click)
  // ES: Navegar el asistente al paso que coincide con pasoId (desde clic en barra de progreso)
  var idx = WIZARD_STEPS.findIndex(function(s) { return String(s.id) === String(pasoId); });
  if (idx === -1) return;
  wizardCurrentPaso = idx;
  renderWizardStep();
}

function resetWizard() {
  // EN: Reset wizard state to start a new quarterly cycle
  // ES: Reiniciar el asistente para iniciar un nuevo ciclo trimestral
  wizardCurrentPaso = 0;
  wizardSubStep = 0;
  wizardCompletedPasos = {};
  localStorage.removeItem("arWizardState");
  renderWizardStep();
}

// ── Simulation mode / Modo simulación ──
function toggleSimulation() {
  // EN: Toggle simulation mode — prevents write API calls
  // ES: Activar/desactivar modo simulación — evita llamadas de escritura a la API
  simulationMode = !simulationMode;
  document.body.classList.toggle("simulation-mode", simulationMode);

  var simBanner = document.getElementById("wizardSimBanner");
  var simBtn = document.getElementById("btnSimulation");

  if (simulationMode) {
    if (simBanner) simBanner.classList.remove("hidden");
    if (simBtn) simBtn.classList.add("active");
    if (typeof showSuccessToast === "function") {
      showSuccessToast("Modo simulación activado — los datos no serán modificados");
      // EN: Simulation mode activated — data will not be modified
    }
  } else {
    if (simBanner) simBanner.classList.add("hidden");
    if (simBtn) simBtn.classList.remove("active");
    log("Modo simulación desactivado.", "ok");
    // EN: Simulation mode deactivated
  }

  if (wizardMode) renderWizardStep();
}

// ── Power BI Desktop functions / Funciones de PBI Desktop ──

async function pbiCheckStatus() {
  // ES: Verificar estado de PBI Desktop / EN: Check PBI Desktop status
  log("Verificando estado de PBI Desktop…");
  var data = await apiGet("/api/pbi/status");
  if (!data) return;

  renderPbiPanel(data);
  show("pbiPanel");
  updatePipelineStep(6, data.running ? "active" : "pending");
  log("Estado de PBI Desktop verificado.", "ok");
}

async function pbiLaunch() {
  // ES: Abrir PBI Desktop con el archivo .pbip / EN: Launch PBI Desktop
  disable("btnPbiLaunch", true);
  log("Abriendo Power BI Desktop…");
  var data = await api("/api/pbi/launch", {});
  if (!data) { disable("btnPbiLaunch", false); return; }

  log(data.message, "ok");
  showSuccessToast("Power BI Desktop iniciado. Esperando motor AS…");
  pbiPollReady(0);
}

function pbiPollReady(elapsed) {
  // ES: Encuestar hasta que el motor AS esté listo / EN: Poll until AS engine is ready
  if (elapsed >= 120) {
    disable("btnPbiLaunch", false);
    log("Tiempo agotado esperando PBI Desktop AS engine.", "warn");
    return;
  }
  setTimeout(async function() {
    var data = await apiGet("/api/pbi/wait");
    if (!data) return;
    if (data.ready) {
      disable("btnPbiLaunch", false);
      log("PBI Desktop listo en puerto " + data.port, "ok");
      showSuccessToast("PBI Desktop listo — puerto " + data.port);
      updatePipelineStep(6, "active", "Puerto " + data.port);
      pbiCheckStatus();
    } else {
      log("Esperando PBI Desktop… (" + (elapsed + 5) + "s)", "info");
      pbiPollReady(elapsed + 5);
    }
  }, 5000);
}

function renderPbiPanel(status) {
  // ES: Renderiza el panel de PBI en el área principal / EN: Render PBI panel in main area
  var panel = document.getElementById("pbiPanel");
  if (!panel) return;

  var html = '<div class="panel-hd"><h3 class="panel-title">Power BI Desktop — Estado</h3></div>';
  html += '<div class="panel-bd">';

  // Status indicator / Indicador de estado
  if (status.running) {
    html += '<div style="color:var(--ar-green);font-weight:700;margin-bottom:10px">';
    html += '● PBI Desktop corriendo en puerto ' + escapeHtml(String(status.port));
    html += '</div>';
    html += '<div style="margin-bottom:10px">';
    html += '<strong>Conexión MCP:</strong>';
    html += '<div style="display:flex;align-items:center;gap:6px;margin-top:4px">';
    html += '<code id="pbiConnStr" style="flex:1;padding:6px 10px;background:var(--bg-alt,#f5f5f5);border-radius:4px;font-size:13px;word-break:break-all">';
    html += escapeHtml(status.connectionString);
    html += '</code>';
    html += '<button class="btn-sm" onclick="pbiCopyConnStr()">Copiar</button>';
    html += '</div></div>';
  } else {
    html += '<div class="text-error" style="font-weight:700;margin-bottom:10px">';
    html += '○ PBI Desktop no está corriendo / Not running';
    html += '</div>';
    html += '<p style="font-size:13px;color:var(--text-2,#666);margin-bottom:10px">';
    html += 'Haga clic en "Abrir PBI Desktop" para iniciar. / Click "Launch" to start.</p>';
  }

  // File status / Estado de archivos
  html += '<div style="font-size:13px;margin-bottom:10px">';
  html += '<div><strong>Archivo PBIP:</strong> ' + (status.pbipExists ? '✓' : '✗') +
    ' <span style="color:var(--text-2,#666)">' + displayPath(status.pbipPath || '') + '</span></div>';
  html += '<div><strong>Carpeta TMDL:</strong> ' + (status.tmdlExists ? '✓' : '✗') + '</div>';
  if (status.basePath) {
    html += '<div><strong>BasePath:</strong> ' + (status.basePathExists ? '✓' : '✗ (no encontrado)');
    html += '<br><span style="color:var(--text-2,#666)">' + displayPath(status.basePath) + '</span></div>';
  }
  html += '</div>';

  // MCP workflow steps (only when running) / Instrucciones MCP
  if (status.running) {
    html += '<div style="border-top:1px solid var(--border,#ddd);padding-top:10px;margin-top:10px">';
    html += '<h4 style="margin:0 0 8px">Flujo de actualización / Refresh workflow</h4>';
    html += '<ol style="margin:0;padding-left:20px;font-size:13px;line-height:1.8">';
    html += '<li style="color:var(--ar-green)">PBI Desktop iniciado ✓</li>';
    html += '<li>Conectar MCP: <code>connection_operations → Connect</code></li>';
    html += '<li>Listar BD: <code>database_operations → List</code></li>';
    html += '<li>Actualizar tablas: <code>partition_operations → Refresh</code></li>';
    html += '<li>Verificar: <code>dax_query_operations → Execute</code></li>';
    html += '<li>Guardar en PBI Desktop (Ctrl+S)</li>';
    html += '</ol></div>';

    // Refreshable tables / Tablas actualizables
    html += '<details style="margin-top:10px"><summary style="cursor:pointer;font-weight:600;font-size:13px">Tablas actualizables</summary>';
    html += '<div id="pbiTableList" style="margin-top:6px"><em>Cargando…</em></div>';
    html += '</details>';
  }

  // Actions / Acciones
  html += '<div style="margin-top:12px;display:flex;gap:8px">';
  if (!status.running) {
    html += '<button class="btn-primary" onclick="pbiLaunch()">Abrir PBI Desktop</button>';
  }
  html += '<button class="btn-sm" onclick="pbiCheckStatus()">Actualizar estado</button>';
  html += '</div>';

  html += '</div>'; // panel-bd
  panel.innerHTML = html;

  if (status.running) pbiLoadTables();
}

async function pbiLoadTables() {
  // ES: Carga la lista de tablas actualizables / EN: Load refreshable tables list
  var data = await apiGet("/api/pbi/tables");
  if (!data) return;
  var el = document.getElementById("pbiTableList");
  if (!el) return;

  var html = '';
  var groups = [
    { key: "excel", label: "Excel" },
    { key: "folder", label: "Folder (Excel múltiples)" },
    { key: "smartsheet", label: "Smartsheet" },
    { key: "erosion", label: "Erosión (SWY)" },
  ];
  groups.forEach(function(g) {
    var items = data[g.key];
    if (!items || !items.length) return;
    html += '<div style="margin:6px 0"><strong>' + g.label + ' (' + items.length + ')</strong>';
    html += '<table style="width:100%;font-size:12px;margin-top:4px"><tbody>';
    items.forEach(function(t) {
      html += '<tr><td style="padding:2px 8px">' + t.table + '</td>';
      html += '<td style="padding:2px 8px;color:var(--text-2,#666)">' + t.source + '</td></tr>';
    });
    html += '</tbody></table></div>';
  });
  el.innerHTML = html;
}

function pbiCopyConnStr() {
  // ES: Copiar cadena de conexión / EN: Copy connection string to clipboard
  var el = document.getElementById("pbiConnStr");
  if (!el) return;
  navigator.clipboard.writeText(el.textContent)
    .then(function() { showSuccessToast("Cadena de conexión copiada"); })
    .catch(function() {
      var ta = document.createElement("textarea"); ta.value = el.textContent;
      document.body.appendChild(ta); ta.select(); document.execCommand("copy");
      document.body.removeChild(ta);
      showSuccessToast("Cadena de conexión copiada");
    });
}

// ── G9: PDF export guide for Power BI / Guía de exportación PDF para Power BI ──
async function exportPbiPdf() {
  // ES: Genera una guía de exportación PDF para Power BI Desktop (sin API Azure AD).
  // EN: Generates a PDF export guide for Power BI Desktop (no Azure AD API available).
  disable("btnPbiExportPdf", true);

  const reportName = (document.getElementById("pbiReportName")?.value || "").trim() || "AR_Dashboard";
  const outputPath = (document.getElementById("pbiOutputPath")?.value || "").trim();
  // EN: Reuse quarter from the work-quarter dropdown if available
  // ES: Reutilizar el trimestre del desplegable de trabajo si está disponible
  const quarter = getWorkQuarter ? getWorkQuarter() : "";

  const data = await api("/api/pbi/export-pdf", {
    report_name: reportName,
    output_path: outputPath,
    quarter: quarter,
    include_mcp: true,
  });

  disable("btnPbiExportPdf", false);
  if (!data) return;

  const resultDiv = document.getElementById("pbiPdfResult");
  if (!resultDiv) return;

  // EN: Show the guide in a scrollable code block with a copy button.
  // ES: Mostrar la guía en un bloque de código desplazable con botón de copiar.
  const escapedGuide = (data.guide || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  resultDiv.style.display = "block";
  resultDiv.innerHTML = `
    <div style="margin-bottom:6px; font-size:11px; color:var(--ar-blue); font-weight:600">
      📄 Guía de exportación PDF / PDF Export Guide
      <span style="color:#888; font-weight:400; margin-left:6px">(${data.strategy || "manual"})</span>
    </div>
    <div style="background:#1e293b; border:1px solid #334155; border-radius:4px; padding:8px; max-height:200px; overflow:auto; margin-bottom:6px">
      <pre style="margin:0; font-size:11px; color:#e2e8f0; white-space:pre-wrap">${escapedGuide}</pre>
    </div>
    <button type="button" class="sb-btn sb-btn-sm" onclick="copyPbiPdfGuide()" id="btnCopyPdfGuide">
      <svg class="sb-btn-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      <span class="sb-btn-lbl">Copiar guía / Copy guide</span>
    </button>
    <span id="pbiPdfCopiedMsg" style="display:none; font-size:11px; color:var(--ar-green); margin-left:8px">✓ Copiado</span>
  `;
  // EN: Store guide text for copy function / ES: Guardar texto de guía para función de copia
  window._pbiPdfGuide = data.guide || "";

  log("Guía de exportación PDF generada. Siga los pasos en el panel. / PDF export guide generated. Follow the steps in the panel.", "ok");
}

function copyPbiPdfGuide() {
  // EN: Copy the PDF export guide to clipboard / ES: Copiar la guía al portapapeles
  const guide = window._pbiPdfGuide || "";
  if (!guide) return;
  navigator.clipboard.writeText(guide).then(() => {
    const msg = document.getElementById("pbiPdfCopiedMsg");
    if (msg) { msg.style.display = "inline"; setTimeout(() => { msg.style.display = "none"; }, 2000); }
  }).catch(() => {
    // EN: Fallback for browsers without clipboard API / ES: Respaldo sin API de portapapeles
    const ta = document.createElement("textarea");
    ta.value = guide;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    const msg = document.getElementById("pbiPdfCopiedMsg");
    if (msg) { msg.style.display = "inline"; setTimeout(() => { msg.style.display = "none"; }, 2000); }
  });
}

// ── G10: Publish-to-Web link check / Verificación de enlace Power BI ──
async function pbiPublishCheck() {
  // ES: Verifica si el enlace "Publicar en Web" de Power BI es accesible.
  // EN: Checks if a Power BI "Publish to Web" embed URL is publicly accessible.
  var input = document.getElementById("publishUrlInput");
  var resultEl = document.getElementById("publishCheckResult");
  if (!input || !resultEl) return;

  var url = (input.value || "").trim();
  if (!url) {
    resultEl.style.display = "block";
    resultEl.innerHTML = '<span style="color:var(--ar-blue,#003f6e)">⚠ Ingrese una URL / Enter a URL</span>';
    return;
  }

  // ES: Mostrar estado de carga / EN: Show loading state
  resultEl.style.display = "block";
  resultEl.innerHTML = '<span style="color:var(--text-2,#666)">Verificando… / Checking…</span>';

  var data = await apiGet("/api/pbi/publish-check?url=" + encodeURIComponent(url));
  if (!data) {
    resultEl.innerHTML = '<span class="text-error">❌ Error al conectar con el servidor / Server connection error</span>';
    return;
  }

  // ES: Mostrar resultado con colores de marca AR / EN: Show result with AR brand colors
  var icon, cls;
  if (data.status === "ok") {
    icon = "✅";
    cls = "text-success";
  } else if (data.status === "warning") {
    icon = "⚠";
    cls = "text-warning";
  } else {
    icon = "❌";
    cls = "text-error";
  }

  var codeStr = data.http_code != null ? " [HTTP " + data.http_code + "]" : "";
  resultEl.innerHTML =
    '<span class="' + cls + '">' + icon + " " + escapeHtml(data.message || "") + escapeHtml(codeStr) + "</span>";
}

// ── State persistence / Persistencia de estado ──
function saveWizardState() {
  // EN: Save wizard progress to localStorage (7-day expiry)
  // ES: Guardar progreso del asistente en localStorage (expira en 7 días)
  try {
    localStorage.setItem("arWizardState", JSON.stringify({
      currentPaso: wizardCurrentPaso,
      subStep: wizardSubStep,
      completed: wizardCompletedPasos,
      mode: wizardMode ? "wizard" : "expert",
      timestamp: Date.now()
    }));
  } catch (_) {}
}

function restoreWizardState() {
  // EN: Restore wizard state from localStorage on page load
  // ES: Restaurar estado del asistente desde localStorage al cargar la página
  try {
    var saved = JSON.parse(localStorage.getItem("arWizardState"));
    if (!saved) return;
    // EN: Expire after 7 days / ES: Expirar después de 7 días
    if (Date.now() - saved.timestamp > 7 * 24 * 60 * 60 * 1000) {
      localStorage.removeItem("arWizardState");
      return;
    }
    wizardCurrentPaso = saved.currentPaso || 0;
    wizardSubStep = saved.subStep || 0;
    wizardCompletedPasos = saved.completed || {};
    // EN: Restore mode — default to expert on first load
    // ES: Restaurar modo — predeterminado experto en primera carga
    if (saved.mode === "wizard") {
      setMode("wizard");
    }
  } catch (_) {}
}

// ── Cleaning Stats — PASO 3 before/after comparison (G5) ─────────────────
// ES: Panel de comparación antes/después de resultados de limpieza (Erase+Append)
// EN: Before/after comparison panel for PASO 3 cleaning results (Erase+Append)

function showCleaningCompare() {
  show("cleaningComparePanel");
  loadCleaningStats();
}

async function loadCleaningStats() {
  // EN: Fetch stored cleaning stats from the server
  // ES: Obtiene las estadísticas de limpieza almacenadas en el servidor
  try {
    const data = await apiGet("/api/pipeline/cleaning-stats");
    updateCleaningStats(data);
  } catch (_) {
    log("Error al cargar estadísticas de limpieza / Error loading cleaning stats", "warn");
  }
}

function updateCleaningStats(data) {
  // EN: Populate the cleaning compare card with before/after data
  // ES: Llena la tarjeta de comparación con los datos antes/después
  if (!data || !data.before) {
    document.getElementById("cleaningStatsMeta").textContent =
      "Sin datos guardados. Use los campos manuales o ejecute el script de Erase en ArcGIS Pro. / No saved data. Use manual fields or run the Erase script in ArcGIS Pro.";
    return;
  }

  var before = data.before || {};
  var after = data.after || {};
  var removed = data.removed || [];

  setText("cleaningBeforeCount", before.count != null ? before.count : "—");
  setText("cleaningBeforeArea", before.area_ha != null ? Number(before.area_ha).toFixed(2) : "—");
  setText("cleaningAfterCount", after.count != null ? after.count : "—");
  setText("cleaningAfterArea", after.area_ha != null ? Number(after.area_ha).toFixed(2) : "—");

  // KPI badges
  if (before.count > 0) {
    var removedCount = before.count - after.count;
    var removalPct = ((removedCount / before.count) * 100).toFixed(1);
    setText("cleaningRemovalPct", removalPct + "%");
    document.getElementById("cleaningKpiRow").style.display = "";
  }
  if (before.area_ha > 0) {
    var areaDelta = (before.area_ha - after.area_ha).toFixed(2);
    setText("cleaningAreaDelta", areaDelta + " ha");
  }

  // Removed items table
  var tbody = document.getElementById("cleaningRemovedBody");
  var section = document.getElementById("cleaningRemovedSection");
  if (removed.length > 0) {
    tbody.innerHTML = removed.map(function(item) {
      return "<tr><td>" + esc(item.cdg || "") + "</td><td>" +
        (item.area_ha != null ? Number(item.area_ha).toFixed(2) : "—") +
        "</td><td>" + esc(item.reason || "") + "</td></tr>";
    }).join("");
    section.style.display = "";
  } else {
    section.style.display = "none";
  }

  // Meta line
  var metaEl = document.getElementById("cleaningStatsMeta");
  if (data.saved_at) {
    metaEl.textContent = "Guardado / Saved: " + data.saved_at;
  } else {
    metaEl.textContent = "";
  }

  // Pre-fill manual inputs
  if (before.count != null) document.getElementById("manualBeforeCount").value = before.count;
  if (before.area_ha != null) document.getElementById("manualBeforeArea").value = Number(before.area_ha).toFixed(2);
  if (after.count != null) document.getElementById("manualAfterCount").value = after.count;
  if (after.area_ha != null) document.getElementById("manualAfterArea").value = Number(after.area_ha).toFixed(2);
}

async function saveCleaningStatsManual() {
  // EN: Save cleaning stats entered manually by the user
  // ES: Guarda las estadísticas ingresadas manualmente por el usuario
  var beforeCount = parseInt(document.getElementById("manualBeforeCount").value) || 0;
  var beforeArea = parseFloat(document.getElementById("manualBeforeArea").value) || 0.0;
  var afterCount = parseInt(document.getElementById("manualAfterCount").value) || 0;
  var afterArea = parseFloat(document.getElementById("manualAfterArea").value) || 0.0;

  try {
    var data = await api("/api/pipeline/cleaning-stats", {
      before: { count: beforeCount, area_ha: beforeArea },
      after:  { count: afterCount,  area_ha: afterArea  },
      removed: [],
    });
    if (data.stats) {
      updateCleaningStats(data.stats);
      showSuccessToast("Estadísticas guardadas / Stats saved");
      document.getElementById("cleaningManualDetails").removeAttribute("open");
    }
  } catch (_) {
    log("Error al guardar estadísticas / Error saving stats", "error");
  }
}

// EN: Escape HTML for safe table injection
// ES: Escapa HTML para inyección segura en tabla
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function setText(id, val) {
  var el = document.getElementById(id);
  if (el) el.textContent = val;
}


// ══════════════════════════════════════════════════════════════════════════════
// Criterios de Limpieza / Cleaning Criteria (G4)
// EN: Functions to load, save, add, delete, and export cleaning criteria
//     decided by the coordinator. Connected to /api/criteria/* endpoints.
// ES: Funciones para cargar, guardar, agregar, eliminar y exportar criterios
//     de limpieza. Conecta a /api/criteria/*.
// ══════════════════════════════════════════════════════════════════════════════

/** EN: In-memory cache of loaded entries / ES: Caché en memoria de entradas */
var _criteriaEntries = [];
var _criteriaCurrentQuarter = "";

async function refreshCriteriaQuarters() {
  // EN: Populate quarter <select> from server / ES: Pobla el <select> de trimestres del servidor
  var sel = document.getElementById("criteriaQuarter");
  if (!sel) return;
  try {
    var resp = await fetch("/api/criteria/");
    if (!resp.ok) throw new Error(resp.status);
    var data = await resp.json();
    var quarters = data.quarters || [];
    var current = sel.value;
    sel.innerHTML = '<option value="">— seleccionar —</option>';
    quarters.forEach(function(q) {
      var opt = document.createElement("option");
      opt.value = q; opt.textContent = q;
      if (q === current) opt.selected = true;
      sel.appendChild(opt);
    });
    var qtField = document.getElementById("currentQt");
    if (qtField && qtField.value && !quarters.includes(qtField.value)) {
      var opt2 = document.createElement("option");
      opt2.value = qtField.value;
      opt2.textContent = qtField.value + " (nuevo)";
      sel.appendChild(opt2);
    }
  } catch (err) { console.warn("[criteria] refreshCriteriaQuarters error:", err); }
}

async function loadCriteria(quarter) {
  // EN: Load criteria for a quarter and render table / ES: Carga criterios de un trimestre
  if (!quarter) {
    _criteriaEntries = []; _criteriaCurrentQuarter = "";
    _renderCriteriaTable(); return;
  }
  _criteriaCurrentQuarter = quarter;
  try {
    var resp = await fetch("/api/criteria/" + encodeURIComponent(quarter));
    if (!resp.ok) throw new Error(resp.status);
    var data = await resp.json();
    _criteriaEntries = data.entries || [];
    _renderCriteriaTable();
    _setCriteriaStatus("", false);
  } catch (err) {
    _setCriteriaStatus("Error al cargar criterios / Error loading criteria: " + err, true);
  }
}

async function addCriterionEntry() {
  // EN: Add a single criterion to current quarter / ES: Agrega un criterio al trimestre actual
  var quarter = (document.getElementById("criteriaQuarter") || {}).value;
  if (!quarter) {
    _setCriteriaStatus("Seleccione un trimestre primero / Please select a quarter first.", true);
    return;
  }
  var layer    = ((document.getElementById("criteriaLayer")    || {}).value || "").trim();
  var reason   = ((document.getElementById("criteriaReason")   || {}).value || "").trim();
  var decision = ((document.getElementById("criteriaDecision") || {}).value || "").trim();
  var cdg      = ((document.getElementById("criteriaCdg")      || {}).value || "").trim();
  var by       = ((document.getElementById("criteriaBy")       || {}).value || "coordinator").trim();
  if (!layer || !reason || !decision) {
    _setCriteriaStatus("Campos requeridos: Capa, Razón, Decisión / Required: Layer, Reason, Decision", true);
    return;
  }
  try {
    var resp = await fetch("/api/criteria/" + encodeURIComponent(quarter) + "/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ layer: layer, reason: reason, decision: decision,
                             cdg_actividad: cdg, recorded_by: by || "coordinator" }),
    });
    if (!resp.ok) {
      var errData = await resp.json().catch(function() { return {}; });
      throw new Error(errData.message || resp.status);
    }
    var newEntry = await resp.json();
    _criteriaEntries.push(newEntry);
    _renderCriteriaTable();
    _clearCriteriaForm();
    _setCriteriaStatus("✅ Criterio #" + newEntry.id + " agregado / Criterion #" + newEntry.id + " added.", false);
  } catch (err) {
    _setCriteriaStatus("Error al agregar / Error adding: " + err, true);
  }
}

async function deleteCriterionEntry(id) {
  // EN: Delete entry by id then save all / ES: Elimina entrada por id y guarda todo
  _criteriaEntries = _criteriaEntries.filter(function(e) { return e.id !== id; });
  await _saveCriteriaAll();
  _renderCriteriaTable();
}

async function _saveCriteriaAll() {
  // EN: Persist full entries list / ES: Persiste la lista completa de entradas
  var quarter = _criteriaCurrentQuarter;
  if (!quarter) return;
  try {
    var resp = await fetch("/api/criteria/" + encodeURIComponent(quarter), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ entries: _criteriaEntries }),
    });
    if (!resp.ok) throw new Error(resp.status);
    var data = await resp.json();
    _criteriaEntries = data.entries || _criteriaEntries;
    _setCriteriaStatus("✅ Guardado / Saved.", false);
  } catch (err) {
    _setCriteriaStatus("Error al guardar / Save error: " + err, true);
  }
}

function exportCriteriaPdf() {
  // EN: Trigger PDF download / ES: Inicia la descarga del PDF de criterios
  var quarter = _criteriaCurrentQuarter || ((document.getElementById("criteriaQuarter") || {}).value);
  if (!quarter) {
    _setCriteriaStatus("Seleccione un trimestre para exportar / Select a quarter to export.", true);
    return;
  }
  window.location.href = "/api/criteria/" + encodeURIComponent(quarter) + "/export-pdf";
}

function _renderCriteriaTable() {
  // EN: Render entries into #criteriaTableBody / ES: Renderiza entradas en la tabla
  var tbody = document.getElementById("criteriaTableBody");
  var wrap  = document.getElementById("criteriaTableWrap");
  var title = document.getElementById("criteriaTableTitle");
  if (!tbody || !wrap) return;
  if (!_criteriaEntries.length) { wrap.style.display = "none"; return; }
  wrap.style.display = "block";
  if (title) title.textContent = "Criterios guardados (" + _criteriaEntries.length + ") \u2014 " + _criteriaCurrentQuarter;
  tbody.innerHTML = _criteriaEntries.map(function(e) {
    return "<tr>" +
      "<td>" + (e.id != null ? e.id : "") + "</td>" +
      "<td>" + _escHtml(e.layer || "") + "</td>" +
      "<td>" + _escHtml(e.reason || "") + "</td>" +
      "<td>" + _escHtml(e.decision || "") + "</td>" +
      "<td>" + _escHtml(e.cdg_actividad || "") + "</td>" +
      "<td>" + _escHtml(e.recorded_by || "") + "</td>" +
      "<td><button class=\"btn-delete-sm\" onclick=\"deleteCriterionEntry(" + e.id + ")\"" +
      " title=\"Eliminar / Delete\">\u2715</button></td></tr>";
  }).join("");
}

function _escHtml(str) {
  // EN: Escape HTML to prevent XSS / ES: Escapa HTML para prevenir XSS
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function _setCriteriaStatus(msg, isError) {
  // EN: Show/hide status message / ES: Muestra u oculta el mensaje de estado
  var el = document.getElementById("criteriaStatus");
  if (!el) return;
  if (!msg) { el.style.display = "none"; return; }
  el.style.display = "block";
  el.className = "criteria-status" + (isError ? " criteria-status-error" : " criteria-status-ok");
  el.textContent = msg;
}

function _clearCriteriaForm() {
  // EN: Reset add-entry form / ES: Limpia el formulario de agregar criterio
  ["criteriaLayer","criteriaReason","criteriaDecision","criteriaCdg"].forEach(function(id) {
    var el = document.getElementById(id); if (el) el.value = "";
  });
}

// EN: Auto-populate quarter list when accordion opens / ES: Auto-pobla cuando se abre el panel
document.addEventListener("DOMContentLoaded", function() {
  // Restore log panel collapsed/expanded state from last session
  try {
    var logCollapsedPref = sessionStorage.getItem("arLogCollapsed");
    var logLayer = document.getElementById("logLayer");
    if (logLayer && logCollapsedPref === "0") {
      // User last left the log expanded — restore that
      logLayer.classList.remove("collapsed");
      var savedLogH = parseInt(sessionStorage.getItem("logH"), 10);
      if (savedLogH && savedLogH >= 80) logLayer.style.height = savedLogH + "px";
    }
  } catch (_) {}

  var details = document.getElementById("criteriaPanelDetails");
  if (details) {
    details.addEventListener("toggle", function() {
      if (details.open) refreshCriteriaQuarters();
    });
  }

  // Event delegation for diagnose panel checkboxes (batch ⬇ and done ✓)
  var groupsEl = document.getElementById("paso0Groups");
  if (groupsEl) {
    groupsEl.addEventListener("change", function(e) {
      var chk = e.target;
      var itemId = chk.getAttribute("data-agent-id");
      if (!itemId) return;

      if (chk.classList.contains("batch-chk")) {
        if (chk.checked) {
          _batchSelectedIds.add(itemId);
        } else {
          _batchSelectedIds.delete(itemId);
        }
        _updateBatchCounter();
      } else if (chk.classList.contains("done-chk")) {
        AgentController.onManualCheck(itemId, chk.checked);
      }
    });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// G8: M&E Comparison Engine — Dafne vs Power BI
// ES: Motor de comparación M&E — Dafne vs Power BI
// ─────────────────────────────────────────────────────────────────────────────

// EN: In-memory cache of last comparison result for saving decisions.
// ES: Caché en memoria del último resultado de comparación para guardar decisiones.
var _cmpLastResult = null;
var _cmpLastIntegradoPath = "";
var _cmpLastPbiSource = null;

function cmpTogglePbiSource() {
  // EN: Show/hide PBI Excel path inputs based on selected source type.
  // ES: Muestra/oculta los campos de ruta Excel PBI según el tipo seleccionado.
  var type = document.getElementById("cmpPbiType").value;
  var row = document.getElementById("cmpPbiExcelRow");
  if (row) row.style.display = type === "excel" ? "block" : "none";
}

function _cmpPbiSource() {
  // EN: Build pbi_source object from current form state.
  // ES: Construye el objeto pbi_source desde el estado actual del formulario.
  var type = document.getElementById("cmpPbiType").value;
  if (type === "excel") {
    return {
      type: "excel",
      path: (document.getElementById("cmpPbiExcelPath").value || "").trim(),
      sheet: (document.getElementById("cmpPbiExcelSheet").value || "").trim()
    };
  }
  return {type: "inline", output: {}, outcome: {}, impact: {}};
}

function _cmpSetStatus(msg, isError) {
  // EN: Show/hide comparison status message.
  // ES: Muestra/oculta el mensaje de estado de comparación.
  var el = document.getElementById("cmpStatus");
  if (!el) return;
  if (!msg) { el.style.display = "none"; return; }
  el.style.display = "block";
  el.className = isError ? "text-error" : "text-success";
  el.textContent = msg;
}

async function cmpRunComparison() {
  // EN: Run M&E comparison between Dafne and PBI values.
  // ES: Ejecuta la comparación M&E entre Dafne y Power BI.
  var quarter = (document.getElementById("cmpQuarter").value || "").trim();
  var integradoPath = (document.getElementById("cmpIntegradoPath").value || "").trim();
  var pbiSource = _cmpPbiSource();

  if (!quarter) { _cmpSetStatus("Ingrese el trimestre / Enter quarter", true); return; }
  if (!integradoPath) { _cmpSetStatus("Ingrese la ruta del archivo Dafne / Enter Dafne file path", true); return; }

  _cmpLastIntegradoPath = integradoPath;
  _cmpLastPbiSource = pbiSource;

  var btn = document.getElementById("btnCmpRun");
  if (btn) btn.disabled = true;
  _cmpSetStatus("Ejecutando comparación... / Running comparison...", false);

  try {
    var res = await api("/api/compare/me", {
      integrado_path: integradoPath,
      pbi_source: pbiSource,
      quarter: quarter
    });

    if (res.error) {
      _cmpSetStatus("Error: " + res.error, true);
      return;
    }

    _cmpLastResult = res;
    var mis = res.summary ? res.summary.mismatches : 0;
    var tot = res.summary ? res.summary.total_metrics : 0;
    _cmpSetStatus(
      mis === 0
        ? "✓ Todos los valores coinciden / All values match (" + tot + ")"
        : "⚠ " + mis + " discrepancias de " + tot + " / " + mis + " mismatches of " + tot,
      mis > 0
    );
    _cmpRenderTable(res);
  } catch (e) {
    _cmpSetStatus("Error de red / Network error: " + e.message, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function _cmpRenderTable(result) {
  // EN: Render comparison results table with decision dropdowns.
  // ES: Renderiza la tabla de resultados con menús desplegables de decisión.
  var wrap = document.getElementById("cmpResultsWrap");
  var tbody = document.getElementById("cmpTableBody");
  if (!wrap || !tbody) return;

  var rows = [];

  // Output fields
  var output = result.output || {};
  ["area_ha", "beneficiarios", "organizaciones"].forEach(function(field) {
    var cell = output[field];
    if (!cell) return;
    rows.push({
      metric: "output." + field,
      label: "Output — " + field,
      dafne: cell.dafne,
      pbi: cell.pbi,
      delta: cell.delta,
      match: cell.match
    });
  });

  // Outcome rows (per CdgActvdd)
  var outcome = result.outcome || {};
  Object.keys(outcome).sort().forEach(function(cdg) {
    var cdgData = outcome[cdg] || {};
    ["area_ha", "pct_logro"].forEach(function(field) {
      var cell = cdgData[field];
      if (!cell) return;
      rows.push({
        metric: "outcome." + cdg + "." + field,
        label: "Outcome — " + cdg + " / " + field,
        dafne: cell.dafne,
        pbi: cell.pbi,
        delta: cell.delta,
        match: cell.match,
        cdg: cdg
      });
    });
  });

  // Impact
  var impact = (result.impact || {}).total_area_ha;
  if (impact) {
    rows.push({
      metric: "impact.total_area_ha",
      label: "Impact — Área total / Total area (ha)",
      dafne: impact.dafne,
      pbi: impact.pbi,
      delta: impact.delta,
      match: impact.match
    });
  }

  tbody.innerHTML = rows.map(function(r) {
    var rowClass = r.match ? "match-row" : "mismatch-row";
    var drillBtn = r.cdg
      ? "<button class=\"btn-drill-sm\" onclick=\"cmpDrill(" + _escHtml(JSON.stringify(r)) + ")\" title=\"Detalle / Detail\">&#128269;</button>"
      : "";
    return "<tr class=\"" + rowClass + "\">" +
      "<td>" + _escHtml(r.label) + drillBtn + "</td>" +
      "<td>" + _fmtNum(r.dafne) + "</td>" +
      "<td>" + _fmtNum(r.pbi) + "</td>" +
      "<td class=\"" + (r.match ? "" : "delta-cell") + "\">" + _fmtNum(r.delta) + "</td>" +
      "<td>" + _cmpDecisionCell(r) + "</td>" +
      "</tr>";
  }).join("");

  wrap.style.display = "block";
}

function _cmpDecisionCell(row) {
  // EN: Render decision dropdown + optional manual value input.
  // ES: Renderiza el desplegable de decisión más campo manual opcional.
  var id = "cmpDec_" + row.metric.replace(/\./g, "_");
  var manId = "cmpMan_" + row.metric.replace(/\./g, "_");
  var sel = "<select class=\"decision-dropdown\" id=\"" + id + "\" " +
    "data-metric=\"" + _escHtml(row.metric) + "\" " +
    "data-dafne=\"" + row.dafne + "\" " +
    "data-pbi=\"" + row.pbi + "\" " +
    "onchange=\"_cmpToggleManual('" + id + "','" + manId + "')\">" +
    "<option value=\"dafne\">Dafne</option>" +
    "<option value=\"pbi\">PBI</option>" +
    "<option value=\"manual\">Manual</option>" +
    "</select>" +
    "<input type=\"number\" step=\"any\" id=\"" + manId + "\" class=\"decision-manual\" " +
    "style=\"display:none\" placeholder=\"Valor manual\" />";
  return sel;
}

function _cmpToggleManual(selId, manId) {
  // EN: Show/hide manual value input based on decision selection.
  // ES: Muestra/oculta el campo de valor manual según la selección.
  var sel = document.getElementById(selId);
  var man = document.getElementById(manId);
  if (sel && man) man.style.display = sel.value === "manual" ? "inline-block" : "none";
}

async function cmpSaveDecisions() {
  // EN: Persist all decision selections to the server.
  // ES: Guarda todas las decisiones de la tabla al servidor.
  var quarter = (document.getElementById("cmpQuarter").value || "").trim();
  if (!quarter) { _cmpSetStatus("Ingrese el trimestre / Enter quarter", true); return; }

  var selects = document.querySelectorAll("#cmpTableBody .decision-dropdown");
  if (!selects.length) { _cmpSetStatus("No hay resultados / No results to save", true); return; }

  var btn = document.getElementById("btnCmpSave");
  if (btn) btn.disabled = true;

  var errors = [];
  for (var i = 0; i < selects.length; i++) {
    var sel = selects[i];
    var metric = sel.dataset.metric;
    var decision = sel.value;
    var dafneVal = parseFloat(sel.dataset.dafne) || 0;
    var pbiVal = parseFloat(sel.dataset.pbi) || 0;
    var manId = "cmpMan_" + metric.replace(/\./g, "_");
    var manEl = document.getElementById(manId);
    var manualVal = (decision === "manual" && manEl) ? parseFloat(manEl.value) : null;

    try {
      var res = await api("/api/compare/me/decision", {
        metric: metric,
        dafne_val: dafneVal,
        pbi_val: pbiVal,
        decision: decision,
        manual_val: manualVal,
        quarter: quarter
      });
      if (res.error) errors.push(metric + ": " + res.error);
    } catch(e) {
      errors.push(metric + ": " + e.message);
    }
  }

  if (btn) btn.disabled = false;
  if (errors.length) {
    _cmpSetStatus("Errores guardando / Save errors: " + errors.join("; "), true);
  } else {
    _cmpSetStatus("✓ Decisiones guardadas / Decisions saved (" + selects.length + ")", false);
  }
}

async function cmpLoadReport() {
  // EN: Load and display the saved comparison report for the quarter.
  // ES: Carga y muestra el reporte de comparación guardado para el trimestre.
  var quarter = (document.getElementById("cmpQuarter").value || "").trim();
  var wrap = document.getElementById("cmpReportWrap");
  if (!wrap) return;
  if (!quarter) { wrap.textContent = "Ingrese el trimestre / Enter quarter"; return; }

  wrap.textContent = "Cargando / Loading…";
  try {
    var res = await api("/api/compare/me/report?quarter=" + encodeURIComponent(quarter));
    if (!res.decisions || !res.decisions.length) {
      wrap.textContent = "Sin decisiones guardadas / No saved decisions";
      return;
    }
    var s = res.summary;
    var html = "<div style=\"margin-bottom:4px\">" +
      "Total: " + s.total_decisions + " | " +
      "Dafne: " + s.dafne + " | PBI: " + s.pbi + " | Manual: " + s.manual +
      "</div><table class=\"compare-table\"><thead><tr>" +
      "<th>Métrica</th><th>Dafne</th><th>PBI</th><th>Decisión</th><th>Valor Final</th>" +
      "</tr></thead><tbody>" +
      res.decisions.map(function(d) {
        return "<tr><td>" + _escHtml(d.metric) + "</td>" +
          "<td>" + _fmtNum(d.dafne_val) + "</td>" +
          "<td>" + _fmtNum(d.pbi_val) + "</td>" +
          "<td>" + _escHtml(d.decision) + "</td>" +
          "<td><strong>" + _fmtNum(d.final_value) + "</strong></td></tr>";
      }).join("") +
      "</tbody></table>";
    wrap.innerHTML = html;
  } catch(e) {
    wrap.textContent = "Error: " + e.message;
  }
}

async function cmpDrill(rowData) {
  // EN: Open drill-down modal showing field-level discrepancy for one activity.
  // ES: Abre el modal de detalle mostrando discrepancias a nivel de campo.
  if (!_cmpLastIntegradoPath) {
    alert("Ejecute la comparación primero / Run comparison first");
    return;
  }
  var overlay = document.getElementById("drillModalOverlay");
  var title = document.getElementById("drillModalTitle");
  var body = document.getElementById("drillModalBody");
  if (!overlay || !body) return;

  title.textContent = "Detalle — " + (rowData.cdg || rowData.label);
  body.innerHTML = "<div style='padding:8px'>Cargando / Loading…</div>";
  overlay.style.display = "flex";

  try {
    var res = await api("/api/compare/me/drill", {
      cdg_actividad: rowData.cdg,
      integrado_path: _cmpLastIntegradoPath,
      pbi_source: _cmpLastPbiSource || {type:"inline",output:{},outcome:{},impact:{}}
    });

    if (res.error) {
      body.innerHTML = "<div style='color:var(--error,#dc2626);padding:8px'>" + _escHtml(res.error) + "</div>";
      return;
    }

    if (!res.field_diffs || !res.field_diffs.length) {
      body.innerHTML = "<div style='padding:8px;color:var(--ar-green-dark,#4a8c1a)'>✓ No se encontraron diferencias a nivel de campo / No field-level differences found</div>";
      return;
    }

    body.innerHTML = "<table class='compare-table' style='width:100%'>" +
      "<thead><tr><th>Campo / Field</th><th>Dafne</th><th>PBI</th></tr></thead><tbody>" +
      res.field_diffs.map(function(d) {
        return "<tr class='mismatch-row'><td>" + _escHtml(d.field) + "</td>" +
          "<td>" + _escHtml(String(d.dafne ?? "—")) + "</td>" +
          "<td>" + _escHtml(String(d.pbi ?? "—")) + "</td></tr>";
      }).join("") +
      "</tbody></table>";
  } catch(e) {
    body.innerHTML = "<div style='color:var(--error,#dc2626);padding:8px'>Error: " + _escHtml(e.message) + "</div>";
  }
}

function cmpCloseDrillModal(evt) {
  // EN: Close the drill-down modal (click overlay or X button).
  // ES: Cierra el modal de detalle (clic en overlay o botón X).
  var overlay = document.getElementById("drillModalOverlay");
  if (!overlay) return;
  if (!evt || evt.target === overlay) overlay.style.display = "none";
}

function _fmtNum(val) {
  // EN: Format a numeric value for display (up to 4 decimals, strip trailing zeros).
  // ES: Formatea un valor numérico para mostrar (hasta 4 decimales).
  if (val === null || val === undefined || val === "") return "—";
  var n = parseFloat(val);
  if (isNaN(n)) return _escHtml(String(val));
  return n % 1 === 0 ? String(n) : parseFloat(n.toFixed(4)).toString();
}

// ─────────────────────────────────────────────────────────────────────────────
// LOG PANEL RESIZE — drag handle at top of log-layer
// ES: Redimensionar panel de registro — manija de arrastre arriba del panel
// ─────────────────────────────────────────────────────────────────────────────
(function initLogResize() {
  var handle = document.getElementById("logResizeHandle");
  var layer  = document.getElementById("logLayer");
  if (!handle || !layer) return;

  var startY = 0;
  var startH = 0;
  var MIN_H  = 80;
  var MAX_H  = Math.round(window.innerHeight * 0.6);

  handle.addEventListener("mousedown", function(e) {
    if (layer.classList.contains("collapsed")) return;
    e.preventDefault();
    startY = e.clientY;
    startH = layer.offsetHeight;
    layer.classList.add("resizing");
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });

  function onMove(e) {
    var delta = startY - e.clientY;           // drag UP → bigger
    var newH = Math.min(MAX_H, Math.max(MIN_H, startH + delta));
    layer.style.height = newH + "px";
  }
  function onUp() {
    layer.classList.remove("resizing");
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
    // Persist preference for session
    try { sessionStorage.setItem("logH", layer.offsetHeight); } catch(_) {}
  }

  // Restore saved height
  try {
    var saved = parseInt(sessionStorage.getItem("logH"), 10);
    if (saved && saved >= MIN_H && saved <= MAX_H) {
      layer.style.height = saved + "px";
    }
  } catch(_) {}
})();

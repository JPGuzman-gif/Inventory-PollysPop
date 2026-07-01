import { api, ENDPOINTS, formatApiError, isNotImplemented } from "./api.js";

const LOCATIONS = ["Production Floor", "Warehouse 1", "Warehouse 2"];
const ROUTES = [
  "dashboard",
  "feature-status",
  "create",
  "move",
  "sell",
  "inventory",
  "expiring",
  "export",
  "scanner",
  "notifications",
  "analytics",
];

const state = {
  brands: [],
  products: [],
  pallets: [],
  expiring: [],
  selectedPallet: null,
};

function el(id) {
  return document.getElementById(id);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function alertHtml(type, message) {
  return `<div class="alert alert-${type}">${escapeHtml(message)}</div>`;
}

function daysUntil(dateString) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(`${dateString}T00:00:00`);
  return Math.ceil((target - today) / (1000 * 60 * 60 * 24));
}

function urgencyClass(days) {
  if (days < 0) return "row-overdue";
  if (days <= 30) return "row-soon";
  return "";
}

function setActiveNav(route) {
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === route);
  });
}

function showRoute(route) {
  const active = ROUTES.includes(route) ? route : "dashboard";
  ROUTES.forEach((name) => {
    el(`view-${name}`)?.classList.toggle("hidden", name !== active);
  });
  setActiveNav(active);
  renderView(active);
}

async function loadBrands() {
  try {
    state.brands = await api.brands();
  } catch (error) {
    if (!isNotImplemented(error)) throw error;
    state.brands = [];
  }
}

async function loadProducts(brandId) {
  try {
    state.products = await api.products(brandId);
  } catch (error) {
    if (!isNotImplemented(error)) throw error;
    state.products = [];
  }
}

async function loadPallets(filters = {}) {
  try {
    state.pallets = await api.pallets(filters);
  } catch (error) {
    if (!isNotImplemented(error)) throw error;
    state.pallets = [];
  }
}

async function loadExpiring() {
  try {
    state.expiring = await api.expiring();
  } catch (error) {
    if (!isNotImplemented(error)) throw error;
    state.expiring = [];
  }
}

function countByLocation(pallets) {
  return LOCATIONS.map((location) => ({
    location,
    count: pallets.filter((p) => p.current_location === location && p.status !== "sold").length,
  }));
}

function renderDashboard() {
  const counts = countByLocation(state.pallets);
  const expiringPreview = state.expiring.slice(0, 5);

  el("view-dashboard").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Dashboard</h1>
        <p>Warehouse snapshot — pallet counts by location and pallets nearing expiration.</p>
      </div>
    </div>

    <div class="grid grid-4">
      ${counts
        .map(
          (item) => `
        <div class="stat">
          <strong>${item.count}</strong>
          <span>${escapeHtml(item.location)}</span>
        </div>`
        )
        .join("")}
    </div>

    <div class="card" style="margin-top:1rem">
      <h2>Expiring within 90 days</h2>
      ${
        expiringPreview.length
          ? `<div class="table-wrap"><table>
              <thead><tr><th>Barcode</th><th>Flavor</th><th>Expires</th><th>Days left</th><th>Location</th></tr></thead>
              <tbody>
                ${expiringPreview
                  .map((p) => {
                    const days = daysUntil(p.expiration_date);
                    return `<tr class="${urgencyClass(days)}">
                      <td>${escapeHtml(p.barcode)}</td>
                      <td>${escapeHtml(p.flavor_name || p.product_name || "—")}</td>
                      <td>${escapeHtml(p.expiration_date)}</td>
                      <td>${days}</td>
                      <td>${escapeHtml(p.current_location)}</td>
                    </tr>`;
                  })
                  .join("")}
              </tbody>
            </table></div>`
          : alertHtml("info", "No expiring pallet data yet — connect the /pallets/expiring API to populate this list.")
      }
    </div>
  `;
}

async function renderFeatureStatus() {
  el("view-feature-status").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Feature Status</h1>
        <p>Live check of each planned API endpoint so you can see what works today vs. what is still in progress.</p>
      </div>
      <button class="btn btn-secondary" id="refresh-status">Refresh</button>
    </div>
    <div class="card"><div id="status-table">Checking endpoints…</div></div>
  `;

  el("refresh-status").addEventListener("click", () => renderFeatureStatus());

  const keys = Object.keys(ENDPOINTS);
  const results = await Promise.all(keys.map((key) => api.probe(key)));

  const rows = results
    .map((item) => {
      const badgeClass =
        item.status === "ready"
          ? "badge-ready"
          : item.status === "missing"
            ? "badge-missing"
            : "badge-offline";
      const statusLabel =
        item.status === "ready"
          ? "Responding"
          : item.status === "missing"
            ? "Not built yet"
            : "Offline / error";
      return `<tr>
        <td>${escapeHtml(item.label)}</td>
        <td><code>${escapeHtml(item.method)} ${escapeHtml(item.path)}</code></td>
        <td><span class="badge badge-phase">Phase ${item.phase}</span></td>
        <td><span class="badge ${badgeClass}">${statusLabel}</span></td>
      </tr>`;
    })
    .join("");

  el("status-table").innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Feature</th><th>Endpoint</th><th>Phase</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function brandOptions(selectedId = "") {
  if (!state.brands.length) {
    return `<option value="">Brands API not available yet</option>`;
  }
  return state.brands
    .map(
      (brand) =>
        `<option value="${brand.id}" ${String(brand.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(brand.name)}</option>`
    )
    .join("");
}

function productOptions(selectedId = "") {
  if (!state.products.length) {
    return `<option value="">Select a brand first</option>`;
  }
  return state.products
    .map(
      (product) =>
        `<option value="${product.id}" ${String(product.id) === String(selectedId) ? "selected" : ""}>${escapeHtml(product.name)}</option>`
    )
    .join("");
}

function renderCreate() {
  el("view-create").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Create Pallet</h1>
        <p>Register a new pallet on the production floor. The system assigns the next global pallet number (00001, 00002, …).</p>
      </div>
    </div>

    <div class="card">
      <form id="create-form" class="form-grid">
        <div class="field">
          <label for="create-brand">Brand</label>
          <select id="create-brand" required>${brandOptions()}</select>
        </div>
        <div class="field">
          <label for="create-product">Flavor</label>
          <select id="create-product" required>${productOptions()}</select>
        </div>
        <div class="field">
          <label for="create-bottled">Bottling date</label>
          <input id="create-bottled" type="date" required />
        </div>
        <div class="field">
          <label for="create-expiration">Expiration date</label>
          <input id="create-expiration" type="date" required />
        </div>
        <div class="field full">
          <label for="create-notes">Notes (optional)</label>
          <textarea id="create-notes" rows="2" placeholder="Batch notes, operator comment…"></textarea>
        </div>
        <div class="field full btn-row">
          <button type="submit" class="btn btn-primary">Create pallet</button>
        </div>
      </form>
      <div id="create-result"></div>
    </div>
  `;

  const bottledInput = el("create-bottled");
  bottledInput.value = new Date().toISOString().slice(0, 10);

  el("create-brand").addEventListener("change", async (event) => {
    await loadProducts(event.target.value);
    el("create-product").innerHTML = productOptions();
  });

  el("create-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      product_id: Number(el("create-product").value),
      bottled_at: el("create-bottled").value,
      expiration_date: el("create-expiration").value,
      notes: el("create-notes").value || null,
    };

    el("create-result").innerHTML = alertHtml("info", "Creating pallet…");
    try {
      const pallet = await api.createPallet(payload);
      el("create-result").innerHTML = `
        ${alertHtml("info", "Pallet created successfully.")}
        <div class="barcode-display">${escapeHtml(pallet.barcode)}</div>
        <div class="btn-row no-print">
          <button type="button" class="btn btn-secondary" id="print-label">Print label</button>
        </div>
      `;
      el("print-label")?.addEventListener("click", () => window.print());
      await loadPallets();
    } catch (error) {
      el("create-result").innerHTML = alertHtml("warn", formatApiError(error));
    }
  });
}

function renderBarcodeLookupForm({ formId, resultId, submitLabel, onSubmit }) {
  return `
    <form id="${formId}" class="form-grid">
      <div class="field full">
        <label for="${formId}-barcode">Pallet barcode</label>
        <input id="${formId}-barcode" type="text" inputmode="numeric" pattern="[0-9]{5}" maxlength="5" placeholder="00001" required />
      </div>
      <div class="field full btn-row">
        <button type="submit" class="btn btn-primary">${escapeHtml(submitLabel)}</button>
      </div>
    </form>
    <div id="${resultId}"></div>
  `;
}

async function lookupPallet(barcode) {
  try {
    return await api.pallet(barcode);
  } catch (error) {
    if (isNotImplemented(error)) return null;
    throw error;
  }
}

function palletSummary(pallet) {
  if (!pallet) return alertHtml("warn", "Pallet not found or lookup API not available.");
  return `
    <div class="card">
      <h3>Pallet ${escapeHtml(pallet.barcode)}</h3>
      <p><strong>Brand:</strong> ${escapeHtml(pallet.brand_name || "—")}</p>
      <p><strong>Flavor:</strong> ${escapeHtml(pallet.flavor_name || pallet.product_name || "—")}</p>
      <p><strong>Expiration:</strong> ${escapeHtml(pallet.expiration_date)}</p>
      <p><strong>Location:</strong> ${escapeHtml(pallet.current_location)}</p>
      <p><strong>Status:</strong> ${escapeHtml(pallet.status)}</p>
    </div>
  `;
}

function renderMove() {
  el("view-move").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Move to Storage</h1>
        <p>Manual barcode entry always available — type or paste the pallet number, then choose Warehouse 1 or 2.</p>
      </div>
    </div>
    <div class="card">
      ${renderBarcodeLookupForm({ formId: "move-form", resultId: "move-result", submitLabel: "Look up pallet" })}
      <form id="move-action" class="form-grid hidden">
        <div class="field full">
          <label for="move-location">Destination</label>
          <select id="move-location">
            <option value="Warehouse 1">Warehouse 1</option>
            <option value="Warehouse 2">Warehouse 2</option>
          </select>
        </div>
        <div class="field full btn-row">
          <button type="submit" class="btn btn-primary">Confirm transfer</button>
        </div>
      </form>
    </div>
  `;

  let currentBarcode = "";

  el("move-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    currentBarcode = el("move-form-barcode").value.trim();
    el("move-result").innerHTML = alertHtml("info", "Looking up pallet…");
    try {
      const pallet = await lookupPallet(currentBarcode);
      el("move-result").innerHTML = palletSummary(pallet);
      el("move-action").classList.toggle("hidden", !pallet);
    } catch (error) {
      el("move-result").innerHTML = alertHtml("error", formatApiError(error));
    }
  });

  el("move-action").addEventListener("submit", async (event) => {
    event.preventDefault();
    const toLocation = el("move-location").value;
    el("move-result").innerHTML = alertHtml("info", "Transferring pallet…");
    try {
      const pallet = await api.transferPallet(currentBarcode, toLocation);
      el("move-result").innerHTML = `
        ${alertHtml("info", `Pallet moved to ${escapeHtml(toLocation)}.`)}
        ${palletSummary(pallet)}
      `;
      el("move-action").classList.add("hidden");
      await loadPallets();
    } catch (error) {
      el("move-result").innerHTML = alertHtml("warn", formatApiError(error));
    }
  });
}

function renderSell() {
  el("view-sell").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Sell Pallet</h1>
        <p>Record a pallet sale. This action is irreversible for inventory tracking.</p>
      </div>
    </div>
    <div class="card">
      ${renderBarcodeLookupForm({ formId: "sell-form", resultId: "sell-result", submitLabel: "Look up pallet" })}
      <form id="sell-action" class="form-grid hidden">
        <div class="field full">
          <label><input type="checkbox" id="sell-confirm" required /> I confirm this pallet is sold and should leave active inventory.</label>
        </div>
        <div class="field full btn-row">
          <button type="submit" class="btn btn-danger">Confirm sell</button>
        </div>
      </form>
    </div>
  `;

  let currentBarcode = "";

  el("sell-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    currentBarcode = el("sell-form-barcode").value.trim();
    el("sell-result").innerHTML = alertHtml("info", "Looking up pallet…");
    try {
      const pallet = await lookupPallet(currentBarcode);
      el("sell-result").innerHTML = palletSummary(pallet);
      el("sell-action").classList.toggle("hidden", !pallet || pallet.status === "sold");
    } catch (error) {
      el("sell-result").innerHTML = alertHtml("error", formatApiError(error));
    }
  });

  el("sell-action").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!el("sell-confirm").checked) return;
    el("sell-result").innerHTML = alertHtml("info", "Recording sale…");
    try {
      const pallet = await api.sellPallet(currentBarcode);
      el("sell-result").innerHTML = `
        ${alertHtml("info", "Pallet marked as sold.")}
        ${palletSummary(pallet)}
      `;
      el("sell-action").classList.add("hidden");
      await loadPallets();
    } catch (error) {
      el("sell-result").innerHTML = alertHtml("warn", formatApiError(error));
    }
  });
}

function renderInventory() {
  el("view-inventory").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Inventory</h1>
        <p>Active pallets across all storage locations.</p>
      </div>
    </div>
    <div class="card">
      <form id="inventory-filters" class="form-grid">
        <div class="field">
          <label for="filter-location">Location</label>
          <select id="filter-location">
            <option value="">All locations</option>
            ${LOCATIONS.map((loc) => `<option value="${loc}">${escapeHtml(loc)}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label for="filter-status">Status</label>
          <select id="filter-status">
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="sold">Sold</option>
          </select>
        </div>
        <div class="field full btn-row">
          <button type="submit" class="btn btn-secondary">Apply filters</button>
        </div>
      </form>
      <div id="inventory-table"></div>
    </div>
  `;

  const renderTable = () => {
    if (!state.pallets.length) {
      el("inventory-table").innerHTML = alertHtml(
        "info",
        "No pallet data yet — connect the GET /pallets API to populate this table."
      );
      return;
    }

    el("inventory-table").innerHTML = `
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Barcode</th><th>Brand</th><th>Flavor</th><th>Expiration</th><th>Location</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${state.pallets
              .map(
                (p) => `<tr>
                  <td>${escapeHtml(p.barcode)}</td>
                  <td>${escapeHtml(p.brand_name || "—")}</td>
                  <td>${escapeHtml(p.flavor_name || p.product_name || "—")}</td>
                  <td>${escapeHtml(p.expiration_date)}</td>
                  <td>${escapeHtml(p.current_location)}</td>
                  <td>${escapeHtml(p.status)}</td>
                </tr>`
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  };

  renderTable();

  el("inventory-filters").addEventListener("submit", async (event) => {
    event.preventDefault();
    const filters = {};
    const location = el("filter-location").value;
    const status = el("filter-status").value;
    if (location) filters.location = location;
    if (status) filters.status = status;
    await loadPallets(filters);
    renderTable();
  });
}

function renderExpiring() {
  el("view-expiring").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Expiring Soon</h1>
        <p>Active pallets within the 90-day expiration threshold.</p>
      </div>
    </div>
    <div class="card" id="expiring-table"></div>
  `;

  if (!state.expiring.length) {
    el("expiring-table").innerHTML = alertHtml(
      "info",
      "No expiring pallet data yet — connect the GET /pallets/expiring API."
    );
    return;
  }

  el("expiring-table").innerHTML = `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Barcode</th><th>Flavor</th><th>Expires</th><th>Days left</th><th>Location</th></tr></thead>
        <tbody>
          ${state.expiring
            .map((p) => {
              const days = daysUntil(p.expiration_date);
              return `<tr class="${urgencyClass(days)}">
                <td>${escapeHtml(p.barcode)}</td>
                <td>${escapeHtml(p.flavor_name || p.product_name || "—")}</td>
                <td>${escapeHtml(p.expiration_date)}</td>
                <td>${days}</td>
                <td>${escapeHtml(p.current_location)}</td>
              </tr>`;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderExport() {
  el("view-export").innerHTML = `
    <div class="page-header">
      <div>
        <h1>Export Sales CSV</h1>
        <p>Download sold-product records for the Polly's Pop Sales Analytics Dashboard.</p>
      </div>
    </div>
    <div class="card">
      <p>The export pulls from the <code>sold_products</code> table via the backend CSV endpoint.</p>
      <div class="btn-row">
        <a class="btn btn-primary" href="${api.exportSoldCsvUrl()}" download="sold-products.csv">Download CSV</a>
      </div>
      <div id="export-status" style="margin-top:1rem"></div>
    </div>
  `;

  fetch(api.exportSoldCsvUrl(), { method: "HEAD" })
    .then((response) => {
      if (response.ok) {
        el("export-status").innerHTML = alertHtml("info", "Export endpoint is available.");
      } else {
        el("export-status").innerHTML = alertHtml(
          "warn",
          "Export endpoint not built yet (expected GET /export/sold-products.csv)."
        );
      }
    })
    .catch(() => {
      el("export-status").innerHTML = alertHtml("error", "Could not reach the export endpoint.");
    });
}

function renderPhase2Placeholder(route, title, description, bullets) {
  el(`view-${route}`).innerHTML = `
    <div class="page-header">
      <div>
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(description)}</p>
      </div>
      <span class="badge badge-phase">Phase 2</span>
    </div>
    <div class="card">
      <h2>Planned capabilities</h2>
      <ul>${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      ${alertHtml("info", "UI shell is ready — backend integration will activate this screen when the Phase 2 API ships.")}
    </div>
  `;
}

function renderScanner() {
  renderPhase2Placeholder(
    "scanner",
    "Scanner Integration",
    "Warehouse scanner gun will call the same pallet APIs as manual entry.",
    [
      "Scan pallet barcode to look up details instantly",
      "Quick-transfer workflow to Warehouse 1 or 2",
      "Sell confirmation from scan without typing",
      "Fallback manual entry always visible on every screen",
    ]
  );
}

function renderNotifications() {
  renderPhase2Placeholder(
    "notifications",
    "Notifications",
    "Expiration alerts and flavor-order reminders.",
    [
      "Email when a pallet is within 3 months of expiry",
      "12-week flavor ordering lead-time reminders",
      "In-app notification history from the notifications table",
    ]
  );
}

function renderAnalytics() {
  renderPhase2Placeholder(
    "analytics",
    "Sales Analytics",
    "Future prediction and reporting API for sales trends.",
    [
      "CSV export feeds the external analytics dashboard today",
      "Future API endpoint for demand forecasting",
      "Flavor velocity and overproduction risk indicators",
    ]
  );
}

async function renderView(route) {
  try {
    if (route === "dashboard") {
      await Promise.all([loadPallets(), loadExpiring()]);
      renderDashboard();
      return;
    }
    if (route === "feature-status") {
      await renderFeatureStatus();
      return;
    }
    if (route === "create") {
      await loadBrands();
      if (state.brands.length) await loadProducts(state.brands[0].id);
      renderCreate();
      return;
    }
    if (route === "move") {
      renderMove();
      return;
    }
    if (route === "sell") {
      renderSell();
      return;
    }
    if (route === "inventory") {
      await loadPallets();
      renderInventory();
      return;
    }
    if (route === "expiring") {
      await loadExpiring();
      renderExpiring();
      return;
    }
    if (route === "export") {
      renderExport();
      return;
    }
    if (route === "scanner") {
      renderScanner();
      return;
    }
    if (route === "notifications") {
      renderNotifications();
      return;
    }
    if (route === "analytics") {
      renderAnalytics();
      return;
    }
  } catch (error) {
    const container = el(`view-${route}`);
    if (container) {
      container.innerHTML = alertHtml("error", formatApiError(error));
    }
  }
}

window.addEventListener("hashchange", () => {
  showRoute(location.hash.replace("#", ""));
});

async function init() {
  const route = location.hash.replace("#", "") || "dashboard";
  showRoute(route);
}

init();

/** API client — calls planned endpoints; surfaces availability for the feature dashboard. */

const API_BASE = window.location.origin;

export const ENDPOINTS = {
  health: { method: "GET", path: "/health", phase: 1, label: "Health check" },
  brands: { method: "GET", path: "/brands", phase: 1, label: "List brands" },
  products: { method: "GET", path: "/products", phase: 1, label: "List products" },
  palletsList: { method: "GET", path: "/pallets", phase: 1, label: "List pallets" },
  palletsCreate: { method: "POST", path: "/pallets", phase: 1, label: "Create pallet" },
  palletLookup: { method: "GET", path: "/pallets/{barcode}", phase: 1, label: "Lookup pallet" },
  palletTransfer: {
    method: "POST",
    path: "/pallets/{barcode}/transfer",
    phase: 1,
    label: "Transfer pallet",
  },
  palletSell: { method: "POST", path: "/pallets/{barcode}/sell", phase: 1, label: "Sell pallet" },
  palletsExpiring: {
    method: "GET",
    path: "/pallets/expiring",
    phase: 1,
    label: "Expiring pallets",
  },
  exportSold: {
    method: "GET",
    path: "/export/sold-products.csv",
    phase: 1,
    label: "Sold products CSV",
  },
  notifications: {
    method: "GET",
    path: "/notifications",
    phase: 2,
    label: "Notifications",
  },
  scannerLookup: {
    method: "POST",
    path: "/scanner/lookup",
    phase: 2,
    label: "Scanner lookup",
  },
};

async function request(method, path, { body, params } = {}) {
  let url = `${API_BASE}${path}`;
  if (params) {
    const search = new URLSearchParams(params);
    url += `?${search}`;
  }

  const options = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";

  let data = null;
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else if (contentType.includes("text/")) {
    data = await response.text();
  }

  if (!response.ok) {
    const message =
      (data && (data.detail || data.message)) ||
      `Request failed (${response.status})`;
    const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  get: (path, options) => request("GET", path, options),
  post: (path, body, options = {}) => request("POST", path, { ...options, body }),

  health: () => api.get("/health"),
  brands: () => api.get("/brands"),
  products: (brandId) =>
    api.get("/products", brandId ? { params: { brand_id: brandId } } : undefined),
  pallets: (filters = {}) => api.get("/pallets", { params: filters }),
  pallet: (barcode) => api.get(`/pallets/${encodeURIComponent(barcode)}`),
  createPallet: (payload) => api.post("/pallets", payload),
  transferPallet: (barcode, toLocation) =>
    api.post(`/pallets/${encodeURIComponent(barcode)}/transfer`, { to_location: toLocation }),
  sellPallet: (barcode) => api.post(`/pallets/${encodeURIComponent(barcode)}/sell`, {}),
  expiring: () => api.get("/pallets/expiring"),
  exportSoldCsvUrl: () => `${API_BASE}/export/sold-products.csv`,

  /** Probe whether an endpoint responds (used by feature status panel). */
  async probe(key) {
    const spec = ENDPOINTS[key];
    if (!spec) return { key, status: "unknown" };

    let path = spec.path;
    if (path.includes("{barcode}")) path = path.replace("{barcode}", "00001");

    try {
      const response = await fetch(`${API_BASE}${path}`, {
        method: spec.method === "POST" ? "OPTIONS" : spec.method,
        headers: { Accept: "application/json" },
      });
      if (response.status === 404 || response.status === 405) {
        return { key, status: "missing", code: response.status, ...spec };
      }
      if (response.ok || response.status === 422 || response.status === 400) {
        return { key, status: "ready", code: response.status, ...spec };
      }
      return { key, status: "error", code: response.status, ...spec };
    } catch {
      return { key, status: "offline", ...spec };
    }
  },
};

export function formatApiError(error) {
  if (!error) return "Unknown error";
  if (error.status === 404) {
    return "This API endpoint is not built yet. It will activate when the backend route is merged.";
  }
  return error.message || String(error);
}

export function isNotImplemented(error) {
  return error && error.status === 404;
}

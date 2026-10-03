// Six API calls, with the same response shapes in mock and deployed modes.
// Include <script src="config.js"></script> before importing this module.
const mockRoot = new URL("./mock/", import.meta.url);
const storageKey = "clear-statement.mock.v1";
const statuses = { approve: "approved", escalate: "escalated", dismiss: "dismissed" };
let state;
let loading;

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function mockEnabled() {
  if (typeof USE_MOCK === "undefined" || typeof API_BASE === "undefined") {
    throw new Error("Load config.js before api.js");
  }
  return USE_MOCK;
}

async function readJSON(url, options) {
  const response = await fetch(url, options);
  let body;
  try { body = await response.json(); }
  catch { throw new ApiError(response.status, "Server returned an invalid JSON response"); }
  if (!response.ok) throw new ApiError(response.status, body.error || response.statusText);
  return body;
}

function request(path, body) {
  return readJSON(`${API_BASE.replace(/\/+$/, "")}${path}`, body === undefined ? undefined : {
    method: "POST",
    ...(body instanceof FormData
      ? { body }
      : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  });
}

function fixture(name) { return readJSON(new URL(name, mockRoot)); }
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function save() {
  // Still usable in private browsing or when browser storage is disabled.
  try { sessionStorage.setItem(storageKey, JSON.stringify(state)); } catch { /* memory only */ }
}

async function mockState() {
  if (state) return state;
  if (!loading) loading = (async () => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey));
      if (saved && Array.isArray(saved.flags) && Array.isArray(saved.audit)) state = saved;
    } catch { /* use fixtures */ }
    if (!state) {
      const [flags, audit] = await Promise.all([fixture("flags.json"), fixture("audit.json")]);
      state = { flags, audit };
    }
    return state;
  })().finally(() => { loading = undefined; });
  return loading;
}

function requireStatement(id) {
  if (id !== "problem") throw new ApiError(404, `unknown statement '${id}'`);
}

// Accept a File, a filename string, or {filename: "problem.pdf"}.
export async function processStatement(input = "problem.pdf") {
  const isFile = typeof File !== "undefined" && input instanceof File;
  const filename = isFile ? input.name : typeof input === "string" ? input : input?.filename;
  if (!mockEnabled()) {
    if (isFile) {
      const form = new FormData();
      form.append("file", input);
      return request("/process", form);
    }
    return request("/process", { filename });
  }
  const id = String(filename || "").split(/[\\/]/).pop().replace(/\.[^.]*$/, "").toLowerCase();
  if (id !== "problem") throw new ApiError(400, "demo supports sample statements only");
  const [current, flags, result] = await Promise.all([
    mockState(), fixture("flags.json"), fixture("process.json"),
  ]);
  // Like the backend, reprocessing reopens flags and retains prior audit records.
  current.flags = flags.map(flag => ({ ...flag, created_at: new Date().toISOString() }));
  save();
  return result;
}

export async function getStatement(id) {
  if (!mockEnabled()) return request(`/statement/${encodeURIComponent(id)}`);
  requireStatement(id);
  return fixture("statement.json");
}

export async function getSummary(id, lang = "en") {
  if (!mockEnabled()) {
    const qs = lang && lang !== "en" ? `?lang=${encodeURIComponent(lang)}` : "";
    return request(`/summary/${encodeURIComponent(id)}${qs}`);
  }
  requireStatement(id);
  // For mock mode use the Spanish fixture when lang=es, falling back to the
  // English fixture (which is also used as the fallback if the Spanish file is absent).
  const fixture_name = lang === "es" ? "summary_es.json" : "summary.json";
  let result;
  try {
    result = await fixture(fixture_name);
  } catch {
    result = await fixture("summary.json");
    result.machine_translated = false;
  }
  result.audio_url = result.audio_url ? new URL(result.audio_url, mockRoot).href : null;
  return result;
}

export async function getFlags(statementId) {
  if (!mockEnabled()) return request("/flags" + (statementId == null ? "" : `?statement_id=${encodeURIComponent(statementId)}`));
  const current = await mockState();
  return copy(current.flags.filter(flag => statementId == null || flag.statement_id === statementId));
}

export async function decideFlag(id, action, note = "") {
  if (!mockEnabled()) return request(`/flags/${encodeURIComponent(id)}/decision`, { action, note });
  if (!Object.hasOwn(statuses, action)) throw new ApiError(400, "action must be approve, escalate or dismiss");
  if (typeof note !== "string") throw new ApiError(400, "note must be text");
  note = note.trim();
  if (action === "escalate" && !note) throw new ApiError(400, "a note is required to escalate");
  const [current, template] = await Promise.all([mockState(), fixture("decision.json")]);
  const flag = current.flags.find(item => item.id === id);
  if (!flag) throw new ApiError(404, `unknown flag '${id}'`);
  if (flag.status !== "open") throw new ApiError(409, `flag ${id} was already ${flag.status}`);
  const record = { ...template, id: crypto.randomUUID(), statement_id: flag.statement_id,
    flag_id: id, action, note, timestamp: new Date().toISOString() };
  flag.status = statuses[action];
  current.audit.push(record);
  save();
  return copy(record);
}

export async function getAudit(id) {
  if (!mockEnabled()) return request(`/audit/${encodeURIComponent(id)}`);
  requireStatement(id);
  const current = await mockState();
  return copy(current.audit.filter(record => record.statement_id === id)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp)));
}

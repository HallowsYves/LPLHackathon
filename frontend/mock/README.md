# Task S: mock API layer

Synthetic demo; tested on sample data. Only the `problem` fixture is supported
in mock mode. Live mode forwards requests to the backend, which also supports `clean`.

From the repository root, serve the frontend:

```sh
python3 -m http.server 8080 --directory frontend
```

Open http://localhost:8080/mock/ and select **Run checks**. This page tests all six
endpoint wrappers, decision errors, persistence and the audio asset. Use its audio
control to hear the full summary. This is a local macOS synthesized voice sample,
not a recording from Polly. No AWS services are contacted with `USE_MOCK = true`.
Use HTTP: browsers do not support fetching these fixtures from `file://` pages.

Pages should load configuration as a classic script, before their module:

```html
<script src="config.js"></script>
<script type="module" src="client.js"></script>
```

Then import the six functions from `./api.js` in the page module. The check page
also exposes them as `window.api` for browser-console calls:

```js
await api.processStatement('problem.pdf'); // also accepts File or {filename}
await api.getStatement('problem');
await api.getSummary('problem');
await api.getFlags('problem'); // omit argument to list all flags
await api.decideFlag('f1', 'escalate', 'Call Margaret to confirm the wire.');
await api.getAudit('problem');
```

`decideFlag` returns the saved audit record, as the backend does. Refresh flags
after deciding. Audit records are oldest first. Catch `ApiError` and inspect its
`status` for HTTP-like failures (400, 404, 409); network failures reject as well.
Decisions are saved in sessionStorage for navigation/reloads within this browser
tab, falling back to memory if storage is unavailable. Reprocessing resets flags
to open and preserves audit history, matching the backend. The check page clears
mock history before each run. Closing the tab starts a fresh session.

Fixture JSON files cover each response. Runtime decisions use `decision.json` as
a template with unique ids and current timestamps. `summary.json` contains the
validated deterministic summary of `statement.json`; `summary.txt` is its audio
transcript. Its audio URL is resolved relative to this folder so nested pages work.

Set `USE_MOCK = false` in `config.js` to use `API_BASE`. Its classic `const`
declarations remain compatible with `infra/deploy.sh`. Live File uploads use
multipart FormData; other writes use JSON. No credentials belong in these files.

# TASKS: Clear Statement build list

Pick any task whose `Needs:` is satisfied (or `none`), paste its prompt into Claude Code or Codex, and work in the folder it owns. Read `CLAUDE.md` first (Codex reads `AGENTS.md`, same content). The idea, scope and design principles live there; do not re-decide them here.

**Rules for every task**
- Touch only the folder(s) named in `Owns:`. Two people never edit the same file.
- Build against the shapes below, not against another task's code. If a prerequisite is not merged yet, use the stub/mock the task tells you to.
- Python 3.12, standard library plus `boto3` (and `reportlab` for PDFs). No other backend dependencies without asking.
- Tag results "tested on sample data". Language is "worth a call", never "fraud".
- Done means the `Done when:` command passes. Mark the task `[x]` below when merged.

## Shared shapes (the contract)

`statement.json`, `flag`, and the endpoint table are in `CLAUDE.md` section 5. Additions, so nobody guesses:

- Statement ids are the ground-truth filenames: `clean`, `problem`. `data/ground_truth/<id>.json` and `data/pdfs/<id>.pdf`.
- A flag also carries `statement_id` and `created_at` (ISO 8601 UTC string).
- Summary response (`GET /summary/{id}`):
  ```json
  {"statement_id": "problem", "text": "...", "audio_url": "https://...",
   "validation": {"figures_checked": 9, "mismatches": [], "attempts": 1, "used_fallback": false}}
  ```
- Audit record (`GET /audit/{id}` returns a list, oldest first):
  ```json
  {"id": "a1", "statement_id": "problem", "flag_id": "f1", "advisor": "Dana Ortiz (demo advisor)",
   "action": "escalate", "note": "...", "timestamp": "2026-10-03T01:14:00Z"}
  ```
- `POST /flags/{id}/decision` body: `{"action": "approve|escalate|dismiss", "note": "..."}`. It sets the flag status to `approved`, `escalated` or `dismissed` and writes one audit record. A note is required for `escalate`.
- Store switch: env var `STORE=local` (JSON files under `.local_store/`) or `STORE=dynamo` (tables `cs_flags`, `cs_audit`). Default `local`.
- Advisor identity is hardcoded: `Dana Ortiz (demo advisor)`.
- Thresholds (constants in `backend/flags/rules.py`): `LARGE_WIRE_MIN = 10000`, `RAPID_COUNT = 3`, `RAPID_DAYS = 7`, `RAPID_TOTAL_MIN = 5000`, `FEE_JUMP_PCT = 25`.
- Config: AWS region and model id come from env vars `AWS_REGION` and `BEDROCK_MODEL_ID`, never hardcoded.

## Track 0: Setup

- [x] **A. AWS login and smoke test** | Needs: none | Owns: `infra/smoke_test.py`
  Prompt: Follow `SETUP.md` to get AWS CLI credentials working, then write `infra/smoke_test.py` that makes one call each to Bedrock (using `BEDROCK_MODEL_ID`), Polly, Textract (`AnalyzeDocument` on a tiny generated image or any bytes the API accepts) and S3 (`list_buckets`), prints PASS/FAIL per service and the region used.
  Done when: `python infra/smoke_test.py` prints PASS for all four, or a clear FAIL reason for each blocked one.
- [x] **B. Scaffold** | Done: folders, `CLAUDE.md`, `AGENTS.md`, this file.

## Track DATA

- [x] **C. Ground-truth statements** | Needs: none | Owns: `data/ground_truth/`
  Prompt: Write `clean.json` and `problem.json` for Margaret Hale (age 78, 2026-Q3) in the `statement.json` shape. Use realistic, internally consistent numbers. `clean` has normal activity and a prior fee total within 25% of the current fee total. `problem` plants all three issues: a wire of at least $10,000 to a payee with `payee_is_new: true`; three or more withdrawals within 7 days totaling at least $5,000; fees more than 25% above `prior_fee_total` (example: 1031.50 vs 640.00). Use fictional payees only. Include `prior_fee_total` in both.
  Done when: both files parse as JSON and match the shape in `CLAUDE.md` section 5.
- [x] **D. Consistency check** | Needs: C | Owns: `data/check_ground_truth.py`
  Prompt: Write a script that loads every `data/ground_truth/*.json` and checks: required keys exist, dates fall in the stated period, transaction ids are unique, fee amounts are positive, and account change from `start_value` to `end_value` is plausible given the listed transactions and fees (document the tolerance). Exit non-zero with a readable message on failure.
  Done when: `python data/check_ground_truth.py` exits 0 on both files, and exits non-zero if you edit one number.
- [x] **E. PDF generator** | Needs: C | Owns: `data/make_pdfs.py`, `data/pdfs/`
  Prompt: Using `reportlab`, generate `data/pdfs/<id>.pdf` from each ground-truth JSON. Make it look like a dense brokerage statement: header with client and period, account summary table, fees table, a transactions table, small print. Every figure printed must come from the JSON, never retyped. Label it "SYNTHETIC SAMPLE, NOT A REAL STATEMENT" in the footer.
  Done when: `python data/make_pdfs.py` writes two PDFs that open and show every transaction.

## Track FLAGS

- [x] **F. Flag rules** | Needs: none | Owns: `backend/flags/rules.py`, `backend/flags/test_rules.py`
  Prompt: Implement three plain-Python functions taking a `statement.json` dict and returning a list of flag dicts (shape in `CLAUDE.md`, ids assigned by the caller): `large_wire_new_payee`, `rapid_withdrawals`, `fee_jump`. Use the threshold constants from the shared shapes. Each flag carries a plain-English `reason` that says "worth a call" and never says fraud. Include `txn_ids`. For `fee_jump`, `txn_ids` is empty. Write tests with inline fixtures (a clean one and a planted one) so you do not wait on task C.
  Done when: `python -m unittest backend.flags.test_rules` passes.
- [x] **G. Flag runner** | Needs: F, H | Owns: `backend/flags/run.py`
  Prompt: Write `run_flags(statement_id)` that loads `data/ground_truth/<id>.json`, runs all rules, assigns ids (`f1`, `f2`, ...), adds `statement_id`, `created_at` and `status: "open"`, and saves via `backend/common/store.py`. It is idempotent: re-running replaces that statement's flags without duplicating.
  Done when: running it for `problem` yields exactly 3 open flags and for `clean` yields 0.

## Track STORE

- [x] **H. Store** | Needs: none | Owns: `backend/common/store.py`
  Prompt: Implement functions `save_flags`, `list_flags(statement_id=None)`, `get_flag`, `update_flag_status`, `add_audit`, `list_audit(statement_id)` with the `STORE=local|dynamo` switch from the shared shapes. The DynamoDB backend uses tables `cs_flags` (key `id`) and `cs_audit` (key `id`, plus a `statement_id` index or scan filter; keep it simple). The local backend writes JSON under `.local_store/` (add it to `.gitignore`).
  Done when: a short script round-trips a flag and an audit record on the local backend, and the dynamo backend passes the same script when the tables exist.

## Track SUMMARY

- [x] **I. Number validator** | Needs: none | Owns: `backend/summary/validator.py`, `backend/summary/test_validator.py`
  Prompt: Write `validate(summary_text, statement) -> {"figures_checked": int, "mismatches": [str]}`. Extract every dollar figure from the text (handle `$1,031.50`, `$48,000`, `$412K` style if you choose to allow it, and say which). A figure is valid if it equals a value in the statement JSON (account values, fees, transaction amounts, `prior_fee_total`) or an allowed derived value (document which: sums and differences of listed values). Tests: a correct summary, one with a wrong figure, and one with an invented figure.
  Done when: `python -m unittest backend.summary.test_validator` passes.
- [x] **J. Summarizer** | Needs: I (code), A (for a live Bedrock call; mock otherwise) | Owns: `backend/summary/summarize.py`
  Prompt: Write `summarize(statement) -> summary response` (shape above, without `audio_url`). The Bedrock prompt receives only the statement JSON and asks for a short, large-print-friendly summary: account value, what changed, fees paid, and 2 to 3 questions to ask the advisor. Plain words, no investment advice, no word "fraud". Run `validate`; on mismatch regenerate up to 3 times, passing back the mismatching figures. If all attempts fail, return a deterministic template summary filled from the JSON with `used_fallback: true`. Use the Bedrock Converse API. Add a `--mock` flag that skips Bedrock and returns the template.
  Done when: `python -m backend.summary.summarize problem --mock` prints a valid summary, and without `--mock` it passes validation against Bedrock.
- [x] **K. Guardrail** | Needs: A | Owns: `infra/create_guardrail.py`
  Prompt: Write a script that creates a Bedrock Guardrail denying topics "fraud accusations" and "investment advice (buy, sell, hold recommendations)" and prints its id and version. Document the env vars `GUARDRAIL_ID` and `GUARDRAIL_VERSION` that `summarize.py` should read and apply when set. Make creation idempotent by name.
  Done when: running it twice does not duplicate the guardrail, and a test prompt asking for investment advice is blocked.
- [x] **L. Read-aloud** | Needs: A | Owns: `backend/summary/speak.py`
  Prompt: Write `speak(statement_id, text) -> presigned_url`. It calls Polly (a neural voice with a slower rate via SSML), writes the mp3 to an S3 bucket named by env var `AUDIO_BUCKET` under `audio/<statement_id>.mp3`, and returns a presigned URL valid for one hour. Cache: if the object exists for the same text hash, skip Polly.
  Done when: running it on sample text gives a URL that plays in a browser.

## Track API

- [x] **N. Decisions and audit** | Needs: H | Owns: `backend/api/decisions.py`
  Prompt: Implement `decide(flag_id, action, note)` and `get_audit(statement_id)` using the shared shapes: validate the action, require a note for `escalate`, update flag status, write one audit record with the hardcoded advisor and a UTC timestamp, and refuse a second decision on a flag that is no longer `open`.
  Done when: tests cover each action, a missing note on escalate, and a double decision.
- [x] **M. API handler** | Needs: H, N; calls G, J, L (use stubs until merged) | Owns: `backend/api/handler.py`
  Prompt: One Lambda handler for API Gateway (proxy integration) that routes the six endpoints in `CLAUDE.md` section 5. `POST /process` accepts a file upload or `{"filename": "problem.pdf"}`, maps the filename to a statement id, and if the id is unknown returns 400 "demo supports sample statements only". It runs the flag runner, then returns the id. `GET /summary/{id}` runs the summarizer and Polly once, then caches. All responses include CORS headers. Add `backend/api/local_server.py` using `http.server` so the frontend can run against it with no AWS deployment.
  Done when: `python backend/api/local_server.py` serves all six endpoints on localhost:8000 with `STORE=local` and the `--mock` summarizer.
- [x] **O. Textract diff** | Needs: A, E | Owns: `backend/api/textract_check.py`
  Prompt: Write `diff_against_ground_truth(statement_id)`: send `data/pdfs/<id>.pdf` to Textract `AnalyzeDocument` (TABLES + FORMS), pull out the dollar amounts and dates, and report which ground-truth figures were found and which were not. Output a small JSON report (found, missing, match_rate). This is a side check only and must never block the demo path.
  Done when: running it on both PDFs prints a match_rate and does not raise.

## Track INFRA

- [x] **P. SAM template** | Needs: M, N (entry points exist), H | Owns: `infra/template.yaml`
  Prompt: Write a SAM template: API Gateway REST API with the six routes pointing at one Python 3.12 Lambda, DynamoDB tables `cs_flags` and `cs_audit` (on-demand billing), an S3 bucket for audio and one for the static site, least-privilege IAM (Bedrock invoke, Polly, Textract, the two tables, the audio bucket), env vars from the shared shapes, and CORS for the site origin.
  Done when: `sam validate` and `sam build` succeed.
- [x] **Q. Deploy script** | Needs: P | Owns: `infra/deploy.sh`
  Prompt: One script that runs `sam deploy`, writes the API URL into `frontend/config.js`, and uploads `frontend/` to the site bucket (CloudFront in front, if time allows; otherwise the simplest hosting the account permits). Print the final site URL.
  Done when: running it from a clean checkout gives a working URL.
- [x] **R. Deployed smoke test** | Needs: Q | Owns: `infra/e2e_test.py`
  Prompt: A script that calls the deployed API: process `problem`, expect 3 flags, fetch the summary (audio URL must respond with 200), escalate a flag with a note, and read the audit trail. Run it from a browser-origin-like request to catch CORS issues.
  Done when: it prints PASS on the deployed stack.

## Track FRONTEND

Plain HTML, CSS and JS, no build step. Large type (at least 20px body), high contrast, keyboard accessible.

- [ ] **S. Mock layer** | Needs: none | Owns: `frontend/mock/`, `frontend/api.js`, `frontend/config.js`
  Prompt: Hand-write mock responses for every endpoint, matching the shapes, under `frontend/mock/`. Write `api.js` exporting one function per endpoint. `config.js` sets `API_BASE` and `USE_MOCK` (true means read the mock files). Use the `problem` statement for realism.
  Done when: opening the page with `USE_MOCK = true` returns data for all six calls from the browser console.
- [ ] **T. Client view** | Needs: S | Owns: `frontend/index.html`, `frontend/client.js`, `frontend/styles.css`
  Prompt: A page with the original statement (an embedded PDF or rendered table) on the left and the plain-language summary in large type on the right, an upload button, a high-contrast toggle, and a small "numbers checked: N, mismatches: 0" badge from `validation`. Sample-data label visible.
  Done when: the page renders against mocks at 1280px and at phone width without horizontal scroll.
- [ ] **U. Read-aloud button** | Needs: T | Owns: `frontend/client.js` (audio section only)
  Prompt: A large Read aloud button with play/pause, driven by `audio_url`, with a clear loading and error state. It must be operable by keyboard.
  Done when: the button plays the mock audio and shows an error message when the URL fails.
- [ ] **V. Advisor view** | Needs: S | Owns: `frontend/advisor.html`, `frontend/advisor.js`
  Prompt: A flag list showing rule, reason and status. Selecting a flag highlights its transactions in a table. Approve, Escalate and Dismiss buttons with a note box (required for Escalate) call the decision endpoint and update the row. No "fraud" wording anywhere in the UI.
  Done when: against mocks, escalating without a note is blocked and escalating with one updates the flag status.
- [ ] **W. Audit trail panel** | Needs: V | Owns: `frontend/advisor.js` (audit section only)
  Prompt: A panel on the advisor page listing audit records newest first (who, action, note, time), refreshed after every decision, plus an "alert sent to advisor" line shown after a new flag appears (the UI shows it regardless of SES).
  Done when: a decision made in the page appears in the panel without a reload.
- [ ] **X. Go live** | Needs: T, U, V, W, and either M (local server) or R (deployed) | Owns: `frontend/config.js`
  Prompt: Flip `USE_MOCK` to false, point `API_BASE` at the local server or the deployed API, and fix any shape mismatches by correcting the frontend, not the contract. Walk the full demo flow.
  Done when: upload, summary, read-aloud, flags, escalate and audit all work end to end.

## Track DEMO

- [ ] **Y. Rehearsal and backup video** | Needs: X | Owns: `docs/demo_script.md`
  Prompt: Turn the 5-minute script in `CLAUDE.md` section 8 into a timed run sheet with exact clicks. Run it three times, fix anything that stumbles, then record a backup video of a clean run.
  Done when: three clean runs and a saved video file.
- [ ] **Z. Deck, ZIP and submission** | Needs: none to start; final numbers need Y | Owns: `docs/`
  Prompt: Research task first: run the research prompt (ask the team lead) and save sources to `docs/sources.md`. Then draft the deck (LPL template) around the pitch in `CLAUDE.md`: problem, demo, architecture slide with why each AWS service was chosen, business-impact slide using only sourced figures, roadmap (audit trail as training data for tuned thresholds, Step Functions, SES). Prepare the code ZIP (no secrets, no `.local_store/`) and the Project Submission Form. Submit with at least a 1-hour buffer before 9:00 AM PT Saturday Oct 3.
  Done when: deck, ZIP and form are ready and uploaded to Box.

## Stretch (only after X works end to end)

- [ ] **AA. Spanish read-aloud** | Needs: J, L, T (and M for the API param) | Owns: `backend/summary/translate.py`; small edits allowed in `summarize.py`, `speak.py`, `handler.py`, `client.js` (coordinate with their owners)
  Prompt: Add Spanish (`es`) alongside English (`en`) only; no other languages. Write `translate_summary(text, lang)` using Amazon Translate on the already-validated English summary, then re-run the number validator on the result and fall back to the English text with a visible notice if figures do not match. `speak.py` maps `en` to a neural English voice and `es` to a neural Spanish (US) voice, and the S3 cache key includes the language. `GET /summary/{id}?lang=es` returns the translated text, `audio_url` and the `validation` block. The frontend gets an English/Español dropdown beside Read aloud, and shows "Machine translated" on screen for Spanish. Guardrails and the "worth a call" tone apply to the English source before translation.
  Done when: selecting Español shows Spanish text and plays Spanish audio on `problem`, and the validation badge shows 0 mismatches.

## Suggested order for two people

- Person 1 (backend): A, H, F, G, I, J, N, M, L, K, O, P, Q, R
- Person 2 (front and story): S, T, U, V, W, C, D, E, X, Y, Z

Tasks C, F, H, I, S and A have `Needs: none`, so everyone can start at once.

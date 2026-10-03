import { setStatementContext } from './navigation.js';
import { getStatement, getFlags, decideFlag } from './api.js';

const byId = id => document.getElementById(id);
const statementId = new URLSearchParams(window.location.search).get('statement_id') || 'problem';
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
const rules = {
  large_wire_new_payee: 'Large wire to a new payee',
  rapid_withdrawals: 'Rapid repeated withdrawals',
  fee_jump: 'Fee increase',
};
const drafts = new Map();
const savedDecisions = new Set();
const actions = [...document.querySelectorAll('[data-action]')];
let statement;
let flags = [];
let selectedId;
let busy = false;
let flagsCurrent = false;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function selectedFlag() { return flags.find(flag => flag.id === selectedId); }
function ruleLabel(flag) { return rules[flag.rule] || flag.rule; }
function showError(id, message) {
  byId(id).textContent = message;
  byId(id).hidden = !message;
}

function updateControls() {
  const flag = selectedFlag();
  const closed = flag && (flag.status !== 'open' || savedDecisions.has(flag.id));
  actions.forEach(button => { button.disabled = busy || !flagsCurrent || !flag || closed; });
  byId('note').disabled = busy || !flagsCurrent || !flag || closed;
  byId('refresh').disabled = busy;
  for (const button of byId('flag-list').querySelectorAll('button')) button.disabled = busy;
  byId('workspace').setAttribute('aria-busy', String(busy));
  byId('closed').hidden = !closed;
  byId('closed').textContent = closed
    ? (flag.status === 'open' ? 'The decision was saved. Refresh flags to confirm its status.' : `This flag is ${flag.status}. A second decision is not available.`)
    : '';
}

function renderDetail() {
  const flag = selectedFlag();
  byId('detail').hidden = !flag;
  if (!flag) { updateControls(); return; }
  byId('detail-title').textContent = ruleLabel(flag);
  byId('reason').textContent = flag.reason;
  byId('flag-status').textContent = `Status: ${flag.status}`;
  byId('note').value = drafts.get(flag.id) || '';
  byId('note').removeAttribute('aria-invalid');
  const related = new Set(flag.txn_ids);
  byId('transaction-help').textContent = related.size
    ? 'Rows marked “Selected flag” are related to this flag.'
    : 'No transactions are associated with this flag.';
  byId('fee-context').hidden = flag.rule !== 'fee_jump';
  if (flag.rule === 'fee_jump') {
    byId('fee-context').replaceChildren(
      element('p', `Current fees: ${money(statement.fees.reduce((sum, fee) => sum + fee.amount, 0))}`),
      element('p', `Prior period fees: ${money(statement.prior_fee_total)}`),
    );
  }
  const rows = statement.transactions.map(txn => {
    const row = element('tr');
    row.dataset.txnId = txn.id;
    row.classList.toggle('transaction-highlight', related.has(txn.id));
    const values = [
      `${txn.date}${txn.account ? ` / ${txn.account}` : ''}`,
      `${txn.type}${txn.payee ? ` · ${txn.payee}` : ''}`,
      money(txn.amount),
    ];
    values.forEach((value, i) => {
      const cell = element('td', value);
      cell.dataset.label = ['Date / account', 'Activity / payee', 'Amount'][i];
      row.append(cell);
    });
    return row;
  });
  byId('transactions').tBodies[0].replaceChildren(...rows);
  updateControls();
}

function renderFlags() {
  if (!flags.some(flag => flag.id === selectedId)) selectedId = flags[0]?.id;
  byId('flag-count').textContent = `${flags.length} total · ${flags.filter(flag => flag.status === 'open').length} open`;
  byId('empty').hidden = flags.length > 0;
  byId('flag-list').replaceChildren(...flags.map(flag => {
    const item = element('li');
    const button = element('button', undefined, 'flag-card');
    button.type = 'button';
    button.dataset.flagId = flag.id;
    button.setAttribute('aria-pressed', String(flag.id === selectedId));
    button.setAttribute('aria-controls', 'detail');
    const badge = element('span', `Status: ${flag.status}`, 'status-badge');
    badge.dataset.status = flag.status;
    button.append(element('span', ruleLabel(flag)), element('p', `Rule: ${flag.rule}`), element('p', flag.reason), badge);
    button.addEventListener('click', () => {
      if (busy) return;
      selectedId = flag.id;
      showError('decision-error', '');
      for (const card of byId('flag-list').querySelectorAll('button')) {
        card.setAttribute('aria-pressed', String(card.dataset.flagId === selectedId));
      }
      renderDetail();
      byId('status').textContent = `Selected: ${ruleLabel(flag)} · ${flag.status}.`;
    });
    item.append(button);
    return item;
  }));
  renderDetail();
}

function renderContext() {
  const context = byId('client-context');
  context.replaceChildren(
    element('span', `Client: ${statement.client.name} (age ${statement.client.age})`),
    element('span', `Accounts: ${statement.accounts.map(account => `${account.type} (${account.id})`).join(' · ')}`),
    element('span', `Period: ${statement.period}`),
  );
  context.hidden = false;
}

// Successful refresh hook reserved for later audit/notification integration.
async function fetchFlags() {
  flags = await getFlags(statementId);
  flagsCurrent = true;
  savedDecisions.clear();
  renderFlags();
  document.dispatchEvent(new CustomEvent('flags-refreshed', { detail: { statementId, flags } }));
}

async function refresh() {
  if (busy) return;
  busy = true;
  flagsCurrent = false;
  updateControls();
  showError('error', '');
  byId('status').textContent = 'Loading the statement and flags…';
  try {
    if (!statement) { statement = await getStatement(statementId); renderContext(); }
    await fetchFlags();
    byId('workspace').hidden = false;
    byId('status').textContent = 'Flags refreshed. Tested on sample data.';
  } catch (error) {
    showError('error', `${error.message || 'Could not load flags.'} Select Refresh flags to retry.`);
    byId('status').textContent = 'Flags could not be refreshed. Decisions are unavailable until refresh succeeds.';
  } finally {
    busy = false;
    updateControls();
  }
}

async function decide(action) {
  const flag = selectedFlag();
  if (busy || !flagsCurrent || !flag || flag.status !== 'open' || savedDecisions.has(flag.id)) return;
  const note = byId('note').value.trim();
  if (action === 'escalate' && !note) {
    showError('decision-error', 'A note is required to Escalate. Please add a note before submitting.');
    byId('note').setAttribute('aria-invalid', 'true');
    byId('note').focus();
    return;
  }
  busy = true;
  updateControls();
  showError('decision-error', '');
  showError('error', '');
  byId('note').removeAttribute('aria-invalid');
  byId('status').textContent = 'Saving your decision…';
  try {
    // The endpoint returns an audit record; only a flag refresh supplies authoritative status.
    await decideFlag(flag.id, action, note);
    savedDecisions.add(flag.id);
    drafts.delete(flag.id);
    byId('note').value = '';
    flagsCurrent = false;
    byId('status').textContent = 'Decision saved. Refreshing flags…';
    try {
      await fetchFlags();
      byId('status').textContent = `Decision saved. Flag is ${selectedFlag()?.status || 'no longer listed'}. Tested on sample data.`;
      document.dispatchEvent(new CustomEvent('decision-saved', { detail: { statementId, flagId: flag.id } }));
    } catch (error) {
      showError('error', `Your decision was saved, but flags could not be refreshed. ${error.message || ''} Select Refresh flags; do not submit the decision again.`);
      byId('status').textContent = 'Decision saved. Displayed flags need a refresh.';
    }
  } catch (error) {
    showError('decision-error', `${error.message || 'The decision could not be confirmed.'} Your note has been kept.`);
    byId('status').textContent = 'Decision could not be confirmed.';
    if (error.status === 409) {
      flagsCurrent = false;
      try { await fetchFlags(); }
      catch { showError('error', 'Could not refresh the already decided flag. Select Refresh flags to retry.'); }
    }
  } finally {
    busy = false;
    updateControls();
  }
}

setStatementContext(statementId);
byId('note').addEventListener('input', () => {
  if (selectedId) drafts.set(selectedId, byId('note').value);
  byId('note').removeAttribute('aria-invalid');
  showError('decision-error', '');
});
byId('refresh').addEventListener('click', refresh);
actions.forEach(button => button.addEventListener('click', () => decide(button.dataset.action)));


// Audit section — Task W. All audit UI, requests and notification behavior stay here.
const { getAudit } = await import('./api.js');
const auditPanel = byId('audit-section');
const auditHeading = element('h2', 'Audit trail & decision log');
auditHeading.id = 'audit-title';
auditPanel.setAttribute('aria-labelledby', auditHeading.id);
const auditStatus = element('p', 'Loading audit records…', 'audit-status');
auditStatus.id = 'audit-status';
auditStatus.setAttribute('role', 'status');
auditStatus.setAttribute('aria-live', 'polite');
const auditError = element('p', undefined, 'audit-error');
auditError.id = 'audit-error';
auditError.setAttribute('role', 'alert');
auditError.hidden = true;
const auditRetry = element('button', 'Refresh audit trail', 'secondary');
auditRetry.type = 'button';
const auditEmpty = element('p', 'No decisions have been recorded for this statement.', 'audit-empty');
auditEmpty.hidden = true;
const alertLine = element('p', undefined, 'alert-line');
alertLine.id = 'advisor-alert';
alertLine.setAttribute('role', 'status');
alertLine.hidden = true;
const auditTable = element('table', undefined, 'audit-table');
auditTable.id = 'audit-records';
auditTable.append(element('caption', 'Saved decisions · newest first'));
const auditHead = element('thead');
const auditHeader = element('tr');
const auditLabels = ['Time', 'Who', 'Action', 'Note'];
for (const label of auditLabels) {
  const cell = element('th', label);
  cell.scope = 'col';
  auditHeader.append(cell);
}
auditHead.append(auditHeader);
const auditBody = element('tbody');
auditTable.append(auditHead, auditBody);
auditTable.hidden = true;
auditPanel.append(auditHeading, alertLine, auditRetry, auditStatus, auditError, auditEmpty, auditTable);
auditPanel.hidden = false;
let auditRequest = 0;
const observedFlags = new Set();

async function refreshAudit() {
  // A later refresh wins if a decision arrives while an earlier request is in flight.
  const requestId = ++auditRequest;
  auditPanel.setAttribute('aria-busy', 'true');
  auditStatus.textContent = 'Loading audit records…';
  auditError.hidden = true;
  auditRetry.disabled = true;
  try {
    const records = await getAudit(statementId);
    if (requestId !== auditRequest) return;
    const newestFirst = [...records].reverse().sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
    auditBody.replaceChildren(...newestFirst.map(record => {
      const row = element('tr');
      row.dataset.auditId = record.id;
      row.dataset.flagId = record.flag_id;
      const timestamp = new Date(record.timestamp);
      const time = element('time', Number.isNaN(timestamp.getTime()) ? record.timestamp :
        new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeStyle: 'long', timeZone: 'UTC' }).format(timestamp));
      time.dateTime = record.timestamp;
      const values = [time, record.advisor, record.action, record.note || 'No note provided.'];
      values.forEach((value, index) => {
        const cell = element('td');
        cell.dataset.label = auditLabels[index];
        if (index === 0) cell.append(value);
        else cell.textContent = value;
        if (index === 2) cell.append(element('span', ` · Flag ${record.flag_id}`));
        row.append(cell);
      });
      return row;
    }));
    auditEmpty.hidden = records.length > 0;
    auditTable.hidden = records.length === 0;
    auditStatus.textContent = `${records.length} saved ${records.length === 1 ? 'decision' : 'decisions'}. Newest first. Tested on sample data.`;
  } catch (error) {
    if (requestId !== auditRequest) return;
    auditError.textContent = `Audit records could not be refreshed. ${error.message || ''} Select Refresh audit trail to retry. Any saved decisions are unchanged.`;
    auditError.hidden = false;
    auditStatus.textContent = 'Audit trail needs a refresh. Previously displayed records may be out of date.';
  } finally {
    if (requestId === auditRequest) {
      auditPanel.setAttribute('aria-busy', 'false');
      auditRetry.disabled = false;
    }
  }
}

document.addEventListener('flags-refreshed', event => {
  if (event.detail.statementId !== statementId) return;
  const newFlags = event.detail.flags.filter(flag => {
    const key = JSON.stringify([flag.id, flag.created_at]);
    const unseen = !observedFlags.has(key);
    observedFlags.add(key);
    return unseen && flag.status === 'open';
  });
  if (newFlags.length) {
    alertLine.textContent = `Alert sent to advisor · Simulated demo notification for ${newFlags.length} newly observed ${newFlags.length === 1 ? 'flag' : 'flags'}. Tested on sample data.`;
    alertLine.hidden = false;
  }
});
document.addEventListener('decision-saved', event => {
  if (event.detail.statementId === statementId) refreshAudit();
});
// Task V emits decision-saved only after its flag refresh succeeds. A saved-decision
// lock surviving the end of that operation identifies the successful save even
// when flag refresh fails, so audit refresh still runs without changing Task V.
new MutationObserver(() => {
  if (!busy && savedDecisions.size) refreshAudit();
}).observe(byId('workspace'), { attributes: true, attributeFilter: ['aria-busy'] });
auditRetry.addEventListener('click', refreshAudit);
byId('refresh').addEventListener('click', refreshAudit);
refreshAudit();
refresh();

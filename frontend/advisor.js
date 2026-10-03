import { getFlags, getStatement, decideFlag } from './api.js';

const byId = id => document.getElementById(id);
const statementId = 'problem';
const titles = {
  large_wire_new_payee: 'Large wire to a new payee',
  rapid_withdrawals: 'Rapid repeated withdrawals',
  fee_jump: 'Sudden fee change',
};
const outcomes = { approve: 'approved', escalate: 'escalated', dismiss: 'dismissed' };
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
let flags = [];
let statement;
let selectedId;
let saving = false;
let loading = false;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function title(flag) { return titles[flag.rule] || flag.rule.replaceAll('_', ' '); }
function flagAmount(flag) {
  if (flag.rule === 'fee_jump') return statement.fees.reduce((sum, fee) => sum + fee.amount, 0);
  return statement.transactions.filter(txn => flag.txn_ids.includes(txn.id)).reduce((sum, txn) => sum + txn.amount, 0);
}
function flagDate(flag) {
  const dates = statement.transactions.filter(txn => flag.txn_ids.includes(txn.id)).map(txn => txn.date).sort();
  return dates.length ? dates[0] : statement.period;
}
function statusText(flag) { return flag.status === 'open' ? 'Needs review · open' : `Status: ${flag.status}`; }
function renderFlagFacts(flag) {
  const facts = element('dl', undefined, 'detail-grid');
  function fact(label, value, className) {
    const group = element('div', undefined, className);
    group.append(element('dt', label), element('dd', value, label.includes('Amount') || label.includes('total') ? 'numeric' : undefined));
    facts.append(group);
  }
  const transactions = statement.transactions.filter(txn => flag.txn_ids.includes(txn.id));
  byId('callout-title').textContent = flag.rule === 'fee_jump' ? 'Fee comparison needed' : 'Transaction verification needed';
  if (flag.rule === 'fee_jump') {
    fact('Statement period', statement.period);
    fact('Current fee total', money(flagAmount(flag)));
    fact('Prior fee total', money(statement.prior_fee_total));
    fact('Fee descriptions', statement.fees.map(fee => fee.label).join(', '), 'wide');
  } else {
    fact('Transaction details', transactions.map(txn => `${txn.date} · ${txn.type}`).join('; '), 'wide');
    fact('Amount in review', money(flagAmount(flag)));
    fact('Account', [...new Set(transactions.map(txn => txn.account).filter(Boolean))].join(', ') || 'See statement');
    fact('Payee', [...new Set(transactions.map(txn => txn.payee).filter(Boolean))].join('; ') || 'Not listed', 'wide');
  }
  byId('flag-facts').replaceChildren(facts);
}
function selectedFlag() { return flags.find(flag => flag.id === selectedId); }
function clearDecisionError() {
  byId('decision-error').hidden = true;
  byId('decision-error').textContent = '';
  byId('note').setAttribute('aria-invalid', 'false');
}
function syncControls() {
  byId('refresh').disabled = loading || saving;
  byId('note').disabled = loading || saving || selectedFlag()?.status !== 'open';
  document.querySelectorAll('#decision-form button').forEach(button => {
    button.disabled = loading || saving || selectedFlag()?.status !== 'open';
  });
  document.querySelectorAll('.flag-choice').forEach(button => { button.disabled = loading || saving; });
  byId('decision-form').setAttribute('aria-busy', String(saving));
}
function renderFlags() {
  const list = flags.map(flag => {
    const item = element('li');
    const button = element('button', undefined, 'flag-choice');
    button.type = 'button';
    button.dataset.flagId = flag.id;
    button.setAttribute('aria-pressed', String(flag.id === selectedId));
    button.setAttribute('aria-controls', 'selection');
    const top = element('span', undefined, 'flag-top');
    top.append(element('span', title(flag), 'rule-chip'), element('span', flagDate(flag), 'flag-date'));
    const bottom = element('span', undefined, 'flag-bottom');
    const badge = element('span', statusText(flag), 'flag-status');
    badge.dataset.status = flag.status;
    bottom.append(element('span', money(flagAmount(flag)), 'flag-amount'), badge);
    button.append(top, element('span', flag.reason, 'flag-reason'), bottom);
    button.addEventListener('click', () => selectFlag(flag.id));
    item.append(button);
    return item;
  });
  byId('flags').replaceChildren(...list);
  updateFlagCount();
  byId('empty').hidden = flags.length > 0;
}
function updateFlagCount() {
  const reviewed = flags.filter(flag => flag.status !== 'open').length;
  const percentage = flags.length ? Math.round(reviewed / flags.length * 100) : 0;
  byId('flag-count').textContent = `${flags.length} total`;
  byId('review-progress').max = flags.length || 1;
  byId('review-progress').value = reviewed;
  byId('progress-count').textContent = `${reviewed} of ${flags.length} reviewed`;
  byId('progress-percent').textContent = `${percentage}% complete`;
}
function renderTable(caption, headings, rows) {
  const table = element('table');
  table.append(element('caption', caption));
  const head = element('thead');
  const header = element('tr');
  headings.forEach(text => {
    const cell = element('th', text);
    cell.scope = 'col';
    header.append(cell);
  });
  head.append(header);
  const body = element('tbody');
  rows.forEach(({ values, related, id }) => {
    const row = element('tr', undefined, related ? 'related' : undefined);
    if (id) row.dataset.txnId = id;
    values.forEach((text, index) => {
      const cell = element('td', text);
      cell.dataset.label = headings[index];
      if (related && index === 0) cell.append(element('span', 'Selected flag', 'related-label'));
      row.append(cell);
    });
    body.append(row);
  });
  table.append(head, body);
  return table;
}
function renderDetails() {
  const flag = selectedFlag();
  byId('selection').hidden = !flag;
  if (!flag) return;
  byId('rule-title').textContent = title(flag);
  renderFlagFacts(flag);
  byId('reason').textContent = flag.reason;
  byId('selected-status').textContent = statusText(flag);
  byId('selected-status').dataset.status = flag.status;
  byId('decision-status').textContent = flag.status === 'open' ? '' : `This flag is ${flag.status}. Its decision has been saved.`;
  const related = new Set(flag.txn_ids);
  byId('transaction-help').textContent = related.size
    ? `${related.size} transaction${related.size === 1 ? '' : 's'} linked to this flag. Highlighted rows are labeled Selected flag.`
    : 'This flag compares period fees; it is not linked to individual transactions. See the fee comparison below.';
  byId('transactions').replaceChildren(renderTable('Statement transactions', ['Date / account', 'Activity / payee', 'Amount'],
    statement.transactions.map(txn => ({ id: txn.id, related: related.has(txn.id), values: [
      `${txn.date}${txn.account ? ` / ${txn.account}` : ''}`,
      `${txn.type}${txn.payee ? ` · ${txn.payee}` : ''}`, money(txn.amount),
    ] }))));
  byId('fee-details').hidden = flag.rule !== 'fee_jump';
  byId('fee-details').replaceChildren();
  if (flag.rule === 'fee_jump') {
    byId('fee-details').append(renderTable('Fee comparison', ['Period / fee', 'Amount'], [
      { values: ['Prior period total', money(statement.prior_fee_total)] },
      ...statement.fees.map(fee => ({ values: [fee.label, money(fee.amount)], related: true })),
      { values: ['Current period total', money(statement.fees.reduce((sum, fee) => sum + fee.amount, 0))] },
    ]));
  }
}
function selectFlag(id) {
  if (saving || loading) return;
  if (selectedId !== id) {
    byId('note').value = '';
    clearDecisionError();
  }
  selectedId = id;
  document.querySelectorAll('.flag-choice').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.flagId === id));
  });
  renderDetails();
  syncControls();
}
async function loadReview() {
  if (saving || loading) return;
  loading = true;
  syncControls();
  byId('review').setAttribute('aria-busy', 'true');
  byId('error').hidden = true;
  byId('status').textContent = 'Loading sample flags and statement…';
  try {
    const [nextFlags, nextStatement] = await Promise.all([getFlags(statementId), getStatement(statementId)]);
    flags = nextFlags;
    statement = nextStatement;
    selectedId = flags.some(flag => flag.id === selectedId) ? selectedId : flags[0]?.id;
    byId('client-context').textContent = `${statement.client.name} (Age ${statement.client.age})`;
    byId('breadcrumb-client').textContent = statement.client.name;
    byId('account-context').textContent = statement.accounts.map(account => `${account.type} (${account.id})`).join(' · ');
    byId('period-context').textContent = statement.period;
    byId('note').value = '';
    clearDecisionError();
    renderFlags();
    renderDetails();
    byId('review').hidden = false;
    byId('status').textContent = 'Review ready. Tested on sample data.';
  } catch (error) {
    byId('review').hidden = true;
    byId('error').textContent = `${error.message || 'Review could not be loaded.'} Select Refresh review to retry.`;
    byId('error').hidden = false;
    byId('status').textContent = 'Review could not be loaded.';
  } finally {
    loading = false;
    byId('review').setAttribute('aria-busy', 'false');
    syncControls();
  }
}
byId('decision-form').addEventListener('submit', async event => {
  event.preventDefault();
  const flag = selectedFlag();
  const action = event.submitter?.value;
  if (saving || loading || !flag || flag.status !== 'open' || !Object.hasOwn(outcomes, action)) return;
  clearDecisionError();
  const note = byId('note').value.trim();
  if (action === 'escalate' && !note) {
    byId('decision-error').textContent = 'Add a review note before escalating this flag.';
    byId('decision-error').hidden = false;
    byId('note').setAttribute('aria-invalid', 'true');
    byId('note').focus();
    return;
  }
  saving = true;
  syncControls();
  byId('decision-status').textContent = 'Saving your decision…';
  let conflict = false;
  try {
    const record = await decideFlag(flag.id, action, note);
    flag.status = outcomes[action];
    // Update this row in place so the review list remains stable.
    const row = Array.from(document.querySelectorAll('.flag-choice')).find(button => button.dataset.flagId === flag.id);
    row.querySelector('.flag-status').textContent = statusText(flag);
    row.querySelector('.flag-status').dataset.status = flag.status;
    byId('selected-status').textContent = statusText(flag);
    byId('selected-status').dataset.status = flag.status;
    updateFlagCount();
    byId('decision-status').textContent = `Decision saved: ${flag.status}. Tested on sample data.`;
    // Task W can listen here to refresh the reserved audit section.
    document.dispatchEvent(new CustomEvent('advisor-decision-saved', { detail: record }));
  } catch (error) {
    conflict = error.status === 409;
    byId('decision-status').textContent = '';
    byId('decision-error').textContent = conflict
      ? 'This flag already has a saved decision. Refreshing the review.'
      : `${error.message || 'Your decision could not be saved.'} Your note is still here; please try again.`;
    byId('decision-error').hidden = false;
  } finally {
    saving = false;
    syncControls();
    if (conflict) await loadReview();
    else if (flag.status !== 'open') {
      Array.from(document.querySelectorAll('.flag-choice')).find(button => button.dataset.flagId === flag.id)?.focus();
    }
  }
});
byId('note').addEventListener('input', clearDecisionError);
byId('refresh').addEventListener('click', loadReview);
byId('contrast').addEventListener('click', () => {
  const enabled = document.body.classList.toggle('high-contrast');
  byId('contrast').setAttribute('aria-pressed', String(enabled));
  byId('contrast').textContent = enabled ? '◐ High contrast: On' : '◐ High contrast: Off';
});

let textSizeIndex = 0;
byId('text-size').addEventListener('click', () => {
  textSizeIndex = (textSizeIndex + 1) % 3;
  document.body.style.setProperty('--body-size', `${[22, 24, 26][textSizeIndex]}px`);
  byId('text-size').textContent = `Aa Text size: ${['A', 'A+', 'A++'][textSizeIndex]}`;
});

// Audit section — reserved for Task W.

loadReview();
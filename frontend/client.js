import { processStatement, getStatement, getSummary } from './api.js';

const byId = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
const controls = [byId('sample'), byId('upload')];

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function table(caption, headings, rows) {
  const result = element('table');
  result.append(element('caption', caption));
  const head = element('thead');
  const header = element('tr');
  for (const title of headings) {
    const cell = element('th', title);
    cell.scope = 'col';
    header.append(cell);
  }
  head.append(header);
  const body = element('tbody');
  for (const row of rows) {
    const tr = element('tr');
    row.forEach((value, index) => {
      const cell = element('td', value);
      cell.dataset.label = headings[index];
      tr.append(cell);
    });
    body.append(tr);
  }
  result.append(head, body);
  return result;
}

function renderStatement(statement) {
  const content = document.createDocumentFragment();
  content.append(element('h3', statement.client.name), element('p', `Statement period: ${statement.period}`, 'period'));
  content.append(table('Account values', ['Account', 'Start', 'End'], statement.accounts.map(account => [
    `${account.type} (${account.id})`, money(account.start_value), money(account.end_value),
  ])));
  content.append(table('Fees', ['Description', 'Amount'], statement.fees.map(fee => [fee.label, money(fee.amount)])));
  content.append(element('p', `Prior period fees: ${money(statement.prior_fee_total)}`, 'prior-fees'));
  content.append(table('Transactions', ['Date / account', 'Activity / payee', 'Amount'], statement.transactions.map(txn => [
    `${txn.date}${txn.account ? ` / ${txn.account}` : ''}`,
    `${txn.type}${txn.payee ? ` · ${txn.payee}` : ''}`,
    money(txn.amount),
  ])));
  byId('statement').replaceChildren(content);
}

function renderSummary(summary) {
  byId('summary').replaceChildren(...summary.text.split(/\n\s*\n/).map(text => element('p', text)));
  const validation = summary.validation;
  byId('validation').textContent = `Numbers checked: ${validation.figures_checked}, mismatches: ${validation.mismatches.length}`;
  byId('validation').classList.toggle('needs-review', validation.mismatches.length > 0);
  if (validation.mismatches.length) {
    byId('summary').replaceChildren(element('p', 'This summary needs a number check. Please refer to the original statement and ask your advisor to review it.'));
  }
}

async function load(input, process = true) {
  controls.forEach(control => { control.disabled = true; });
  byId('comparison').hidden = true;
  byId('comparison').setAttribute('aria-busy', 'true');
  byId('error').hidden = true;
  byId('status').textContent = 'Loading your sample statement and checking the summary…';
  try {
    const id = process ? (await processStatement(input)).statement_id : 'problem';
    const [statement, summary] = await Promise.all([getStatement(id), getSummary(id)]);
    renderStatement(statement);
    renderSummary(summary);
    byId('comparison').hidden = false;
    byId('status').textContent = `Ready: ${statement.client.name} · ${statement.period} · Tested on sample data.`;
  } catch (error) {
    byId('status').textContent = 'Statement could not be loaded.';
    byId('error').textContent = `${error.message || 'Please try again.'} Use Load sample to retry.`;
    byId('error').hidden = false;
  } finally {
    byId('comparison').setAttribute('aria-busy', 'false');
    controls.forEach(control => { control.disabled = false; });
    byId('upload').value = '';
  }
}

byId('sample').addEventListener('click', () => load('problem.pdf'));
byId('upload').addEventListener('change', event => {
  const file = event.target.files[0];
  if (file) load(file);
});
byId('contrast').addEventListener('click', () => {
  const enabled = document.body.classList.toggle('high-contrast');
  byId('contrast').setAttribute('aria-pressed', String(enabled));
});

// Audio section — reserved for Task U.

// Reading on initial load preserves any decisions already made in this tab.
load(null, false);

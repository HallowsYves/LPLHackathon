import { processStatement, getStatement, getSummary } from './api.js';

const byId = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
const controls = [byId('sample'), byId('upload')];
let statementReady = false;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function uiIcon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'ui-icon'); svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `icons.svg#${name}`); svg.append(use); return svg;
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
  const heading = element('div', undefined, 'statement-heading');
  heading.append(element('h3', statement.client.name), element('p', `Statement period: ${statement.period}`, 'period'));
  content.append(heading);
  const highlights = element('section', undefined, 'statement-highlights');
  highlights.append(element('h3', 'Statement figures'));
  const figures = element('dl');
  for (const [label, value] of [
    ['Total ending value', statement.accounts.reduce((sum, account) => sum + account.end_value, 0)],
    ['Fees this period', statement.fees.reduce((sum, fee) => sum + fee.amount, 0)],
    ['Prior period fees', statement.prior_fee_total],
  ]) {
    const row = element('div'); row.append(element('dt', label), element('dd', money(value))); figures.append(row);
  }
  highlights.append(figures); content.append(highlights);
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
  byId('summary').replaceChildren(...summary.text.split(/\n\s*\n/).map(text => {
    if (/^Questions to ask/i.test(text.trim())) {
      const questions = element('section', undefined, 'questions');
      questions.id = 'questions'; questions.tabIndex = -1;
      const lines = text.trim().split('\n');
      const heading = element('h3'); heading.append(uiIcon('questions'), document.createTextNode(lines[0]));
      const list = element('ol');
      lines.slice(1).filter(line => line.trim()).forEach(line => list.append(element('li', line.replace(/^\d+\.\s*/, ''))));
      questions.append(heading, list); return questions;
    }
    const paragraph = element('p');
    const body = element('span', undefined, 'summary-body');
    text.split(/(\$[\d,]+(?:\.\d{2})?)/).forEach(part => body.append(part.startsWith('$') ? element('strong', part) : document.createTextNode(part)));
    if (text.includes('$')) {
      paragraph.className = 'summary-card';
      const badge = element('span', undefined, 'icon-badge');
      badge.append(uiIcon(/fees/i.test(text) ? 'receipt' : 'bank')); paragraph.append(badge);
    }
    paragraph.append(body); return paragraph;
  }));
  const validation = summary.validation;
  byId('validation').textContent = `Numbers checked: ${validation.figures_checked}, mismatches: ${validation.mismatches.length}`;
  byId('validation').classList.toggle('needs-review', validation.mismatches.length > 0);
  if (validation.mismatches.length) {
    byId('summary').replaceChildren(element('p', 'This summary needs a number check. Please refer to the original statement and ask your advisor to review it.'));
  }
}

async function load(input, process = true) {
  controls.forEach(control => { control.disabled = true; });
  statementReady = false;
  byId('comparison').hidden = true;
  byId('comparison').setAttribute('aria-busy', 'true');
  byId('error').hidden = true;
  byId('status').textContent = 'Loading your sample statement and checking the summary…';
  try {
    const id = process ? (await processStatement(input)).statement_id : 'problem';
    const [statement, summary] = await Promise.all([getStatement(id), getSummary(id)]);
    renderStatement(statement);
    renderSummary(summary);
    statementReady = true;
    if (process) location.hash = 'summary';
    showRoute(location.hash === '#questions');
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
  byId('contrast').textContent = enabled ? '◐ High contrast: On' : '◐ High contrast: Off';
});

// Audio section — Task U. All audio UI and integration stay in this section.
const audioSection = byId('audio-section');
const readAloud = element('button', 'Read aloud');
readAloud.id = 'read-aloud';
readAloud.type = 'button';
readAloud.style.width = '100%';
readAloud.style.minHeight = '56px';
readAloud.setAttribute('aria-pressed', 'false');
readAloud.setAttribute('aria-describedby', 'audio-status audio-error');
const audioStatus = element('p', 'Audio will be available after the summary loads.');
audioStatus.id = 'audio-status';
audioStatus.setAttribute('role', 'status');
const audioError = element('p');
audioError.id = 'audio-error';
audioError.setAttribute('role', 'alert');
audioError.hidden = true;
audioSection.append(readAloud, audioStatus, audioError);

let summaryAudio = null;
let audioState = 'unavailable';
let audioTimer;

function setAudioState(state, message) {
  audioState = state;
  readAloud.disabled = state === 'unavailable' || state === 'loading';
  const audioLabel = ({ playing: 'Pause reading', paused: 'Resume reading',
    loading: 'Loading audio…', error: 'Retry read aloud' })[state] || 'Read aloud';
  readAloud.replaceChildren(uiIcon('volume'), document.createTextNode(audioLabel));
  readAloud.setAttribute('aria-pressed', String(state === 'playing'));
  readAloud.setAttribute('aria-busy', String(state === 'loading'));
  audioStatus.textContent = message;
  if (state !== 'loading') clearTimeout(audioTimer);
}

function resetAudio() {
  const previous = summaryAudio;
  summaryAudio = null; // Ignore late events and play promises from the old source.
  if (previous) {
    previous.pause();
    previous.removeAttribute('src');
    previous.load();
  }
  audioError.hidden = true;
  audioError.textContent = '';
  setAudioState('unavailable', 'Audio will be available after the summary loads.');
}

function configureAudio(summary) {
  resetAudio();
  if (summary.validation?.mismatches?.length) {
    setAudioState('unavailable', 'Read aloud is unavailable until the summary numbers are checked.');
    return;
  }
  if (typeof summary.audio_url !== 'string' || !summary.audio_url.trim()) {
    setAudioState('unavailable', 'No audio is available for this summary.');
    return;
  }
  const audio = document.createElement('audio');
  audio.preload = 'none';
  audio.src = summary.audio_url;
  summaryAudio = audio;
  const current = () => summaryAudio === audio;
  const fail = () => {
    if (!current() || audioState === 'error') return;
    setAudioState('error', 'Reading stopped.');
    audio.pause();
    audioError.textContent = 'We could not load or play the audio. Try Retry read aloud. If it still fails, use Load sample to refresh the audio link.';
    audioError.hidden = false;
  };
  audio.addEventListener('error', fail);
  audio.addEventListener('playing', () => {
    if (!current()) return;
    if (audioState === 'error') { audio.pause(); return; }
    setAudioState('playing', 'Reading your summary aloud.');
  });
  audio.addEventListener('pause', () => {
    if (current() && audioState === 'playing' && !audio.ended) setAudioState('paused', 'Reading paused. Select Resume reading to continue.');
  });
  audio.addEventListener('ended', () => {
    if (current()) setAudioState('ready', 'Reading finished. Select Read aloud to listen again.');
  });
  for (const event of ['waiting', 'stalled']) {
    audio.addEventListener(event, () => {
      if (current() && audioState === 'playing') {
        setAudioState('loading', 'Audio is buffering…');
        audioTimer = setTimeout(fail, 20000);
      }
    });
  }
  readAloud.onclick = async () => {
    if (!current()) return;
    if (audioState === 'playing') {
      audio.pause();
      return;
    }
    audioError.hidden = true;
    audioError.textContent = '';
    if (audioState === 'error') audio.load();
    if (audio.ended) audio.currentTime = 0;
    setAudioState('loading', 'Loading audio…');
    audioTimer = setTimeout(fail, 20000);
    try {
      await audio.play(); // Native button click supports Enter and Space, preserving user activation.
    } catch {
      fail();
    }
  };
  setAudioState('ready', 'Select Read aloud to hear your summary.');
}

// Hook Task T without changing its statement/summary rendering section.
const renderSummaryBeforeAudio = renderSummary;
renderSummary = summary => {
  renderSummaryBeforeAudio(summary);
  configureAudio(summary);
};
new MutationObserver(() => {
  if (byId('comparison').getAttribute('aria-busy') === 'true') resetAudio();
}).observe(byId('comparison'), { attributes: true, attributeFilter: ['aria-busy'] });
setAudioState('unavailable', audioStatus.textContent);

// Connected upload → summary → questions flow; browser Back follows the same routes.
function showRoute(focus = true) {
  const route = location.hash.slice(1);
  const showSummary = route === 'summary' || route === 'questions';
  byId('home-view').hidden = showSummary;
  byId('summary-view').hidden = !showSummary;
  byId('comparison').hidden = !showSummary || !statementReady;
  for (const [id, active] of [['summary-step', route === 'summary'], ['questions-step', route === 'questions']]) {
    if (active) byId(id).setAttribute('aria-current', 'step');
    else byId(id).removeAttribute('aria-current');
  }
  if (!showSummary && summaryAudio) {
    summaryAudio.pause();
    summaryAudio.currentTime = 0;
    if (audioState !== 'error') setAudioState('ready', 'Select Read aloud to hear your summary.');
  }
  if (focus) {
    const target = byId(showSummary ? (route === 'questions' ? 'questions' : 'summary-title') : 'home-title');
    if (target) { target.focus(); target.scrollIntoView({ block: 'start' }); }
  }
}
window.addEventListener('hashchange', () => showRoute());
window.addEventListener('pagehide', () => summaryAudio?.pause());
document.querySelector('.skip-link').addEventListener('click', event => {
  event.preventDefault();
  byId('main').tabIndex = -1;
  byId('main').focus();
  byId('main').scrollIntoView();
});
byId('print').addEventListener('click', () => window.print());
byId('explain-toggle').addEventListener('click', () => {
  const open = byId('explanation').hidden;
  byId('explanation').hidden = !open;
  byId('explain-toggle').setAttribute('aria-expanded', String(open));
});
let textSizeIndex = 0;
byId('text-size').addEventListener('click', () => {
  textSizeIndex = (textSizeIndex + 1) % 3;
  document.body.style.setProperty('--body-size', `${[22, 24, 26][textSizeIndex]}px`);
  byId('text-size').textContent = `Aa Text size: ${['A', 'A+', 'A++'][textSizeIndex]}`;
});
showRoute(false);

// Reading on initial load preserves any decisions already made in this tab.
load(null, false);

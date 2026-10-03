// Shared static-page navigation. Navigation never processes a statement.
export function setStatementContext(statementId) {
  for (const link of document.querySelectorAll('a[data-page]')) {
    link.href = `${link.dataset.page}?statement_id=${encodeURIComponent(statementId)}`;
  }
}
setStatementContext(new URLSearchParams(window.location.search).get('statement_id') || 'problem');
const contrast = document.getElementById('contrast');
contrast.addEventListener('click', () => {
  const enabled = document.body.classList.toggle('high-contrast');
  contrast.setAttribute('aria-pressed', String(enabled));
  contrast.textContent = `High contrast: ${enabled ? 'On' : 'Off'}`;
});

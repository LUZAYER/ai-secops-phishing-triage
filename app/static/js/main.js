// ── Auto-dismiss alerts ───────────────────────────
document.querySelectorAll('.alert-dismissible').forEach(el => {
  setTimeout(() => el.classList.add('fade'), 3000);
});

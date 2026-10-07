/* Navigation enhancement. Content, contact links and FAQ work without JS. */
const toggle = document.querySelector('.menu-toggle');
const mobileNav = document.getElementById('mobile-nav');
if (toggle && mobileNav) {
  function setOpen(open) {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? toggle.dataset.close : toggle.dataset.open);
    mobileNav.hidden = !open;
  }
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  mobileNav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setOpen(false)));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });
  window.matchMedia('(min-width: 961px)').addEventListener('change', event => {
    if (event.matches) setOpen(false);
  });
}

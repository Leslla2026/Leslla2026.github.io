document.addEventListener('DOMContentLoaded', function () {
  const dropdown = document.querySelector('.dropdown');
  if (!dropdown) return;

  const toggle = dropdown.querySelector('.dropdown-toggle');

  toggle.addEventListener('click', function (e) {
    e.stopPropagation();
    const isOpen = dropdown.classList.toggle('open');
    toggle.setAttribute('aria-expanded', isOpen);
  });

  document.addEventListener('click', function () {
    dropdown.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  });
});

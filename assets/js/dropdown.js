document.addEventListener('DOMContentLoaded', function () {

  document.querySelectorAll('.dropdown').forEach(dropdown => {
    const toggle = dropdown.querySelector('.dropdown-toggle');

    toggle.addEventListener('click', function (e) {
      e.stopPropagation();

      const isOpen = dropdown.classList.toggle('open');
      toggle.setAttribute('aria-expanded', isOpen);
    });
  });

  document.addEventListener('click', function () {
    document.querySelectorAll('.dropdown').forEach(dropdown => {
      dropdown.classList.remove('open');
      const toggle = dropdown.querySelector('.dropdown-toggle');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    });
  });

});

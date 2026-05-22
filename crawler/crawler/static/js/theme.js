(function () {
  var STORAGE_KEY = 'pacs-ris-theme';

  function storedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return null;
    }
  }

  function systemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  window.PacsTheme = {
    get: function () {
      return document.documentElement.getAttribute('data-theme') || 'light';
    },
    set: function (theme) {
      apply(theme);
      try {
        localStorage.setItem(STORAGE_KEY, theme);
      } catch (e) {}
      document.dispatchEvent(new CustomEvent('pacs-theme-change', { detail: { theme: theme } }));
      updateToggleButtons();
    },
    toggle: function () {
      this.set(this.get() === 'dark' ? 'light' : 'dark');
    }
  };

  function updateToggleButtons() {
    var dark = window.PacsTheme.get() === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      var icon = btn.querySelector('.theme-toggle-icon');
      if (icon) {
        icon.className = dark
          ? 'bi bi-sun theme-toggle-icon'
          : 'bi bi-moon-stars theme-toggle-icon';
      }
      btn.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      btn.setAttribute('title', dark ? 'Light mode' : 'Dark mode');
    });
  }

  apply(storedTheme() || systemTheme());

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        window.PacsTheme.toggle();
      });
    });
    updateToggleButtons();
  });
})();

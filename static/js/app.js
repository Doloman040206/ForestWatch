(function () {
  if (window.forestWatchAppInitialized) {
    return;
  }

  window.forestWatchAppInitialized = true;

  const SIDEBAR_SCROLL_KEY = "forestwatch-sidebar-scroll";

  function initializeRevealAnimations() {
    const items = document.querySelectorAll(".reveal:not(.revealed)");

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add("revealed");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.08 },
      );

      items.forEach(function (item) {
        observer.observe(item);
      });
    } else {
      items.forEach(function (item) {
        item.classList.add("revealed");
      });
    }
  }

  function saveSidebarScroll() {
    const sidebar = document.getElementById("app-sidebar");

    if (sidebar) {
      sessionStorage.setItem(SIDEBAR_SCROLL_KEY, String(sidebar.scrollTop));
    }
  }

  function restoreSidebarScroll() {
    const sidebar = document.getElementById("app-sidebar");
    const savedScroll = sessionStorage.getItem(SIDEBAR_SCROLL_KEY);

    if (sidebar && savedScroll !== null) {
      sidebar.scrollTop = Number(savedScroll);
    }

    sessionStorage.removeItem(SIDEBAR_SCROLL_KEY);
  }

  function initializePage() {
    initializeRevealAnimations();
  }

  document.addEventListener("DOMContentLoaded", function () {
    initializePage();
  });

  document.addEventListener("turbo:load", function () {
    initializePage();
    restoreSidebarScroll();
  });

  document.addEventListener("turbo:before-visit", function () {
    saveSidebarScroll();
  });

  document.addEventListener("submit", function (event) {
    const form = event.target;

    if (!(form instanceof HTMLFormElement)) {
      return;
    }

    if (form.classList.contains("search-form")) {
      return;
    }

    const button = form.querySelector(
      'button[type="submit"], button:not([type])',
    );

    if (button && !button.disabled) {
      button.dataset.originalText = button.innerHTML;
      button.disabled = true;
      button.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2"></span>Обробка...';
    }
  });
})();

/* a11y.js — accessibility helpers (European Accessibility Act / WCAG 2.2).
   • Makes the "Skip to content" link move keyboard focus into <main>.
   • Adds a polite live region so screen-reader users hear the deal count
     whenever the grid is filtered, searched or sorted.
   No dependencies, no inline code (CSP-safe). */
(function () {
  "use strict";

  // Skip link → focus main content (belt-and-braces for browsers that don't).
  var skip = document.querySelector(".skip-link");
  var main = document.getElementById("main");
  if (skip && main) {
    skip.addEventListener("click", function () {
      main.setAttribute("tabindex", "-1");
      main.focus();
    });
  }

  // Announce result counts to assistive tech.
  var count = document.getElementById("resultCount");
  if (count) {
    var live = document.createElement("p");
    live.className = "visually-hidden";
    live.setAttribute("aria-live", "polite");
    live.setAttribute("aria-atomic", "true");
    document.body.appendChild(live);

    var announce = function () {
      var n = (count.textContent || "").trim();
      if (n) live.textContent = n + " deal" + (n === "1" ? "" : "s") + " shown";
    };
    new MutationObserver(announce).observe(count, {
      childList: true, characterData: true, subtree: true
    });
  }
})();

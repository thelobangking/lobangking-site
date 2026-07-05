/* langgate-ui.js — the first-page language gate's interactive behaviour.
   When the visitor picks a language we (1) apply it via the on-device translator
   (js/translate.js), then (2) play an epic transition: the king crown charges up
   and DETONATES into a burst of gold shards that scatter into the background, a
   shockwave + flash ripple out, and the gate dissolves to reveal the hero.
   The whole burst is CSS-driven (see css/styles.css) — this file only toggles
   classes and builds the shard particles, so nothing violates the strict CSP.
   Honours prefers-reduced-motion by skipping straight to a gentle fade. */
(function () {
  "use strict";
  var gate = document.getElementById("langGate");
  if (!gate) return;
  var html = document.documentElement;

  // Build the shard particles once (trajectories are defined per-class in CSS).
  var burst = gate.querySelector(".lg-burst");
  var SHARDS = 24;
  if (burst && !burst.childNodes.length) {
    for (var i = 1; i <= SHARDS; i++) {
      var s = document.createElement("i");
      s.className = "shard shard--" + i;
      burst.appendChild(s);
    }
  }

  var reduce = false;
  try { reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}
  var done = false;

  function apply(lang) {
    try {
      if (typeof window.__lkSetLang === "function") window.__lkSetLang(lang);
      else {
        localStorage.setItem("lk-lang", lang);
        if (lang !== "en") html.setAttribute("lang", lang);
      }
    } catch (e) {}
  }

  function finish() {
    html.classList.add("lang-chosen");   // CSS keeps the gate hidden from now on
    gate.setAttribute("hidden", "");      // drop it from the a11y tree
    var h1 = document.querySelector(".hero__title");
    if (h1) { h1.setAttribute("tabindex", "-1"); try { h1.focus({ preventScroll: true }); } catch (e) {} }
  }

  function choose(lang) {
    if (done) return; done = true;
    apply(lang);
    html.classList.remove("lang-ask");

    if (reduce) {                          // reduced motion → gentle fade only
      gate.classList.add("is-done");
      window.setTimeout(finish, 380);
      return;
    }
    gate.classList.add("is-go");                                            // panel out, crown charges
    window.setTimeout(function () { gate.classList.add("is-boom"); }, 640); // detonate
    window.setTimeout(function () { gate.classList.add("is-done"); }, 1520);// dissolve to hero
    window.setTimeout(finish, 2180);
  }

  gate.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest(".lg-btn[data-lang]") : null;
    if (!btn) return;
    btn.classList.add("is-chosen");
    choose(btn.getAttribute("data-lang"));
  });

  // Keyboard shortcut: press 1–4 to pick a language.
  gate.addEventListener("keydown", function (ev) {
    var map = { "1": "en", "2": "zh", "3": "ms", "4": "ta" };
    var lang = map[ev.key];
    if (!lang) return;
    var b = gate.querySelector('.lg-btn[data-lang="' + lang + '"]');
    if (b) { b.classList.add("is-chosen"); choose(lang); }
  });
})();

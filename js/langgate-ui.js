/* langgate-ui.js — the first-page language gate's interactive behaviour.
   When the visitor picks a language we (1) apply it via the on-device
   translator (js/translate.js), then (2) play a royal welcome cinematic:
     go     → god-rays fan out, the King's crown rises with a glowing halo
              while charging rings implode, and a localized greeting shimmers in
     charge → the crown inhales and glows to near-white (anticipation)
     boom   → the crown DETONATES — flash + shockwaves + a burst of gold shards,
              brand confetti, twinkling sparks and light streaks scatter outward
     done   → the gate dissolves to reveal the hero
   Everything visual is CSS-driven (see css/styles.css) — this file only toggles
   classes, injects the greeting text and builds the particle elements, so
   nothing violates the strict CSP. Honours prefers-reduced-motion with a
   gentle fade instead of the spectacle. */
(function () {
  "use strict";
  var gate = document.getElementById("langGate");
  if (!gate) return;
  var html = document.documentElement;

  // Localized "Welcome to the Kingdom" greeting, keyed by the chosen language.
  var GREET = {
    en: ["Welcome", "to the Kingdom of Lobang"],
    zh: ["欢迎", "进入罗邦王国"],
    ms: ["Selamat Datang", "ke Kerajaan Lobang"],
    ta: ["வணக்கம்", "லோபாங் இராஜ்ஜியத்திற்கு"]
  };

  // Build the particle sets once. Each set lives in its own container so the
  // nth-child colour/shape rules in CSS apply cleanly. Trajectories are defined
  // per-index in CSS (.shard--N / .conf--N / .spark--N / .streak--N).
  function build(sel, base, n) {
    var box = gate.querySelector(sel);
    if (!box || box.childNodes.length) return;
    var frag = document.createDocumentFragment();
    for (var i = 1; i <= n; i++) {
      var el = document.createElement("i");
      el.className = base + " " + base + "--" + i;
      frag.appendChild(el);
    }
    box.appendChild(frag);
  }
  build(".lg-streaks", "streak", 10);
  build(".lg-burst", "shard", 30);
  build(".lg-confetti", "conf", 18);
  build(".lg-sparks", "spark", 14);

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

  function setWelcome(lang) {
    var g = GREET[lang] || GREET.en;
    var hi = gate.querySelector(".lg-welcome__hi");
    var sub = gate.querySelector(".lg-welcome__sub");
    if (hi) hi.textContent = g[0];
    if (sub) sub.textContent = g[1];
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
    setWelcome(lang);
    html.classList.remove("lang-ask");

    if (reduce) {                          // reduced motion → gentle fade only
      gate.classList.add("is-done");
      window.setTimeout(finish, 420);
      return;
    }
    gate.classList.add("is-go");                                              // panel out, crown rises, welcome in
    window.setTimeout(function () { gate.classList.add("is-charge"); }, 1000); // crown charges up
    window.setTimeout(function () { gate.classList.add("is-boom"); }, 1750);   // DETONATE
    window.setTimeout(function () { gate.classList.add("is-done"); }, 2500);   // dissolve to hero
    window.setTimeout(finish, 3050);
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

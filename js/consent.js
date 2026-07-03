/* consent.js — privacy-first consent notice (GDPR / Singapore PDPA).
   Honors the browser's Global Privacy Control and Do-Not-Track signals
   automatically (no banner shown if the visitor already opted out). Otherwise
   shows a lightweight one-time notice and remembers the choice locally — no
   cookies. Sets <html data-consent="granted|denied|unset"> so any analytics or
   marketing script can gate itself before running. CSP-safe: no inline code. */
(function () {
  "use strict";
  var KEY = "lk-consent";
  var root = document.documentElement;

  function apply(state) { root.setAttribute("data-consent", state); window.lkConsent = state; }
  function store(state) { try { localStorage.setItem(KEY, state); } catch (e) {} apply(state); }

  // 1. Respect an explicit browser privacy signal — treat as opt-out, no banner.
  var gpc = navigator.globalPrivacyControl === true;
  var dnt = navigator.doNotTrack === "1" || navigator.doNotTrack === "yes" || window.doNotTrack === "1";
  if (gpc || dnt) { apply("denied"); return; }

  // 2. Respect a previously saved choice.
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved === "granted" || saved === "denied") { apply(saved); return; }

  // 3. First visit → show the notice.
  apply("unset");
  function build() {
    var box = document.createElement("div");
    box.className = "consent";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-label", "Privacy notice");

    var p = document.createElement("p");
    p.className = "consent__text";
    p.appendChild(document.createTextNode(
      "We use privacy-first, anonymous analytics to improve LobangKing — no ads, no selling your data. "));
    var a = document.createElement("a");
    a.href = "privacy.html"; a.className = "consent__link"; a.textContent = "Learn more";
    p.appendChild(a);

    var actions = document.createElement("div");
    actions.className = "consent__actions";
    var decline = document.createElement("button");
    decline.type = "button"; decline.className = "btn btn--ghost"; decline.textContent = "Decline";
    var accept = document.createElement("button");
    accept.type = "button"; accept.className = "btn btn--gold"; accept.textContent = "Accept";
    decline.addEventListener("click", function () { store("denied"); box.remove(); });
    accept.addEventListener("click", function () { store("granted"); box.remove(); });
    actions.appendChild(decline); actions.appendChild(accept);

    box.appendChild(p); box.appendChild(actions);
    document.body.appendChild(box);
  }
  if (document.body) build();
  else document.addEventListener("DOMContentLoaded", build);
})();

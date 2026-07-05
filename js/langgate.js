/* langgate.js — first-page language gate boot (runs in <head>, before paint).
   Progressive enhancement: the gate is display:none by default in CSS, so with
   JavaScript disabled it never appears and the site loads normally in English.
   This tiny blocking script decides, before the first paint, whether to show it:
     • a language was already chosen  → mark <html class="lang-chosen"> (stay hidden)
     • first visit / no choice yet     → mark <html class="lang-ask">    (reveal gate)
   Keeping this in the <head> (like theme.js) avoids any flash of the hero before
   the gate covers it. The interactive behaviour lives in js/langgate-ui.js. */
(function () {
  "use strict";
  var el = document.documentElement, lang = null;
  try { lang = localStorage.getItem("lk-lang"); } catch (e) {}
  if (lang) {
    if (lang !== "en") el.setAttribute("lang", lang);
    el.classList.add("lang-chosen");
  } else {
    el.classList.add("lang-ask");
  }
})();

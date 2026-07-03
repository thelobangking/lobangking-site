/* On-device translation — Chrome built-in AI Translator (Gemini Nano, 2026).
   The model runs LOCALLY: no network request leaves the page, so it's private,
   free, and works under the strict 'self' Content-Security-Policy. Singapore is
   multilingual, so this opens the site to 中文 / Malay / Tamil readers instantly.
   Progressive enhancement: if the API isn't available, the switcher simply never
   appears and the site stays English-only. */
(function () {
  "use strict";
  if (!("Translator" in self)) return;          // unsupported browser → English only

  var LANGS = [["en", "EN"], ["zh", "中文"], ["ms", "Melayu"], ["ta", "தமிழ்"]];
  var SEL = ".hero__title,.hero__sub,.section__title,.page-hero__inner h1,.page-hero__inner p,"
          + ".deal-card__title,.deal-card__desc,.deal-card__store,.spotlight__title,.spotlight__desc,"
          + ".feature h3,.feature p,.subscribe h2,.subscribe p,.prose h2,.prose h3,.prose p,.preview-item";
  var KEY = "lk-lang";
  var translators = {};                          // targetLang -> Translator instance
  var current = "en";

  function nodes() { return Array.prototype.slice.call(document.querySelectorAll(SEL)); }

  function getTranslator(to) {
    if (translators[to]) return Promise.resolve(translators[to]);
    var opts = { sourceLanguage: "en", targetLanguage: to };
    var avail = (self.Translator.availability)
      ? self.Translator.availability(opts) : Promise.resolve("available");
    return Promise.resolve(avail).then(function (a) {
      if (a === "unavailable") return null;
      return self.Translator.create(opts).then(function (t) { translators[to] = t; return t; });
    }).catch(function () { return null; });
  }

  function apply(to) {
    var els = nodes();
    if (to === "en") {
      els.forEach(function (el) { if (el.dataset.en != null) el.textContent = el.dataset.en; });
      return Promise.resolve();
    }
    return getTranslator(to).then(function (tr) {
      if (!tr) { if (window.console) console.warn("Translator unavailable for", to); return; }
      // translate sequentially to keep it light on the device
      return els.reduce(function (p, el) {
        return p.then(function () {
          if (el.dataset.en == null) el.dataset.en = el.textContent;
          return Promise.resolve(tr.translate(el.dataset.en))
            .then(function (out) { el.textContent = out; }).catch(function () {});
        });
      }, Promise.resolve());
    });
  }

  // Let main.js re-apply the chosen language after it re-renders the deal grid.
  window.__lkRetranslate = function () { if (current !== "en") apply(current); };

  function inject() {
    var host = document.querySelector(".nav__actions");
    if (!host || document.getElementById("langSelect")) return;
    var sel = document.createElement("select");
    sel.id = "langSelect"; sel.className = "lang-select"; sel.setAttribute("aria-label", "Choose language");
    LANGS.forEach(function (l) {
      var o = document.createElement("option"); o.value = l[0]; o.textContent = l[1]; sel.appendChild(o);
    });
    try { current = localStorage.getItem(KEY) || "en"; } catch (e) {}
    sel.value = current;
    sel.addEventListener("change", function () {
      current = sel.value;
      try { localStorage.setItem(KEY, current); } catch (e) {}
      apply(current);
    });
    host.insertBefore(sel, host.firstChild);
    if (current !== "en") apply(current);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", inject);
  else inject();
})();

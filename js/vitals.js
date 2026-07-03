/* Core Web Vitals — Real User Monitoring (dependency-free, no external calls).
   Measures the Google ranking metrics LCP, CLS, INP and TTFB with the browser's
   PerformanceObserver, stores the latest snapshot in localStorage ('lk-vitals'),
   and prints a table to the console for the site owner. Because it never makes a
   network request, it works under the strict 'self'-only Content-Security-Policy.
   Good vitals = faster feel for users AND a real SEO ranking boost. */
(function () {
  "use strict";
  if (!("PerformanceObserver" in window)) return;
  if (document.documentElement.getAttribute("data-consent") === "denied") return;
  var v = {};
  function save() { try { localStorage.setItem("lk-vitals", JSON.stringify(v)); } catch (e) {} }
  function observe(type, cb, opts) {
    try { var o = new PerformanceObserver(cb); o.observe(Object.assign({ type: type, buffered: true }, opts || {})); return o; }
    catch (e) { return null; }
  }

  // Largest Contentful Paint — main content load speed
  observe("largest-contentful-paint", function (l) {
    var e = l.getEntries(); v.LCP = Math.round(e[e.length - 1].startTime); save();
  });

  // Cumulative Layout Shift — visual stability
  var cls = 0;
  observe("layout-shift", function (l) {
    l.getEntries().forEach(function (en) { if (!en.hadRecentInput) cls += en.value; });
    v.CLS = Math.round(cls * 1000) / 1000; save();
  });

  // Interaction to Next Paint — responsiveness (track worst interaction)
  var inp = 0;
  observe("event", function (l) {
    l.getEntries().forEach(function (en) { if (en.duration > inp) { inp = en.duration; v.INP = Math.round(inp); save(); } });
  }, { durationThreshold: 40 });

  // Time To First Byte — server/CDN responsiveness
  try {
    var nav = performance.getEntriesByType("navigation")[0];
    if (nav) { v.TTFB = Math.round(nav.responseStart); save(); }
  } catch (e) {}

  // Report once when the user leaves/hides the tab
  addEventListener("visibilitychange", function () {
    if (document.visibilityState === "hidden") {
      save();
      if (window.console && console.table) console.table(v);
    }
  }, { once: true });
})();

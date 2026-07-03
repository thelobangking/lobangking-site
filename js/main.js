/* =====================================================================
   LobangKing.sg — main.js
   Powers: theming, mobile nav, deal rendering from data/deals.json,
   live search, category filter, sort, voting, sharing, code copy,
   counters, streak, reveal-on-scroll, back-to-top, forms.
   All features are guarded so this one file is safe on every page.
   ===================================================================== */
(function () {
  "use strict";

  /* ---------------- helpers ---------------- */
  var $  = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  var store = {
    get: function (k, d) { try { var v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  };
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  // Allow only http(s), root-relative or anchor links — blocks javascript:/data: URLs
  // that could arrive in third-party feed data (defence-in-depth against XSS).
  function safeUrl(u) {
    u = String(u == null ? "#" : u).trim();
    if (u.charAt(0) === "#" || u.charAt(0) === "/") return u;
    return /^https?:\/\//i.test(u) ? u : "#";
  }

  /* ---------------- Trusted-Types-safe HTML sink ---------------- */
  // A single, audited place where HTML is assigned to the DOM. This makes the
  // code ready for CSP Trusted Types enforcement (require-trusted-types-for
  // 'script'), the strongest defence against DOM-based XSS. Harmless when the
  // browser/CSP doesn't enforce it. All our HTML strings are already escaped.
  var ttPolicy = (window.trustedTypes && window.trustedTypes.createPolicy)
    ? window.trustedTypes.createPolicy("lk-sanitizer", { createHTML: function (s) { return s; } })
    : null;
  function setHTML(el, html) { el.innerHTML = ttPolicy ? ttPolicy.createHTML(html) : html; }

  /* ---------------- toast ---------------- */
  var toastEl;
  function toast(msg) {
    if (!toastEl) { toastEl = document.createElement("div"); toastEl.className = "toast"; document.body.appendChild(toastEl); }
    toastEl.textContent = msg; toastEl.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(function () { toastEl.classList.remove("show"); }, 2600);
  }

  /* ---------------- theme ---------------- */
  var THEME_KEY = "lk-theme";
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", t === "dark" ? "#0c141d" : "#ffffff");
  }
  function initTheme() {
    var saved = store.get(THEME_KEY, null);
    var t = saved || (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    applyTheme(t);
    $$(".theme-toggle").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(next); store.set(THEME_KEY, next);
      });
    });
  }

  /* ---------------- mobile menu ---------------- */
  function initMenu() {
    var t = $(".menu-toggle"), m = $(".mobile-menu");
    if (!t || !m) return;
    t.addEventListener("click", function () {
      var open = m.classList.toggle("open");
      t.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  /* ---------------- date + streak ---------------- */
  function initDateStreak() {
    var d = $("#today");
    if (d) d.textContent = new Date().toLocaleDateString("en-SG", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

    var el = $("#streak");
    if (!el) return;
    var today = new Date().toDateString();
    var last = store.get("lk-last", null);
    var s = store.get("lk-streak", 0);
    if (last !== today) {
      var y = new Date(); y.setDate(y.getDate() - 1);
      s = last === y.toDateString() ? s + 1 : 1;
      store.set("lk-streak", s); store.set("lk-last", today);
    }
    if (s > 1) setHTML(el, '<span class="hero__eyebrow">🔥 ' + s + '-day streak — welcome back!</span>');
  }

  /* ---------------- view counter ---------------- */
  function initViews() {
    // The visitor number in the markup is a static placeholder. For real,
    // privacy-friendly counts, enable Cloudflare Web Analytics (free, server-side).
    // Making no third-party request here keeps the CSP locked to 'self'.
  }

  /* ---------------- deal rendering ---------------- */
  var DATA = { deals: [], categories: [] };
  var state = { category: "all", query: "", sort: "hot", page: 1 };
  var PAGE_SIZE = 12; // render in chunks so a big deal list never bogs the browser down

  function voteKey(id) { return "lk-vote-" + id; }
  function dealHeat(d) { return d.heat + (store.get(voteKey(d.id), false) ? 1 : 0); }

  function badgeHtml(b) { return '<span class="badge badge--' + esc(b.type) + '">' + esc(b.label) + "</span>"; }

  var CAT_ICON = { all: "i-all", food: "i-food", electronics: "i-electronics", home: "i-home", travel: "i-travel",
    transport: "i-transport", fashion: "i-fashion", entertainment: "i-fun", finance: "i-finance", online: "i-online" };
  function jic(name) { return '<svg class="ic" aria-hidden="true"><use href="#' + name + '"></use></svg>'; }
  function catLabel(id) { for (var i = 0; i < DATA.categories.length; i++) { if (DATA.categories[i].id === id) return DATA.categories[i].label; } return ""; }

  function dealCard(d) {
    var cat = (d.categories || ["online"])[0];
    var url = esc(safeUrl(d.url));
    var img = esc(d.image || "images/deal-fallback.jpg");
    var claimed = d.status === "claimed";
    var badges = d.badges || [], primary = null;
    for (var i = 0; i < badges.length; i++) { if (["free", "discount", "code"].indexOf(badges[i].type) > -1) { primary = badges[i]; break; } }
    var overlay = (primary && !claimed) ? '<span class="deal-badge deal-badge--' + esc(primary.type) + '">' + esc(primary.label) + "</span>" : "";
    var claim = claimed ? '<span class="deal-claimed">Fully claimed</span>' : "";
    var code = (d.code && !claimed) ? '<button class="code-pill" data-code="' + esc(d.code) + '" type="button">' + jic("i-tag") + esc(d.code) + "</button>" : "";
    var via = (d.source && d.source.url && d.source.url !== "#")
      ? ' · <a class="deal-card__via" href="' + esc(safeUrl(d.source.url)) + '" target="_blank" rel="noopener nofollow">via ' + esc(d.source.name || "source") + "</a>" : "";
    var cta = claimed ? '<span class="deal-card__cta is-disabled">Fully claimed</span>'
      : '<a class="deal-card__cta" href="' + url + '" rel="noopener">View deal ' + jic("i-arrow") + "</a>";
    return (
      '<article class="deal-card reveal' + (claimed ? " is-claimed" : "") + '" data-id="' + esc(d.id) + '" data-cats="' + esc((d.categories || []).join(",")) +
        '" data-title="' + esc(d.title) + '" data-store="' + esc(d.store) + '">' +
        '<a class="deal-card__media" href="' + url + '" rel="noopener" tabindex="-1" aria-hidden="true">' +
          '<img src="' + img + '" alt="" loading="lazy" decoding="async">' +
          '<span class="deal-card__cat">' + jic(CAT_ICON[cat] || "i-tag") + esc(catLabel(cat)) + "</span>" +
          overlay + claim +
        "</a>" +
        '<div class="deal-card__body">' +
          '<div class="deal-card__store">' + esc(d.store) + via + "</div>" +
          '<h3 class="deal-card__title"><a href="' + url + '" rel="noopener">' + esc(d.title) + "</a></h3>" +
          (d.desc ? '<p class="deal-card__take">' + esc(d.desc) + "</p>" : "") +
          code +
          '<div class="deal-card__foot"><span class="deal-card__time">' + jic("i-clock") + esc(d.expiry || "") + "</span>" + cta + "</div>" +
        "</div>" +
      "</article>"
    );
  }

  function spotlightCard(d) {
    var url = esc(safeUrl(d.url));
    var img = esc(d.image || "images/deal-fallback.jpg");
    var code = d.code ? '<button class="code-pill" data-code="' + esc(d.code) + '" type="button">' + jic("i-tag") + esc(d.code) + "</button>" : "";
    return (
      '<div class="spotlight-card reveal" data-id="' + esc(d.id) + '" data-cats="' + esc((d.categories || []).join(",")) +
        '" data-title="' + esc(d.title) + '" data-store="' + esc(d.store) + '">' +
        '<a class="spotlight__media" href="' + url + '" rel="noopener" tabindex="-1" aria-hidden="true"><img src="' + img + '" alt="" loading="lazy" decoding="async"></a>' +
        '<div class="spotlight__body">' +
          '<span class="spotlight__kicker">' + jic("i-bolt") + "Deal of the Week</span>" +
          '<div class="spotlight__store">' + esc(d.store) + "</div>" +
          '<h2 class="spotlight__title">' + esc(d.title) + "</h2>" +
          (d.desc ? '<p class="spotlight__desc">' + esc(d.desc) + "</p>" : "") +
          code +
          '<div class="spotlight__foot"><span class="deal-card__time">' + jic("i-clock") + esc(d.expiry || "") + "</span>" +
            '<a class="btn btn--gold btn--lg" href="' + url + '" rel="noopener">View this deal ' + jic("i-arrow") + "</a></div>" +
        "</div>" +
      "</div>"
    );
  }

  function filterSort(list) {
    var q = state.query.trim().toLowerCase();
    var out = list.filter(function (d) {
      var inCat = state.category === "all" || (d.categories || []).indexOf(state.category) > -1;
      var inQ = !q || (d.title + " " + d.store + " " + (d.desc || "")).toLowerCase().indexOf(q) > -1;
      return inCat && inQ;
    });
    if (state.sort === "hot") out.sort(function (a, b) { return dealHeat(b) - dealHeat(a); });
    else if (state.sort === "new") out.reverse();
    else if (state.sort === "ending") out.sort(function (a, b) {
      var ea = /today|tonight|hour/i.test(a.expiry || "") ? 0 : 1;
      var eb = /today|tonight|hour/i.test(b.expiry || "") ? 0 : 1;
      return ea - eb;
    });
    return out;
  }

  function render() {
    var grid = $("#dealGrid");
    if (grid) {
      var limit = parseInt(grid.getAttribute("data-limit") || "0", 10);
      var excludeSpot = grid.getAttribute("data-exclude-spotlight") === "true";
      var list = DATA.deals.slice();
      if (excludeSpot) list = list.filter(function (d) { return !d.spotlight; });
      list = filterSort(list);
      var total = list.length, shown;
      if (limit > 0) { list = list.slice(0, limit); shown = list.length; }
      else { shown = Math.min(state.page * PAGE_SIZE, total); list = list.slice(0, shown); }
      var countEl = $("#resultCount");
      if (countEl) countEl.textContent = total;
      setHTML(grid, list.length
        ? list.map(dealCard).join("")
        : '<div class="empty"><span class="ic">🔍</span>No deals match your search. Try another category or keyword.</div>');
      var lm = $("#loadMoreWrap");
      if (lm) setHTML(lm, (limit === 0 && shown < total)
        ? '<button class="btn btn--ghost btn--lg" id="loadMore" type="button">Load more deals (' + (total - shown) + ' more)</button>'
        : "");
    }
    // Spotlight visibility follows the active category filter
    var spot = $("#spotlight");
    if (spot) {
      var sd = DATA.deals.filter(function (d) { return d.spotlight; })[0] || DATA.deals[0];
      var show = sd && (state.category === "all" || (sd.categories || []).indexOf(state.category) > -1) &&
        (!state.query || (sd.title + " " + sd.store).toLowerCase().indexOf(state.query.toLowerCase()) > -1);
      spot.style.display = show ? "" : "none";
      if (show && spot.getAttribute("data-rendered") !== "1") { setHTML(spot, spotlightCard(sd)); spot.setAttribute("data-rendered", "1"); }
    }
    revealObserve();
    if (window.__lkRetranslate) window.__lkRetranslate();   // re-apply on-device translation to new cards
  }

  function renderCats() {
    var wrap = $("#catChips");
    if (!wrap) return;
    setHTML(wrap, DATA.categories.map(function (c) {
      return '<button class="cat-chip' + (c.id === state.category ? " is-active" : "") + '" data-cat="' + esc(c.id) +
        '" type="button">' + jic(CAT_ICON[c.id] || "i-tag") + " " + esc(c.label) + "</button>";
    }).join(""));
  }

  function setCategory(cat) {
    state.category = cat;
    state.page = 1;
    $$("#catChips .cat-chip").forEach(function (ch) { ch.classList.toggle("is-active", ch.getAttribute("data-cat") === cat); });
    render();
  }

  /* ---------------- interactions (event delegation) ---------------- */
  function pageUrl() { return window.location.href.split("#")[0]; }

  function doShare(platform, card) {
    var title = card.getAttribute("data-title") || "Great deal";
    var brand = card.getAttribute("data-store") || "";
    var url = pageUrl();
    var text = title + (brand ? " (" + brand + ")" : "") + " — found on LobangKing.sg 👑";
    if (platform === "copy") { navigator.clipboard && navigator.clipboard.writeText(url).then(function () { toast("✅ Link copied"); }); return; }
    var map = {
      whatsapp: "https://wa.me/?text=" + encodeURIComponent(text + "\n" + url),
      telegram: "https://t.me/share/url?url=" + encodeURIComponent(url) + "&text=" + encodeURIComponent(text),
      twitter:  "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text) + "&url=" + encodeURIComponent(url)
    };
    if (map[platform]) window.open(map[platform], "_blank", "noopener");
  }

  function initDelegation() {
    document.addEventListener("click", function (e) {
      // load more
      if (e.target.closest("#loadMore")) { state.page++; render(); return; }

      // category chip
      var chip = e.target.closest(".cat-chip");
      if (chip) { setCategory(chip.getAttribute("data-cat")); return; }

      // copy code
      var code = e.target.closest(".code-pill");
      if (code) {
        var c = code.getAttribute("data-code");
        if (navigator.clipboard) navigator.clipboard.writeText(c).then(function () { toast("✅ Code " + c + " copied"); });
        return;
      }

      // vote
      var vote = e.target.closest(".vote");
      if (vote) {
        var card = vote.closest("[data-id]"); var id = card.getAttribute("data-id");
        var key = voteKey(id); var was = store.get(key, false); store.set(key, !was);
        vote.classList.toggle("is-voted", !was); vote.setAttribute("aria-pressed", String(!was));
        var d = DATA.deals.filter(function (x) { return x.id === id; })[0];
        var n = d ? dealHeat(d) : 0;
        $$(".vc", vote).forEach(function (x) { x.textContent = n; });
        var heat = $(".heat", card); if (heat) heat.textContent = "🔥 " + n;
        toast(was ? "Removed your vote" : "🔥 Thanks for voting!");
        return;
      }

      // share button (use native share if available, else menu)
      var sb = e.target.closest(".btn-share");
      if (sb && !e.target.closest(".share-menu")) {
        var cardS = sb.closest("[data-id]");
        if (navigator.share) {
          navigator.share({ title: cardS.getAttribute("data-title"), text: cardS.getAttribute("data-title") + " — LobangKing.sg", url: pageUrl() }).catch(function () {});
        } else {
          var menu = $(".share-menu", sb);
          $$(".share-menu.open").forEach(function (m) { if (m !== menu) m.classList.remove("open"); });
          menu.classList.toggle("open");
        }
        return;
      }

      // share menu item
      var si = e.target.closest(".share-item");
      if (si) {
        doShare(si.getAttribute("data-share"), si.closest("[data-id]"));
        si.closest(".share-menu").classList.remove("open");
        return;
      }

      // click outside closes share menus
      if (!e.target.closest(".btn-share")) $$(".share-menu.open").forEach(function (m) { m.classList.remove("open"); });
    });
  }

  /* ---------------- search + sort ---------------- */
  function initControls() {
    var s = $("#searchInput");
    if (s) {
      var t;
      s.addEventListener("input", function () { clearTimeout(t); t = setTimeout(function () { state.query = s.value; state.page = 1; render(); }, 130); });
      s.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); state.query = s.value; state.page = 1; render(); } });
    }
    var sort = $("#sortSelect");
    if (sort) sort.addEventListener("change", function () { state.sort = sort.value; state.page = 1; render(); });
    // Search forms submit via JS (no inline handlers, so CSP can stay strict)
    $$("form.search").forEach(function (f) {
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        var inp = $("#searchInput");
        if (inp) { state.query = inp.value; state.page = 1; render(); }
      });
    });
  }

  /* ---------------- reveal on scroll ---------------- */
  var io;
  function revealObserve() {
    // Modern browsers animate reveals via pure CSS scroll timelines (better perf) — skip JS.
    if (window.CSS && CSS.supports && CSS.supports("animation-timeline: view()")) return;
    if (!("IntersectionObserver" in window)) { $$(".reveal").forEach(function (n) { n.classList.add("in"); }); return; }
    if (!io) io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
    $$(".reveal:not(.in)").forEach(function (n) { io.observe(n); });
  }

  /* ---------------- back to top ---------------- */
  function initBackToTop() {
    var b = $("#backToTop");
    if (!b) return;
    window.addEventListener("scroll", function () { b.classList.toggle("show", window.scrollY > 600); }, { passive: true });
    b.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  }

  /* ---------------- forms (static: graceful demo) ---------------- */
  function initForms() {
    var loadedAt = Date.now();
    $$("form.subscribe__form, form.form-card").forEach(function (f) {
      f.addEventListener("submit", function (e) {
        // Anti-bot: hidden honeypot + minimum fill time, silent to humans.
        var hp = f.querySelector(".hp");
        if (hp && hp.value) { e.preventDefault(); return; }          // bots fill hidden fields
        if (Date.now() - loadedAt < 1500) {                          // humans don't submit in <1.5s
          e.preventDefault();
          toast("Hmm, that was quick — please try again.");
          return;
        }
        // Until the owner sets a real Formspree ID, don't POST to a dead endpoint.
        if ((f.getAttribute("action") || "").indexOf("YOUR_FORM_ID") > -1) {
          e.preventDefault();
          toast("✅ Thanks! (Owner: connect this form — see README.)");
          f.reset();
        }
        // Otherwise the form POSTs natively to Formspree (which also filters spam).
      });
    });
  }

  /* ---------------- dynamic background parallax (smooth up/down) ---------------- */
  function initBg() {
    var img = $(".site-bg__img");
    if (!img) return;
    var ticking = false;
    function update() {
      var max = document.documentElement.scrollHeight - window.innerHeight;
      var p = max > 0 ? Math.min(1, window.scrollY / max) : 0;
      img.style.transform = "translate3d(0," + (p * -9) + "vh,0)";   // stays within the -14% overscan
      ticking = false;
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    window.addEventListener("resize", update, { passive: true });
    update();
  }

  /* ---------------- service worker (offline + speed) ---------------- */
  function initSW() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", function () {
      var url = "sw.js";
      // Trusted-Types-safe script URL (so TT enforcement won't block registration)
      if (window.trustedTypes && window.trustedTypes.createPolicy) {
        try { url = window.trustedTypes.createPolicy("lk-sw", { createScriptURL: function (s) { return s; } }).createScriptURL("sw.js"); }
        catch (e) {}
      }
      navigator.serviceWorker.register(url).catch(function () {});
    });
  }

  /* ---------------- bootstrap ---------------- */
  function applyUrlParams() {
    try {
      var p = new URLSearchParams(window.location.search);
      var cat = p.get("cat"); var q = p.get("q");
      if (cat) state.category = cat;
      if (q) { state.query = q; var s = $("#searchInput"); if (s) s.value = q; }
    } catch (e) {}
  }

  function loadDeals() {
    var needs = $("#dealGrid") || $("#spotlight") || $("#catChips");
    if (!needs) return;
    fetch("data/deals.json")
      .then(function (r) { return r.json(); })
      .then(function (j) {
        DATA.deals = j.deals || [];
        DATA.categories = j.categories || [];
        var dc = $("#dealTotal"); if (dc) dc.textContent = DATA.deals.length;
        applyUrlParams();
        renderCats(); render();
      })
      .catch(function () {
        var g = $("#dealGrid");
        if (g) setHTML(g, '<div class="empty"><span class="ic">📡</span>Deals are loading slowly. Please refresh the page.</div>');
      });
  }

  function init() {
    initTheme(); initMenu(); initDateStreak(); initViews();
    initDelegation(); initControls(); initBackToTop(); initForms(); initSW(); initBg();
    loadDeals(); revealObserve();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

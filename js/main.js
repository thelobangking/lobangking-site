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

  /* ---------------- daily check-in + lobang tiers ---------------- */
  // Return-visitor hook. Streak/tier state is 100% localStorage — no account,
  // no server, no tracking. Checking in is an explicit tap (once per day).
  var TIERS = [
    { min: 1,  emoji: "🥉", name: "Kaki" },
    { min: 3,  emoji: "🔥", name: "Regular" },
    { min: 7,  emoji: "🥇", name: "Lobang Hunter" },
    { min: 14, emoji: "💎", name: "Lobang Pro" },
    { min: 30, emoji: "👑", name: "Lobang King" }
  ];
  function dayStr(d) { return d.toDateString(); }
  function todayStr() { return dayStr(new Date()); }
  function yesterdayStr() { var y = new Date(); y.setDate(y.getDate() - 1); return dayStr(y); }

  // Celebratory confetti burst; silently skipped for reduced-motion users.
  function confetti(big) {
    if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var wrap = document.createElement("div"); wrap.className = "confetti";
    var EM = ["🎉", "👑", "🔥", "✨", "💎", "🥳"], n = big ? 26 : 14;
    for (var i = 0; i < n; i++) {
      var b = document.createElement("span"); b.className = "confetti-bit";
      b.textContent = EM[i % EM.length];
      b.style.setProperty("--x", Math.round(Math.random() * 100) + "%");
      b.style.setProperty("--r", Math.round(Math.random() * 720 - 360) + "deg");
      b.style.setProperty("--d", (i % 6) * 55 + "ms");
      wrap.appendChild(b);
    }
    document.body.appendChild(wrap);
    setTimeout(function () { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }, 1700);
  }

  function initCheckin() {
    var panel = $("#checkin");
    if (!panel) return;
    var elStreak = $("#ciStreak"), elTier = $("#ciTier"), elNext = $("#ciNext"), elBar = $("#ciBar"),
        elBtn = $("#ciBtn"), elBest = $("#ciBest"), elTotal = $("#ciTotal"), elTiers = $("#ciTiers"),
        elFlame = $("#ciFlame"), elLive = $("#ciLive"), heroEb = $("#streak");

    // Streak counts only if the last check-in was today or yesterday; a missed
    // day breaks it back to 0 until the next check-in restarts the count.
    function effectiveStreak() {
      var last = store.get("lk-last", null), s = store.get("lk-streak", 0);
      return (last === todayStr() || last === yesterdayStr()) ? s : 0;
    }
    function checkedToday() { return store.get("lk-last", null) === todayStr(); }
    function nextTier(s) { for (var i = 0; i < TIERS.length; i++) { if (s < TIERS[i].min) return TIERS[i]; } return null; }
    function currentTier(s) { var t = null; for (var i = 0; i < TIERS.length; i++) { if (s >= TIERS[i].min) t = TIERS[i]; } return t; }

    function paint() {
      var s = effectiveStreak(), best = store.get("lk-best", 0), total = store.get("lk-checkins", 0);
      var ct = currentTier(s), nt = nextTier(s);
      elStreak.textContent = s;
      elTier.textContent = ct ? (ct.emoji + " " + ct.name) : "✨ New here";
      elBest.textContent = best; elTotal.textContent = total;
      if (elFlame) elFlame.style.opacity = s >= 1 ? "1" : ".35";
      var prevMin = ct ? ct.min : 0;
      if (nt) {
        var need = nt.min - s;
        elNext.textContent = need + " more day" + (need === 1 ? "" : "s") + " to " + nt.emoji + " " + nt.name;
        var pct = Math.round(((s - prevMin) / (nt.min - prevMin)) * 100);
        elBar.style.width = Math.max(6, Math.min(100, pct)) + "%";
      } else {
        elNext.textContent = "👑 Top tier reached — you're a true Lobang King!";
        elBar.style.width = "100%";
      }
      if (checkedToday()) {
        elBtn.textContent = "✓ Checked in today"; elBtn.setAttribute("disabled", "disabled"); elBtn.classList.add("is-done");
      } else {
        elBtn.textContent = s >= 1 ? "Check in — keep it going!" : "Start your streak";
        elBtn.removeAttribute("disabled"); elBtn.classList.remove("is-done");
      }
      setHTML(elTiers, TIERS.map(function (t) {
        var on = best >= t.min || s >= t.min;
        return '<li class="tier-chip' + (on ? " is-on" : "") + '" title="' + esc(t.name + " · " + t.min + "-day streak") + '">' +
          '<span class="tier-chip__em" aria-hidden="true">' + t.emoji + "</span>" +
          '<span class="tier-chip__lbl">' + esc(t.name) + "</span>" +
          '<span class="tier-chip__req">' + t.min + "d</span></li>";
      }).join(""));
      if (heroEb) setHTML(heroEb, s > 1 ? '<span class="hero__eyebrow">🔥 ' + s + '-day check-in streak — welcome back!</span>' : "");
    }

    function doCheckin() {
      if (checkedToday()) return;
      var last = store.get("lk-last", null), s = store.get("lk-streak", 0);
      s = (last === yesterdayStr()) ? s + 1 : 1;
      var best = Math.max(store.get("lk-best", 0), s), total = store.get("lk-checkins", 0) + 1;
      store.set("lk-streak", s); store.set("lk-last", todayStr());
      store.set("lk-best", best); store.set("lk-checkins", total);
      var milestone = null;
      for (var i = 0; i < TIERS.length; i++) { if (s === TIERS[i].min) milestone = TIERS[i]; }
      paint();
      if (milestone) {
        toast("🎉 New tier unlocked — " + milestone.emoji + " " + milestone.name + "!"); confetti(true);
        if (elLive) elLive.textContent = "New tier unlocked: " + milestone.name + ". " + s + "-day streak.";
      } else {
        toast("🔥 Day " + s + " — checked in! See you tomorrow."); confetti(false);
        if (elLive) elLive.textContent = "Checked in. " + s + "-day streak.";
      }
      renderLobangOfDay();   // unwrap today's Lobang of the Day on check-in
    }

    elBtn.addEventListener("click", doCheckin);
    panel.hidden = false;
    paint();
  }

  /* ---------------- view counter ---------------- */
  function initViews() {
    // The visitor number in the markup is a static placeholder. For real,
    // privacy-friendly counts, enable Cloudflare Web Analytics (free, server-side).
    // Making no third-party request here keeps the CSP locked to 'self'.
  }

  /* ---------------- deal rendering ---------------- */
  var DATA = { deals: [], categories: [] };
  var state = { category: "all", query: "", sort: "new", page: 1 };
  var PAGE_SIZE = 12; // render in chunks so a big deal list never bogs the browser down

  function voteKey(id) { return "lk-vote-" + id; }
  function dealHeat(d) { return d.heat + (store.get(voteKey(d.id), false) ? 1 : 0); }

  function badgeHtml(b) { return '<span class="badge badge--' + esc(b.type) + '">' + esc(b.label) + "</span>"; }

  var CAT_ICON = { all: "i-all", food: "i-food", electronics: "i-electronics", home: "i-home", travel: "i-travel",
    transport: "i-transport", fashion: "i-fashion", entertainment: "i-fun", finance: "i-finance", online: "i-online" };
  function jic(name) { return '<svg class="ic" aria-hidden="true"><use href="#' + name + '"></use></svg>'; }
  function catLabel(id) { for (var i = 0; i < DATA.categories.length; i++) { if (DATA.categories[i].id === id) return DATA.categories[i].label; } return ""; }

  // Inline bookmark glyph (its own <path>, not the sprite) so the Chope save
  // button renders on every page — mirrors BOOKMARK_SVG in scripts/build_pages.py.
  var BOOKMARK = '<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z"></path></svg>';
  function chopeBtn() {
    return '<button class="deal-chope" type="button" data-chope aria-label="Save this lobang" ' +
      'aria-pressed="false" title="Chope (save) this lobang">' + BOOKMARK + "</button>";
  }
  // Expiry chip carrying a machine-readable end date; applyCountdowns() turns it
  // into a live countdown. Structure mirrors time_chip() in build_pages.py.
  function timeChip(d) {
    var ex = d.expires_at || "", label = d.expiry || "";
    return '<span class="deal-card__time" data-expires="' + esc(ex) + '" data-label="' + esc(label) + '">' +
      jic("i-clock") + '<span class="tc-text">' + esc(label) + "</span></span>";
  }

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
    // Compact "mini source link": the raw publisher name is no longer the visible
    // hyperlink — instead a small labelled Source chip carries the outbound link.
    var src = (d.source && d.source.url && d.source.url !== "#")
      ? ' · <a class="deal-card__src" href="' + esc(safeUrl(d.source.url)) + '" target="_blank" rel="noopener nofollow" title="Source: ' + esc(d.source.name || "source") + '">' + jic("i-arrow") + "Source</a>" : "";
    // Share button — hidden until the card is hovered or focused (see styles.css).
    var share = '<button class="deal-share" type="button" data-share-open aria-label="Share this lobang">' + jic("i-share") + "</button>";
    var chope = chopeBtn();   // always-visible save button
    var cta = claimed ? '<span class="deal-card__cta is-disabled">Fully claimed</span>'
      : '<a class="deal-card__cta" href="' + url + '" rel="noopener">View lobang ' + jic("i-arrow") + "</a>";
    return (
      '<article class="deal-card reveal' + (claimed ? " is-claimed" : "") + '" data-id="' + esc(d.id) + '" data-cats="' + esc((d.categories || []).join(",")) +
        '" data-title="' + esc(d.title) + '" data-store="' + esc(d.store) + '" data-url="' + url + '" data-img="' + img + '" data-expires="' + esc(d.expires_at || "") + '">' +
        '<a class="deal-card__media" href="' + url + '" rel="noopener" tabindex="-1" aria-hidden="true">' +
          '<img src="' + img + '" alt="" loading="lazy" decoding="async">' +
          '<span class="deal-card__cat">' + jic(CAT_ICON[cat] || "i-tag") + esc(catLabel(cat)) + "</span>" +
          overlay + claim +
        "</a>" + chope + share +
        '<div class="deal-card__body">' +
          '<div class="deal-card__store">' + esc(d.store) + src + "</div>" +
          '<h3 class="deal-card__title"><a href="' + url + '" rel="noopener">' + esc(d.title) + "</a></h3>" +
          (d.desc ? '<p class="deal-card__take">' + esc(d.desc) + "</p>" : "") +
          code +
          '<div class="deal-card__foot">' + timeChip(d) + cta + "</div>" +
        "</div>" +
      "</article>"
    );
  }

  function spotlightCard(d, noReveal) {
    var url = esc(safeUrl(d.url));
    var img = esc(d.image || "images/deal-fallback.jpg");
    var code = d.code ? '<button class="code-pill" data-code="' + esc(d.code) + '" type="button">' + jic("i-tag") + esc(d.code) + "</button>" : "";
    return (
      '<div class="spotlight-card' + (noReveal ? "" : " reveal") + '" data-id="' + esc(d.id) + '" data-cats="' + esc((d.categories || []).join(",")) +
        '" data-title="' + esc(d.title) + '" data-store="' + esc(d.store) + '" data-url="' + url + '" data-img="' + img + '" data-expires="' + esc(d.expires_at || "") + '">' +
        '<a class="spotlight__media" href="' + url + '" rel="noopener" tabindex="-1" aria-hidden="true"><img src="' + img + '" alt="" loading="lazy" decoding="async"></a>' +
        chopeBtn() +
        '<div class="spotlight__body">' +
          '<span class="spotlight__kicker">' + jic("i-bolt") + "Latest Lobang</span>" +
          '<div class="spotlight__store">' + esc(d.store) + "</div>" +
          '<h2 class="spotlight__title">' + esc(d.title) + "</h2>" +
          (d.desc ? '<p class="spotlight__desc">' + esc(d.desc) + "</p>" : "") +
          code +
          '<div class="spotlight__foot">' + timeChip(d) +
            '<a class="btn btn--gold btn--lg" href="' + url + '" rel="noopener">View this lobang ' + jic("i-arrow") + "</a></div>" +
        "</div>" +
      "</div>"
    );
  }

  // Build the "latest lobangs" carousel markup from the newest N deals.
  function spotlightCarousel(items) {
    var slides = items.map(function (d, i) {
      return '<li class="spot-slide" role="group" aria-roledescription="slide" aria-label="' +
        (i + 1) + " of " + items.length + '"' + (i === 0 ? "" : ' aria-hidden="true"') + ">" +
        spotlightCard(d, true) + "</li>";
    }).join("");
    var dots = items.map(function (d, i) {
      return '<button class="spot-dot' + (i === 0 ? " is-active" : "") + '" type="button" role="tab" ' +
        'aria-label="Show latest lobang ' + (i + 1) + '" aria-selected="' + (i === 0 ? "true" : "false") +
        '" data-i="' + i + '"></button>';
    }).join("");
    var controls = items.length > 1
      ? '<button class="spot-arrow spot-arrow--prev" type="button" aria-label="Previous lobang">' + jic("i-arrow") + "</button>" +
        '<button class="spot-arrow spot-arrow--next" type="button" aria-label="Next lobang">' + jic("i-arrow") + "</button>" +
        '<div class="spot-dots" role="tablist" aria-label="Choose a lobang">' + dots + "</div>"
      : "";
    return '<div class="spot-carousel" aria-roledescription="carousel" aria-label="Latest lobangs">' +
        '<div class="spot-viewport"><ul class="spot-track">' + slides + "</ul></div>" +
        controls + "</div>";
  }

  // Wire up sliding, dots, autoplay, swipe and keyboard for one carousel.
  function initCarousel(root) {
    if (!root) return;
    var track = root.querySelector(".spot-track");
    var slides = Array.prototype.slice.call(root.querySelectorAll(".spot-slide"));
    var dots = Array.prototype.slice.call(root.querySelectorAll(".spot-dot"));
    var n = slides.length, idx = 0, timer = null;
    if (n < 2) return;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function go(to) {
      idx = (to + n) % n;
      track.style.transform = "translateX(-" + (idx * 100) + "%)";
      for (var i = 0; i < n; i++) {
        slides[i].setAttribute("aria-hidden", i === idx ? "false" : "true");
        if (dots[i]) {
          dots[i].classList.toggle("is-active", i === idx);
          dots[i].setAttribute("aria-selected", i === idx ? "true" : "false");
        }
      }
    }
    function next() { go(idx + 1); }
    function prev() { go(idx - 1); }
    function start() { if (!reduce && !timer) timer = setInterval(next, 5000); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function bump() { stop(); start(); } // reset the clock after a manual move

    var pv = root.querySelector(".spot-arrow--next"); if (pv) pv.addEventListener("click", function () { next(); bump(); });
    var pp = root.querySelector(".spot-arrow--prev"); if (pp) pp.addEventListener("click", function () { prev(); bump(); });
    dots.forEach(function (dot) {
      dot.addEventListener("click", function () { go(parseInt(dot.getAttribute("data-i"), 10)); bump(); });
    });

    // Pause while hovered or keyboard-focused inside.
    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", start);
    root.addEventListener("focusin", stop);
    root.addEventListener("focusout", start);

    // Keyboard: left/right arrows when focus is inside the carousel.
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { prev(); bump(); e.preventDefault(); }
      else if (e.key === "ArrowRight") { next(); bump(); e.preventDefault(); }
    });

    // Touch swipe.
    var sx = 0, sy = 0, swiping = false;
    root.addEventListener("touchstart", function (e) {
      var t = e.changedTouches[0]; sx = t.clientX; sy = t.clientY; swiping = true; stop();
    }, { passive: true });
    root.addEventListener("touchend", function (e) {
      if (!swiping) return; swiping = false;
      var t = e.changedTouches[0], dx = t.clientX - sx, dy = t.clientY - sy;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { (dx < 0 ? next : prev)(); }
      bump();
    }, { passive: true });

    // Pause when the tab is hidden (saves battery, avoids jumps on return).
    document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });

    go(0); start();
  }

  function filterSort(list) {
    var q = state.query.trim().toLowerCase();
    var out = list.filter(function (d) {
      var inCat = state.category === "all" || (d.categories || []).indexOf(state.category) > -1;
      var inQ = !q || (d.title + " " + d.store + " " + (d.desc || "")).toLowerCase().indexOf(q) > -1;
      return inCat && inQ;
    });
    if (state.sort === "hot") out.sort(function (a, b) { return dealHeat(b) - dealHeat(a); });
    else if (state.sort === "new") out.sort(function (a, b) { var x = a.first_seen || "", y = b.first_seen || ""; return x < y ? 1 : x > y ? -1 : 0; });
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
        : '<div class="empty"><span class="ic">🔍</span>No lobangs match your search. Try another category or keyword.</div>');
      var lm = $("#loadMoreWrap");
      if (lm) setHTML(lm, (limit === 0 && shown < total)
        ? '<button class="btn btn--ghost btn--lg" id="loadMore" type="button">Load more lobangs (' + (total - shown) + ' more)</button>'
        : "");
    }
    // "Latest lobangs" carousel — a showcase of the newest deals. Shown only in
    // the default view (no category filter, no search); hidden while filtering.
    var spot = $("#spotlight");
    if (spot) {
      var show = state.category === "all" && !state.query.trim();
      spot.style.display = show ? "" : "none";
      if (show && spot.getAttribute("data-rendered") !== "1") {
        var latest = DATA.deals.slice().sort(function (a, b) {
          var x = a.first_seen || "", y = b.first_seen || ""; return x < y ? 1 : x > y ? -1 : 0;
        }).slice(0, 6);
        if (latest.length) {
          setHTML(spot, spotlightCarousel(latest));
          spot.setAttribute("data-rendered", "1");
          initCarousel(spot.querySelector(".spot-carousel"));
        }
      }
    }
    revealObserve();
    paintChopeButtons();      // reflect saved state on freshly-rendered cards
    applyCountdowns();        // turn time chips into live countdowns
    renderLobangOfDay();      // refresh the daily pick once deals are in
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

  /* ================================================================
     Chope This Lobang — save deals, browse them in a site-wide drawer.
     100% localStorage: no account, no server. A saved deal stores a small
     self-contained snapshot so the drawer works on every page, even ones
     that never fetch deals.json (per-deal SEO pages, 404, etc.).
     ================================================================ */
  var CHOPE_KEY = "lk-choped";
  function chopeGet() { var a = store.get(CHOPE_KEY, []); return Array.isArray(a) ? a : []; }
  function chopeSet(a) { store.set(CHOPE_KEY, a); updateChopeUI(); }
  function chopeHas(id) { var a = chopeGet(); for (var i = 0; i < a.length; i++) { if (a[i].id === id) return true; } return false; }
  function chopeCount() { return chopeGet().length; }

  // Build a saveable snapshot from a card element's data-* attributes. This is
  // why the drawer never needs the full deal list — everything it shows is here.
  function snapshotFromCard(card) {
    var timeEl = card.querySelector(".deal-card__time");
    var firstLink = card.querySelector("a[href]");
    return {
      id: card.getAttribute("data-id") || "",
      title: card.getAttribute("data-title") || "",
      store: card.getAttribute("data-store") || "",
      url: card.getAttribute("data-url") || (firstLink ? firstLink.getAttribute("href") : "#"),
      image: card.getAttribute("data-img") || "images/deal-fallback.jpg",
      expiry: timeEl ? (timeEl.getAttribute("data-label") || "") : "",
      expires_at: (timeEl ? timeEl.getAttribute("data-expires") || "" : "") || card.getAttribute("data-expires") || "",
      saved_at: todayStr()
    };
  }

  function toggleChope(card) {
    var id = card.getAttribute("data-id"); if (!id) return;
    var a = chopeGet(), i = -1, k;
    for (k = 0; k < a.length; k++) { if (a[k].id === id) { i = k; break; } }
    var nowSaved;
    if (i > -1) { a.splice(i, 1); nowSaved = false; }
    else { a.unshift(snapshotFromCard(card)); nowSaved = true; }
    chopeSet(a);
    toast(nowSaved ? "🔖 Choped! Saved to your list." : "Removed from your list");
    return nowSaved;
  }

  function removeChope(id) {
    var a = chopeGet().filter(function (x) { return x.id !== id; });
    chopeSet(a);
  }

  // Reflect saved state on every visible card + keep the floating button's count in sync.
  function paintChopeButtons() {
    $$("[data-chope]").forEach(function (btn) {
      var card = btn.closest("[data-id]"); if (!card) return;
      var on = chopeHas(card.getAttribute("data-id"));
      btn.classList.toggle("is-choped", on);
      btn.setAttribute("aria-pressed", String(on));
      btn.setAttribute("aria-label", on ? "Saved — tap to remove" : "Save this lobang");
    });
  }

  var chopeFab = null, chopeDrawer = null;
  function ensureChopeUI() {
    if (chopeFab) return;
    // Floating launcher
    chopeFab = document.createElement("button");
    chopeFab.className = "chope-fab";
    chopeFab.type = "button";
    chopeFab.setAttribute("aria-label", "Open your saved lobangs");
    setHTML(chopeFab, BOOKMARK + '<span class="chope-fab__lbl">Saved</span><span class="chope-fab__count" id="chopeCount">0</span>');
    chopeFab.addEventListener("click", openChopeDrawer);
    document.body.appendChild(chopeFab);
    // Drawer (built once, reused)
    chopeDrawer = document.createElement("div");
    chopeDrawer.className = "chope-drawer";
    setHTML(chopeDrawer,
      '<div class="chope-drawer__backdrop" data-chope-close></div>' +
      '<aside class="chope-drawer__panel" role="dialog" aria-modal="true" aria-labelledby="chopeTitle">' +
        '<div class="chope-drawer__head">' +
          '<h2 class="chope-drawer__title" id="chopeTitle">' + BOOKMARK + "Your choped lobangs</h2>" +
          '<button class="chope-drawer__x" type="button" aria-label="Close" data-chope-close>&times;</button>' +
        "</div>" +
        '<div class="chope-drawer__list" id="chopeList"></div>' +
        '<div class="chope-drawer__foot"><button class="btn chope-clear" type="button" id="chopeClear">Clear all</button></div>' +
      "</aside>");
    document.body.appendChild(chopeDrawer);
    chopeDrawer.addEventListener("click", function (e) {
      if (e.target.closest("[data-chope-close]")) { closeChopeDrawer(); return; }
      var rm = e.target.closest("[data-chope-remove]");
      if (rm) { removeChope(rm.getAttribute("data-chope-remove")); renderChopeList(); paintChopeButtons(); return; }
      var clr = e.target.closest("#chopeClear");
      if (clr) { chopeSet([]); renderChopeList(); paintChopeButtons(); toast("Cleared your saved lobangs"); return; }
    });
  }

  function renderChopeList() {
    var list = $("#chopeList"); if (!list) return;
    var a = chopeGet();
    if (!a.length) {
      setHTML(list, '<div class="chope-empty"><span class="chope-empty__em">🔖</span>' +
        "<p>No lobangs choped yet.</p><p>Tap the bookmark on any lobang to save it here for later.</p></div>");
      var clrBtn = $("#chopeClear"); if (clrBtn) clrBtn.style.display = "none";
      return;
    }
    var clrBtn2 = $("#chopeClear"); if (clrBtn2) clrBtn2.style.display = "";
    setHTML(list, a.map(function (d) {
      var u = esc(safeUrl(d.url));
      var timeTxt = countdownLabel(d.expires_at, d.expiry);
      return '<div class="chope-item" data-id="' + esc(d.id) + '">' +
        '<img class="chope-item__img" src="' + esc(d.image || "images/deal-fallback.jpg") + '" alt="" loading="lazy">' +
        '<div class="chope-item__body">' +
          '<div class="chope-item__store">' + esc(d.store || "") + "</div>" +
          '<div class="chope-item__title"><a href="' + u + '" rel="noopener">' + esc(d.title || "") + "</a></div>" +
          '<span class="chope-item__time' + timeTxt.cls + '">' + jic("i-clock") + esc(timeTxt.text) + "</span>" +
        "</div>" +
        '<button class="chope-item__rm" type="button" aria-label="Remove" data-chope-remove="' + esc(d.id) + '">&times;</button>' +
      "</div>";
    }).join(""));
  }

  function updateChopeUI() {
    ensureChopeUI();
    var n = chopeCount();
    var c = $("#chopeCount"); if (c) c.textContent = n;
    if (chopeFab) chopeFab.classList.toggle("show", n > 0);
    if (chopeDrawer && chopeDrawer.classList.contains("open")) renderChopeList();
  }

  function openChopeDrawer() {
    ensureChopeUI(); renderChopeList();
    chopeDrawer.classList.add("open");
    document.body.classList.add("chope-open");
    var x = chopeDrawer.querySelector(".chope-drawer__x"); if (x) x.focus();
  }
  function closeChopeDrawer() {
    if (!chopeDrawer) return;
    chopeDrawer.classList.remove("open");
    document.body.classList.remove("chope-open");
    if (chopeFab) chopeFab.focus();
  }

  function initChope() {
    ensureChopeUI();
    updateChopeUI();
    paintChopeButtons();
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && chopeDrawer && chopeDrawer.classList.contains("open")) closeChopeDrawer();
    });
  }

  /* ================================================================
     Live expiry countdowns — turn each time chip into a ticking count.
     Authoritative on the client (uses real "now"), so it's always correct
     even on a page cached/pre-rendered hours earlier.
     ================================================================ */
  var MS_DAY = 86400000;
  // Days until end-of-day on the expiry date (local). null if no/invalid date.
  function daysLeft(iso) {
    if (!iso) return null;
    var p = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso); if (!p) return null;
    var end = new Date(+p[1], +p[2] - 1, +p[3], 23, 59, 59, 999);
    var now = new Date();
    return Math.floor((end.getTime() - now.getTime()) / MS_DAY);
  }
  // Returns {text, cls} for a countdown. cls is a leading-space class suffix.
  function countdownLabel(iso, fallback) {
    var d = daysLeft(iso);
    if (d === null) return { text: fallback || "Ongoing", cls: "" };
    if (d < 0)   return { text: "Expired", cls: " is-expired" };
    if (d === 0) return { text: "Ends today", cls: " is-urgent" };
    if (d === 1) return { text: "1 day left", cls: " is-urgent" };
    if (d === 2) return { text: "2 days left", cls: " is-urgent" };
    if (d <= 6)  return { text: d + " days left", cls: " is-soon" };
    return { text: fallback || (d + " days left"), cls: "" };   // far off → keep the "Ends 31 Jul" label
  }
  function applyCountdowns() {
    $$(".deal-card__time[data-expires]").forEach(function (chip) {
      var r = countdownLabel(chip.getAttribute("data-expires"), chip.getAttribute("data-label"));
      chip.classList.remove("is-urgent", "is-soon", "is-expired");
      if (r.cls) chip.classList.add(r.cls.trim());
      var txt = chip.querySelector(".tc-text");
      if (txt) txt.textContent = r.text; else chip.appendChild(document.createTextNode(r.text));
    });
  }
  var _cdTimer = null;
  function startCountdownTicker() {
    if (_cdTimer) return;
    _cdTimer = setInterval(applyCountdowns, 60000);   // refresh every minute
    document.addEventListener("visibilitychange", function () { if (!document.hidden) applyCountdowns(); });
  }

  /* ================================================================
     Lobang of the Day — one deterministic daily pick, "unwrapped" by
     checking in. Same pick for everyone on a given day (date-seeded), so
     it feels like a shared daily ritual. Tied to the streak feature.
     ================================================================ */
  function dayHash(str) {   // small deterministic hash of the date string
    var h = 5381; for (var i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) & 0x7fffffff;
    return h;
  }
  function pickOfTheDay(deals) {
    if (!deals || !deals.length) return null;
    return deals[dayHash(todayStr()) % deals.length];
  }
  function lodRevealedToday() { return store.get("lk-last", null) === todayStr(); }

  function renderLobangOfDay() {
    var host = $("#lobangOfDay");
    if (!host || !DATA.deals.length) return;
    var d = pickOfTheDay(DATA.deals);
    if (!d) { host.hidden = true; return; }
    host.hidden = false;
    if (lodRevealedToday()) {
      var url = esc(safeUrl(d.url));
      var img = esc(d.image || "images/deal-fallback.jpg");
      var t = countdownLabel(d.expires_at, d.expiry);
      setHTML(host,
        '<div class="lod__inner">' +
          '<span class="lod__kicker">' + jic("i-bolt") + "Lobang of the Day</span>" +
          '<div class="lod__deal">' +
            '<div class="lod__media"><img src="' + img + '" alt="" loading="lazy" decoding="async"></div>' +
            '<div class="lod__deal-body">' +
              '<div class="lod__deal-store">' + esc(d.store || "") + "</div>" +
              '<h3 class="lod__deal-title"><a href="' + url + '" rel="noopener">' + esc(d.title || "") + "</a></h3>" +
              (d.desc ? '<p class="lod__deal-desc">' + esc(d.desc) + "</p>" : "") +
              '<div class="lod__deal-foot">' +
                '<span class="deal-card__time' + t.cls + '">' + jic("i-clock") + esc(t.text) + "</span>" +
                '<a class="btn btn--gold" href="' + url + '" rel="noopener">Grab it ' + jic("i-arrow") + "</a>" +
              "</div>" +
            "</div>" +
          "</div>" +
        "</div>");
    } else {
      setHTML(host,
        '<div class="lod__inner">' +
          '<span class="lod__kicker">' + jic("i-bolt") + "Lobang of the Day</span>" +
          '<div class="lod__wrap">' +
            '<div class="lod__gift" aria-hidden="true">🎁</div>' +
            '<div class="lod__wrap-info">' +
              '<h3 class="lod__wrap-title">Today’s pick is wrapped up</h3>' +
              '<p class="lod__wrap-sub">Check in above to unwrap today’s hand-picked lobang — a fresh one every day.</p>' +
              '<p class="lod__reveal-note">Same pick for everyone today. Come back tomorrow for a new one.</p>' +
            "</div>" +
          "</div>" +
        "</div>");
    }
    applyCountdowns();
  }

  /* ---------------- interactions (event delegation) ---------------- */
  function pageUrl() { return window.location.href.split("#")[0]; }

  /* ---------------- "Share this lobang" popup + success animation ---------------- */
  // One reusable modal for the whole page. A card's share button opens it,
  // populated with that lobang's title/store and its own deal-page link. Every
  // share target (WhatsApp / Facebook / Instagram / X / Message / copy) fires an
  // animated success confirmation. All CSP-safe: markup here, styling in CSS.
  var shareCtx = { title: "", store: "", url: "" };
  var shareModal = null;

  function shareText() {
    return shareCtx.title + (shareCtx.store ? " (" + shareCtx.store + ")" : "") + " — found on LobangKing.sg 👑";
  }
  function dealShareUrl(card) {
    // Prefer the lobang's own page (keeps sharers on LobangKing); fall back to this page.
    var id = card.getAttribute("data-id");
    if (id) { try { return new URL("deal-" + id + ".html", location.href).href; } catch (e) {} }
    return pageUrl();
  }

  function buildShareModal() {
    if (shareModal) return shareModal;
    var opts = [
      ["whatsapp",  "WhatsApp",  "wa",   "💬"],
      ["facebook",  "Facebook",  "fb",   "📘"],
      ["instagram", "Instagram", "ig",   "📸"],
      ["twitter",   "X",         "x",    "𝕏"],
      ["message",   "Message",   "msg",  "✉️"],
      ["copy",      "Copy link", "copy", "🔗"]
    ];
    var grid = opts.map(function (o) {
      return '<button class="share-opt share-opt--' + o[2] + '" type="button" data-share="' + o[0] + '">' +
        '<span class="share-opt__ic" aria-hidden="true">' + o[3] + "</span>" +
        '<span class="share-opt__lbl">' + o[1] + "</span></button>";
    }).join("");
    var m = document.createElement("div");
    m.className = "share-modal";
    m.id = "lkShareModal";
    m.setAttribute("role", "dialog");
    m.setAttribute("aria-modal", "true");
    m.setAttribute("aria-labelledby", "lkShareTitle");
    m.hidden = true;
    setHTML(m,
      '<div class="share-modal__backdrop" data-share-close></div>' +
      '<div class="share-modal__panel" role="document">' +
        '<button class="share-modal__x" type="button" aria-label="Close" data-share-close>&times;</button>' +
        '<h2 class="share-modal__title" id="lkShareTitle">Share this lobang</h2>' +
        '<p class="share-modal__deal" id="lkShareDeal"></p>' +
        '<div class="share-modal__grid">' + grid + "</div>" +
        '<div class="share-success" aria-hidden="true">' +
          '<svg class="share-success__check" viewBox="0 0 52 52" aria-hidden="true">' +
            '<circle class="ssc-ring" cx="26" cy="26" r="23" fill="none"/>' +
            '<path class="ssc-tick" fill="none" d="M15 27l7.5 7.5L37 19"/></svg>' +
          '<p class="share-success__msg">Lobang shared! 🎉</p>' +
        "</div>" +
      "</div>");
    document.body.appendChild(m);
    shareModal = m;
    return m;
  }

  function openShare(card) {
    shareCtx.title = card.getAttribute("data-title") || "Great lobang";
    shareCtx.store = card.getAttribute("data-store") || "";
    shareCtx.url = dealShareUrl(card);
    var m = buildShareModal();
    var dealEl = m.querySelector("#lkShareDeal");
    if (dealEl) dealEl.textContent = shareCtx.title + (shareCtx.store ? " · " + shareCtx.store : "");
    m.classList.remove("is-success");
    m.hidden = false;
    document.body.classList.add("share-open");
    m._opener = card.querySelector("[data-share-open]") || null;
    var first = m.querySelector(".share-opt");
    if (first) { try { first.focus(); } catch (e) {} }
  }
  function closeShare() {
    if (!shareModal || shareModal.hidden) return;
    clearTimeout(shareSuccess._t);
    shareModal.hidden = true;
    shareModal.classList.remove("is-success");
    document.body.classList.remove("share-open");
    var op = shareModal._opener;
    if (op && op.focus) { try { op.focus(); } catch (e) {} }
  }

  // Play the professional success animation, then auto-dismiss.
  function shareSuccess() {
    var m = shareModal;
    if (!m) return;
    m.classList.add("is-success");
    confetti(false);
    clearTimeout(shareSuccess._t);
    shareSuccess._t = setTimeout(closeShare, 1750);
  }

  function doShare(platform) {
    var url = shareCtx.url, text = shareText();
    // Instagram has no public web share intent — copy caption+link so it can be
    // pasted into a story or DM. "Copy link" copies just the link.
    if (platform === "instagram" || platform === "copy") {
      var payload = platform === "instagram" ? (text + " " + url) : url;
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(payload).catch(function () {});
      toast(platform === "instagram" ? "📸 Caption copied — paste into your Instagram story or DM" : "✅ Link copied");
      shareSuccess();
      return;
    }
    var map = {
      whatsapp: "https://wa.me/?text=" + encodeURIComponent(text + "\n" + url),
      facebook: "https://www.facebook.com/sharer/sharer.php?u=" + encodeURIComponent(url),
      twitter:  "https://twitter.com/intent/tweet?text=" + encodeURIComponent(text) + "&url=" + encodeURIComponent(url),
      message:  "sms:?&body=" + encodeURIComponent(text + " " + url)
    };
    if (map[platform]) window.open(map[platform], "_blank", "noopener");
    shareSuccess();
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

      // chope (save) button on a card
      var chopeB = e.target.closest("[data-chope]");
      if (chopeB) {
        e.preventDefault();
        var cardC = chopeB.closest("[data-id]");
        if (cardC) {
          var saved = toggleChope(cardC);
          chopeB.classList.toggle("is-choped", saved);
          chopeB.setAttribute("aria-pressed", String(saved));
          chopeB.setAttribute("aria-label", saved ? "Saved — tap to remove" : "Save this lobang");
          if (saved) { chopeB.classList.remove("just-choped"); void chopeB.offsetWidth; chopeB.classList.add("just-choped"); }
          paintChopeButtons();
        }
        return;
      }

      // open the "Share this lobang" popup from a card's hover share button
      var opener = e.target.closest("[data-share-open]");
      if (opener) {
        e.preventDefault();
        var cardS = opener.closest("[data-id]");
        if (cardS) openShare(cardS);
        return;
      }

      // a share target inside the popup (WhatsApp / Facebook / Instagram / X / Message / copy)
      var opt = e.target.closest(".share-opt");
      if (opt) { doShare(opt.getAttribute("data-share")); return; }

      // close controls (backdrop or ✕)
      if (e.target.closest("[data-share-close]")) { closeShare(); return; }
    });

    // Esc closes the share popup; Tab is kept inside it while open (focus trap).
    document.addEventListener("keydown", function (e) {
      if (!shareModal || shareModal.hidden) return;
      if (e.key === "Escape") { closeShare(); return; }
      if (e.key === "Tab") {
        var f = $$('.share-opt, .share-modal__x', shareModal);
        if (!f.length) return;
        var first = f[0], last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault(); }
        else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault(); }
      }
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
        if (g) setHTML(g, '<div class="empty"><span class="ic">📡</span>Lobangs are loading slowly. Please refresh the page.</div>');
      });
  }

  function init() {
    initTheme(); initMenu(); initCheckin(); initViews();
    initDelegation(); initControls(); initBackToTop(); initForms(); initSW(); initBg();
    initChope(); startCountdownTicker();
    loadDeals(); revealObserve();
    applyCountdowns();   // enhance any server-pre-rendered time chips before deals.json loads
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();

/* Engagement & retention helpers (dependency-free, no external calls).
   1) A tasteful "Add to home screen" prompt — installed users return far more often.
   2) A "deals refreshed since your last visit" badge — a reason to come back.
   Both are progressive: they no-op on browsers that don't support them. */
(function () {
  "use strict";

  /* ---- 1) PWA install prompt (recurring visits) ---- */
  var deferred = null;
  addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault(); deferred = e; showInstall();
  });
  function showInstall() {
    try { if (localStorage.getItem("lk-installed") === "1") return; } catch (e) {}
    if (document.getElementById("lkInstall")) return;
    var b = document.createElement("button");
    b.id = "lkInstall"; b.type = "button"; b.className = "lk-install";
    b.textContent = "⬇️ Add LobangKing to your home screen";
    b.addEventListener("click", function () {
      if (!deferred) { b.remove(); return; }
      deferred.prompt();
      deferred.userChoice.then(function (c) {
        if (c && c.outcome === "accepted") { try { localStorage.setItem("lk-installed", "1"); } catch (e) {} }
        b.remove();
      });
    });
    var close = document.createElement("span");
    close.className = "lk-install__x"; close.textContent = "✕"; close.setAttribute("aria-hidden", "true");
    close.addEventListener("click", function (e) { e.stopPropagation(); b.remove(); });
    b.appendChild(close);
    document.body.appendChild(b);
    setTimeout(function () { b.classList.add("show"); }, 1500);
  }
  addEventListener("appinstalled", function () {
    try { localStorage.setItem("lk-installed", "1"); } catch (e) {}
    var b = document.getElementById("lkInstall"); if (b) b.remove();
  });

  /* ---- 2) "New since your last visit" badge (return-visit hook) ---- */
  function newSince() {
    if (!document.getElementById("dealGrid")) return;
    fetch("data/deals.json").then(function (r) { return r.json(); }).then(function (d) {
      var last; try { last = localStorage.getItem("lk-seen"); } catch (e) {}
      var upd = d && d.updated;
      if (last && upd && last !== upd) {
        var n = (d.deals || []).length;
        var bar = document.createElement("div");
        bar.className = "lk-new";
        bar.textContent = "✨ Deals refreshed since your last visit — " + n + " live now";
        var host = document.querySelector(".cats .container") || document.querySelector("main");
        if (host) host.appendChild(bar);
      }
      if (upd) { try { localStorage.setItem("lk-seen", upd); } catch (e) {} }
    }).catch(function () {});
  }
  if ("requestIdleCallback" in window) requestIdleCallback(newSince);
  else addEventListener("load", function () { setTimeout(newSince, 800); });
})();

/* Content-protection deterrents (dependency-free, no external calls).
   HONEST NOTE: public web content can always be viewed/saved — this does NOT make
   the site un-copyable. It raises the effort for casual copycats and leaves a
   traceable fingerprint, without harming SEO, accessibility or performance
   (text stays selectable; only image drag/right-click is discouraged). */
(function () {
  "use strict";

  // 1) Console copyright notice — visible to anyone poking at the source.
  try {
    console.log("%c👑 LobangKing.sg", "color:#e5a429;font-weight:800;font-size:20px");
    console.log("%cContent © 2026 LobangKing.sg — rebuilt automatically every day. "
      + "Clones go stale within 24h. Copying our listings wholesale is prohibited (see /privacy.html).",
      "color:#9a6b0f;font-size:13px");
  } catch (e) {}

  // 2) Discourage casual image theft — block drag + right-click on IMAGES ONLY.
  //    (We deliberately do NOT block right-click or text selection on the page —
  //     that would hurt real users and accessibility for no real protection.)
  document.addEventListener("dragstart", function (e) {
    if (e.target && e.target.tagName === "IMG") e.preventDefault();
  });
  document.addEventListener("contextmenu", function (e) {
    if (e.target && e.target.tagName === "IMG") e.preventDefault();
  });

  // 3) Invisible canary — a unique marker that rides along with a verbatim copy,
  //    so a scraped clone is easy to prove. Hidden from users and screen readers.
  function canary() {
    if (document.querySelector('[data-lk-origin]')) return;
    var c = document.createElement("span");
    c.setAttribute("data-lk-origin", "lobangking.sg");
    c.setAttribute("aria-hidden", "true");
    c.style.cssText = "position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden";
    c.textContent = "Original content © LobangKing.sg";
    document.body.appendChild(c);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", canary);
  else canary();
})();

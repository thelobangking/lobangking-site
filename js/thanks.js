/* LobangKing.sg — thank-you page copy.
   Tailors the confirmation message to the flow the visitor came from.
   Formspree redirects here via the form's hidden _next field, e.g.
   /thank-you.html?type=lobang (submissions) or ?type=subscribe (signups).
   Progressive enhancement: the HTML already shows a friendly default,
   so the page still reads well if this script never runs. */
(function () {
  "use strict";
  var COPY = {
    lobang: {
      emoji: "👑",
      title: "Lobang received! 👑",
      sub: "Thanks for the tip — we'll check it out and crown the best ones on the site. Keep 'em coming!"
    },
    subscribe: {
      emoji: "🎉",
      title: "You're in! 🎉",
      sub: "Singapore's hottest lobangs are heading to your inbox. Watch out for a quick confirmation email to lock it in."
    }
  };

  var type;
  try { type = new URLSearchParams(window.location.search).get("type"); } catch (e) { type = null; }
  var c = type && COPY[type];
  if (!c) return; // unknown / missing type → keep the friendly default already in the HTML

  var emoji = document.getElementById("ty-emoji");
  var title = document.getElementById("ty-title");
  var sub = document.getElementById("ty-sub");
  if (emoji) emoji.textContent = c.emoji;
  if (title) title.textContent = c.title;
  if (sub) sub.textContent = c.sub;
  document.title = c.title.replace(/\s*[^\w\s].*$/, "").trim() + " — LobangKing.sg";
})();

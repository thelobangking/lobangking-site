/* Theme bootstrap — sets light/dark before paint to avoid a flash.
   Kept as a separate file so the site can use a strict Content-Security-Policy
   (no inline scripts). Loaded in <head> before the stylesheet. */
(function () {
  try {
    var t = localStorage.getItem('lk-theme');
    t = t ? JSON.parse(t) : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', t);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();

/* LobangKing.sg service worker
   Reliability + performance: serves the site instantly on repeat visits and
   keeps it working offline. Static assets are cache-first; the live deals file
   is network-first so deals stay fresh, falling back to cache when offline.
   Bump CACHE when you change site assets to push an update to visitors. */
const CACHE = 'lobangking-v13';
const CORE = [
  './', 'index.html', 'deals.html', 'about.html', 'submit.html', 'privacy.html', '404.html',
  'css/styles.min.css?v=9', 'js/main.js?v=9', 'js/theme.js?v=9', 'js/vitals.js?v=9', 'js/protect.js?v=9', 'js/engagement.js?v=9', 'js/translate.js?v=9', 'js/consent.js?v=9', 'js/a11y.js?v=9',
  'data/deals.json', 'manifest.webmanifest',
  'images/icon-192.png', 'images/logo.png', 'images/favicon-32.png', 'images/bg-hero.jpg', 'images/bg-hero-light.jpg', 'images/deal-fallback.jpg', 'images/hero-banner.jpg'
];

self.addEventListener('install', (e) => {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE).catch(() => {})));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // let fonts/counter go straight to network

  // Live deals: network-first (always try fresh), fall back to cache offline.
  if (url.pathname.endsWith('/data/deals.json') || url.pathname.endsWith('data/deals.json')) {
    e.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }

  // Everything else: cache-first, then network; offline navigations fall back to home.
  e.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).then((res) => {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
      return res;
    }).catch(() => (req.mode === 'navigate' ? caches.match('index.html') : undefined)))
  );
});

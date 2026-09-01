/* TIPLOOP 서비스 워커 — 설치 가능(PWA) + 정적 자산 캐시.
   서버 렌더링 앱이라 HTML/데이터는 항상 네트워크 우선(최신 유지),
   /static/* 만 캐시 우선으로 빠르게. */
const CACHE = "tiploop-v2";
const PRECACHE = [
  "/static/tipping.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

self.addEventListener("install", function (e) {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(PRECACHE).catch(function () {}); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.indexOf("/static/") === 0) {
    // 정적 자산: 캐시 우선, 없으면 네트워크 후 캐시.
    e.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
          return res;
        });
      })
    );
  } else {
    // HTML·데이터: 네트워크 우선, 오프라인이면 캐시 폴백.
    e.respondWith(fetch(req).catch(function () { return caches.match(req); }));
  }
});

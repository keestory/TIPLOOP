/* TIPLOOP 서비스 워커 — 설치 가능(PWA) + 정적 자산 캐시.
   서버 렌더링 앱이라 HTML/데이터는 항상 네트워크 우선(최신 유지),
   /static/* 는 네트워크를 우선해 새 배포를 즉시 반영하고, 오프라인일 때만 캐시를 사용한다. */
const CACHE = "tiploop-v5";
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
    // 정적 자산: 네트워크 우선, 성공 응답을 캐시하고 오프라인이면 캐시 폴백.
    e.respondWith(
      fetch(req).then(function (res) {
          if (!res.ok) return res;
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
          return res;
        }).catch(function () { return caches.match(req); })
    );
  } else {
    // HTML·데이터: 네트워크 우선, 오프라인이면 캐시 폴백.
    e.respondWith(fetch(req).catch(function () { return caches.match(req); }));
  }
});

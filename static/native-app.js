/* Capacitor 앱에서만 켜지는 작은 네이티브 UX 브릿지. 웹 동작은 바꾸지 않는다. */
(function () {
  "use strict";
  var cap = window.Capacitor;
  var isNative = !!(cap && cap.isNativePlatform && cap.isNativePlatform());
  var plugins = (cap && cap.Plugins) || {};
  var existing = window.tiploopNative || {};

  async function share(payload) {
    if (isNative && plugins.Share) return plugins.Share.share(payload);
    if (navigator.share) return navigator.share(payload);
    throw new Error("share_unavailable");
  }

  async function impact(style) {
    if (!isNative || !plugins.Haptics) return;
    try { await plugins.Haptics.impact({ style: style || "Light" }); } catch (error) {}
  }

  async function openBrowser(url) {
    if (isNative && plugins.Browser) return plugins.Browser.open({ url: url });
    window.open(url, "_blank", "noopener,noreferrer");
  }

  window.tiploopNative = Object.assign(existing, {
    isNative: isNative,
    share: share,
    impact: impact,
    openBrowser: openBrowser
  });

  if (!isNative) return;

  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest("a[href]");
    if (!link || link.hasAttribute("download")) return;
    var target;
    try { target = new URL(link.href, location.href); } catch (error) { return; }
    if (target.origin === location.origin && link.target !== "_blank") return;
    if (!/^https?:$/.test(target.protocol)) return;
    event.preventDefault();
    impact("Light");
    openBrowser(target.href);
  });

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (form && String(form.method || "").toLowerCase() === "post") impact("Light");
  });
})();

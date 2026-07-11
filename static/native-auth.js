/* Capacitor 셸(iOS/Android 앱) 전용 로그인 브릿지. 웹에서는 isNative=false로 아무 동작 없음.

   구글은 WebView 안 OAuth를 차단하므로(disallowed_useragent), 앱에서는:
   1) 로그인 페이지가 OAuth URL을 시스템 브라우저(SFSafariViewController)로 연다
   2) Supabase가 tipping://auth-callback#access_token=... 으로 앱을 다시 연다
   3) 여기(appUrlOpen)서 토큰을 꺼내 기존 POST /auth/session 으로 세션 쿠키를 만든다 */
(function () {
  "use strict";
  var cap = window.Capacitor;
  var isNative = !!(cap && cap.isNativePlatform && cap.isNativePlatform());

  window.tippingNative = {
    isNative: isNative,
    openBrowser: function (url) {
      if (cap && cap.Plugins && cap.Plugins.Browser) cap.Plugins.Browser.open({ url: url });
      else window.open(url, "_blank");
    }
  };

  if (!isNative || !cap.Plugins || !cap.Plugins.App) return;

  cap.Plugins.App.addListener("appUrlOpen", function (ev) {
    var url = (ev && ev.url) || "";
    if (url.indexOf("auth-callback") === -1) return;
    try { cap.Plugins.Browser.close(); } catch (e) { /* Browser.close는 iOS 전용 — 무시 */ }

    var frag = url.split("#")[1] || "";
    var token = new URLSearchParams(frag).get("access_token");
    if (!token) { alert("로그인 정보를 받지 못했습니다. 다시 시도해 주세요."); return; }

    var body = new URLSearchParams();
    body.set("access_token", token);
    fetch("/auth/session", { method: "POST", body: body })
      .then(function (res) { return res.ok ? res.json() : Promise.reject(new Error("session")); })
      .then(function (j) { window.location.replace(j.next || "/"); })
      .catch(function () { alert("세션 생성에 실패했습니다. 다시 시도해 주세요."); });
  });
})();

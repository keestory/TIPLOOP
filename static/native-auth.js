/* Capacitor 셸(iOS/Android 앱) 전용 OAuth 복귀 브릿지.

   appUrlOpen은 현재 화면과 무관하게 먼저 받을 수 있으므로 일회용 code가 든 콜백
   URL을 잠시 보관하고, 실제 PKCE 교환은 login.html의 같은 SDK 인스턴스가 맡는다. */
(function () {
  "use strict";
  var cap = window.Capacitor;
  var isNative = !!(cap && cap.isNativePlatform && cap.isNativePlatform());
  var pendingKey = "tiploop.pendingAuthUrl";

  function isAuthCallback(url) {
    var parsed;
    try { parsed = new URL(url); } catch (error) { return false; }
    return parsed.protocol === "tiploop:" && parsed.hostname === "auth-callback";
  }

  function rememberAuthCallback(url) {
    if (!isAuthCallback(url)) return false;
    try { sessionStorage.setItem(pendingKey, url); } catch (error) {}
    window.dispatchEvent(new CustomEvent("tiploop:auth-url", { detail: { url: url } }));
    if (location.pathname !== "/login") location.replace("/login");
    return true;
  }

  function consumePendingAuthUrl() {
    var url = "";
    try {
      url = sessionStorage.getItem(pendingKey) || "";
      sessionStorage.removeItem(pendingKey);
    } catch (error) {}
    return isAuthCallback(url) ? url : "";
  }

  function clearLocalAuthState(supabaseUrl) {
    var projectRef = "";
    try {
      var host = new URL(supabaseUrl).hostname;
      if (/\.supabase\.co$/i.test(host)) projectRef = host.split(".")[0];
    } catch (error) {}
    try {
      sessionStorage.removeItem(pendingKey);
      sessionStorage.removeItem("tiploop.authLaunchUrlChecked");
    } catch (error) {}
    if (!projectRef) return;
    try { localStorage.removeItem("sb-" + projectRef + "-auth-token"); } catch (error) {}
  }

  window.tiploopNative = Object.assign(window.tiploopNative || {}, {
    isNative: isNative,
    consumePendingAuthUrl: consumePendingAuthUrl,
    clearLocalAuthState: clearLocalAuthState,
    openBrowser: function (url) {
      if (cap && cap.Plugins && cap.Plugins.Browser) cap.Plugins.Browser.open({ url: url });
      else window.open(url, "_blank");
    }
  });

  if (!isNative || !cap.Plugins || !cap.Plugins.App) return;

  cap.Plugins.App.addListener("appUrlOpen", function (event) {
    rememberAuthCallback((event && event.url) || "");
  });
})();

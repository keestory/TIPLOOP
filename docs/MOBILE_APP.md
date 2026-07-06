# 모바일 앱 배포 가이드 (티핑)

티핑은 서버 렌더링 웹앱이다. 네이티브 앱으로 내보내는 방법은 두 갈래다.

---

## 1) PWA — 지금 바로, 무료 (이미 적용됨)

홈 화면에 설치되는 앱. **스토어 심사·비용 없음.** 코드에 이미 붙어 있다:
- `static/manifest.webmanifest` (이름·아이콘·standalone)
- `static/sw.js` + `/sw.js` 라우트(루트 스코프) — 설치 가능 + 정적 자산 캐시
- `static/icons/` (192·512·180) / head 메타(theme-color·apple-touch-icon)

### 사용자 설치법
- **Android (Chrome)**: 사이트 접속 → 주소창 "앱 설치" 배너 또는 ⋮ → "앱 설치"
- **iOS (Safari)**: 공유 버튼 → "홈 화면에 추가"
설치하면 전체화면·자체 아이콘으로 앱처럼 실행된다.

> PWA는 App Store/Play Store에는 안 올라간다(아래 2번 필요). 하지만 링크만 있으면
> 누구나 즉시 "설치"할 수 있어, 가장 빠른 배포 경로다.

---

## 2) 네이티브 앱 (App Store / Play Store) — Capacitor

웹앱을 네이티브 WebView로 감싸 스토어에 올린다. **이 작업은 당신 Mac에서** 해야 한다
(샌드박스에선 빌드·서명·제출 불가).

### 준비물 (비용 주의)
- **Mac + Xcode** (iOS 빌드는 Mac 필수)
- **Android Studio** (Android 빌드)
- **Apple Developer Program** — $99/년 (App Store 제출)
- **Google Play Console** — $25 1회 (Play Store 제출)
- Node.js 18+

### 셋업 (프로젝트 밖, 별도 폴더에서 권장)
```bash
# 새 폴더에서
npm create @capacitor/app   # 또는 아래처럼 수동
npm i @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android
npx cap init 티핑 im.tipping.app --web-dir=www
mkdir www && echo "<!doctype html>" > www/index.html   # 원격 URL을 쓸 거라 껍데기만
```

`capacitor.config.json` — **배포된 Vercel 앱을 그대로 로드**:
```json
{
  "appId": "im.tipping.app",
  "appName": "티핑",
  "webDir": "www",
  "server": { "url": "https://fortomorrow.vercel.app", "cleartext": false }
}
```

```bash
npx cap add ios
npx cap add android
npx cap sync
npx cap open ios       # Xcode 열림 → 서명(팀 선택) → 실기기/시뮬 실행 → Archive → App Store Connect
npx cap open android   # Android Studio 열림 → Build > Generate Signed Bundle(AAB) → Play Console 업로드
```

### 아이콘/스플래시
`static/icons/icon-512.png` 를 소스로 `@capacitor/assets` 로 생성:
```bash
npm i -D @capacitor/assets
npx capacitor-assets generate --iconBackgroundColor '#CDFF47' --splashBackgroundColor '#FCFBF8'
```

### 심사 주의 (특히 애플)
- 애플 가이드라인 4.2: "웹사이트를 그대로 감싼 앱"은 반려될 수 있다.
  티핑은 모바일 최적화 UX라 유리하지만, **네이티브 기능 한 가지 이상**(푸시 알림 등)을
  붙이면 통과율이 오른다. 필요 시 `@capacitor/push-notifications` 추가.
- OAuth 콜백: 앱에서 구글/카카오 로그인 시 리디렉트가 앱으로 돌아오도록
  Supabase Redirect URL에 앱 스킴/도메인 추가 필요할 수 있음.

---

## 3) Android만 빠르게 — TWA (Bubblewrap)

PWA를 그대로 Play Store 앱(AAB)으로 만드는 경량 방법(네이티브 코드 0):
```bash
npm i -g @bubblewrap/cli
bubblewrap init --manifest https://fortomorrow.vercel.app/static/manifest.webmanifest
bubblewrap build      # AAB 생성 → Play Console 업로드
```
(iOS는 TWA가 없어 Capacitor를 써야 한다.)

---

## 권장 순서
1. **지금**: PWA 링크 공유 → 사용자 즉시 설치 (0원, 0심사)
2. **Play Store**: Bubblewrap(TWA)로 빠르게 (또는 Capacitor)
3. **App Store**: Capacitor + Apple Developer + Xcode + 심사

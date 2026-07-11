# 티핑 iOS 앱 (Capacitor) — App Store 배포

배포된 웹앱(`https://fortomorrow.vercel.app`)을 네이티브 셸로 감싸 App Store에 올린다.
아래는 **당신 Mac에서** 실행하는 순서다. (샌드박스에선 빌드·서명·제출 불가)

## 0. 준비물
- **Apple Developer Program** 가입 ($99/년, 승인 1~2일) — 제일 먼저 신청
- **Xcode** (App Store에서 설치) + Command Line Tools
- **Node.js 18+**, CocoaPods (`sudo gem install cocoapods`)

## 1. Capacitor iOS 프로젝트 생성
```bash
cd FT/mobile
npm install
npx cap add ios          # ios/ 네이티브 프로젝트 생성
npx cap sync
```

## 2. 앱 아이콘/스플래시
```bash
npm i -D @capacitor/assets
# 리포의 브랜드 아이콘을 소스로 사용
cp ../static/icons/icon-512.png ./assets/icon.png   # 폴더 없으면 mkdir assets 먼저
npx capacitor-assets generate --ios \
  --iconBackgroundColor '#CDFF47' --splashBackgroundColor '#FCFBF8'
npx cap sync
```

## 3. Xcode에서 서명·실행
```bash
npx cap open ios
```
Xcode에서:
1. 좌측 **App** 타겟 → **Signing & Capabilities**
2. **Team** = 본인 Apple Developer 계정 선택 (자동 서명 체크)
3. **Bundle Identifier** = `com.keestory.tipping` (고유해야 함; 중복이면 바꾸기)
4. **Display Name** = 티핑, **Version** 1.0.0, **Build** 1
5. 상단에서 실기기/시뮬레이터 선택 → ▶ 실행해 동작 확인

## 4. 아카이브 → App Store 업로드
1. 상단 기기 선택을 **Any iOS Device**로
2. 메뉴 **Product → Archive**
3. Organizer 창 → **Distribute App → App Store Connect → Upload**
4. [appstoreconnect.apple.com](https://appstoreconnect.apple.com) → **앱 생성**(같은 Bundle ID)
   → 이름·설명·스크린샷·개인정보 처리방침 URL·연령등급 입력 → **심사 제출**
   (먼저 **TestFlight**로 본인 폰에서 테스트 후 제출 추천)

---

## ⚠️ 미리 알아둘 두 가지 (중요)

### (a) 애플 심사 4.2 — "웹사이트 래퍼" 반려 위험
티핑은 모바일 최적화가 잘 돼 있어 유리하지만, 안전하게 통과하려면
**네이티브 기능 1개**를 붙이는 걸 권장한다 → **푸시 알림**(`@capacitor/push-notifications`).
첫 제출은 그대로 넣어보고, 4.2로 반려되면 그때 푸시를 추가해도 된다.

### (b) 구글 로그인이 WebView에서 막힘 — ✅ 해결됨 (설정 2가지만 하면 됨)
구글은 임베디드 WebView 안 OAuth를 차단한다(`disallowed_useragent`).
웹 코드에 앱 분기가 이미 들어가 있다: 앱에서는 로그인만 **시스템 브라우저**
(SFSafariViewController)로 열고, `tipping://auth-callback` 딥링크로 토큰을
받아 세션을 만든다. (`templates/login.html` + `static/native-auth.js`)

**당신이 할 설정 2가지:**

1. **iOS URL 스킴 등록** — Xcode에서 App 타겟 → **Info → URL Types → +**
   - URL Schemes: `tipping`  (Identifier는 `com.keestory.tipping` 등 아무거나)
   - 또는 `ios/App/App/Info.plist`에 직접:
   ```xml
   <key>CFBundleURLTypes</key>
   <array><dict>
     <key>CFBundleURLSchemes</key><array><string>tipping</string></array>
   </dict></array>
   ```

2. **Supabase Redirect URL 추가** — 대시보드 → Authentication → URL Configuration
   → Redirect URLs에 추가:
   ```
   tipping://auth-callback
   ```

플러그인(`@capacitor/app`, `@capacitor/browser`)은 package.json에 포함돼 있어
`npm install && npx cap sync` 하면 적용된다.

---

## 이후 업데이트
웹앱(Vercel)만 배포하면 앱은 그 URL을 로드하므로 **대부분의 변경은 앱 재제출 없이 반영**된다.
네이티브 설정(아이콘·권한·플러그인)이 바뀔 때만 `npx cap sync` 후 재아카이브·재제출.

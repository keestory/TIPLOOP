# TIPLOOP 모바일 앱 배포 가이드

## 제공 방식

- PWA: Safari·Chrome에서 홈 화면에 추가
- iOS: `mobile/ios/App/App.xcworkspace`의 Capacitor 앱
- Android: 이번 App Store 출시 범위에서 제외

## iOS 출시 기준

| 항목 | 값 |
|---|---|
| 앱 이름 | TIPLOOP |
| Bundle ID | `com.keestory.tiploop` |
| 버전 | 1.0.0 (빌드 1) |
| 기기 | iPhone 전용 |
| 방향 | 세로 |
| 배포 URL | `https://tiploop.vercel.app` |
| 지원 URL | `https://tiploop.vercel.app/support` |
| 개인정보 처리방침 | `https://tiploop.vercel.app/terms/privacy` |

## 심사 필수 흐름

- 로그인 화면에서 Google·Kakao와 동등한 Apple 로그인 제공
- 계정 화면에서 계정과 저장 데이터 삭제 시작·완료
- 심사 계정 또는 완전한 데모 접근 제공
- App Privacy에 계정 정보, 사용자 ID, 사진·영상, 기타 사용자 콘텐츠 신고
- 심사 노트에 네이티브 공유·햅틱·시스템 브라우저 연동과 서비스 분석 전용 UX 설명

## 빌드 검증

```bash
cd mobile
npm ci
npm run sync
xcodebuild \
  -workspace ios/App/App.xcworkspace \
  -scheme App \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/tiploop-derived \
  CODE_SIGNING_ALLOWED=NO build
```

서명 전 빌드가 성공한 뒤 Xcode에서 올바른 Apple Developer Team을 선택하고
`Any iOS Device` 대상으로 Archive한다. 업로드한 빌드는 TestFlight에서 로그인,
노트 작성·첨부·공유·삭제를 실제 기기로 확인한 다음 심사에 제출한다.

## OAuth 콜백

앱은 로그인 URL을 시스템 브라우저로 열고 `tiploop://auth-callback`으로 돌아온다.
같은 값을 iOS URL Types와 Supabase Redirect URLs 양쪽에 등록해야 한다.

## 원격 화면 운영 주의

현재 네이티브 앱은 서버 렌더링 웹 화면을 원격으로 불러온다. 심사 중 운영 화면을
크게 바꾸지 않고, 서버 장애 시 최소한 이해 가능한 오류 안내를 제공해야 한다.
단순 웹사이트 래퍼로 보이지 않도록 네이티브 공유·햅틱·시스템 브라우저 연결을
유지하고 앱 전용 가치와 테스트 경로를 심사 노트에 적는다.

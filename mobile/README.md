# TIPLOOP iOS 앱

배포된 TIPLOOP(`https://tiploop.vercel.app`)을 Capacitor 기반 iPhone 앱으로 제공한다.

## 현재 값

- 앱 이름: `TIPLOOP`
- Bundle ID: `com.keestory.tipping` (기존 App Store Connect 앱 6790769878)
- 버전 / 빌드: `1.0.0` / `1`
- 대상: iPhone, 세로 화면
- 최소 iOS: 14.0
- 개인정보 처리방침: `https://tiploop.vercel.app/terms/privacy`
- 지원 URL: `https://tiploop.vercel.app/support`

## 동기화와 빌드

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

`npm run sync` 마지막에 실행되는 Xcode clean이 로컬 권한 때문에 실패하더라도,
웹 자산 복사와 Pod 설치가 완료됐는지 확인한 뒤 위 빌드를 별도로 실행한다.

## 제출 전 외부 설정

1. Apple Developer에서 기존 `com.keestory.tipping` App ID의 설정 확인
2. Sign in with Apple capability와 `App.entitlements` 서명 연결 확인
3. App Store Connect에 한국어 기본 앱 레코드 생성
4. Supabase Authentication에서 Apple provider 설정
5. Supabase Redirect URLs에 `tiploop://auth-callback` 추가
6. Vercel에 Apple client ID·client secret·토큰 암호화 키를 비공개 환경 변수로 설정
7. Apple 로그인·탈퇴 연결 해제를 실제 계정으로 검증한 뒤 `APPLE_AUTH_ENABLED=1` 설정
8. 법적 운영자명과 지원 이메일 설정
9. Xcode Signing & Capabilities에서 올바른 Team 선택
10. Archive 업로드 후 TestFlight 실기기 QA

Apple 로그인이 실제로 성공하기 전에는 `APPLE_AUTH_ENABLED`를 켜지 않는다.

## 네이티브 기능

- 시스템 공유 시트
- 주요 동작 햅틱
- OAuth·외부 링크 시스템 브라우저 열기
- `tiploop://auth-callback` 딥링크
- 앱 안 계정과 콘텐츠 삭제
- 앱 개인정보 선언(`PrivacyInfo.xcprivacy`)
- 네트워크·서버 오류 시 로컬 안내 화면

앱은 현재 원격 서버 렌더링 화면을 사용한다. 웹 배포만으로 화면이 바뀔 수 있으므로,
스토어 심사 중에는 핵심 흐름을 고정하고 제출 빌드와 같은 운영 버전을 유지한다.

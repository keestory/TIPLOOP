# Known Issues & Fixes

> 프로젝트 진행 중 발생한 에러와 해결법을 기록합니다.
> 같은 실수를 두 번 하지 않기 위한 문서입니다.

---

## 2026-04-04

### AST에서 Name 노드의 속성은 id이지 name이 아니다

**증상**: naming_linter.py 실행 시 `AttributeError: 'Name' object has no attribute 'name'`
**원인**: `ast.Name` 노드에서 변수명을 가져올 때 `target.name` 대신 `target.id`를 써야 함
**해결**: `target.name` → `target.id`로 수정
**방지**: Python AST 노드 속성은 공식 문서 확인. coder 에이전트가 AST 코드 작성 시 주의

### 네이버 쇼핑 compositeList가 dict인데 list로 접근 시도

**증상**: `compositeList[:3]`에서 `KeyError: slice(None, 3, None)`
**원인**: `compositeList`가 list가 아니라 dict (`{"list": [...], "total": int}`)
**해결**: `comp.get("list", [])` if `isinstance(comp, dict)` 분기 추가
**방지**: 외부 API/크롤링 데이터의 타입을 가정하지 말고 `isinstance` 체크 후 접근

### 기본값 누락으로 일부 기능이 동작하지 않음

**증상**: coupang 스크래퍼가 실행되지 않음
**원인**: `platforms = platforms or ["smartstore"]`에서 coupang 누락
**해결**: 기본값에 모든 플랫폼 포함
**방지**: 기본값 설정 시 "지원하는 모든 옵션이 포함되었는가?" 확인. 새 옵션 추가 시 기본값도 업데이트

### 필터 없이 영업 대상이 아닌 곳에 메일 생성

**증상**: 자사(KREAM), 경쟁사(솔드아웃), 대형몰(SSG)에게 콜드메일 생성
**원인**: 제외 필터가 없었음
**해결**: `filters.py`로 이름+URL 기반 이중 필터링
**방지**: 외부 발송/연락 기능은 반드시 제외 목록(blocklist) 먼저 구현

---

(새 이슈는 위 형식으로 이 줄 위에 추가)

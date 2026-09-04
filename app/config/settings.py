"""환경 설정과 도메인 상수.

Types만 import 가능. 시크릿·연결정보는 환경 변수에서만 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

# .env 자동 로딩 (있으면) — 매번 export 하지 않아도 되도록
try:
    from dotenv import load_dotenv

    _env_file = Path(__file__).resolve().parents[2] / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
except ImportError:
    pass

# ── 브랜드 ────────────────────────────────────────────────────────────
BRAND = "TIPLOOP"
TAGLINE = "서비스를 뜯어보고, 내 일과 프로젝트에 써보는 서비스 노트"

# 공유 카드(OG)의 절대 URL 기준 — 스크레이퍼는 절대 경로만 읽는다
SITE_URL = os.environ.get("SITE_URL", "https://tiploop.vercel.app")

# ── Supabase / Postgres ──────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# 새 API 키 체계의 publishable key를 우선 사용한다.
# SUPABASE_ANON_KEY는 기존 배포 환경과의 하위 호환용 별칭이다.
SUPABASE_PUBLISHABLE_KEY = (
    os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY", "")
)
SUPABASE_ANON_KEY = SUPABASE_PUBLISHABLE_KEY
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# Apple 로그인은 Apple Developer와 Supabase provider 설정이 모두 끝난 뒤에만
# 화면에 노출한다. 준비 전 버튼을 보여 실패하는 로그인 흐름을 만들지 않는다.
APPLE_AUTH_ENABLED = os.environ.get("APPLE_AUTH_ENABLED", "0") == "1"
APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID", "")
APPLE_CLIENT_SECRET = os.environ.get("APPLE_CLIENT_SECRET", "")
APPLE_TOKEN_ENCRYPTION_KEY = os.environ.get("APPLE_TOKEN_ENCRYPTION_KEY", "")

# 공개 법률·지원 화면. 실제 법적 운영자명과 공개 이메일은 배포 환경에서
# 설정할 수 있으며, 이메일이 없을 때는 공개 GitHub 지원 창구를 제공한다.
OPERATOR_NAME = os.environ.get("OPERATOR_NAME", "TIPLOOP 운영자")
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "")
SUPPORT_URL = os.environ.get(
    "SUPPORT_URL", "https://github.com/keestory/TIPLOOP/issues"
)

# 크론 엔드포인트 보호 — Vercel이 Authorization: Bearer <CRON_SECRET>로 호출
CRON_SECRET = os.environ.get("CRON_SECRET", "")

# ── 세션 (자체 서명 쿠키) ────────────────────────────────────────────
SESSION_COOKIE = "tipping_session"
_DEFAULT_SESSION_SECRET = "dev-only-change-me"
SESSION_SECRET = os.environ.get("IEUM_SECRET", _DEFAULT_SESSION_SECRET)
SESSION_TTL_DAYS = 14
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "1") != "0"


def validate_runtime_security() -> None:
    """DB를 쓰는 실행 환경은 위조 불가능한 세션 설정을 강제한다."""
    if DATABASE_URL and (
        SESSION_SECRET == _DEFAULT_SESSION_SECRET or len(SESSION_SECRET) < 32
    ):
        raise RuntimeError(
            "DATABASE_URL을 사용하는 환경은 32자 이상의 IEUM_SECRET이 필요합니다."
        )
    api_ref = _project_ref_from_supabase_url(SUPABASE_URL)
    database_ref = _project_ref_from_database_url(DATABASE_URL)
    if api_ref and database_ref and api_ref != database_ref:
        raise RuntimeError(
            "SUPABASE_URL과 DATABASE_URL이 서로 다른 Supabase 프로젝트를 가리킵니다."
        )
    if APPLE_AUTH_ENABLED:
        missing = [
            name
            for name, value in (
                ("APPLE_CLIENT_ID", APPLE_CLIENT_ID),
                ("APPLE_CLIENT_SECRET", APPLE_CLIENT_SECRET),
                ("APPLE_TOKEN_ENCRYPTION_KEY", APPLE_TOKEN_ENCRYPTION_KEY),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Apple 로그인을 켜려면 다음 환경 변수가 필요합니다: "
                + ", ".join(missing)
            )
        if len(APPLE_TOKEN_ENCRYPTION_KEY) < 32:
            raise RuntimeError("APPLE_TOKEN_ENCRYPTION_KEY는 32자 이상이어야 합니다.")


def _project_ref_from_supabase_url(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    if hostname.endswith(".supabase.co"):
        return hostname.split(".", 1)[0]
    return ""


def _project_ref_from_database_url(url: str) -> str:
    parsed = urlparse(url.replace("postgres://", "postgresql://", 1))
    username = unquote(parsed.username or "")
    if username.startswith("postgres."):
        return username.split(".", 1)[1]
    hostname = (parsed.hostname or "").lower()
    if hostname.startswith("db.") and hostname.endswith(".supabase.co"):
        return hostname.split(".", 2)[1]
    return ""

# ── 도메인 상수 — 화면과 검증에서 공유 ──────────────────────────────
# 온보딩에서 받는 프로필 (소셜이 주지 않는 값)
JOB_ROLES = ["PM", "개발", "디자인", "마케팅", "데이터", "기획", "MD", "운영", "기타"]
YEARS = ["1년 미만", "1~3년", "3~5년", "5~10년", "10년+"]
INDUSTRIES = ["커머스", "핀테크", "SaaS", "콘텐츠·미디어", "광고·마케팅", "교육", "게임", "기타"]

# 온보딩 2단계 — 관심 주제(피드 개인화 씨앗). 게이트가 아닌 추가 신호.
TOPICS = [
    "리텐션", "퍼널 분석", "체크아웃", "CS 자동화", "SQL",
    "A/B 테스트", "온보딩", "광고 효율", "가격 실험", "리서치",
]

# 글 카테고리: 코드값 → 한글 라벨
CATEGORIES = {
    "tip": "팁",
    "reference": "서비스 노트",
    "question": "질문",
    "retro": "회고",
}

# 로그인 제공자. 이메일/비밀번호 가입은 화면에 열지 않고, 운영자가 만든
# App Store 심사 계정처럼 확인된 계정의 로그인만 허용한다.
PROVIDERS = ["google", "email"] + (["apple"] if APPLE_AUTH_ENABLED else [])

# 크루 — 함께 쓰는 주간 기록 (셋로그식 소그룹). 주가 바뀌면 프롬프트 자동 로테이션.
CREW_MAX_MEMBERS = 12
CREW_PROMPTS = [
    "이번 주에 배운 것 한 가지, 한 줄로",
    "최근에 본 인상적인 서비스·기능 하나",
    "이번 주 삽질 — 남들은 겪지 않게",
    "요즘 팀에서 가장 큰 고민은?",
    "숫자 하나로 남기는 이번 주 성과",
    "동료에게 추천하고 싶은 최근 읽은·본 것",
    "이번 주에 버린 것 (기능·가설·습관)",
    "다음 주에 실험해볼 것",
]

# 글쓰기 템플릿 — 유형별 안내 섹션. 여러 칸을 하나의 body로 합쳐 저장한다.
# hl=True 이면 "결과는 숫자로" 처럼 형광펜 강조로 임팩트 신호를 유도.
WRITE_TEMPLATES = {
    "tip": [
        {"label": "상황", "hint": "어떤 맥락이었나요?", "ph": "예: 결제 전환율이 정체돼 있었어요"},
        {"label": "팁", "hint": "무엇을 하면 되나요?", "ph": "핵심 방법을 적어주세요"},
        {"label": "결과", "hint": "숫자로 남기면 후기가 붙어요", "ph": "예: 이탈률 12% ↓", "hl": True},
    ],
    "reference": [
        {"id": "ref.why_now", "lens": "맥락", "group": "관찰의 출발점", "group_no": "01", "label": "왜 이 서비스를 봤나요?", "hint": "어떤 계기로 관심이 생겼나요?", "ph": "예: 첫 방문자를 가입까지 이끄는 방식을 배우고 싶었어요"},
        {"id": "ref.audience_problem", "lens": "기능", "group": "제품", "group_no": "02", "label": "타깃과 문제", "hint": "누구의 어떤 문제를 푸나요?", "ph": "핵심 사용자를 한 문장으로 적어보세요"},
        {"id": "ref.core_journey", "lens": "기능", "label": "핵심 기능과 흐름", "hint": "발견부터 가치 경험까지", "ph": "사용자가 처음 들어와 핵심 가치를 얻기까지의 흐름"},
        {"id": "ref.planning_ux", "lens": "기획·UX", "group": "경험", "group_no": "03", "label": "기획과 UX", "hint": "매력적이거나 불편한 장면", "ph": "정보 구조, 상호작용, 전환 장치에서 눈에 띈 점"},
        {"id": "ref.content_strategy", "lens": "콘텐츠", "label": "콘텐츠", "hint": "무엇을 어떤 방식으로 보여주나요?", "ph": "카피, 이미지, 추천, 큐레이션 방식"},
        {"id": "ref.acquisition", "lens": "마케팅", "group": "성장과 사업", "group_no": "04", "label": "마케팅과 유입", "hint": "사람들은 어떻게 이 서비스를 알게 되나요?", "ph": "검색, 광고, SNS, 입소문, 제휴 등"},
        {"id": "ref.retention_referral", "lens": "리텐션", "label": "리텐션과 초대", "hint": "왜 다시 오고, 왜 남에게 말하나요?", "ph": "반복 사용과 공유를 만드는 장치"},
        {"id": "ref.business_model", "lens": "비즈니스", "label": "비즈니스 모델", "hint": "누가 무엇에 돈을 내나요?", "ph": "수익원, 가격, 비용 구조에 대한 관찰"},
        {"id": "ref.service_operations", "lens": "운영", "label": "서비스 운영", "hint": "이 경험을 뒤에서 어떻게 굴릴까요?", "ph": "정책, 공급, CS, 품질 관리, 파트너 운영"},
        {"id": "ref.strengths_gaps", "lens": "판단", "group": "결론", "group_no": "05", "label": "잘한 점과 아쉬운 점", "hint": "근거가 드러나게", "ph": "좋았던 점과 개선할 점을 함께 적어보세요"},
        {"id": "ref.transferable_principle", "lens": "적용", "label": "가져올 아이디어", "hint": "내 제품에 옮길 수 있는 것", "ph": "그대로 복사하지 않고 원리를 추출해보세요"},
        {"id": "ref.next_action", "lens": "적용", "label": "내가 적용한다면?", "hint": "내 방식으로 바꿔보기", "ph": "예: 다음 랜딩 개편에서 첫 화면 가치 제안을 한 문장으로 줄인다", "hl": True},
    ],
    "question": [
        {"label": "상황", "hint": "어떤 걸 겪고 있나요?", "ph": "배경을 적어주세요"},
        {"label": "궁금한 점", "hint": "무엇이 가장 알고 싶나요?", "ph": "구체적으로 물으면 좋은 답이 와요", "hl": True},
    ],
    "retro": [
        {"label": "상황", "hint": "무엇을 했나요?", "ph": "프로젝트·실험 개요"},
        {"label": "잘한 것", "hint": "효과가 있었던 것", "ph": ""},
        {"label": "아쉬운 것 · 배운 것", "hint": "다음엔 이렇게", "ph": "", "hl": True},
    ],
}

# 서비스 분석 질문 체계. 본문은 과거 호환을 위해 한글 라벨 블록으로 유지하고,
# 선택 상태만 안정적인 id로 별도 저장한다.
REFERENCE_TEMPLATE_VERSION = "reference_v1"
REFERENCE_ANALYSIS_MODES = ("quick", "focus", "full")
REFERENCE_QUESTION_IDS = tuple(
    section["id"] for section in WRITE_TEMPLATES["reference"]
)
REFERENCE_QUICK_QUESTION_IDS = (
    "ref.audience_problem",
    "ref.core_journey",
    "ref.next_action",
)
REFERENCE_REQUIRED_FINAL_ID = "ref.next_action"
REFERENCE_WHY_LABEL = next(
    section["label"]
    for section in WRITE_TEMPLATES["reference"]
    if section["id"] == "ref.why_now"
)
REFERENCE_APPLICATION_LABEL = next(
    section["label"]
    for section in WRITE_TEMPLATES["reference"]
    if section["id"] == REFERENCE_REQUIRED_FINAL_ID
)

# 비공개 연구 미디어. Storage 버킷의 50 MiB 상한과 별개로 이미지는 더 작게 제한한다.
REFERENCE_IMAGE_BUCKET = "tiploop-research-images"
REFERENCE_VIDEO_BUCKET = "tiploop-research-videos"
REFERENCE_MEDIA_BUCKETS = {
    "image": REFERENCE_IMAGE_BUCKET,
    "video": REFERENCE_VIDEO_BUCKET,
}
REFERENCE_MEDIA_MAX_FILES = 6
REFERENCE_MEDIA_MAX_VIDEOS = 1
REFERENCE_MEDIA_MAX_TOTAL_BYTES = 100 * 1024 * 1024
REFERENCE_IMAGE_MAX_BYTES = 10 * 1024 * 1024
REFERENCE_VIDEO_MAX_BYTES = 50 * 1024 * 1024
REFERENCE_MEDIA_TYPES = {
    "image/jpeg": ("image", "jpg"),
    "image/png": ("image", "png"),
    "image/webp": ("image", "webp"),
    "image/gif": ("image", "gif"),
    "video/mp4": ("video", "mp4"),
    "video/webm": ("video", "webm"),
    "video/quicktime": ("video", "mov"),
}


def category_label(code: str) -> str:
    """카테고리 코드의 한글 라벨. 모르는 값은 그대로 돌려준다."""
    return CATEGORIES.get(code, code)

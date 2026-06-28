"""엔트리포인트.

레이어 디렉토리 밖(아키텍처 린터 제외 대상)에서 UI를 조립한다.

    uvicorn app.main:app --reload
"""

from __future__ import annotations


from app.ui.app_factory import create_app

app = create_app()

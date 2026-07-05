"""Vercel 서버리스 진입점.

@vercel/python 은 이 파일에서 `app`(ASGI) 객체를 찾아 실행한다.
저장소 루트를 sys.path에 넣어 app 패키지를 import 할 수 있게 한다.
템플릿·정적 파일은 vercel.json의 includeFiles로 함께 번들된다.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402,F401  (Vercel이 참조하는 ASGI 앱)

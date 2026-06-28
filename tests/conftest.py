"""테스트 공통 설정 — 격리된 임시 DB.

app 모듈이 import 시점에 DB 경로를 읽으므로, import 전에 환경 변수를 설정한다.
"""

import os
import tempfile

import pytest

# app.* import보다 먼저 실행되어야 한다
_TMP_DB = os.path.join(tempfile.gettempdir(), "ieum_test.db")
os.environ["IEUM_DB_PATH"] = _TMP_DB


@pytest.fixture(autouse=True)
def fresh_db():
    """각 테스트마다 빈 스키마로 초기화."""
    if os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)
    from app.repo.database import init_db

    init_db()
    yield
    if os.path.exists(_TMP_DB):
        os.remove(_TMP_DB)

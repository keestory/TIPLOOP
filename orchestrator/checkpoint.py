"""
체크포인트 관리

파일 수정 전 자동 스냅샷을 생성하고, 롤백을 지원합니다.
"""

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Checkpoint:
    """체크포인트"""
    id: str
    timestamp: float
    task_id: str
    files: dict[str, str]  # path -> content
    description: str = ""


class CheckpointManager:
    """체크포인트 관리자"""

    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints: list[Checkpoint] = []

    def create(self, task_id: str, files: list[Path], description: str = "") -> Checkpoint:
        """체크포인트 생성 — 파일 수정 전 호출"""
        file_contents = {}
        for f in files:
            if f.exists():
                try:
                    file_contents[str(f)] = f.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    file_contents[str(f)] = f.read_bytes().hex()

        cp_id = f"cp-{int(time.time())}-{task_id[:8]}"
        checkpoint = Checkpoint(
            id=cp_id,
            timestamp=time.time(),
            task_id=task_id,
            files=file_contents,
            description=description,
        )

        # 디스크에 저장
        cp_path = self.checkpoint_dir / f"{cp_id}.json"
        cp_path.write_text(
            json.dumps({
                "id": checkpoint.id,
                "timestamp": checkpoint.timestamp,
                "task_id": checkpoint.task_id,
                "files": checkpoint.files,
                "description": checkpoint.description,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._checkpoints.append(checkpoint)
        return checkpoint

    def rollback(self, checkpoint_id: str) -> list[str]:
        """체크포인트로 롤백"""
        cp = self._find_checkpoint(checkpoint_id)
        if cp is None:
            raise ValueError(f"체크포인트 없음: {checkpoint_id}")

        restored = []
        for path_str, content in cp.files.items():
            path = Path(path_str)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            restored.append(path_str)

        return restored

    def rollback_to_latest(self, task_id: Optional[str] = None) -> list[str]:
        """가장 최근 체크포인트로 롤백"""
        candidates = self._checkpoints
        if task_id:
            candidates = [c for c in candidates if c.task_id == task_id]
        if not candidates:
            raise ValueError("롤백할 체크포인트 없음")
        return self.rollback(candidates[-1].id)

    def list_checkpoints(self) -> list[dict]:
        """체크포인트 목록"""
        return [
            {
                "id": cp.id,
                "timestamp": cp.timestamp,
                "task_id": cp.task_id,
                "files_count": len(cp.files),
                "description": cp.description,
            }
            for cp in self._checkpoints
        ]

    def _find_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """ID로 체크포인트 검색"""
        for cp in self._checkpoints:
            if cp.id == checkpoint_id:
                return cp

        # 디스크에서 로드 시도
        cp_path = self.checkpoint_dir / f"{checkpoint_id}.json"
        if cp_path.exists():
            data = json.loads(cp_path.read_text(encoding="utf-8"))
            checkpoint = Checkpoint(**data)
            self._checkpoints.append(checkpoint)
            return checkpoint

        return None

    def cleanup(self, max_age_hours: int = 24):
        """오래된 체크포인트 정리"""
        cutoff = time.time() - (max_age_hours * 3600)
        to_remove = []

        for cp in self._checkpoints:
            if cp.timestamp < cutoff:
                to_remove.append(cp)
                cp_path = self.checkpoint_dir / f"{cp.id}.json"
                if cp_path.exists():
                    cp_path.unlink()

        for cp in to_remove:
            self._checkpoints.remove(cp)

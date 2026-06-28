"""
DocGardener — 문서 관리 에이전트 (가비지 컬렉션)

문서를 스캔하여 오래되거나 부정확한 내용을 찾고 수정합니다.
주기적으로 실행되어 코드베이스와 문서의 일관성을 유지합니다.
"""

import os
import time
from pathlib import Path
from agents.base_agent import BaseAgent


class DocGardener(BaseAgent):
    name = "doc_gardener"
    description = "문서 최신화, 정리, 교차 링크 검증을 수행하는 에이전트"

    SYSTEM_PROMPT = """당신은 문서 관리 전문 에이전트(Doc Gardener)입니다.

## 역할
- 문서를 스캔하여 오래되거나 부정확한 내용을 찾습니다.
- 코드와 문서의 일관성을 검증합니다.
- 교차 링크가 올바른지 확인합니다.
- 문서 품질을 개선합니다.

## 점검 항목
1. **신선도**: 문서가 현재 코드를 반영하는가?
2. **정확성**: 기술적 설명이 올바른가?
3. **교차 링크**: 링크가 유효한가?
4. **커버리지**: 문서화되지 않은 영역이 있는가?
5. **구조**: 올바른 위치에 있는가?

## 출력 형식

### 스캔 결과
- [파일] 상태: 최신/오래됨/부정확
- 발견된 이슈 목록

### 수정 사항
- [파일] 변경 내용

### 문서 커버리지
- 문서화된 영역: N개
- 문서 부재 영역: N개
"""

    def get_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    async def execute(self, task_description: str, context: dict = None) -> str:
        messages = [
            {"role": "user", "content": f"## 태스크\n{task_description}"},
        ]
        result = await self.call_model(messages, max_tokens=4096)
        self.log(f"문서 관리 완료: {task_description[:50]}")
        return result

    async def scan_docs(self) -> dict:
        """docs/ 디렉토리 전체 스캔"""
        docs_dir = self.project_root / "docs"
        if not docs_dir.exists():
            return {"error": "docs/ 디렉토리 없음"}

        doc_files = list(docs_dir.rglob("*.md"))
        results = {
            "total_files": len(doc_files),
            "issues": [],
            "stale": [],
            "broken_links": [],
        }

        for doc_file in doc_files:
            content = doc_file.read_text(encoding="utf-8")

            # 빈 파일 검사
            if len(content.strip()) < 10:
                results["issues"].append({
                    "file": str(doc_file.relative_to(self.project_root)),
                    "issue": "내용이 거의 없음",
                    "severity": "warning",
                })

            # 깨진 링크 검사
            import re
            links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
            for text, href in links:
                if href.startswith("http"):
                    continue
                linked_path = doc_file.parent / href
                if not linked_path.exists():
                    results["broken_links"].append({
                        "file": str(doc_file.relative_to(self.project_root)),
                        "link_text": text,
                        "link_href": href,
                    })

            # 오래된 파일 검사 (30일 이상 수정 안 됨)
            mtime = os.path.getmtime(doc_file)
            age_days = (time.time() - mtime) / 86400
            if age_days > 30:
                results["stale"].append({
                    "file": str(doc_file.relative_to(self.project_root)),
                    "last_modified_days_ago": round(age_days),
                })

        return results

    async def fix_broken_links(self) -> list[str]:
        """깨진 링크 수정"""
        scan = await self.scan_docs()
        fixed = []

        for bl in scan.get("broken_links", []):
            self.log(f"깨진 링크 발견: {bl['file']} -> {bl['link_href']}", "warning")
            fixed.append(f"{bl['file']}: {bl['link_text']} -> {bl['link_href']}")

        return fixed

    async def generate_coverage_report(self) -> str:
        """문서 커버리지 보고서"""
        # 코드 디렉토리와 문서 디렉토리 비교
        code_dirs = set()
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                rel = py_file.parent.relative_to(self.project_root)
                code_dirs.add(str(rel))

        doc_files = set()
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            for md_file in docs_dir.rglob("*.md"):
                doc_files.add(str(md_file.relative_to(self.project_root)))

        return (
            f"코드 디렉토리: {len(code_dirs)}개\n"
            f"문서 파일: {len(doc_files)}개\n"
            f"코드 디렉토리: {sorted(code_dirs)}\n"
            f"문서 파일: {sorted(doc_files)}"
        )

"""
Publisher Agent — articles-db-v2.json + blog.html 업데이트
비용: $0  /  순수 파일 조작
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from pipeline.config import BLOG_PATH, DB_PATH, MARKER_END, MARKER_START
from pipeline.utils import get_logger, load_db, save_db

log = get_logger("publisher")


class PublisherAgent:
    """
    Writer Agent 결과를 받아:
      1. articles-db-v2.json 에 append
      2. blog.html 의 ARTICLES 배열 앞에 신규 기사 삽입
      3. nav-count 숫자 업데이트
    git 조작은 하지 않음 (GitHub Actions workflow 에서 처리)
    """

    def publish(self, new_articles: list[dict]) -> int:
        if not new_articles:
            log.info("Publisher Agent — 추가할 기사 없음")
            return 0

        # 1. JSON DB 업데이트
        db = load_db()
        # 임시 ID 슬롯 제거 (WriterAgent가 ID 계산용으로 넣은 것)
        db["articles"] = [a for a in db["articles"] if len(a) > 1]
        # 신규 기사는 맨 앞에 (최신 기사 상단 노출)
        db["articles"] = new_articles + db["articles"]
        save_db(db)

        total = len(db["articles"])

        # 2. blog.html 업데이트
        ok = self._update_blog_html(new_articles, total)
        if ok:
            log.info(f"Publisher Agent — blog.html 업데이트 완료 (총 {total}개)")
        else:
            log.warning("Publisher Agent — blog.html 업데이트 실패 (마커 없음, 수동 확인 필요)")

        log.info(f"Publisher Agent — {len(new_articles)}개 기사 발행 완료")
        return len(new_articles)

    # ── private ──────────────────────────────────────────────────────

    def _update_blog_html(self, new_articles: list[dict], total_count: int) -> bool:
        html_path = Path(BLOG_PATH)
        if not html_path.exists():
            log.warning("blog.html 파일을 찾을 수 없음")
            return False

        # 백업
        backup = html_path.with_suffix(".html.bak")
        shutil.copy2(html_path, backup)

        html = html_path.read_text(encoding="utf-8")

        # ── 마커가 있는 경우: 배열 교체 ─────────────────────────────
        if MARKER_START in html and MARKER_END in html:
            pattern = re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END)
            match   = re.search(pattern, html, re.DOTALL)
            if not match:
                return False

            existing_block = match.group(0)
            # 기존 배열 JSON 추출
            arr_match = re.search(r"const ARTICLES\s*=\s*(\[.*?\]);", existing_block, re.DOTALL)
            if arr_match:
                try:
                    existing = json.loads(arr_match.group(1))
                except json.JSONDecodeError:
                    existing = []
            else:
                existing = []

            merged    = new_articles + existing
            new_block = (
                f"{MARKER_START}\n"
                f"    const ARTICLES = {self._to_js(merged)};\n"
                f"    {MARKER_END}"
            )
            html = html[:match.start()] + new_block + html[match.end():]

        # ── 마커 없는 경우: const ARTICLES = [...] 패턴으로 교체 ────
        else:
            pattern = r"(const ARTICLES\s*=\s*)(\[.*?\])(\s*;)"
            match   = re.search(pattern, html, re.DOTALL)
            if not match:
                log.warning("blog.html에서 ARTICLES 배열을 찾을 수 없음")
                backup.unlink(missing_ok=True)
                return False

            try:
                existing = json.loads(match.group(2))
            except json.JSONDecodeError:
                existing = []

            merged  = new_articles + existing
            new_arr = self._to_js(merged)
            html    = html[:match.start(1)] + f"const ARTICLES = {new_arr};" + html[match.end(3):]

        # ── nav-count 숫자 업데이트 ──────────────────────────────────
        html = re.sub(
            r'(<div class="nav-count"[^>]*>)\d+ Articles(</div>)',
            rf'\g<1>{total_count} Articles\g<2>',
            html,
        )

        html_path.write_text(html, encoding="utf-8")
        backup.unlink(missing_ok=True)  # 성공 시 백업 삭제
        return True

    @staticmethod
    def _to_js(articles: list[dict]) -> str:
        """기사 배열을 blog.html 스타일의 JS 리터럴로 직렬화."""
        lines = ["["]
        for i, art in enumerate(articles):
            comma = "," if i < len(articles) - 1 else ""
            # blog.html 에 필요한 인라인 형식으로 직렬화
            lines.append(
                "      " + json.dumps(art, ensure_ascii=False) + comma
            )
        lines.append("    ]")
        return "\n".join(lines)

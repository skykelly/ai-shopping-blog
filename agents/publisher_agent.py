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
      2. blog.html 의 ARTICLES 배열을 DB 전체 기사로 교체
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

        # 2. blog.html 업데이트 — DB 전체를 단일 소스로 사용
        ok = self._update_blog_html(db["articles"], total)
        if ok:
            log.info(f"Publisher Agent — blog.html 업데이트 완료 (총 {total}개)")
        else:
            log.warning("Publisher Agent — blog.html 업데이트 실패 (마커 없음, 수동 확인 필요)")

        log.info(f"Publisher Agent — {len(new_articles)}개 기사 발행 완료")
        return len(new_articles)

    # ── private ──────────────────────────────────────────────────────

    def _update_blog_html(self, all_articles: list[dict], total_count: int) -> bool:
        """
        DB의 전체 기사 목록으로 blog.html의 ARTICLES 배열을 교체한다.
        HTML에서 기존 배열을 파싱하지 않고 DB를 단일 소스(source of truth)로 사용.
        """
        html_path = Path(BLOG_PATH)
        if not html_path.exists():
            log.warning("blog.html 파일을 찾을 수 없음")
            return False

        # 백업
        backup = html_path.with_suffix(".html.bak")
        shutil.copy2(html_path, backup)

        html = html_path.read_text(encoding="utf-8")

        new_js_block = (
            f"{MARKER_START}\n"
            f"    const ARTICLES = {self._to_js(all_articles)};\n"
            f"    {MARKER_END}"
        )

        # ── 마커가 있는 경우: 마커 사이 전체 교체 ─────────────────────
        if MARKER_START in html and MARKER_END in html:
            pattern = re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END)
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                log.warning("ARTICLES_DATA 마커를 찾았지만 패턴 매칭 실패")
                backup.unlink(missing_ok=True)
                return False

            html = html[:match.start()] + new_js_block + html[match.end():]

        # ── 마커 없는 경우: const ARTICLES = [...] 패턴으로 교체 ────
        else:
            # JS/JSON 혼합 형식에 대응하기 위해 마커 기반 교체로 전환
            # const ARTICLES = 다음에 오는 [ ... ] 블록 전체를 교체
            # 중첩 배열(tags 등)을 처리하기 위해 괄호 카운팅 방식 사용
            start_idx = html.find("const ARTICLES")
            if start_idx == -1:
                log.warning("blog.html에서 ARTICLES 배열을 찾을 수 없음")
                backup.unlink(missing_ok=True)
                return False

            bracket_start = html.find("[", start_idx)
            if bracket_start == -1:
                backup.unlink(missing_ok=True)
                return False

            # 괄호 카운팅으로 배열 끝 찾기
            depth = 0
            bracket_end = bracket_start
            in_string = False
            escape_next = False
            for i, ch in enumerate(html[bracket_start:], bracket_start):
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\" and in_string:
                    escape_next = True
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        bracket_end = i
                        break

            # 세미콜론까지 포함
            semi_idx = html.find(";", bracket_end)
            if semi_idx == -1:
                semi_idx = bracket_end

            new_const = f"const ARTICLES = {self._to_js(all_articles)};"
            # 마커도 함께 삽입
            new_block = f"{MARKER_START}\n    {new_const}\n    {MARKER_END}"
            const_start = html.rfind("const ARTICLES", 0, bracket_start)
            html = html[:const_start] + new_block + html[semi_idx + 1:]

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
            lines.append(
                "      " + json.dumps(art, ensure_ascii=False) + comma
            )
        lines.append("    ]")
        return "\n".join(lines)

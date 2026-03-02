#!/usr/bin/env python3
"""
Coordinator — 4개 서브 에이전트를 순서대로 실행하는 오케스트레이터
실행: python pipeline/coordinator.py

환경변수:
  GITHUB_TOKEN   GitHub Actions에서 자동 주입 (GitHub Models 사용)
  NEWS_API_KEY   NewsAPI 무료 키 (없으면 Search Agent 건너뜀)
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (로컬 실행 시)
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.publisher_agent import PublisherAgent
from agents.quality_agent import QualityAgent
from agents.search_agent import SearchAgent
from agents.writer_agent import WriterAgent
from pipeline.utils import (
    get_existing_titles,
    get_existing_urls,
    get_logger,
    load_db,
)

log = get_logger("coordinator")


def run_pipeline() -> dict:
    """
    전체 파이프라인 실행. 실행 결과 요약 dict 반환.
    """
    start_time   = time.time()
    github_token = os.environ.get("GITHUB_TOKEN", "")
    news_api_key = os.environ.get("NEWS_API_KEY", "")

    log.info("=" * 60)
    log.info("🚀 AI×Retail 기사 자동화 파이프라인 시작")
    log.info(f"   실행 시각: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"   NEWS_API_KEY:  {'✅ 있음' if news_api_key  else '❌ 없음 (Search 건너뜀)'}")
    log.info(f"   GITHUB_TOKEN:  {'✅ 있음' if github_token else '❌ 없음 (규칙 기반 폴백)'}")
    log.info("=" * 60)

    # ── 0. DB 로드 ────────────────────────────────────────────────────
    db              = load_db()
    existing_urls   = get_existing_urls(db)
    existing_titles = get_existing_titles(db)
    log.info(f"기존 기사 수: {len(db['articles'])}개")

    # ── 1. Search Agent ───────────────────────────────────────────────
    log.info("\n[1/4] 🔍 Search Agent 실행...")
    candidates = SearchAgent().run(existing_urls, existing_titles)

    if not candidates:
        log.warning("후보 기사 없음. NEWS_API_KEY를 확인하거나 수동으로 실행하세요.")
        _print_summary(0, 0, 0, time.time() - start_time)
        return {"added": 0, "reason": "no_candidates"}

    # ── 2. Quality Agent ──────────────────────────────────────────────
    log.info(f"\n[2/4] ✅ Quality Agent 실행 (후보 {len(candidates)}개)...")
    approved = QualityAgent(github_token).evaluate(candidates, db["articles"])

    if not approved:
        log.info("품질 기준 통과 기사 없음. 오늘은 업데이트 없이 종료.")
        _print_summary(len(candidates), 0, 0, time.time() - start_time)
        return {"added": 0, "reason": "quality_filter"}

    # ── 3. Writer Agent ───────────────────────────────────────────────
    log.info(f"\n[3/4] ✍️  Writer Agent 실행 ({len(approved)}개 포맷 중)...")
    formatted = WriterAgent(github_token, db).format_articles(approved)

    if not formatted:
        log.warning("포맷 변환 실패. Writer Agent 오류를 확인하세요.")
        _print_summary(len(candidates), len(approved), 0, time.time() - start_time)
        return {"added": 0, "reason": "writer_error"}

    # ── 4. Publisher Agent ────────────────────────────────────────────
    log.info(f"\n[4/4] 📤 Publisher Agent 실행 ({len(formatted)}개 발행 중)...")
    added = PublisherAgent().publish(formatted)

    elapsed = time.time() - start_time
    _print_summary(len(candidates), len(approved), added, elapsed)

    return {
        "added":      added,
        "candidates": len(candidates),
        "approved":   len(approved),
        "elapsed_s":  round(elapsed, 1),
    }


def _print_summary(candidates: int, approved: int, added: int, elapsed: float):
    log.info("\n" + "=" * 60)
    log.info("📊 파이프라인 결과 요약")
    log.info(f"   수집 후보:  {candidates}개")
    log.info(f"   품질 통과:  {approved}개")
    log.info(f"   발행 완료:  {added}개")
    log.info(f"   소요 시간:  {elapsed:.1f}초")
    log.info("=" * 60)

    if added > 0:
        log.info(f"✅ {added}개 기사가 추가되었습니다.")
    else:
        log.info("📭 오늘은 추가된 기사가 없습니다.")


if __name__ == "__main__":
    result = run_pipeline()
    # added > 0이면 exit code 0 (GitHub Actions에서 변경 감지용)
    sys.exit(0)

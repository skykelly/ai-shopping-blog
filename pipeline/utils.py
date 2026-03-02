"""공통 유틸리티 — DB 로더, 로거, URL 정규화, ID 생성"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qs

from pipeline.config import DB_PATH, LOG_PATH


# ── 로거 설정 ────────────────────────────────────────────────────────
def get_logger(name: str = "pipeline") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")

    # 콘솔 출력
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # 파일 기록
    try:
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception:
        pass

    return logger


log = get_logger()


# ── DB 유틸 ──────────────────────────────────────────────────────────
def load_db() -> dict:
    """articles-db-v2.json 로드. 없으면 빈 구조 반환."""
    if DB_PATH.exists():
        with open(DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {
        "metadata": {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "last_updated": "",
            "total_articles": 0,
        },
        "articles": [],
    }


def save_db(db: dict) -> None:
    db.setdefault("metadata", {})
    db["metadata"]["last_updated"] = datetime.now().isoformat()
    db["metadata"]["total_articles"] = len(db["articles"])
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    log.info(f"DB 저장 완료 — 총 {len(db['articles'])}개")


def get_existing_urls(db: dict) -> set[str]:
    """기존 모든 URL을 정규화하여 set으로 반환."""
    urls = set()
    for art in db.get("articles", []):
        for key in ("source_url", "url"):
            if v := art.get(key):
                urls.add(normalize_url(v))
    return urls


def get_existing_titles(db: dict) -> list[str]:
    return [a.get("title", "") for a in db.get("articles", [])]


def next_article_id(db: dict) -> str:
    nums = []
    for art in db.get("articles", []):
        m = re.match(r"A(\d+)", art.get("id", ""))
        if m:
            nums.append(int(m.group(1)))
    return f"A{(max(nums, default=0) + 1):03d}"


# ── URL 유틸 ─────────────────────────────────────────────────────────
def normalize_url(url: str) -> str:
    """쿼리스트링·UTM·프래그먼트·trailing slash 제거."""
    try:
        p = urlparse(url)
        # utm_* 파라미터 제거
        qs = {k: v for k, v in parse_qs(p.query).items()
              if not k.lower().startswith("utm")}
        clean_query = "&".join(f"{k}={v[0]}" for k, v in qs.items())
        clean_path  = p.path.rstrip("/")
        return urlunparse(p._replace(query=clean_query, fragment="", path=clean_path))
    except Exception:
        return url


def title_similarity(a: str, b: str) -> float:
    """간단한 단어 집합 유사도 (Jaccard)."""
    wa = set(re.sub(r"[^\w\s]", "", a.lower()).split())
    wb = set(re.sub(r"[^\w\s]", "", b.lower()).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def is_duplicate(url: str, title: str,
                 existing_urls: set[str], existing_titles: list[str],
                 sim_threshold: float = 0.75) -> bool:
    """URL 정규화 + 제목 유사도 이중 중복 체크."""
    if normalize_url(url) in existing_urls:
        return True
    for et in existing_titles:
        if title_similarity(title, et) >= sim_threshold:
            return True
    return False

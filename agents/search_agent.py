"""
Search Agent — NewsAPI 무료 티어로 기사 후보 수집
비용: $0  /  하루 최대 100건 요청 (무료 한도 내)
"""

import os
import time
from datetime import datetime, timedelta

import requests

from pipeline.config import NEWS_LOOKBACK_DAYS, NEWS_PAGE_SIZE, SEARCH_TOPICS
from pipeline.utils import get_logger, is_duplicate, normalize_url

log = get_logger("search")

NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"


class SearchAgent:
    """
    5개 대주제 × 복수 쿼리로 후보 기사를 수집한다.
    NEWS_API_KEY 없으면 조용히 빈 리스트 반환.
    """

    def __init__(self):
        self.api_key = os.environ.get("NEWS_API_KEY", "")

    # ── public ───────────────────────────────────────────────────────

    def run(self, existing_urls: set[str], existing_titles: list[str]) -> list[dict]:
        if not self.api_key:
            log.warning("NEWS_API_KEY 없음 — Search Agent 건너뜀")
            return []

        from_date = (datetime.utcnow() - timedelta(days=NEWS_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
        candidates: list[dict] = []
        seen_urls: set[str] = set(existing_urls)  # 로컬 중복 방지용

        for topic_cfg in SEARCH_TOPICS:
            topic = topic_cfg["topic"]
            for query in topic_cfg["queries"]:
                results = self._fetch(query, from_date)
                for raw in results:
                    art = self._parse(raw, topic)
                    if art is None:
                        continue
                    if is_duplicate(art["url"], art["title"], seen_urls, existing_titles):
                        continue
                    seen_urls.add(normalize_url(art["url"]))
                    candidates.append(art)

                time.sleep(0.3)  # NewsAPI 초당 요청 제한 방지

        log.info(f"Search Agent — 후보 {len(candidates)}개 수집")
        return candidates

    # ── private ──────────────────────────────────────────────────────

    def _fetch(self, query: str, from_date: str) -> list[dict]:
        try:
            resp = requests.get(
                NEWSAPI_ENDPOINT,
                params={
                    "q":        query,
                    "from":     from_date,
                    "sortBy":   "publishedAt",
                    "language": "en",
                    "pageSize": NEWS_PAGE_SIZE,
                    "apiKey":   self.api_key,
                },
                timeout=10,
            )
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            log.info(f"  [{query[:40]}] → {len(articles)}건")
            return articles
        except Exception as e:
            log.warning(f"  NewsAPI 오류 ({query[:30]}): {e}")
            return []

    @staticmethod
    def _parse(raw: dict, topic: str) -> dict | None:
        title = (raw.get("title") or "").strip()
        url   = (raw.get("url")   or "").strip()
        if not title or not url or title == "[Removed]":
            return None

        return {
            "title":       title,
            "url":         url,
            "source":      raw.get("source", {}).get("name", "Unknown"),
            "date":        (raw.get("publishedAt") or "")[:10],
            "description": (raw.get("description") or "").strip(),
            "topic":       topic,
        }

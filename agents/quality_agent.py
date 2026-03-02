"""
Quality Agent — GitHub Models (GPT-4o mini) 로 기사 품질 평가
비용: $0  /  GitHub Actions GITHUB_TOKEN 으로 무료 사용
"""

import json
import time

from openai import OpenAI

from pipeline.config import (
    GITHUB_MODELS_ENDPOINT,
    MAX_ARTICLES_PER_RUN,
    MIN_ARTICLES_PER_RUN,
    QUALITY_MODEL,
    QUALITY_THRESHOLD,
)
from pipeline.utils import get_logger

log = get_logger("quality")

# 배치당 평가 기사 수 (GitHub Models RPM 한도 고려)
BATCH_SIZE = 5


SYSTEM_PROMPT = """당신은 AI 리테일/쇼핑 전문 기사 큐레이터입니다.
주어진 기사들을 아래 기준으로 평가하고 JSON 배열만 반환합니다.

평가 기준 (100점 만점):
- source_score  (25점): 유명 미디어·기업 공식 블로그·리서치 기관 여부
- stat_score    (25점): 구체적 수치(%·금액·사용자수 등) 포함 여부
- relevance     (25점): AI 쇼핑/리테일/커머스와의 직접 연관성
- freshness     (15점): 최신성 (7일 이내=15, 30일=10, 90일=5)
- uniqueness    (10점): 기존 기사들과 다른 새로운 각도·기업·사례

반드시 아래 JSON 형식으로만 응답:
[
  {
    "index": 0,
    "total_score": 78,
    "source_score": 20,
    "stat_score": 22,
    "relevance": 20,
    "freshness": 12,
    "uniqueness": 4,
    "reason": "Modern Retail 출처, +35% CVR 수치 포함, Agentic Commerce 직접 관련"
  }
]"""


class QualityAgent:
    """
    후보 기사를 LLM으로 평가해 품질 통과 기사만 반환.
    GITHUB_TOKEN 없으면 규칙 기반 폴백 사용.
    """

    def __init__(self, github_token: str):
        self.token = github_token
        self.client = (
            OpenAI(base_url=GITHUB_MODELS_ENDPOINT, api_key=github_token)
            if github_token else None
        )

    # ── public ───────────────────────────────────────────────────────

    def evaluate(self, candidates: list[dict], existing_articles: list[dict]) -> list[dict]:
        if not candidates:
            return []

        if self.client:
            scored = self._llm_evaluate(candidates, existing_articles)
        else:
            log.warning("GITHUB_TOKEN 없음 — 규칙 기반 폴백 사용")
            scored = self._rule_evaluate(candidates)

        # 통과 기준 적용 + 최대 개수 제한
        passed = [c for c in scored if c["_score"] >= QUALITY_THRESHOLD]
        passed.sort(key=lambda x: x["_score"], reverse=True)
        passed = passed[:MAX_ARTICLES_PER_RUN]

        # 최소 1개 보장 (점수 미달이어도 가장 높은 것 1개 선택)
        if not passed and scored and MIN_ARTICLES_PER_RUN > 0:
            best = max(scored, key=lambda x: x["_score"])
            passed = [best]
            log.info(f"  품질 기준 미달이지만 최고점 기사 1개 선택 (점수: {best['_score']})")

        log.info(f"Quality Agent — {len(candidates)}개 평가 → {len(passed)}개 통과")
        return passed

    # ── private: LLM 평가 ────────────────────────────────────────────

    def _llm_evaluate(self, candidates: list[dict], existing_articles: list[dict]) -> list[dict]:
        existing_titles = [a.get("title", "") for a in existing_articles[-10:]]  # 최근 10개만 참고

        scored: list[dict] = []
        # 배치 처리
        for i in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[i: i + BATCH_SIZE]
            results = self._evaluate_batch(batch, existing_titles, offset=i)
            scored.extend(results)
            if i + BATCH_SIZE < len(candidates):
                time.sleep(4)  # GitHub Models RPM 제한 (15 req/min)

        return scored

    def _evaluate_batch(self, batch: list[dict], existing_titles: list[str], offset: int) -> list[dict]:
        articles_text = "\n\n".join(
            f"[{offset + j}] 제목: {a['title']}\n출처: {a['source']}\n날짜: {a['date']}\n설명: {a['description'][:200]}"
            for j, a in enumerate(batch)
        )
        existing_text = "\n".join(f"- {t}" for t in existing_titles) if existing_titles else "(없음)"

        user_msg = f"""기존 등록된 기사 제목 (중복·유사도 평가 참고):
{existing_text}

평가할 후보 기사:
{articles_text}

위 기사들을 평가 기준에 따라 JSON 배열로만 응답해주세요."""

        try:
            resp = self.client.chat.completions.create(
                model=QUALITY_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            raw = resp.choices[0].message.content.strip()
            # JSON 파싱
            if "```" in raw:
                raw = raw.split("```")[1].lstrip("json").strip()
            scores = json.loads(raw)
        except Exception as e:
            log.warning(f"  LLM 평가 실패: {e} → 폴백 사용")
            return [dict(a, _score=50, _reason="LLM 실패") for a in batch]

        result = []
        for item in scores:
            idx = item.get("index", 0)
            local_idx = idx - offset
            if 0 <= local_idx < len(batch):
                art = dict(batch[local_idx])
                art["_score"]  = item.get("total_score", 50)
                art["_reason"] = item.get("reason", "")
                result.append(art)

        return result

    # ── private: 규칙 기반 폴백 ──────────────────────────────────────

    @staticmethod
    def _rule_evaluate(candidates: list[dict]) -> list[dict]:
        TRUSTED_SOURCES = {
            "modern retail", "retail dive", "business of fashion", "bloomberg",
            "reuters", "techcrunch", "wired", "forbes", "mckinsey", "gartner",
            "harvard business review", "wsj", "new york times",
        }
        STAT_PATTERNS = ["%", "$", "billion", "million", "x growth", "× ", "fold"]

        result = []
        for art in candidates:
            score = 40  # 기본
            src = art.get("source", "").lower()
            desc = (art.get("description") or "").lower()
            title = art.get("title", "").lower()
            combined = title + " " + desc

            if any(s in src for s in TRUSTED_SOURCES):
                score += 25
            if any(p in combined for p in STAT_PATTERNS):
                score += 20
            if any(kw in combined for kw in ["ai", "retail", "commerce", "shopping"]):
                score += 15

            art["_score"]  = min(score, 100)
            art["_reason"] = "규칙 기반 평가"
            result.append(art)

        return result

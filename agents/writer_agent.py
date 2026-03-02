"""
Writer Agent — GitHub Models (GPT-4o mini) 로 기사를 DB + blog.html 포맷으로 변환
비용: $0  /  기존 32개 기사를 few-shot 예시로 사용
"""

import json
import time

from openai import OpenAI

from pipeline.config import CATEGORIES, GITHUB_MODELS_ENDPOINT, WRITER_MODEL
from pipeline.utils import get_logger, next_article_id

log = get_logger("writer")

# ── Few-shot 예시 (기존 DB에서 카테고리별 1개씩 발췌) ─────────────────
FEW_SHOT_EXAMPLES = """
예시 1 (AI 쇼핑 어시스턴트):
{
  "id": "A001", "blog_category": "AI 쇼핑 어시스턴트", "region": "Global", "company": "Amazon",
  "title": "Why the AI Shopping Agent Wars Will Heat Up in 2026",
  "excerpt": "Amazon Rufus가 2025년 2억5천만 명 달성, MAU 140% 성장. 사용자는 전환율 60% 더 높고, 연간 $100억 증분 매출. Auto Buy로 자동 결제까지.",
  "source_url": "https://modernretail.co/...", "source_name": "Modern Retail",
  "date": "2026.01", "read_time": "4 min", "is_featured": false,
  "key_stat": "250M", "key_stat_label": "Users",
  "thumb_emoji": "🤖", "thumb_stat": "250M Users", "thumb_label": "Amazon Rufus", "grad": "cat-1",
  "tags": ["Amazon", "Rufus", "Agentic Commerce", "Auto Buy"]
}

예시 2 (데이터 & 리포트):
{
  "id": "A008", "blog_category": "데이터 & 리포트", "region": "Global", "company": "McKinsey",
  "title": "McKinsey: Agentic Commerce Will Generate $5 Trillion Globally by 2030",
  "excerpt": "McKinsey 보고서: AI 에이전트 기반 커머스가 2030년까지 전 세계 $5조 창출 전망. 리테일러 42%가 12개월 내 에이전틱 AI 도입 계획.",
  "source_url": "https://mckinsey.com/...", "source_name": "McKinsey & Company",
  "date": "2026.01", "read_time": "5 min", "is_featured": false,
  "key_stat": "$5T", "key_stat_label": "Global by 2030",
  "thumb_emoji": "📊", "thumb_stat": "$5T Market", "thumb_label": "McKinsey Report", "grad": "cat-7",
  "tags": ["McKinsey", "Market Forecast", "Agentic Commerce", "$5T"]
}

예시 3 (한국 사례):
{
  "id": "A025", "blog_category": "한국 사례", "region": "Korea", "company": "네이버",
  "title": "네이버 'AI 기업' 전환 선언—에이전트N 2026년 Q3 출시, 커머스 +26.2%",
  "excerpt": "네이버 AI 기업 공식 전환. 에이전트N이 쇼핑·검색·예약 통합 에이전트로 2026년 Q3 출시. 커머스 매출 26.2% 성장으로 AI 투자 성과 입증.",
  "source_url": "https://...", "source_name": "서울경제",
  "date": "2025.12", "read_time": "4 min", "is_featured": true,
  "key_stat": "+26.2%", "key_stat_label": "Commerce Growth",
  "thumb_emoji": "🇰🇷", "thumb_stat": "+26.2% 성장", "thumb_label": "네이버 에이전트N", "grad": "cat-6",
  "tags": ["네이버", "에이전트N", "AI 전환", "커머스 성장"]
}
"""

SYSTEM_PROMPT = f"""당신은 AI 리테일 전문 블로그의 기사 편집자입니다.
입력된 기사 정보를 아래 JSON 스키마로 변환하여 JSON 객체만 반환합니다.

=== 스키마 필드 설명 ===
- id: 지정해주는 값 사용
- blog_category: 7개 중 하나 ["AI 쇼핑 어시스턴트","AI 플랫폼 커머스","리테일러 AI 도입","브랜드 AI 마케팅/세일즈","GEO","한국 사례","데이터 & 리포트"]
- region: "Global" / "US" / "Korea" / "Europe" / 국가명
- company: 주요 기업/기관명 (1개)
- title: 원문 제목 유지 (영문이면 영문, 한국어면 한국어)
- excerpt: 한국어 80자 이내. 핵심 수치·인사이트 포함. AI/리테일 담당자에게 유용한 정보 중심.
- source_url: 원본 URL
- source_name: 미디어/출처명
- date: "YYYY.MM" 형식
- read_time: "N min" 형식 (기사 길이 추정)
- is_featured: false (항상)
- key_stat: 가장 임팩트 있는 단일 수치 1개 (예: "+35%", "$5T", "250M")
- key_stat_label: 수치 설명, 3단어 이내 영문 (예: "Order Value", "Users", "Market Size")
- thumb_emoji: 카테고리에 맞는 이모지 1개
- thumb_stat: 썸네일 표시용 수치 + 단위 (예: "+35% AOV", "250M Users")
- thumb_label: 썸네일 하단 라벨 (회사명 + 제품/주제, 20자 이내)
- grad: 카테고리별 그라디언트 클래스
  AI 쇼핑 어시스턴트→cat-1, AI 플랫폼 커머스→cat-2, 리테일러 AI 도입→cat-3,
  브랜드 AI 마케팅/세일즈→cat-4, GEO→cat-5, 한국 사례→cat-6, 데이터 & 리포트→cat-7
- tags: 2~4개 영문/한국어 태그 배열
- auto_collected: true
- collected_at: ISO 8601 타임스탬프 (지정해주는 값)

=== Few-shot 예시 ===
{FEW_SHOT_EXAMPLES}

JSON 객체만 반환. 추가 설명 불필요."""


class WriterAgent:
    """
    품질 통과 기사를 blog.html과 articles-db-v2.json의 정확한 포맷으로 변환.
    GITHUB_TOKEN 없으면 규칙 기반 폴백 사용.
    """

    def __init__(self, github_token: str, db: dict):
        self.token = github_token
        self.db    = db
        self.client = (
            OpenAI(base_url=GITHUB_MODELS_ENDPOINT, api_key=github_token)
            if github_token else None
        )

    # ── public ───────────────────────────────────────────────────────

    def format_articles(self, approved: list[dict]) -> list[dict]:
        results = []
        for art in approved:
            formatted = self._format_one(art)
            if formatted:
                results.append(formatted)
            time.sleep(3)  # GitHub Models RPM 제한

        log.info(f"Writer Agent — {len(results)}개 포맷 완료")
        return results

    # ── private: LLM 변환 ────────────────────────────────────────────

    def _format_one(self, art: dict) -> dict | None:
        new_id        = next_article_id(self.db)
        collected_at  = __import__("datetime").datetime.utcnow().isoformat() + "Z"

        user_msg = f"""아래 기사를 JSON 스키마로 변환해주세요.

id: {new_id}
collected_at: {collected_at}

기사 정보:
제목: {art['title']}
출처: {art['source']}
URL: {art['url']}
날짜: {art['date']}
설명: {art.get('description', '')[:400]}
주제 분류(참고): {art.get('topic', '')}
품질 평가 근거: {art.get('_reason', '')}"""

        if self.client:
            return self._llm_format(user_msg, new_id, art)
        else:
            return self._rule_format(art, new_id, collected_at)

    def _llm_format(self, user_msg: str, new_id: str, raw: dict) -> dict | None:
        try:
            resp = self.client.chat.completions.create(
                model=WRITER_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=600,
            )
            text = resp.choices[0].message.content.strip()
            if "```" in text:
                text = text.split("```")[1].lstrip("json").strip()
            obj = json.loads(text)
            # id가 LLM에 의해 바뀌지 않도록 강제
            obj["id"] = new_id
            # 가상 DB에 임시 등록 (다음 기사 ID 계산용)
            self.db["articles"].append({"id": new_id})
            return obj
        except Exception as e:
            log.warning(f"  LLM 포맷 실패 ({raw['title'][:30]}): {e} → 폴백")
            return self._rule_format(raw, new_id,
                                     __import__("datetime").datetime.utcnow().isoformat() + "Z")

    # ── private: 규칙 기반 폴백 ──────────────────────────────────────

    def _rule_format(self, art: dict, new_id: str, collected_at: str) -> dict:
        title    = art.get("title", "")
        desc     = art.get("description", "")
        source   = art.get("source", "Unknown")
        url      = art.get("url", "")
        raw_date = art.get("date", "")[:7].replace("-", ".")

        category = self._classify(title, desc)
        cat_cfg  = CATEGORIES[category]

        import re
        stats = re.findall(r'\d+\.?\d*\s*(?:%|billion|million|trillion|\$[\d.]+[BMT]?)', title + " " + desc)
        key_stat = stats[0].strip() if stats else "NEW"

        self.db["articles"].append({"id": new_id})
        return {
            "id":             new_id,
            "blog_category":  category,
            "region":         "Korea" if category == "한국 사례" else "Global",
            "company":        source,
            "title":          title,
            "excerpt":        (desc[:77] + "...") if len(desc) > 77 else desc or f"{source} 보도 기사",
            "source_url":     url,
            "source_name":    source,
            "date":           raw_date,
            "read_time":      "3 min",
            "is_featured":    False,
            "key_stat":       key_stat,
            "key_stat_label": "Key Metric",
            "thumb_emoji":    cat_cfg["emoji"],
            "thumb_stat":     key_stat,
            "thumb_label":    source[:20],
            "grad":           cat_cfg["grad"],
            "tags":           [source, category],
            "auto_collected": True,
            "collected_at":   collected_at,
        }

    @staticmethod
    def _classify(title: str, desc: str) -> str:
        text = (title + " " + desc).lower()
        scores: dict[str, int] = {}
        for cat, cfg in CATEGORIES.items():
            scores[cat] = sum(1 for kw in cfg["keywords"] if kw in text)
        best = max(scores, key=lambda k: scores[k])
        return best if scores[best] > 0 else "데이터 & 리포트"

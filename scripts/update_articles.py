#!/usr/bin/env python3
"""
AI Retail 기사 자동 수집 & DB 업데이트 스크립트
============================================
매일 GitHub Actions에서 실행되며:
  1. NewsAPI로 AI 리테일 관련 최신 기사 검색
  2. 중복 제거 후 articles-db-v2.json 업데이트
  3. (선택) OpenAI로 한국어 요약 생성

환경변수 설정 (GitHub Repository Secrets):
  - NEWS_API_KEY  : https://newsapi.org 에서 무료 발급 (필수)
  - OPENAI_API_KEY: GPT 요약 생성용 (선택, 없으면 원문 description 사용)

실행:
  python scripts/update_articles.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ── 경로 설정 ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
DB_PATH = ROOT_DIR / "articles-db-v2.json"

# ── 환경변수 ──────────────────────────────────────────────────────
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# ── 검색 쿼리 목록 ────────────────────────────────────────────────
SEARCH_QUERIES = [
    "AI shopping assistant ecommerce",
    "artificial intelligence retail personalization",
    "generative AI commerce platform",
    "AI retail technology adoption",
    "agentic commerce AI agent",
    "GEO generative engine optimization retail",
    "AI 쇼핑 리테일",           # 한국어 검색 (NewsAPI에서 지원)
]

# ── 카테고리 키워드 매핑 ──────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "AI 쇼핑 어시스턴트": [
        "shopping assistant", "chatbot", "conversational commerce",
        "rufus", "perplexity shopping", "claude shopping", "agentic commerce",
        "ai chat", "voice shopping"
    ],
    "AI 플랫폼 커머스": [
        "shopify", "salesforce commerce", "adobe commerce", "platform",
        "ecommerce platform", "magento", "commercetools", "headless"
    ],
    "리테일러 AI 도입": [
        "walmart", "target", "amazon", "kroger", "costco", "best buy",
        "retailer adopts", "store ai", "retail adoption", "in-store ai"
    ],
    "브랜드 AI 마케팅/세일즈": [
        "marketing ai", "ai advertising", "content generation", "personalized ad",
        "brand ai", "campaign", "ai copywriting", "product description ai"
    ],
    "GEO": [
        "generative engine optimization", "geo seo", "llm search",
        "ai search visibility", "chatgpt shopping", "perplexity brand"
    ],
    "한국 사례": [
        "naver", "kakao", "coupang", "lotte", "shinsegae", "hyundai shopping",
        "korea", "korean retail", "네이버", "카카오", "쿠팡"
    ],
    "데이터 & 리포트": [
        "report", "survey", "study", "research", "statistics", "forecast",
        "market size", "mckinsey", "gartner", "deloitte", "capgemini", "pwc"
    ],
}

# ── 카테고리별 썸네일 메타데이터 ──────────────────────────────────
THUMBNAIL_META = {
    "AI 쇼핑 어시스턴트":      {"emoji": "🛒", "gradient": "cat-1"},
    "AI 플랫폼 커머스":        {"emoji": "🔮", "gradient": "cat-2"},
    "리테일러 AI 도입":        {"emoji": "🏪", "gradient": "cat-3"},
    "브랜드 AI 마케팅/세일즈": {"emoji": "📢", "gradient": "cat-4"},
    "GEO":                    {"emoji": "🌐", "gradient": "cat-5"},
    "한국 사례":               {"emoji": "🇰🇷", "gradient": "cat-6"},
    "데이터 & 리포트":         {"emoji": "📊", "gradient": "cat-7"},
}


# ════════════════════════════════════════════════════════════════
# DB 유틸
# ════════════════════════════════════════════════════════════════

def load_db() -> dict:
    if DB_PATH.exists():
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # 빈 DB 구조 초기화
    return {
        "metadata": {
            "version": "2.0",
            "created": datetime.now().isoformat(),
            "last_updated": "",
            "total_articles": 0,
        },
        "articles": [],
    }


def save_db(db: dict):
    db.setdefault("metadata", {})
    db["metadata"]["last_updated"] = datetime.now().isoformat()
    db["metadata"]["total_articles"] = len(db["articles"])
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"✅ DB 저장 완료: {len(db['articles'])}개 기사")


def get_existing_urls(db: dict) -> set:
    urls = set()
    for art in db.get("articles", []):
        for key in ("url", "source_url"):
            if art.get(key):
                urls.add(art[key])
    return urls


def next_article_id(db: dict) -> str:
    nums = []
    for art in db.get("articles", []):
        aid = art.get("id", "A000")
        try:
            nums.append(int(aid[1:]))
        except ValueError:
            pass
    return f"A{(max(nums, default=0) + 1):03d}"


# ════════════════════════════════════════════════════════════════
# 분류 & 처리
# ════════════════════════════════════════════════════════════════

def classify_category(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score:
            scores[cat] = score
    return max(scores, key=scores.get) if scores else "데이터 & 리포트"


def make_excerpt(description: str, source: str) -> str:
    if not description:
        return f"{source} 보도 — AI 리테일 관련 최신 동향"
    return description[:80] + ("..." if len(description) > 80 else "")


def summarize_with_openai(title: str, description: str) -> str:
    """OpenAI API로 80자 한국어 요약 생성 (선택적)"""
    if not OPENAI_API_KEY:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f"다음 영문 기사를 80자 이내 한국어로 요약해주세요. "
                    f"마케터/리테일러 관점에서 핵심 인사이트 중심으로.\n\n"
                    f"제목: {title}\n설명: {description}"
                )
            }],
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip()[:80]
    except Exception as e:
        print(f"  ⚠️ OpenAI 요약 실패: {e}")
        return ""


# ════════════════════════════════════════════════════════════════
# NewsAPI 연동
# ════════════════════════════════════════════════════════════════

def fetch_newsapi(query: str, from_date: str) -> list:
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "from": from_date,
                "sortBy": "publishedAt",
                "pageSize": 10,
                "apiKey": NEWS_API_KEY,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("articles", [])
    except Exception as e:
        print(f"  ⚠️ NewsAPI 오류 ({query[:30]}): {e}")
        return []


def process_raw_article(raw: dict, db: dict, existing_urls: set) -> dict | None:
    url = raw.get("url", "")
    if not url or url in existing_urls or raw.get("title") == "[Removed]":
        return None

    title = raw.get("title", "").strip()
    if not title:
        return None

    description = (raw.get("description") or "").strip()
    source = raw.get("source", {}).get("name", "Unknown")
    published = (raw.get("publishedAt") or "")[:10]

    category = classify_category(title, description)
    thumb = THUMBNAIL_META.get(category, {"emoji": "📰", "gradient": "cat-1"})

    # 한국어 요약: OpenAI 우선, 없으면 원문 발췌
    excerpt = summarize_with_openai(title, description) or make_excerpt(description, source)

    article = {
        "id": next_article_id(db),
        "title": title,
        "source": source,
        "source_url": url,
        "url": url,
        "date": published,
        "region": "한국" if category == "한국 사례" else "Global",
        "blog_category": category,
        "excerpt_short": excerpt,
        "read_time": "3 min read",
        "is_featured": False,
        "thumbnail": {
            "type": "generated",
            "emoji": thumb["emoji"],
            "stat": source,
            "label": category,
            "gradient": thumb["gradient"],
        },
        "auto_collected": True,
        "collected_at": datetime.now().isoformat(),
    }

    # DB에 즉시 추가하고 URL 집합 갱신 (같은 실행 내 중복 방지)
    db["articles"].append(article)
    existing_urls.add(url)
    return article


# ════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════

def main() -> int:
    print("=" * 60)
    print("🤖 AI Retail 기사 자동 수집 시작")
    print(f"   실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not NEWS_API_KEY:
        print()
        print("❌ NEWS_API_KEY 가 설정되지 않았습니다.")
        print()
        print("   ▶ 설정 방법:")
        print("   1. https://newsapi.org 에서 무료 API 키 발급")
        print("   2. GitHub 레포 → Settings → Secrets and variables → Actions")
        print("   3. 'New repository secret' 클릭")
        print("   4. Name: NEWS_API_KEY  /  Value: 발급받은 키 입력")
        print()
        print("   ※ 키 없이는 기사 수집을 건너뜁니다.")
        return 0

    db = load_db()
    existing_urls = get_existing_urls(db)
    from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"\n📅 검색 기간: {from_date} ~ 오늘")
    print(f"📚 기존 기사 수: {len(db['articles'])}개\n")

    new_articles: list[dict] = []

    for query in SEARCH_QUERIES:
        print(f"🔍 검색: {query}")
        raw_list = fetch_newsapi(query, from_date)
        for raw in raw_list:
            art = process_raw_article(raw, db, existing_urls)
            if art:
                new_articles.append(art)
                print(f"  ✅ 추가: [{art['blog_category']}] {art['title'][:55]}...")

    print()
    if new_articles:
        save_db(db)
        print(f"\n🎉 {len(new_articles)}개 새 기사 추가 완료!")
    else:
        print("📭 추가된 새 기사가 없습니다 (이미 최신 상태).")

    print("=" * 60)
    return len(new_articles)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)

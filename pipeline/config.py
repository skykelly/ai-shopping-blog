"""
파이프라인 설정값 — 주제·키워드·품질 기준·카테고리 매핑
수정이 필요할 때 이 파일만 변경하면 됩니다.
"""

# ── 검색 대주제 × 쿼리 ──────────────────────────────────────────────
SEARCH_TOPICS = [
    {
        "topic": "Agentic Shopping",
        "queries": [
            "agentic commerce AI agent auto purchase 2026",
            "AI shopping agent completes purchase autonomously",
            "agentic AI retail checkout automation",
        ],
    },
    {
        "topic": "AI 플랫폼 커머스 진출",
        "queries": [
            "OpenAI Google Meta Apple commerce platform 2026",
            "ChatGPT Perplexity shopping checkout integration",
            "big tech AI platform ecommerce launch",
        ],
    },
    {
        "topic": "Future of AI Shopping",
        "queries": [
            "future of AI shopping retail forecast 2026 2027",
            "AI retail market report McKinsey Gartner 2026",
            "conversational commerce personalization trends",
        ],
    },
    {
        "topic": "브랜드사 AI 기술 활용",
        "queries": [
            "brand AI marketing product recommendation 2026",
            "Nike Zara HM Loreal AI technology campaign",
            "generative AI fashion luxury brand retail",
        ],
    },
    {
        "topic": "Retail 업체 AI 기술 활용",
        "queries": [
            "retailer AI adoption store technology 2026",
            "Walmart Target Amazon Kroger AI in-store",
            "department store ecommerce AI personalization deployment",
        ],
    },
]

# ── 7개 카테고리 설정 ────────────────────────────────────────────────
CATEGORIES = {
    "AI 쇼핑 어시스턴트": {
        "grad": "cat-1",
        "emoji": "🛒",
        "keywords": [
            "shopping assistant", "chatbot", "conversational", "agentic commerce",
            "auto buy", "auto purchase", "voice shopping", "rufus", "sparky",
        ],
    },
    "AI 플랫폼 커머스": {
        "grad": "cat-2",
        "emoji": "🔮",
        "keywords": [
            "platform", "chatgpt commerce", "openai shop", "google shopping",
            "checkout api", "instant checkout", "perplexity", "alexa",
        ],
    },
    "리테일러 AI 도입": {
        "grad": "cat-3",
        "emoji": "🏪",
        "keywords": [
            "walmart", "target", "kroger", "costco", "best buy", "retailer",
            "in-store ai", "store technology", "brick and mortar",
        ],
    },
    "브랜드 AI 마케팅/세일즈": {
        "grad": "cat-4",
        "emoji": "📢",
        "keywords": [
            "brand ai", "ai marketing", "ad campaign", "content generation",
            "nike", "zara", "hm", "loreal", "fashion ai", "personalized ad",
        ],
    },
    "GEO": {
        "grad": "cat-5",
        "emoji": "🌐",
        "keywords": [
            "geo", "generative engine optimization", "ai search visibility",
            "llm seo", "chatgpt brand mention", "perplexity seo",
        ],
    },
    "한국 사례": {
        "grad": "cat-6",
        "emoji": "🇰🇷",
        "keywords": [
            "naver", "kakao", "coupang", "lotte", "shinsegae", "hyundai",
            "korea", "korean retail", "ssg", "gs", "homeplus",
        ],
    },
    "데이터 & 리포트": {
        "grad": "cat-7",
        "emoji": "📊",
        "keywords": [
            "report", "survey", "research", "forecast", "statistics",
            "mckinsey", "gartner", "deloitte", "capgemini", "adobe analytics",
        ],
    },
}

# ── 품질 평가 기준 (Quality Agent) ──────────────────────────────────
QUALITY_THRESHOLD = 65          # 100점 만점, 이 이상만 등록
MIN_ARTICLES_PER_RUN = 1        # 하루 최소 등록 수 (0개라도 허용하려면 0)
MAX_ARTICLES_PER_RUN = 5        # 하루 최대 등록 수

# ── NewsAPI 설정 ─────────────────────────────────────────────────────
NEWS_LOOKBACK_DAYS = 3          # 며칠치 기사를 검색할지
NEWS_PAGE_SIZE     = 5          # 쿼리당 최대 결과 수 (무료 티어 부담 최소화)

# ── GitHub Models (검색 제외 모든 LLM 처리) ─────────────────────────
GITHUB_MODELS_ENDPOINT = "https://models.inference.ai.azure.com"
QUALITY_MODEL = "gpt-4o-mini"   # 품질 평가 — 저렴·빠름
WRITER_MODEL  = "gpt-4o-mini"   # 포맷 변환 + 한국어 요약

# ── 경로 ────────────────────────────────────────────────────────────
import pathlib
ROOT_DIR     = pathlib.Path(__file__).parent.parent
DB_PATH      = ROOT_DIR / "articles-db-v2.json"
BLOG_PATH    = ROOT_DIR / "blog.html"
LOG_PATH     = ROOT_DIR / "pipeline-run.log"

# blog.html 내 ARTICLES 배열 교체용 마커
MARKER_START = "/* ARTICLES_DATA_START */"
MARKER_END   = "/* ARTICLES_DATA_END */"

# AI×Retail Blog — 일별 자동화 파이프라인 설계 계획
> 작성일: 2026-03-02 | 버전: v1.0

---

## 0. 목표 요약

| 항목 | 내용 |
|---|---|
| 실행 시각 | 매일 한국 시간 오후 4시 (UTC 07:00) |
| 기사 수 | 하루 1~5개 신규 기사 추가 |
| 탐색 주제 | 5개 대주제 + 7개 카테고리 태그 기반 |
| 품질 기준 | 기존 32개 기사와 동일한 수준 (실제 수치 포함, 유명 미디어 출처) |
| 중복 방지 | URL + 제목 유사도 체크 |
| 블로그 반영 | 기존 blog.html 디자인·포맷 동일하게 자동 생성·추가 |
| 배포 | GitHub Actions → GitHub Pages 자동 배포 |

---

## 1. 탐색 대상 주제

### 1-1. 5개 대주제 (매일 우선 탐색)

| # | 대주제 | 설명 | 검색 키워드 예시 |
|---|---|---|---|
| T1 | **Agentic Shopping** | AI 에이전트가 대신 쇼핑하는 새로운 패러다임 | "agentic commerce 2026", "AI shopping agent auto-buy", "AI completes purchase" |
| T2 | **AI 플랫폼의 커머스 진출** | OpenAI, Google, Meta 등 빅테크의 커머스 진입 | "OpenAI commerce", "Google shopping AI", "ChatGPT checkout", "LLM platform retail" |
| T3 | **Future of AI Shopping** | AI가 바꾸는 쇼핑의 미래 트렌드·전망 리포트 | "future of AI shopping 2026", "retail AI forecast", "AI retail report" |
| T4 | **브랜드사의 AI 기술 활용** | Nike, Zara, L'Oréal 등 브랜드의 AI 마케팅·판매 적용 | "brand AI marketing 2026", "AI product recommendation brand", "generative AI fashion" |
| T5 | **Retail 업체의 AI 기술 활용** | 유통사(백화점, 이커머스 등)의 AI 도입·성과 사례 | "retailer AI adoption", "department store AI", "ecommerce AI personalization" |

### 1-2. 7개 카테고리 태그 (분류 기준)

| 태그 | 색상 클래스 | 대표 키워드 |
|---|---|---|
| AI 쇼핑 어시스턴트 | cat-1 | shopping assistant, chatbot, agentic commerce |
| AI 플랫폼 커머스 | cat-2 | platform, checkout, ChatGPT, Google |
| 리테일러 AI 도입 | cat-3 | retailer, in-store AI, adoption |
| 브랜드 AI 마케팅/세일즈 | cat-4 | brand, marketing, ad, content AI |
| GEO | cat-5 | generative engine optimization, AI search |
| 한국 사례 | cat-6 | 네이버, 카카오, 현대, 롯데, 쿠팡 |
| 데이터 & 리포트 | cat-7 | McKinsey, Gartner, report, forecast |

---

## 2. 멀티 서브 에이전트 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Cron (매일 16:00 KST / UTC 07:00)          │
│                          │                                   │
│              ┌───────────▼────────────┐                     │
│              │   Coordinator Agent    │  ← 전체 파이프라인   │
│              │  (orchestrator.py)     │    지휘·상태 관리    │
│              └──┬──────┬──────┬──────┘                     │
│                 │      │      │                              │
│        ┌────────▼─┐ ┌──▼──────┐ ┌──▼────────┐             │
│        │  Search  │ │Quality  │ │  Writer   │             │
│        │  Agent   │ │ Agent   │ │  Agent    │             │
│        │          │ │         │ │           │             │
│        │웹 검색   │ │관련성   │ │DB 포맷    │             │
│        │기사 수집 │ │품질평가 │ │요약 생성  │             │
│        └────────┬─┘ └──┬──────┘ └──┬────────┘             │
│                 │      │            │                        │
│              ┌──▼──────▼────────────▼──┐                   │
│              │     Publisher Agent      │                   │
│              │                          │                   │
│              │  articles-db-v2.json 업데이트               │
│              │  blog.html 신규 카드 삽입                    │
│              │  git commit + push                           │
│              │  GitHub Pages 자동 재배포                    │
│              └──────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 2-1. 에이전트별 역할 정의

#### 🔍 Search Agent (`agents/search_agent.py`)
**역할**: 5개 대주제 × n개 쿼리로 후보 기사를 수집

- **입력**: 탐색 주제 목록, 기존 기사 URL 목록
- **도구**: Perplexity API (추천) 또는 SerpAPI / Google Custom Search
- **출력**: 후보 기사 리스트 `[{title, url, source, date, snippet}]`
- **로직**:
  1. 5개 대주제 × 3개 쿼리 = 최대 15개 쿼리 실행
  2. 각 쿼리에서 최대 5개 결과 수집 (총 최대 75개 후보)
  3. URL 기반 1차 중복 제거 (기존 DB 대조)
  4. 최근 30일 이내 기사만 통과

```python
class SearchAgent:
    def run(self, topics: list[str], existing_urls: set) -> list[dict]:
        ...
```

---

#### ✅ Quality Agent (`agents/quality_agent.py`)
**역할**: 후보 기사를 평가하여 기존 32개와 동일한 수준만 통과

- **입력**: 후보 기사 리스트
- **도구**: Claude API (Sonnet) — 품질 평가 프롬프트
- **출력**: 점수 기반 필터링된 기사 리스트 (최대 5개)
- **평가 기준** (100점 만점):

| 기준 | 배점 | 설명 |
|---|---|---|
| 출처 신뢰도 | 25점 | 유명 미디어/기업 공식 블로그/리서치 기관 |
| 구체적 수치 | 25점 | 퍼센트, 금액, 사용자 수 등 key_stat 추출 가능 |
| 주제 관련성 | 25점 | 5개 대주제 또는 7개 카테고리와의 직접 연관성 |
| 신선도 | 15점 | 최신성 (최근 7일 > 30일 > 90일) |
| 중복성 | 10점 | 기존 32개 기사와 다른 각도/회사/사례 |

- **통과 기준**: 70점 이상 기사만 DB 등록
- **하루 최대 5개, 최소 1개** (70점 이상 없으면 가장 높은 1개 선택)

```python
class QualityAgent:
    def evaluate(self, candidates: list[dict], existing_articles: list[dict]) -> list[dict]:
        # Claude API로 배치 평가
        ...
```

---

#### ✍️ Writer Agent (`agents/writer_agent.py`)
**역할**: 통과된 기사를 articles-db-v2.json의 정확한 포맷으로 변환

- **입력**: 품질 통과 기사 리스트
- **도구**: Claude API (Sonnet) — 정보 추출 + 한국어 요약 생성
- **출력**: DB 등록 준비된 article JSON 객체

**생성 필드 목록**:

```json
{
  "id": "A033",                          // 자동 증분
  "blog_category": "AI 쇼핑 어시스턴트",  // 7개 카테고리 중 1개
  "region": "Global",                    // 국가 판단
  "company": "Amazon",                   // 주요 기업명 추출
  "product": "Rufus 2.0",               // 제품/서비스명 (있을 경우)
  "title": "...",                        // 원문 제목 (영문/한문 유지)
  "excerpt": "...",                      // 80자 한국어 핵심 인사이트 요약
  "source_url": "https://...",
  "source_name": "Modern Retail",
  "date": "2026.03",
  "read_time": "3 min",
  "is_featured": false,
  "key_stat": "+42%",                    // 가장 임팩트 있는 수치 1개
  "key_stat_label": "Conversion Rate",  // 수치 설명 (3단어 이내)
  "thumbnail": {
    "type": "generated",
    "emoji": "🛒",                       // 카테고리별 이모지
    "stat": "+42% CVR",                  // 썸네일 표시 수치
    "label": "Amazon Rufus 2.0",        // 썸네일 하단 라벨
    "gradient": "cat-1"                  // 카테고리별 그라디언트
  },
  "tags": ["Amazon", "Rufus", "Agentic Commerce", "2026"],
  "auto_collected": true,
  "collected_at": "2026-03-02T07:00:00"
}
```

**Writer Agent 프롬프트 전략**:
- 기존 32개 기사를 few-shot 예시로 제공
- "key_stat는 기사에서 가장 임팩트 있는 단일 숫자 1개를 추출하라"
- "excerpt는 한국어 마케터/리테일러에게 유용한 핵심 인사이트 80자 이내"
- "tags는 기존 태그 목록과 일관성 유지, 2~4개"

---

#### 📤 Publisher Agent (`agents/publisher_agent.py`)
**역할**: DB 업데이트 + blog.html에 신규 카드 삽입 + 배포

- **입력**: Writer Agent가 생성한 article JSON 리스트
- **출력**: 업데이트된 `articles-db-v2.json` + `blog.html`

**Publisher 로직**:

```
1. articles-db-v2.json에 신규 기사 append
2. blog.html의 <!-- ARTICLES_DATA --> 마커를 찾아
   JavaScript articles 배열 업데이트
3. blog.html stats 섹션 업데이트 (총 기사 수)
4. git add + commit + push
5. GitHub Actions deploy.yml 트리거 (자동 재배포)
```

**blog.html 업데이트 전략**:
- blog.html 내 `const articles = [...]` 배열을 정규식으로 탐색
- 배열 끝에 신규 기사 객체 삽입
- stats ticker 숫자 업데이트 (`32 Articles` → `34 Articles`)
- 기존 is_featured 기사는 유지 (신규는 false)

---

#### 🎯 Coordinator (`pipeline/coordinator.py`)
**역할**: 전체 에이전트 실행 순서 조율 + 로깅 + 에러 핸들링

```python
class Coordinator:
    def run(self):
        log("🚀 파이프라인 시작")

        # 1. 기존 DB 로드
        db = load_db()
        existing_urls = get_existing_urls(db)

        # 2. Search Agent 실행
        candidates = SearchAgent().run(TOPICS, existing_urls)
        log(f"  후보 기사: {len(candidates)}개")

        # 3. Quality Agent 실행
        approved = QualityAgent().evaluate(candidates, db['articles'])
        log(f"  통과 기사: {len(approved)}개")

        # 4. Writer Agent 실행
        formatted = WriterAgent().format(approved, db['articles'])
        log(f"  포맷 완료: {len(formatted)}개")

        # 5. Publisher Agent 실행
        PublisherAgent().publish(formatted, db)

        log("✅ 파이프라인 완료")
```

---

## 3. 파일 구조

```
ai-shopping-blog/
├── .github/
│   └── workflows/
│       ├── deploy.yml                  # [기존] push 시 배포
│       └── update-articles.yml        # [수정] 일별 파이프라인 실행
│
├── agents/
│   ├── __init__.py
│   ├── search_agent.py                # 웹 검색 + 후보 수집
│   ├── quality_agent.py               # Claude API 품질 평가
│   ├── writer_agent.py                # Claude API 포맷 변환 + 요약
│   └── publisher_agent.py             # DB + HTML 업데이트
│
├── pipeline/
│   ├── __init__.py
│   ├── coordinator.py                 # 에이전트 오케스트레이션
│   ├── config.py                      # 설정값 (주제, 기준 등)
│   └── utils.py                       # 공통 유틸 (로거, DB 로더 등)
│
├── scripts/
│   ├── update_articles.py             # [기존, 레거시] 유지
│   └── requirements.txt               # [수정] 의존성 추가
│
├── articles-db-v2.json                # 기사 DB (자동 업데이트)
├── blog.html                          # 블로그 (자동 업데이트)
├── ai-shopping-v4.html                # 메인 소개 페이지
└── index.html                         # 리다이렉트
```

---

## 4. GitHub Actions 워크플로우 수정

```yaml
# .github/workflows/update-articles.yml

name: 🤖 Daily Article Pipeline

on:
  schedule:
    - cron: "0 7 * * *"   # 매일 UTC 07:00 = 한국 시간 16:00
  workflow_dispatch:        # 수동 실행 가능

jobs:
  pipeline:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pages: write
      id-token: write

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r scripts/requirements.txt

      - name: Run pipeline
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
          # NEWS_API_KEY: ${{ secrets.NEWS_API_KEY }}  # 대체 검색 소스
        run: python pipeline/coordinator.py

      - name: Commit & push if changed
        run: |
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git config user.name "github-actions[bot]"
          git add articles-db-v2.json blog.html
          git diff --staged --quiet || \
            git commit -m "🤖 $(date +'%Y-%m-%d') 자동 기사 업데이트"
          git push

      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with: { path: "." }
      - uses: actions/deploy-pages@v4
```

---

## 5. 필요 API 키 (GitHub Secrets 등록)

| Secret 이름 | 용도 | 발급처 | 무료 여부 |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Quality Agent + Writer Agent (핵심) | console.anthropic.com | 유료 (필수) |
| `PERPLEXITY_API_KEY` | Search Agent — 웹 검색 (추천) | perplexity.ai/settings/api | 유료 ($5/mo) |
| `NEWS_API_KEY` | Search Agent — 대체 검색 소스 | newsapi.org | 무료 티어 |

**권장 조합**: Anthropic API + Perplexity API
**최소 구성**: Anthropic API만으로 동작 (검색 없이 Claude web_search 툴 사용)

---

## 6. 중복 방지 전략

### 6-1. URL 정규화 + 매칭
```python
def normalize_url(url: str) -> str:
    # 쿼리스트링, utm 파라미터, trailing slash 제거
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))
```

### 6-2. 제목 유사도 체크 (Levenshtein / 코사인 유사도)
```python
def is_duplicate_title(new_title: str, existing_titles: list[str]) -> bool:
    # 80% 이상 유사하면 중복으로 판단
    ...
```

### 6-3. 기업+이벤트 조합 중복 방지
- 동일 기업(company) + 동일 분기(date) 기사는 Quality Agent가 감점

---

## 7. blog.html 자동 업데이트 전략

### 현재 구조
blog.html은 `const articles = [...]` JavaScript 배열에 모든 기사 데이터를 내장.

### 업데이트 방법
Publisher Agent가 아래 마커를 활용해 배열을 교체:

```javascript
// blog.html 내 마커 추가 (구현 시)
/* ARTICLES_DATA_START */
const articles = [ ... ];
/* ARTICLES_DATA_END */
```

```python
# publisher_agent.py
import re, json

def update_blog_html(new_articles: list, html_path: str):
    with open(html_path, 'r') as f:
        html = f.read()

    # 기존 배열 추출
    pattern = r'/\* ARTICLES_DATA_START \*/(.*?)/\* ARTICLES_DATA_END \*/'
    match = re.search(pattern, html, re.DOTALL)
    existing_data = json.loads(match.group(1).strip().replace('const articles = ', '').rstrip(';'))

    # 신규 기사 앞에 추가 (최신 기사가 상단에)
    updated = new_articles + existing_data

    new_block = f"""/* ARTICLES_DATA_START */
const articles = {json.dumps(updated, ensure_ascii=False, indent=2)};
/* ARTICLES_DATA_END */"""

    html = re.sub(pattern, new_block, html, flags=re.DOTALL)

    # stats ticker 업데이트
    html = re.sub(r'\d+ Articles', f'{len(updated)} Articles', html)

    with open(html_path, 'w') as f:
        f.write(html)
```

---

## 8. 구현 단계 (체크리스트)

### Phase 1: 기반 구조 구축
- [ ] `pipeline/config.py` — 주제, 카테고리, 품질 기준 설정값
- [ ] `pipeline/utils.py` — DB 로더, 로거, URL 정규화
- [ ] `pipeline/coordinator.py` — 에이전트 오케스트레이션
- [ ] `scripts/requirements.txt` 업데이트 (anthropic, perplexity 추가)

### Phase 2: Search Agent 구현
- [ ] `agents/search_agent.py` — Perplexity API 연동
- [ ] 5개 대주제 × 3개 쿼리 생성 로직
- [ ] 후보 기사 수집 + 1차 필터링 (날짜, URL 중복)

### Phase 3: Quality + Writer Agent 구현
- [ ] `agents/quality_agent.py` — Claude API 품질 평가 (배치)
- [ ] `agents/writer_agent.py` — 포맷 변환 + 한국어 요약 (few-shot)
- [ ] 기존 32개 기사를 few-shot 예시로 활용하는 프롬프트 설계

### Phase 4: Publisher Agent + blog.html 마커 추가
- [ ] `blog.html`에 `/* ARTICLES_DATA_START/END */` 마커 삽입
- [ ] `agents/publisher_agent.py` — JSON + HTML 업데이트 로직
- [ ] git 커밋 + push 자동화

### Phase 5: GitHub Actions + 통합 테스트
- [ ] `.github/workflows/update-articles.yml` 수정
- [ ] GitHub Secrets에 API 키 등록
  - `ANTHROPIC_API_KEY`
  - `PERPLEXITY_API_KEY` (선택)
- [ ] `workflow_dispatch`로 수동 테스트 실행
- [ ] 결과 검증 (기사 품질, HTML 렌더링, 중복 없음)

### Phase 6: 모니터링
- [ ] GitHub Actions 실행 로그 정기 확인
- [ ] 품질 기준 미달 시 알림 (선택: GitHub Issues 자동 생성)
- [ ] 월 1회 프롬프트 & 쿼리 리뷰

---

## 9. 예상 비용

| 항목 | 일일 예상 | 월간 예상 |
|---|---|---|
| Claude API (Sonnet) | ~$0.05–0.15 | ~$2–5 |
| Perplexity API | ~$0.01–0.03 | ~$0.3–1 |
| GitHub Actions | 무료 (2,000분/월 이내) | $0 |
| **합계** | **~$0.06–0.18** | **~$2–6** |

---

## 10. 리스크 & 대응책

| 리스크 | 대응 |
|---|---|
| 검색 결과 품질 저하 | Quality Agent 통과 기준 조정 + 쿼리 다양화 |
| API 키 소진 / 오류 | 재시도 로직 + 실패 시 GitHub Issue 자동 생성 |
| blog.html 파싱 실패 | 마커 기반 안전한 교체 + 백업 파일 유지 |
| 저품질 기사 자동 등록 | 70점 미만 전부 기각 (하루 0개 등록도 허용) |
| 중복 기사 | URL 정규화 + 제목 유사도 이중 체크 |

---

*다음 단계: Phase 1 구현 시작 — `pipeline/config.py` → `utils.py` → `coordinator.py` → 각 에이전트 순서로 진행*

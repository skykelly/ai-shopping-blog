# AI Shopping Blog Page — 실행 계획
> 작성일: 2026-03-02 | 담당: Claude (Cowork)

---

## 0. 참고 구조: PayPal Newsroom (newsroom.paypal-corp.com/stories)

PayPal Newsroom의 핵심 UX 패턴:
- **고정 헤더**: 로고 + 카테고리 필터 pill 탭 (수평 스크롤)
- **히어로 카드**: 최신/주요 기사 1~2개 — 와이드 썸네일 + 카테고리 태그 + 제목 + 날짜 + 요약 + Read More
- **카드 그리드**: 3열 균등 그리드 — 각 카드에 썸네일(16:9), 카테고리 뱃지, 제목, 날짜, 요약 70자, Read More
- **로드 더보기**: "Load More" 버튼 (무한 스크롤 X)
- **태그 필터**: 클릭 시 해당 카테고리만 필터링 (JS 클라이언트 사이드)
- **카드 호버**: 썸네일 줌, 타이틀 색상 변화, 화살표 이동

---

## 1. 최종 산출물

| 파일명 | 설명 |
|---|---|
| `articles-db-v2.json` | 개선된 기사 DB (썸네일 정보, 7개 카테고리, 발췌문 포함) |
| `blog.html` | 완성된 블로그 페이지 (v4 디자인 시스템 적용) |
| `plan.md` | 본 파일 — 작업 관리 |

---

## 2. DB 개선 사항 (articles-db → articles-db-v2)

### 2-1. 카테고리 재분류: 6개 → 7개

현재 DB의 "리테일러 AI 도입" 카테고리에서 데이터/리포트 중심 기사를 분리:

| 기존 | 새 카테고리 | 대상 기사 |
|---|---|---|
| 리테일러 AI 도입 | **데이터 & 리포트** | A008(McKinsey), A009(Gartner), A010(Adobe), A011(Capgemini), A013(Personalization Stats) |
| 리테일러 AI 도입 | 리테일러 AI 도입 (유지) | A012(Deloitte), A029(Pushback), A030(Commercetools) |

**7개 최종 카테고리:**
1. AI 쇼핑 어시스턴트 — 3건
2. AI 플랫폼 커머스 — 5건
3. 리테일러 AI 도입 — 4건
4. 브랜드 AI 마케팅/세일즈 — 6건
5. GEO — 2건
6. 한국 사례 — 9건
7. 데이터 & 리포트 — 5건 (신설)

### 2-2. 각 기사에 추가할 필드

```json
{
  "blog_category": "AI 쇼핑 어시스턴트",   // 7개 중 하나 (필터 태그용)
  "excerpt_short": "...",                  // 카드 본문용 80자 한국어 요약
  "read_time": "3 min read",
  "is_featured": false,                    // 히어로 카드 여부 (상위 3건만 true)
  "thumbnail": {
    "type": "generated",                   // 모두 CSS/Canvas 생성 (외부 이미지 불가)
    "emoji": "🛒",                         // 썸네일 중앙 대형 이모지
    "stat": "250M Users",                  // 썸네일에 표시할 핵심 수치
    "label": "Amazon Rufus",               // 썸네일 하단 라벨
    "gradient": "cat-1"                    // 카테고리별 그라디언트 클래스
  }
}
```

### 2-3. 카테고리별 그라디언트 색상

| 카테고리 | 클래스 | 색상 |
|---|---|---|
| AI 쇼핑 어시스턴트 | cat-1 | `#7c3aed → #e879f9` (purple → plasma) |
| AI 플랫폼 커머스 | cat-2 | `#1d4ed8 → #7c3aed` (blue → purple) |
| 리테일러 AI 도입 | cat-3 | `#5b21b6 → #0f0a1e` (deep purple → void) |
| 브랜드 AI 마케팅/세일즈 | cat-4 | `#d946ef → #f43f5e` (fuchsia → rose) |
| GEO | cat-5 | `#059669 → #7c3aed` (emerald → purple) |
| 한국 사례 | cat-6 | `#ea580c → #d946ef` (orange → fuchsia) |
| 데이터 & 리포트 | cat-7 | `#0891b2 → #7c3aed` (cyan → purple) |

---

## 3. 블로그 페이지 구조 (PayPal Newsroom 참고)

### 3-1. 레이아웃 와이어프레임

```
┌─────────────────────────────────────────────────────────────┐
│ NAV: AI×RETAIL BLOG  [All][쇼핑 어시스턴트][플랫폼]...  🔍 │ ← sticky
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HERO SECTION                                               │
│  ┌─────────────────────────┐  ┌────────────┐ ┌────────────┐│
│  │                         │  │  Featured  │ │  Featured  ││
│  │  HERO FEATURED ARTICLE  │  │  Card 2    │ │  Card 3    ││
│  │  (large 2/3 width)      │  │  (1/3)     │ │  (1/3)     ││
│  └─────────────────────────┘  └────────────┘ └────────────┘│
│                                                             │
├──────── STATS TICKER ────────────────────────────────────────│
│   32 Articles  ·  7 Categories  ·  Global + Korea  ·  2026  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FILTER PILLS: [All] [AI 쇼핑] [플랫폼] [리테일러] ...      │
│                                                             │
│  ARTICLE GRID (3 columns)                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ thumbnail│  │ thumbnail│  │ thumbnail│                  │
│  │ [태그]   │  │ [태그]   │  │ [태그]   │                  │
│  │ Title    │  │ Title    │  │ Title    │                  │
│  │ Date     │  │ Date     │  │ Date     │                  │
│  │ Excerpt  │  │ Excerpt  │  │ Excerpt  │                  │
│  │ Read More│  │ Read More│  │ Read More│                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│       ...           ...           ...                       │
│                                                             │
│              [ LOAD MORE ]                                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  FOOTER: © 2026 AI RETAIL BLOG                              │
└─────────────────────────────────────────────────────────────┘
```

### 3-2. 히어로 카드 선정 (is_featured: true)

| 순위 | 기사 | 이유 |
|---|---|---|
| 1 (메인) | A001 Amazon Rufus AI Wars | 가장 임팩트 큰 글로벌 트렌드 |
| 2 | A025 네이버 에이전트N | 한국 독자용 최신 기사 |
| 3 | A008 McKinsey $5T 전망 | 시장 규모 데이터로 관심 유도 |

### 3-3. 카드 컴포넌트 상세

```
┌────────────────────────────────┐
│                                │ ← 썸네일 (16:9, 생성형)
│  [emoji]  stat_number          │   - 카테고리별 그라디언트 배경
│           label_text           │   - 중앙 이모지 + 핵심 수치
│                                │   - hover: scale(1.05)
├────────────────────────────────┤
│ [카테고리 태그]    [Region]     │ ← 메타 행
│ 기사 제목 (2줄 max)            │ ← font: Bebas Neue
│ 날짜 · Source                  │ ← font: DM Mono
│ 요약 텍스트 (80자)             │ ← font: Syne
│ READ MORE →                    │ ← hover: underline + 화살표 이동
└────────────────────────────────┘
```

---

## 4. 기술 구현 사항

### 4-1. 썸네일 생성
- 외부 이미지 URL 사용 불가 (접근 차단 가능성)
- **방법**: 각 카드에 CSS gradient + SVG inline 텍스트로 썸네일 생성
- 카테고리별 그라디언트 색상 매핑
- 카드별 이모지(중앙) + 핵심 수치(하단) 표시
- `<canvas>`나 SVG 기반으로 동적 생성

### 4-2. 필터 기능
```javascript
// 카테고리 필터 (JS 클라이언트 사이드)
function filterCards(category) {
  document.querySelectorAll('.article-card').forEach(card => {
    const show = category === 'all' || card.dataset.category === category;
    card.style.display = show ? 'flex' : 'none';
  });
  updateActiveFilter(category);
}
```

### 4-3. Load More
- 초기 12개 노출
- "Load More" 클릭 시 다음 9개 표시
- 모두 표시 시 버튼 숨김

### 4-4. v4 디자인 시스템 재사용
- `--void, --deep, --nebula, --purple, --lavender, --fuchsia, --plasma` 동일
- `Bebas Neue, DM Mono, Syne` 동일
- Three.js 파티클 배경 (opacity 0.2로 줄임 — 콘텐츠 가독성 우선)
- GSAP ScrollTrigger 카드 reveal 애니메이션
- Custom cursor 동일

---

## 5. 작업 순서 (체크리스트)

- [x] 기사 리서치 및 DB 생성 (32건)
- [x] plan.md 작성
- [x] DB v2 생성 (7개 카테고리 + thumbnail 메타데이터 추가) → `articles-db-v2.json`
- [x] blog.html 작성
  - [x] HTML 구조 (nav + hero + filter + grid + footer)
  - [x] CSS (v4 디자인 시스템 + 블로그 전용 스타일)
  - [x] 썸네일 생성 로직 (CSS gradient + emoji/stat 오버레이, cat-1~cat-7)
  - [x] 필터 기능 (JS — data-category 클라이언트 사이드 필터)
  - [x] Load More 기능 (JS — 초기 12개, +9 per click)
  - [x] GSAP 애니메이션 (ScrollTrigger card reveal)
  - [x] Three.js 배경 (1800 파티클, opacity 0.18)
- [x] 최종 검토 완료

### 썸네일 결정 사항
- 모든 외부 기사 이미지 URL 접근 차단 확인 (modernretail.co, corporate.walmart.com, retaildive.com 등 전부 EGRESS_BLOCKED)
- CSS gradient + 이모지 + 핵심 수치 방식으로 모든 썸네일 생성
- 카테고리별 7가지 그라디언트로 시각적 일관성 확보

---

## 6. 리스크 & 결정 사항

| 이슈 | 결정 |
|---|---|
| 외부 썸네일 이미지 접근 차단 | CSS/SVG 생성형 썸네일로 대체 (디자인 일관성 오히려 향상) |
| PayPal Newsroom 직접 접근 불가 | 알려진 패턴 + 일반 뉴스룸 UX 패턴으로 재현 |
| 32개 기사 전체 로딩 성능 | Load More 패턴으로 초기 12개만 렌더링 |
| 카테고리 6→7개 | "데이터 & 리포트" 신설, A008·A009·A010·A011·A013 재분류 |

---
*다음 단계: DB v2 생성 → blog.html 제작*

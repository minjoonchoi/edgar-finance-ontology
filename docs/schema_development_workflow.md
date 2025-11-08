# EFIN 온톨로지 스키마 개발 과정 (ODP 기반)

## 문서 목적

본 문서는 **EFIN Financial Ontology의 스키마 개발 과정**을 설명합니다. ODP(Ontology Design Pattern) 기반의 3단계 개발 과정(용어 추출, 개념화, 형식화)과 CQ(Competency Question) 기반 설계 근거를 다룹니다.

**다른 문서:**
- [스키마 참조 문서](./schema.md): 최종 스키마 구조 상세
- [계층 구조 설명서](./hierarchy-structure.md): 온톨로지의 전체 계층 구조와 설계 의도 상세 설명
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [온톨로지 디자인 평가](./ontology_design_evaluation.md): 온톨로지 아키텍처 및 설계 평가

---

본 문서는 **EDGAR-FIN 2024 온톨로지(efin:)**의  
- 개발 방식(ODP 기반),  
- 스키마 구조 요약(클래스·프로퍼티·제약·지표),  
- CQ(Competency Question) 및 자연어로부터의 용어 추출 근거(annotation),  
를 통합 정리한 것이다.

---

## 1. 온톨로지 개요

| 항목 | 설명 |
|---|---|
| **이름** | EDGAR-FIN 2024 Financial Ontology |
| **Namespace** | `https://w3id.org/edgar-fin/2024#` (`efin:`) |
| **도메인** | 미국 S&P500 기업의 FY2024 재무제표 (SEC EDGAR XBRL 데이터 기준) |
| **목표** | 동일 재무지표에 대해 기업별·업종별로 다른 XBRL 태그를 사용하더라도 Canonical(표준화)된 지표로 통합 표현 |
| **재사용 온톨로지** | FIBO (fibo-be:LegalEntity), FinRegOnt (fro:RegulatoryFiling) |
| **ODP 적용 패턴** | Observation Pattern, Data Normalization Pattern, Property Chain Pattern, Key Pattern |

---

## 2. Ontology Design Pattern(ODP) 단계별 개발 과정

온톨로지 개발은 ODP 접근을 적용해 **3단계**로 진행되었다:

> **1단계** 용어추출 (Term Extraction)  
> **2단계** 개념화 (Conceptualization)  
> **3단계** 형식화 (Formalization)

---

### 2.1 1단계 — 용어추출 (Term Extraction)

#### (1) 데이터 원천
- SEC **EDGAR Company Facts API**
- **US-GAAP / IFRS Taxonomy (2024)**  
  - 회계 기준별 공식 태그 명칭 추출 (예: `us-gaap:Revenues`, `ifrs-full:ProfitLoss`)
- **기업 확장태그(Extension)**  
  - `ext:` prefix 태그 포함. 회사별 비표준 항목 식별.
- **Competency Questions (CQ)**  
  - 예시 1: “Which companies reported Revenue in FY2024?”  
  - 예시 2: “What is the Operating Income of each REIT?”  
  - 예시 3: “Which REITs derive revenue from rental income?”
- **분석 용어집 (Analytical Vocabulary)**  
  - 회계·재무 분석 교재 및 산업 분류체계에서 수집한 지표 명칭.

#### (2) 용어 정제 과정
1. **텍스트 마이닝 기반 후보 식별**  
   - XBRL 태그 네임(`us-gaap:*`, `ifrs-full:*`, `ext:*`)에서 의미 단위 추출.  
   - 명사 중심 후보(`Revenue`, `OperatingIncome`, `Assets`) 생성.
2. **유의어·동의어 병합**  
   - `SalesRevenueNet`, `Revenues`, `OperatingRevenue` → `Revenue`로 통합.
3. **CQ 및 자연어 패턴 매핑**
   - CQ 문장의 **명사구 → 클래스 후보**, **동사구 → 프로퍼티 후보**로 대응.
   - 예시:
     ```
     CQ: Which companies reported Revenue in FY2024?
          └─ [companies] → LegalEntity
          └─ [reported]  → forMetric
          └─ [Revenue]   → CanonicalMetric
          └─ [FY2024]    → Period
     CQ: Revenue derived from rental income.
          └─ [Revenue] → CanonicalMetric
          └─ [rental income] → XbrlConcept
          └─ [derived from] → computedFrom
     ```

#### (3) 참고 출처 (Reference Sources)
용어추출 단계에서 참조한 주요 공식/학술/산업 출처는 아래와 같다.

| 구분 | 출처 | 발행기관/저자 | 활용 목적 |
|---|---|---|---|
| **회계 표준** | US-GAAP Taxonomy (2024) | FASB | CanonicalMetric 태그 기준 |
|  | IFRS Taxonomy (2024) | IASB | 국제 기준 대응어 정의 |
|  | EDGAR Filer Manual | SEC | Period, Currency 클래스 정의 |
| **분석 교재** | Penman, *Financial Statement Analysis* | Columbia Univ. | 주요 손익·현금흐름 지표 용어 |
|  | White, Sondhi & Fried, *Analysis & Use of Financial Statements* | NYU Stern | 손익항목 간 관계식 추출 (computedFrom) |
|  | Kieso et al., *Intermediate Accounting* | Wiley | CanonicalMetric 기본 집합 확정 |
|  | Damodaran, *Investment Valuation* | NYU Stern | 파생 Comparable 지표(EBIT, FCF 등) 추가 |
| **산업/규제 표준** | SIC, GICS, NAICS | S&P, U.S. Census | Industry 클래스 계층 구조 |
|  | SEC Submissions JSON | SEC | CIK, SIC, fiscalYearEnd, 회사 메타데이터 |
| **보조 사전** | Investopedia, CFA Curriculum, OECD Glossary | 다양한 기관 | CanonicalMetric 정의문(rdfs:comment) 작성 근거 |

이러한 복합 출처를 통합하여 **CanonicalMetric 및 Observation 관련 용어 집합을 구축**하고,  
해당 용어를 기반으로 2단계 클래스 및 프로퍼티 정의로 연결하였다.

---

### 2.2 2단계 — 클래스 및 프로퍼티 정의 (Conceptualization)

#### (1) 핵심 설계 패턴
- **Observation Pattern**  
  - 수치 데이터 = (주체, 속성, 맥락, 값) → `FinancialObservation` 중심 구조.
- **Canonicalization Pattern**  
  - 다양한 XBRL 태그를 CanonicalMetric으로 통합 (`TagMapping`, `XbrlConcept` 도입).
- **Contextualization Pattern**  
  - 기간(`Period`), 통화(`Currency`), 회계기준(`AccountingStandard`)을 맥락(Context)으로 표현.
- **Upper Ontology Reuse**  
  - `LegalEntity` ← `fibo-be:LegalEntity`  
  - `RegulatoryFiling` ← `fro:RegulatoryFiling`

#### (2) CQ 기반 클래스/프로퍼티 도출 근거
| CQ/자연어 예문 | 도출 클래스/프로퍼티 | 근거 설명 |
|---|---|---|
| “Which companies reported Revenue?” | Class: LegalEntity, CanonicalMetric; Property: forMetric | “companies” 명사구 → 기업 클래스, “reported” 동사 → forMetric |
| “Revenue in USD during FY2024” | Property: hasCurrency, hasPeriod | “USD” → 통화 속성, “FY2024” → 기간 속성 |
| “Operating Income derived from GrossProfit minus SG&A” | Property: computedFrom | 계산식 문장 구조로부터 도출 |
| “Each observation has exactly one period.” | Restriction: (hasPeriod exactly 1 Period) | 자연어 제약 문장 패턴에서 추출 |

---

### 2.3 3단계 — 제약조건 정의 (Formalization)

#### (1) 적용된 OWL 제약 패턴
| 유형 | 예시 표현 | 목적 |
|---|---|---|
| **Cardinality (필수)** | `(forEntity exactly 1 LegalEntity)` | 관측치의 필수 구성요소 보장 |
| **Functional (기능적)** | `FunctionalProperty(forMetric)` | 1:1 관계 강제 |
| **Disjoint (상호배타)** | `DurationPeriod ⊥ InstantPeriod` | 시점/기간 혼동 방지 |
| **Key (유일성)** | `HasKey(FinancialObservation (forEntity, forMetric, hasPeriod, hasCurrency))` | 동일 조합 중복 방지 |
| **EquivalentClass (정의 클래스)** | `RevenueObservation ≡ FinancialObservation ⊓ (forMetric value Revenue)` | 추론기 자동 분류 가능 |
| **PropertyChain** | `(forEntity ∘ hasIndustry) ⊑ hasIndustryOfObservation` | 산업 자동 상속 |
| **AllDifferent** | `AllDifferent(CanonicalMetrics)` | 지표 의미 충돌 방지 |

---

## 3. 온톨로지 스키마 요약

### 3.1 재사용 vs 자체 구축 클래스

| 구분 | 클래스 | 출처/유형 | Annotation 근거(CQ·자연어) |
|---|---|---|---|
| **재사용** | `efin:Company` | 상속: `fibo-be:LegalEntity` | CQ "Which companies reported Revenue?"에서 [companies] → 기업 명사구 |
|  | `efin:RegulatoryFiling` | 상속: `fro:RegulatoryFiling` | CQ “In which filings was NetIncome reported?”의 [filings] 명사구 |
| **핵심 (자체)** | `efin:MetricObservation` | 자체 정의 | CQ 구조 전체("companies–reported–Revenue–FY2024")의 삼항 패턴에서 Observation 패턴 도출 |
|  | `efin:Metric` (BaseMetric/DerivedMetric) | 자체 정의 | CQ의 [Revenue], [Operating Income], [Assets] 등 명사구에서 추출 |
|  | `efin:XbrlConcept` | 자체 정의 | 자연어 “tag”, “concept”, “XBRL element”에서 명시적 등장 |
|  | `efin:TagMapping` | 자체 정의 | “map”, “corresponds to” 구문에서 매핑 개념 도출 |
| **시간·맥락 (자체)** | `efin:DurationObservation`, `efin:InstantObservation` | 정의 클래스 | CQ "in FY2024" / "at 2024-12-31" 에서 기간 표현 추출 (periodType으로 구분) |
|  | `efin:Sector`, `efin:Industry` | 자체 정의 | "for banks", "for REITs" 등 업종 한정 문장에서 명사구 추출 |
| **벤치마크/랭킹** | `efin:IndustryBenchmark`, `efin:SectorBenchmark` | 자체 정의 | 산업/섹터별 통계값 |
|  | `efin:TopRanking` | 자체 정의 | TopN 랭킹 데이터 |
| **파생 정의 클래스** | `efin:DurationObservation`, `efin:InstantObservation` | 정의 클래스 | CQ "Which observations are duration/instant?" → 정의식 생성 |

---

### 3.2 핵심 오브젝트/데이터 프로퍼티 요약

| 프로퍼티 | Domain → Range | Annotation 근거(CQ·자연어) |
|---|---|---|
| `efin:ofCompany` | MetricObservation → Company | CQ "Which companies…"의 주어 [companies]와 Observation 주체 연결 |
| `efin:observesMetric` | MetricObservation → Metric | CQ "reported [Revenue]"의 목적어 [Revenue] |
| `efin:hasFiscalYear` | MetricObservation → xsd:gYear | CQ "in [FY2024]" 시간구 표현 |
| `efin:hasPeriodType` | MetricObservation → xsd:string | 기간 타입 ("duration" 또는 "instant") |
| `efin:hasPeriodEnd` | MetricObservation → xsd:date | 기간 종료일 |
| `efin:hasUnit` | MetricObservation → xsd:string | "in [USD]" 화폐 명시 |
| `efin:hasXbrlConcept` | MetricObservation → XBRLConcept | 자연어 "tagged as [us-gaap:Revenue]" 구문 |
| `efin:computedFromObservation` | MetricObservation → MetricObservation | "Operating Income derived from Revenue – Expenses" 문장 구조 |
| `efin:computedFromMetric` | MetricObservation → Metric | 파생 계산의 입력 메트릭 |
| `efin:mapsFrom`, `efin:mapsTo` | TagMapping → (XbrlConcept / CanonicalMetric) | “maps from”, “corresponds to” 표현 |
| `efin:hasNumericValue` | MetricObservation → xsd:decimal | CQ "What was the value of Revenue?" 의 [value] 명사구 |
| `efin:hasPeriodEnd`, `efin:hasFiscalYear` | MetricObservation → xsd:date / xsd:gYear | "from Jan 1 to Dec 31", "FY2024" 시간 표현 |

---

### 3.3 제약(Constraints) 시각 요약

| 제약 | 표현 | CQ/자연어 근거 |
|---|---|---|
| 필수 키 구성요소 | `(forEntity, forMetric, hasPeriod, hasCurrency)` | “Each observation must specify company, metric, period, and currency.” |
| 상호배타 | `DurationPeriod ⊥ InstantPeriod` | “Periods are either duration or instant, never both.” |
| 유일성 | `HasKey(FinancialObservation (...))` | “There should be only one observation per company per metric per period.” |
| 정의 클래스 | `RevenueObservation ≡ FinancialObservation ⊓ (forMetric value Revenue)` | “Revenue observations are those whose metric is Revenue.” |
| 체인 | `(forEntity ∘ hasIndustry) ⊑ hasIndustryOfObservation` | “An observation inherits the industry of its entity.” |

---

### 3.4 Canonical 지표 집합

| 카테고리 | 지표 | CQ 및 자연어 근거 |
|---|---|---|
| **손익 (P&L)** | Revenue, OperatingIncome, NetIncome | CQ “What was Revenue of company X?” “Operating Income by industry?” |
| **현금흐름 (CF)** | CFO, FreeCashFlow | “Net Cash Provided by Operating Activities” 문장 구조 |
| **재무상태 (BS)** | Assets, Liabilities, Equity, CashAndCashEquivalents | “What are total assets/liabilities at end of FY2024?” |
| **파생 (Comparable)** | OperatingIncomeComparable, RevenueComparable | “Comparable Operating Income across firms” 구문에서 추출 |

---

## 4. 결론

- EDGAR-FIN 2024 온톨로지는 **FIBO·FinRegOnt 최소 재사용 + Observation 패턴 중심 자체 구축**으로 설계되었다.  
- **ODP 단계별 개발**을 통해:
  - 용어추출 단계에서 회계·분석·산업 표준 용어를 교차 검증하고,
  - 클래스·프로퍼티·제약조건을 CQ 기반으로 체계화하며,
  - Reasoner를 통한 자동 분류와 데이터 유일성을 확보하였다.
- 결과적으로, 동일 재무지표의 이질적 태그를 Canonical 형태로 통합함으로써  
  **XBRL 데이터의 의미적 정합성(Semantic Consistency)** 과  
  **투자자·분석가 질의의 재현성(Query Reproducibility)** 을 동시에 실현하였다.

---

## 관련 문서

- [스키마 참조 문서](./schema.md): 최종 스키마 구조 상세
- [계층 구조 설명서](./hierarchy-structure.md): 온톨로지의 전체 계층 구조와 설계 의도 상세 설명
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [온톨로지 디자인 평가](./ontology_design_evaluation.md): 온톨로지 아키텍처 및 설계 평가
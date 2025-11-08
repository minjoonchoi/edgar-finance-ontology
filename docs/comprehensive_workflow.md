# EFIN Financial Ontology 전체 워크플로우

## 문서 목적

본 문서는 **EFIN Financial Ontology의 전체 워크플로우**를 설명합니다. 데이터 추출부터 인스턴스 생성까지의 전체 프로세스를 다룹니다.

**다른 문서:**
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티, 제약 조건 등 스키마 구조 상세
- [스키마 개발 과정](./schema_development_workflow.md): ODP 기반 온톨로지 개발 과정
- [메트릭 추출 로직](./metric_extraction_logic.md): XBRL 태그 선택 및 메트릭 추출 상세 로직

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [온톨로지 스키마 설계](#2-온톨로지-스키마-설계)
3. [데이터 추출 프로세스](#3-데이터-추출-프로세스)
4. [데이터 처리 및 변환](#4-데이터-처리-및-변환)
5. [인스턴스 생성 로직](#5-인스턴스-생성-로직)
6. [전체 파이프라인](#6-전체-파이프라인)
7. [사용 예시](#7-사용-예시)

---

## 1. 시스템 개요

### 1.1 프로젝트 목적

EFIN (EDGAR Financial) 온톨로지는 SEC EDGAR의 XBRL 데이터에서 재무 지표를 추출하고, 이를 구조화된 RDF/OWL 형식으로 변환하여 의미론적 쿼리와 분석을 가능하게 하는 시스템입니다.

**주요 목표:**
- SEC EDGAR XBRL 데이터의 자동 추출 및 정규화
- 기업별, 산업별, 섹터별 재무 지표 비교 분석 지원
- 벤치마크 및 랭킹 데이터 생성
- OWL 온톨로지를 통한 의미론적 데이터 표현

### 1.2 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    SEC EDGAR API                            │
│         (Company Facts, Submissions)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           데이터 추출 모듈                                      │
│  (select_xbrl_tags.py)                                      │
│  ├─ XBRL 태그 선택 전략                                        │
│  ├─ Base Metrics 추출                                        │
│  └─ Derived Metrics 계산                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              CSV 출력 파일                                     │
│  ├─ tags_{fy}.csv (관측값)                                    │
│  ├─ companies_{fy}.csv (기업 정보)                             │
│  ├─ benchmarks_{fy}.csv (벤치마크 통계)                         │
│  └─ rankings_{fy}.csv (랭킹 데이터)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│          데이터 처리 모듈                                     │
│  ├─ 벤치마크 계산 (전체/Industry/Sector별)                   │
│  └─ 랭킹 계산 (전체/Industry/Sector별)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         인스턴스 생성 모듈                                    │
│  (emit_efin_ttl)                                            │
│  ├─ Company 인스턴스                                         │
│  ├─ Sector/Industry 인스턴스                                 │
│  ├─ MetricObservation 인스턴스                               │
│  ├─ Benchmark 인스턴스                                       │
│  └─ Ranking 인스턴스                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              RDF/TTL 출력                                     │
│         instances_{fy}.ttl                                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 주요 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|---------|------|------|
| **온톨로지 스키마** | `ontology/efin_schema.ttl` | 클래스, 프로퍼티, 제약 조건 정의 |
| **데이터 추출 스크립트** | `scripts/select_xbrl_tags.py` | SEC API 연동, XBRL 추출, CSV 생성 |
| **인스턴스 생성 함수** | `emit_efin_ttl()` | CSV → TTL 변환 |
| **벤치마크 계산** | `compute_benchmarks()` | 통계값 계산 |
| **랭킹 계산** | `compute_rankings()` | TopN 랭킹 생성 |

---

## 2. 온톨로지 스키마 설계

**네임스페이스**: `https://w3id.org/edgar-fin/2024#`  
**Prefix**: `efin:`  
**스키마 파일**: `ontology/efin_schema.ttl`

**표준 온톨로지 통합:**
- FIBO-BE (Business Entities): `https://spec.edmcouncil.org/fibo/ontology/BE/`
- `efin:Company`는 `fibo-be:LegalEntity`의 하위 클래스

**상세한 스키마 구조는** [스키마 참조 문서](./schema.md)를 참조하세요.

### 2.1 클래스 계층 구조 (요약)

#### 2.1.1 핵심 클래스

```
owl:Thing
├── efin:Company          (기업)
├── efin:Sector           (섹터 분류)
├── efin:Industry         (산업 분류)
├── efin:Metric           (재무 지표 개념)
│   ├── efin:BaseMetric   (기초 지표)
│   │   ├── efin:Revenue
│   │   ├── efin:OperatingIncome
│   │   ├── efin:NetIncome
│   │   └── ... (24개 Base Metrics)
│   └── efin:DerivedMetric (파생 지표)
│       ├── efin:DerivedRatio
│       │   ├── efin:RevenueGrowthYoY
│       │   ├── efin:GrossMargin
│       │   └── ... (17개 Derived Ratios)
│       └── efin:FreeCashFlow, efin:EBITDA
├── efin:MetricObservation (관측값)
│   ├── efin:DurationObservation (기간형)
│   └── efin:InstantObservation (시점형)
├── efin:IndustryBenchmark (산업별 벤치마크)
├── efin:SectorBenchmark   (섹터별 벤치마크)
└── efin:TopRanking        (랭킹)
```

#### 2.1.2 클래스 정의 원칙

**1. 계층적 분류 (Hierarchical Classification)**
- `rdfs:subClassOf`를 사용한 명확한 IS-A 관계
- 단일 상속 원칙 준수
- 적절한 추상화 수준 유지

**2. 분리 제약 (Disjointness)**
```turtle
efin:BaseMetric owl:disjointWith efin:DerivedMetric .
efin:DurationObservation owl:disjointWith efin:InstantObservation .
```

**3. 완전 분할 (Complete Partition)**
```turtle
efin:Metric owl:equivalentClass [
  owl:unionOf (efin:BaseMetric efin:DerivedMetric)
] .
```

**4. 정의 클래스 (Defined Classes)**
```turtle
efin:DurationObservation owl:equivalentClass [
  owl:intersectionOf (
    efin:MetricObservation
    [ owl:onProperty efin:hasPeriodType ;
      owl:hasValue "duration" ]
  )
] .
```

### 2.2 프로퍼티 정의 (요약)

**주요 ObjectProperty:**
- `efin:ofCompany`, `efin:observesMetric`: 관측값과 기업/메트릭 연결
- `efin:inSector`, `efin:inIndustry`: 기업의 섹터/산업 분류
- `efin:computedFromMetric`, `efin:computedFromObservation`: 파생 관계 추적
- `efin:forIndustry`, `efin:forSector`, `efin:forMetric`: 벤치마크/랭킹 연결

**주요 DatatypeProperty:**
- Company: `hasCIK`, `hasTicker`, `hasCompanyName`, `hasSIC` 등
- MetricObservation: `hasFiscalYear`, `hasPeriodType`, `hasNumericValue`, `hasConfidence` 등
- Benchmark/Ranking: 통계값 및 랭킹 정보

**상세한 프로퍼티 목록은** [스키마 참조 문서](./schema.md)를 참조하세요.

### 2.3 OWL 제약 조건 (요약)

- **Disjoint 제약**: `BaseMetric`와 `DerivedMetric` 상호 배타적
- **Functional Property**: `ofCompany`, `observesMetric`, `hasFiscalYear` 등
- **Cardinality 제약**: 필수 속성 정의 (`minCardinality 1`)
- **Key 제약**: (기업, 메트릭, 회계연도) 조합의 유일성
- **정의 클래스**: `DurationObservation`, `InstantObservation` 자동 분류

**상세한 제약 조건은** [스키마 참조 문서](./schema.md) 및 [온톨로지 디자인 평가 문서](./ontology_design_evaluation.md)를 참조하세요.

---

## 3. 데이터 추출 프로세스

### 3.1 SEC EDGAR API 연동

#### 3.1.1 API 엔드포인트

**Company Facts API:**
```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
```
- 회사의 모든 XBRL 팩트 데이터 제공
- Taxonomy별로 그룹화된 태그 및 값

**Submissions API:**
```
GET https://data.sec.gov/submissions/CIK{cik}.json
```
- 회사 메타데이터 (SIC 코드, 섹터, 산업 등)
- 제출 이력 정보

#### 3.1.2 캐싱 전략

- **로컬 캐시:** `.cache/companyfacts/` 및 `.cache/submissions/`
- **캐시 키:** CIK 기반 파일명
- **캐시 무효화:** `--force` 옵션으로 강제 재다운로드

### 3.2 XBRL 태그 선택 전략

#### 3.2.1 Static Candidates (정적 후보)

**우선순위 기반 선택:**
- 각 메트릭마다 사전 정의된 태그 후보 목록
- 우선순위 점수 (0.0 ~ 1.0)로 정렬
- 산업별 특화 태그 포함 (예: REIT, Utilities)

**예시:**
```python
"Revenue": [
    Candidate("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", 1.00, None, "Revenue"),
    Candidate("us-gaap:Revenues", 0.975, None, "Revenue"),
    Candidate("us-gaap:SalesRevenueNet", 0.970, None, "Revenue"),
    # 산업별
    Candidate("us-gaap:RealEstateRevenueNet", 0.950, {"Real Estate"}, "Revenue"),
    Candidate("us-gaap:UtilityRevenue", 0.960, {"Utilities"}, "Revenue"),
]
```

#### 3.2.2 Dynamic Mining (동적 채굴)

**패턴 기반 태그 발견:**
- 확장 태그(Extension)에서 패턴 매칭
- 정규표현식 기반 자동 발견
- 블랙리스트로 관련 없는 태그 필터링

**예시 (Growth Metrics):**
```python
_DIRECT_GROWTH_PATS = {
    "RevenueGrowthYoY": [
        r"(?:^|:)Revenue.*(Growth|Increase|Change).*(YoY|YearOverYear|Percent)$",
        r"(?:^|:)ChangeInRevenue$"
    ],
    ...
}
```

#### 3.2.3 Fallback 전략

**다단계 Fallback:**

1. **FY/FP 태그 우선** (`annual`)
   - `fp` 필드가 "FY", "CY", "FYR"인 레코드
   - 회계연도 종료일 기준 ±90일 tolerance

2. **분기 합산** (`ytd-q4`)
   - `qtrs=4`인 연간 누적 분기 데이터
   - 회계연도 종료일 기준 ±90일 tolerance

3. **날짜만 매칭** (`lenient`)
   - `fp` 필드 없이 날짜만으로 매칭
   - 회계연도 종료일 기준 ±90일 tolerance

4. **단위 우선순위**
   - USD 우선, 없으면 다른 단위 허용

### 3.3 Base Metrics 추출 로직

#### 3.3.1 추출 프로세스

```
For each Base Metric:
  1. Static Candidates 목록 순회
  2. 각 후보 태그에 대해:
     a. Company Facts에서 태그 검색
     b. 단위별 레코드 수집
     c. 회계연도 매칭 (smart_pick)
     d. 점수 계산 (신뢰도 + 조정)
  3. 최고 점수 레코드 선택
  4. CSV 행 추가
```

#### 3.3.2 신뢰도 점수 계산

**기본 점수:**
- Static Candidate의 우선순위 점수

**조정 요소:**
- `+0.06`: Form이 "10-K", "20-F" 등 연간 보고서
- `+0.03`: 단위가 "USD"
- `+0.03`: FP가 "FY", "CY", "FYR"
- `-0.01`: 세그먼트 데이터
- `+0.02`: 산업별 특화 태그 매칭

#### 3.3.3 Source Type 분류

| Source Type | 설명 | 예시 |
|------------|------|------|
| `annual` | FY/FP 태그로 매칭 | `fp="FY"` |
| `ytd-q4` | 분기 합산 데이터 | `qtrs=4` |
| `instant` | 시점형 데이터 | Balance Sheet 항목 |
| `lenient` | 날짜만 매칭 | `fp` 없음 |

### 3.4 Derived Metrics 계산 로직

#### 3.4.1 Growth Metrics 특수 처리

**1. Direct-growth 우선 검색**
- 확장 태그에서 성장률 태그 직접 검색
- 정규화 필요 시 정규화 (절대값 → 비율)

**2. 전년도 값 추출 (Fallback)**
- `_select_prior_year_with_fallback()` 함수 사용
- Tolerance 단계적 확대 (90일 → 120일 → 180일)
- 분기/세그먼트 데이터 보조 활용

**3. 성장률 계산**
```python
growth = (current_value - prior_value) / prior_value
```

**4. Direct-growth 정규화**
- 비정상적으로 큰 값 감지 (>100 또는 >10% of current)
- 절대 증가액으로 추정 시 전년도 값으로 나눔

#### 3.4.2 기타 파생 메트릭

**마진 (Margin):**
```python
margin = numerator / denominator
# 예: OperatingMargin = OperatingIncome / Revenue
```

**비율 (Ratio):**
```python
ratio = metric1 / metric2
# 예: DebtToEquity = TotalDebt / Equity
```

**복합 계산:**
```python
# 예: EBITDA = OperatingIncome + DepAmort
# 예: FreeCashFlow = CFO - CapEx
```

#### 3.4.3 Computed From 파싱

**형식:**
- 쉼표 또는 세미콜론으로 구분
- `(cur)`, `(prior)` 접미사 제거

**예시:**
- `"Revenue(cur),Revenue(prior)"` → `["Revenue"]`
- `"NetIncome;Revenue"` → `["NetIncome", "Revenue"]`
- `"direct-growth"` → `[]`

---

## 4. 데이터 처리 및 변환

### 4.1 CSV 출력 형식

#### 4.1.1 tags_{fy}.csv

**컬럼 구조:**
- `cik`, `symbol`, `name`: 기업 식별 정보
- `sector`, `industry`, `sic`, `sic_description`: 분류 정보
- `fye`: 회계연도 종료일
- `fy`: 회계연도
- `metric`: 메트릭 이름
- `is_derived`: 파생 여부 (true/false)
- `value`: 수치값
- `unit`: 단위
- `period_type`: "duration" 또는 "instant"
- `end`: 기간 종료일
- `form`: 보고서 형식 (10-K, 10-Q 등)
- `accn`: Accession Number
- `source_type`: 추출 방식
- `selected_tag`: 선택된 XBRL 태그
- `composite_name`: 복합 계산명
- `computed_from`: 계산 입력 메트릭
- `confidence`: 신뢰도 (0.0 ~ 1.0)
- `reason`: 선택 이유
- `components`: JSON 형식의 구성 요소

#### 4.1.2 companies_{fy}.csv

**컬럼 구조:**
- `symbol`: 티커 심볼
- `cik`: CIK 코드
- `name`: 회사명
- `sector`: 섹터
- `industry`: 산업
- `sic`: SIC 코드
- `sic_description`: SIC 설명
- `fye`: 회계연도 종료일

### 4.2 데이터 정규화

#### 4.2.1 단위 통일
- 모든 금액은 USD로 변환 (가능한 경우)
- 단위 정보는 `unit` 필드에 보존

#### 4.2.2 날짜 정규화
- ISO 8601 형식 (`YYYY-MM-DD`)
- 회계연도 종료일 기준 정규화

#### 4.2.3 값 정규화
- 소수점 6자리까지 표시
- NaN, Inf 값 제거

### 4.3 벤치마크 계산

#### 4.3.1 계산 대상 메트릭

**핵심 지표 (KEY_METRICS):**
- ROE, ROIC, NetProfitMargin, DebtToEquity, CurrentRatio
- RevenueGrowthYoY, NetIncomeGrowthYoY, OperatingMargin, AssetTurnover

#### 4.3.2 통계값 계산

**계산 항목:**
- `average_value`: 평균
- `median_value`: 중앙값
- `max_value`: 최대값
- `min_value`: 최소값
- `percentile25`: 25백분위수
- `percentile75`: 75백분위수
- `sample_size`: 샘플 크기

#### 4.3.3 그룹화 수준

**3가지 유형:**
1. **Industry별:** 각 산업 내 통계
2. **Sector별:** 각 섹터 내 통계 (모든 산업 포함)
3. **전체:** 모든 회사 통계

**구분 방법:**
- Industry별: `industry` 필드 값 존재
- Sector별: `industry=""`, `sector` 필드 값 존재
- 전체: `industry=""`, `sector=""`

### 4.4 랭킹 계산

#### 4.4.1 개별 메트릭 랭킹

**랭킹 유형:**
- Top10, Top50, Top100

**정렬 기준:**
- 대부분 메트릭: 내림차순 (높은 값이 좋음)
- DebtToEquity: 오름차순 (낮은 값이 좋음)

#### 4.4.2 종합 랭킹 (Composite)

**점수 계산:**
1. 각 메트릭을 0-1 범위로 정규화
   ```python
   normalized = (value - min) / (max - min)
   ```
2. DebtToEquity는 반전 (낮은 값이 좋음)
   ```python
   normalized = 1.0 - normalized
   ```
3. 모든 메트릭의 정규화 점수 합산

**그룹화 수준:**
- Industry별, Sector별, 전체 (3가지)

---

## 5. 인스턴스 생성 로직

### 5.1 TTL 생성 프로세스

#### 5.1.1 전체 흐름

```
1. Prefix 선언
2. Sector/Industry 인스턴스 생성
3. Company 인스턴스 생성 및 관계 설정
4. MetricObservation 인스턴스 생성
5. Benchmark 인스턴스 생성
6. Ranking 인스턴스 생성
```

### 5.2 Company 인스턴스 생성

#### 5.2.1 인스턴스 IRI

```turtle
efin:CIK{cik} a efin:Company ;
  efin:hasCIK "{cik}" ;
  efin:hasTicker "{symbol}" ;
  efin:hasCompanyName "{name}" ;
  efin:inSector efin:Sector{sector_name} ;
  efin:inIndustry efin:Industry{industry_name} .
```

#### 5.2.2 Sector/Industry 인스턴스

**Sector 인스턴스:**
```turtle
efin:Sector{sector_name} a efin:Sector .
efin:SectorAll a efin:Sector .  # 전체 벤치마크용
```

**Industry 인스턴스:**
```turtle
efin:Industry{industry_name} a efin:Industry ;
  efin:inSectorOf efin:Sector{sector_name} .
```

### 5.3 MetricObservation 인스턴스 생성

#### 5.3.1 인스턴스 구조

```turtle
efin:Observation-{cik}-{metric}-{fy} a efin:{Duration|Instant}Observation ;
  efin:ofCompany efin:CIK{cik} ;
  efin:observesMetric efin:{metric} ;
  efin:hasFiscalYear "{fy}"^^xsd:gYear ;
  efin:hasPeriodType "{period_type}" ;
  efin:hasNumericValue {value} ;
  efin:isDerived "{is_derived}"^^xsd:boolean ;
  efin:hasSourceType "{source_type}" ;
  efin:hasSelectedTag "{tag}" ;
  efin:hasConfidence {confidence} .
```

#### 5.3.2 클래스 타입 결정

- `period_type == "duration"` → `efin:DurationObservation`
- `period_type == "instant"` → `efin:InstantObservation`

#### 5.3.3 ComputedFrom 관계 생성

**computed_from 파싱:**
```python
metrics = _parse_computed_from(computed_from)
# 예: "Revenue(cur),Revenue(prior)" → ["Revenue"]
```

**관계 생성:**
```turtle
efin:Observation-{cik}-{metric}-{fy}
  efin:computedFromMetric efin:{source_metric} .
```

### 5.4 Benchmark 인스턴스 생성

#### 5.4.1 Industry별 벤치마크

```turtle
efin:IndustryBenchmark{industry}{metric}{fy} a efin:IndustryBenchmark ;
  efin:forIndustry efin:Industry{industry} ;
  efin:forMetric efin:{metric} ;
  efin:forFiscalYear "{fy}"^^xsd:gYear ;
  efin:averageValue {avg} ;
  efin:medianValue {median} ;
  efin:maxValue {max} ;
  efin:minValue {min} ;
  efin:percentile25 {p25} ;
  efin:percentile75 {p75} ;
  efin:sampleSize {n} .
```

#### 5.4.2 Sector별 벤치마크

```turtle
efin:SectorBenchmark{sector}{metric}{fy} a efin:SectorBenchmark ;
  efin:forSector efin:Sector{sector} ;
  efin:forMetric efin:{metric} ;
  efin:forFiscalYear "{fy}"^^xsd:gYear ;
  ... (통계값 동일) ...
```

#### 5.4.3 전체 벤치마크

```turtle
efin:SectorBenchmarkAll{metric}{fy} a efin:SectorBenchmark ;
  efin:forSector efin:SectorAll ;
  efin:forMetric efin:{metric} ;
  efin:forFiscalYear "{fy}"^^xsd:gYear ;
  ... (통계값 동일) ...
```

### 5.5 Ranking 인스턴스 생성

#### 5.5.1 랭킹 그룹화

**키 형식:** `(scope_type, scope_value, metric, ranking_type)`
- `scope_type`: "industry" | "sector" | "all"
- `scope_value`: 산업명 | 섹터명 | "All"

#### 5.5.2 인스턴스 생성

**Industry별:**
```turtle
efin:TopRanking{industry}{metric}{ranking_type}{fy} a efin:TopRanking ;
  efin:forIndustry efin:Industry{industry} ;
  efin:forMetric efin:{metric} ;
  efin:forFiscalYear "{fy}"^^xsd:gYear ;
  efin:rankingType "{ranking_type}" .

efin:CIK{cik} efin:hasRanking efin:TopRanking{industry}{metric}{ranking_type}{fy} .
```

**Sector별:**
```turtle
efin:TopRankingSector{sector}{metric}{ranking_type}{fy} a efin:TopRanking ;
  efin:forSector efin:Sector{sector} ;
  ...
```

**전체:**
```turtle
efin:TopRankingAll{metric}{ranking_type}{fy} a efin:TopRanking ;
  efin:forSector efin:SectorAll ;
  ...
```

---

## 6. 전체 파이프라인

### 6.1 실행 순서 및 의존성

```
1. SEC API 데이터 수집
   ├─ Company Facts API 호출
   └─ Submissions API 호출
   
2. Base Metrics 추출
   ├─ Static Candidates 검색
   ├─ Dynamic Mining (필요 시)
   └─ Fallback 전략 적용
   
3. Derived Metrics 계산
   ├─ Growth Metrics 특수 처리
   └─ 기타 파생 메트릭 계산
   
4. CSV 파일 생성
   ├─ tags_{fy}.csv
   └─ companies_{fy}.csv
   
5. 벤치마크 계산
   ├─ Industry별 통계
   ├─ Sector별 통계
   └─ 전체 통계
   
6. 랭킹 계산
   ├─ Industry별 랭킹
   ├─ Sector별 랭킹
   └─ 전체 랭킹
   
7. CSV 파일 저장
   ├─ benchmarks_{fy}.csv
   └─ rankings_{fy}.csv
   
8. TTL 인스턴스 생성 (옵션)
   ├─ Company 인스턴스
   ├─ Sector/Industry 인스턴스
   ├─ MetricObservation 인스턴스
   ├─ Benchmark 인스턴스
   └─ Ranking 인스턴스
```

### 6.2 입력/출력 파일 매핑

| 단계 | 입력 | 출력 |
|------|------|------|
| **데이터 추출** | SEC API | `tags_{fy}.csv`, `companies_{fy}.csv` |
| **벤치마크 계산** | `tags_{fy}.csv` | `benchmarks_{fy}.csv` |
| **랭킹 계산** | `tags_{fy}.csv`, `benchmarks_{fy}.csv` | `rankings_{fy}.csv` |
| **TTL 생성** | 모든 CSV 파일 | `instances_{fy}.ttl` |

### 6.3 에러 처리 및 로깅

#### 6.3.1 에러 처리

- **API 에러:** 재시도 없이 다음 회사로 진행
- **데이터 부재:** 해당 메트릭 건너뛰기
- **계산 에러:** 경고 메시지 출력 후 계속 진행

#### 6.3.2 로깅

**디버그 모드 (`--debug`):**
- 태그 선택 과정 상세 로그
- 점수 계산 과정
- Fallback 전략 적용 과정

**로그 파일 (`--debug-file`):**
- 파일로 저장 가능
- 각 회사별 상세 정보

---

## 7. 사용 예시

### 7.1 기본 실행 방법

```bash
# 환경 변수 설정
export SEC_USER_AGENT="MyApp/1.0 you@org.com"

# 기본 실행 (50개 회사, 2024년)
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --use-api \
  --limit 50 \
  --include-derived \
  --emit-ttl data/instances_2024.ttl
```

### 7.2 고급 옵션 사용법

#### 7.2.1 특정 회사만 추출

```bash
# 티커 심볼로 필터링
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --use-api \
  --tickers AAPL MSFT GOOGL \
  --include-derived

# CIK로 필터링
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --use-api \
  --ciks "320193,789019" \
  --include-derived
```

#### 7.2.2 특정 메트릭만 추출

```bash
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --use-api \
  --metrics Revenue OperatingIncome NetIncome \
  --include-derived
```

#### 7.2.3 출력 파일 지정

```bash
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --use-api \
  --out-tags data/my_tags_2024.csv \
  --out-companies data/my_companies_2024.csv \
  --out-benchmarks data/my_benchmarks_2024.csv \
  --out-rankings data/my_rankings_2024.csv \
  --emit-ttl data/my_instances_2024.ttl
```

#### 7.2.4 디버그 모드

```bash
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --use-api \
  --debug \
  --debug-file logs/debug_2024.log \
  --include-derived
```

#### 7.2.5 로컬 파일 사용

```bash
# Company Facts JSON 파일 직접 지정
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --facts data/company_facts/*.json \
  --include-derived

# 디렉토리 지정
python scripts/select_xbrl_tags.py \
  --fy 2024 \
  --facts-dir data/company_facts \
  --include-derived
```

### 7.3 결과 확인 방법

#### 7.3.1 CSV 파일 확인

```bash
# tags 파일 확인
head -20 data/tags_2024.csv

# companies 파일 확인
cat data/companies_2024.csv

# benchmarks 확인
head -20 data/benchmarks_2024.csv

# rankings 확인
head -20 data/rankings_2024.csv
```

#### 7.3.2 TTL 파일 확인

```bash
# TTL 파일 구조 확인
head -100 data/instances_2024.ttl

# 특정 회사 검색
grep "CIK0000320193" data/instances_2024.ttl

# 특정 메트릭 검색
grep "Revenue" data/instances_2024.ttl
```

#### 7.3.3 데이터 품질 확인

```bash
# 메트릭별 추출률 확인
cut -d',' -f13 data/tags_2024.csv | sort | uniq -c | sort -rn

# 결측치 확인
awk -F',' 'NR>1 && $13=="" {print}' data/tags_2024.csv | wc -l
```

---

## 참고 자료

- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티, 제약 조건 등 스키마 구조 상세
- [계층 구조 설명서](./hierarchy-structure.md): 온톨로지의 전체 계층 구조와 설계 의도 상세 설명
- [스키마 개발 과정](./schema_development_workflow.md): ODP 기반 온톨로지 개발 과정
- [메트릭 추출 로직](./metric_extraction_logic.md): XBRL 태그 선택 및 메트릭 추출 상세 로직
- [온톨로지 디자인 평가](./ontology_design_evaluation.md): 온톨로지 아키텍처 및 설계 평가
- [상호 운용성 가이드](./interoperability.md): FIBO 등 표준 온톨로지와의 통합
- [투자 분석 쿼리](./investment_analysis_queries.md): SPARQL 쿼리 예시
- [인스턴스 통계](./instance_statistics.md): 현재 인스턴스 데이터의 클래스별/연도별 분포


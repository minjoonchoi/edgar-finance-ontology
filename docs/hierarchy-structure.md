# EFIN 온톨로지 계층 구조 설명서

## 목차
1. [개요](#개요)
2. [클래스 계층 구조](#클래스-계층-구조)
3. [속성 계층 구조](#속성-계층-구조)
4. [제약 조건 및 공리](#제약-조건-및-공리)
5. [데이터 흐름 및 관계](#데이터-흐름-및-관계)

---

## 개요

EFIN(EDGAR Financial) 온톨로지는 SEC EDGAR XBRL 데이터를 표준화된 형식으로 표현하기 위한 재무 보고 온톨로지입니다. 본 문서는 온톨로지의 전체 계층 구조와 각 요소 간의 관계를 설명합니다.

### 온톨로지 메타데이터
- **버전**: 1.1.0-filing-support
- **네임스페이스**: `https://w3id.org/edgar-fin/2024#`
- **외부 온톨로지 연동**: FIBO-BE, QUDT, OM-2
- **최종 수정일**: 2025-01-19

**관련 문서:**
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티, 제약 조건 등 스키마 구조 빠른 참조
- [온톨로지 디자인 평가](./ontology_design_evaluation.md): 온톨로지 아키텍처 및 설계 평가
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [스키마 개발 과정](./schema_development_workflow.md): ODP 기반 온톨로지 개발 과정

---

## 클래스 계층 구조

### 1. 조직 및 분류 계층

```
owl:Thing
├── fibo-be:LegalEntity
│   └── efin:Company
│       └── 속성: hasCIK, hasTicker, hasCompanyName, hasSIC
│       └── 관계: inSector, inIndustry, hasObservation, hasRanking
│
├── efin:Sector
│   └── 인스턴스 예시: efin:SectorInformationTechnology
│   └── 역관계: Company ← inSector
│
└── efin:Industry
    └── 인스턴스 예시: efin:IndustryServicesPrepackagedSoftware
    └── 관계: inSectorOf → Sector
    └── 역관계: Company ← inIndustry
```

**설계 의도**:
- `Company`는 FIBO 표준과의 상호운용성을 위해 `fibo-be:LegalEntity`를 상속
- `Industry`는 `inSectorOf` 비대칭 속성을 통해 `Sector`와 계층적 관계 형성
- CIK는 SEC 특화 식별자, Ticker는 거래소 식별자로 다중 식별 체계 지원

### 2. 메트릭 계층 구조

```
efin:Metric (추상 클래스)
│   └── 완전 분할: Metric ≡ BaseMetric ⊔ DerivedMetric
│   └── 분리 제약: BaseMetric ⊓ DerivedMetric = ∅
│
├── efin:BaseMetric (XBRL 직접 추출)
│   ├── 손익계산서 항목
│   │   ├── Revenue
│   │   ├── OperatingIncome
│   │   ├── NetIncome
│   │   ├── GrossProfit
│   │   ├── CostOfGoodsSold
│   │   ├── IncomeTaxExpense
│   │   └── PreTaxIncome
│   │
│   ├── 재무상태표 항목
│   │   ├── Assets
│   │   ├── Liabilities
│   │   ├── Equity
│   │   ├── CurrentAssets
│   │   ├── CurrentLiabilities
│   │   ├── Inventories
│   │   ├── AccountsReceivable
│   │   ├── CashAndCashEquivalents
│   │   ├── LongTermDebt
│   │   ├── ShortTermDebt
│   │   └── DebtCurrent
│   │
│   ├── 현금흐름표 항목
│   │   ├── CFO (영업활동 현금흐름)
│   │   ├── CapEx
│   │   └── DepAmort
│   │
│   └── 기타 항목
│       ├── EPSDiluted
│       ├── DilutedShares
│       └── InterestExpense
│
└── efin:DerivedMetric (계산된 지표)
    ├── efin:DerivedRatio (비율 형태)
    │   ├── 수익성 비율
    │   │   ├── GrossMargin (= GrossProfit / Revenue)
    │   │   ├── OperatingMargin (= OperatingIncome / Revenue)
    │   │   ├── NetProfitMargin (= NetIncome / Revenue)
    │   │   ├── EBITDAMargin (= EBITDA / Revenue)
    │   │   ├── ROE (= NetIncome / Avg(Equity))
    │   │   └── ROIC (= NOPAT / InvestedCapital)
    │   │
    │   ├── 성장률 비율
    │   │   ├── RevenueGrowthYoY
    │   │   ├── NetIncomeGrowthYoY
    │   │   ├── CFOGrowthYoY
    │   │   └── AssetGrowthRate
    │   │
    │   ├── 유동성/활동성 비율
    │   │   ├── CurrentRatio
    │   │   ├── QuickRatio
    │   │   ├── InventoryTurnover
    │   │   ├── ReceivablesTurnover
    │   │   ├── AssetTurnover
    │   │   └── OperatingCashFlowRatio
    │   │
    │   └── 레버리지 비율
    │       ├── DebtToEquity
    │       ├── EquityRatio
    │       └── InterestCoverage
    │
    └── 기타 파생 메트릭
        ├── FreeCashFlow (= CFO - CapEx)
        ├── EBITDA
        ├── NOPAT
        └── InvestedCapital
```

**설계 의도**:
- **완전 분할**: 모든 메트릭은 반드시 BaseMetric 또는 DerivedMetric 중 하나
- **분리 제약**: BaseMetric과 DerivedMetric은 상호 배타적
- **DerivedRatio**: 두 메트릭의 나눗셈으로 표현되는 정규화된 지표
- 각 파생 메트릭은 `hasFormulaNote`로 계산 공식 명시

### 3. 관측값 계층 구조

```
efin:MetricObservation
├── 필수 속성 (minCardinality = 1)
│   ├── ofCompany: Company (함수형)
│   ├── observesMetric: Metric (함수형)
│   ├── hasFiscalYear: xsd:gYear (함수형)
│   ├── hasNumericValue: xsd:decimal (함수형)
│   └── hasPeriodType: xsd:string {"duration", "instant"}
│
├── 선택적 속성
│   ├── hasPeriodEnd: xsd:date
│   ├── fromFiling: Filing (함수형)
│   ├── hasUnit: Unit
│   ├── hasCurrency: Currency
│   ├── hasXbrlConcept: XBRLConcept
│   ├── isDerived: xsd:boolean
│   ├── hasSourceNote: xsd:string
│   ├── computedFromMetric: Metric (다중)
│   ├── computedFromObservation: MetricObservation (다중, 전이적)
│   └── hasBenchmark: IndustryBenchmark | SectorBenchmark
│
├── efin:DurationObservation
│   └── ≡ MetricObservation ⊓ (hasPeriodType value "duration")
│   └── 예시: Revenue, NetIncome, CFO
│   └── 의미: 특정 기간 동안 누적된 값
│
└── efin:InstantObservation
    └── ≡ MetricObservation ⊓ (hasPeriodType value "instant")
    └── 예시: Assets, Liabilities, Equity
    └── 의미: 특정 시점의 잔액
    └── 분리 제약: DurationObservation ⊓ InstantObservation = ∅
```

**설계 의도**:
- **복합 키**: (ofCompany, observesMetric, hasFiscalYear) 조합으로 고유 식별
- **함수형 속성**: 핵심 관계는 함수형으로 제약하여 데이터 무결성 보장
- **자동 분류**: `hasPeriodType` 값에 따라 Duration/InstantObservation으로 자동 분류
- **계보 추적**: `computedFromObservation`은 전이적 속성으로 다단계 파생 관계 추적
- **출처 추적**: `fromFiling`으로 관측값을 원본 SEC 공시 문서와 연결

### 4. 공시 문서 계층 구조

```
efin:Filing (추상 클래스)
├── 속성
│   ├── accessionNumber: xsd:string (함수형, 고유 식별자)
│   ├── filingDate: xsd:date (함수형)
│   ├── fiscalPeriod: xsd:string (함수형) {"FY", "Q1", "Q2", "Q3", "Q4"}
│   ├── documentUrl: xsd:anyURI (함수형)
│   └── acceptanceDateTime: xsd:dateTime (함수형)
│
├── 관계
│   ├── filedBy: Filing → Company (함수형)
│   └── containsObservation: Filing → MetricObservation (fromFiling의 역속성)
│
├── efin:TenK
│   └── 연간보고서 (Form 10-K)
│   └── 특징: 회계연도 종료 후 제출, 감사된 재무제표 포함
│   └── fiscalPeriod: "FY"
│
├── efin:TenQ
│   └── 분기보고서 (Form 10-Q)
│   └── 특징: 분기 종료 후 제출, 검토 수준의 재무제표
│   └── fiscalPeriod: "Q1", "Q2", "Q3", "Q4"
│
├── efin:EightK
│   └── 임시보고서 (Form 8-K)
│   └── 특징: 중요 사건 발생 시 수시 제출
│   └── fiscalPeriod: 다양 (사건에 따름)
│
└── efin:TwentyF
    └── 외국 기업 연간보고서 (Form 20-F)
    └── 특징: 미국 외 국가 본사 기업의 연간 보고서
    └── fiscalPeriod: "FY"
```

**설계 의도**:
- **데이터 출처 추적**: 모든 재무 관측값을 원본 SEC 제출 문서로 역추적 가능
- **시간 구분**:
  - `hasFiscalYear`/`hasPeriodEnd` (관측값) = 데이터가 "언제에 대한" 것인지
  - `filingDate` (Filing) = 데이터가 "언제 보고되었는지"
- **고유 식별**: `accessionNumber`는 SEC가 부여하는 문서의 고유 ID (예: 0000320193-23-000106)
- **확장 가능**: Filing 추상 클래스를 통해 향후 다른 SEC 문서 유형 추가 용이
- **감사 추적**: `documentUrl`로 SEC EDGAR 시스템의 원본 문서 직접 접근

### 5. 벤치마크 및 랭킹 계층

```
벤치마크 체계
├── efin:IndustryBenchmark
│   └── 관계: forIndustry → Industry, forMetric → Metric
│   └── 속성: forFiscalYear, hasAverageValue, hasMedianValue,
│              hasMaxValue, hasMinValue, hasPercentile25,
│              hasPercentile75, hasSampleSize
│
├── efin:SectorBenchmark
│   └── 관계: forSector → Sector, forMetric → Metric
│   └── 속성: (IndustryBenchmark와 동일)
│
└── efin:TopRanking
    └── 관계: forIndustry/forSector, forMetric → Metric
    └── 속성: forFiscalYear, hasRankingType {"Top10", "Top50", "Top100", "Composite"},
               hasRank, hasRankingValue, hasCompositeScore
```

**설계 의도**:
- **다층 집계**: Industry(세분화) 및 Sector(거시적) 수준 벤치마크 제공
- **통계적 분포**: 평균, 중앙값, 백분위수로 메트릭 분포 특성 제공
- **신뢰도 지표**: `hasSampleSize`로 통계적 신뢰도 판단 가능
- **복합 랭킹**: 단일 메트릭 또는 여러 메트릭의 종합 점수 기반 순위 지원

### 5. 메타데이터 클래스

```
메타데이터 체계
├── efin:Unit
│   └── owl:equivalentClass qudt:Unit, om:Unit
│   └── 예시: USD, shares, percent
│   └── 표준 정렬로 상호운용성 확보
│
├── efin:Currency
│   └── owl:equivalentClass qudt:CurrencyUnit
│   └── 예시: USD, EUR, KRW
│   └── QUDT 통화 체계 활용
│
└── efin:XBRLConcept
    └── 속성: hasQName (예: us-gaap:Revenue),
              hasNamespace (예: http://fasb.org/us-gaap/2023),
              hasConceptLabel
    └── 역할: SEC EDGAR XBRL 택소노미와의 추적성 확보
```

---

## 속성 계층 구조

### 1. 객체 속성 (Object Properties)

#### 1.1 핵심 관계 속성

```
MetricObservation 중심 관계
├── ofCompany: MetricObservation → Company [함수형]
│   └── 역속성: hasObservation: Company → MetricObservation
│   └── 의미: 각 관측값은 정확히 하나의 회사에 속함
│
├── observesMetric: MetricObservation → Metric [함수형]
│   └── 역속성: observedBy: Metric → MetricObservation
│   └── 의미: 각 관측값은 정확히 하나의 메트릭을 측정
│
└── computedFromObservation: MetricObservation → MetricObservation [전이적]
    └── 의미: 파생 관측값의 계보 추적 (A→B→C이면 A→C도 성립)
```

#### 1.2 분류 체계 속성

```
Company 분류 관계
├── inSector: Company → Sector
│   └── 의미: 회사의 섹터 분류 (거시적 범주)
│
├── inIndustry: Company → Industry
│   └── 의미: 회사의 산업 분류 (세분화된 범주)
│
└── inSectorOf: Industry → Sector [비대칭]
    └── 의미: 산업의 상위 섹터 (순환 참조 방지)
```

#### 1.3 벤치마크/랭킹 속성

```
비교 분석 관계
├── hasBenchmark: MetricObservation → (IndustryBenchmark | SectorBenchmark)
│   └── 의미: 관측값을 동종 업계 통계와 연결
│
├── hasRanking: Company → TopRanking
│   └── 의미: 회사의 산업/섹터 내 순위 정보
│
├── forIndustry: IndustryBenchmark → Industry
├── forSector: SectorBenchmark → Sector
└── forMetric: (Benchmark | Ranking) → Metric
    └── 의미: 벤치마크/랭킹의 대상 메트릭 명시
```

#### 1.4 Filing 관계 속성

```
Filing 중심 관계
├── fromFiling: MetricObservation → Filing [함수형]
│   └── 역속성: containsObservation: Filing → MetricObservation
│   └── 의미: 관측값이 추출된 원본 SEC 공시 문서
│   └── 예시: obs1 fromFiling filing_10K_2023
│
└── filedBy: Filing → Company [함수형]
    └── 의미: 공시 문서를 제출한 회사
    └── 예시: filing_10K_2023 filedBy appleInc
```

**중요 설계 포인트**:
- `fromFiling`과 `containsObservation`은 역속성 관계로 양방향 탐색 가능
- 함수형 속성: 각 관측값은 정확히 하나의 Filing에서만 추출
- 각 Filing은 정확히 하나의 Company에 의해 제출

#### 1.5 메타데이터 속성

```
측정 단위 및 XBRL 연결
├── hasUnit: MetricObservation → Unit
│   └── 예시: unit:USD, unit:PERCENT
│
├── hasCurrency: MetricObservation → Currency
│   └── 예시: USD, EUR, KRW
│
└── hasXbrlConcept: MetricObservation → XBRLConcept
    └── 역할: XBRL 택소노미 원본 태그와의 추적성
```

### 2. 데이터 속성 (Datatype Properties)

#### 2.1 회사 식별자

```
Company 속성
├── hasCIK: xsd:string [SEC 특화 식별자]
├── hasTicker: xsd:string [거래소 티커]
├── hasCompanyName: xsd:string [공식 명칭]
├── hasSIC: xsd:string [표준 산업 분류 코드]
├── hasSICDescription: xsd:string
└── hasFiscalYearEnd: xsd:string [예: "1231"]
```

#### 2.2 관측값 핵심 속성

```
MetricObservation 속성
├── hasFiscalYear: xsd:gYear [함수형, 복합키 구성요소]
│   └── 의미: 데이터가 "언제에 대한" 것인지 (관측 시점)
│   └── 주의: Filing의 filingDate(보고 시점)와 독립적
│
├── hasQuarter: xsd:integer [선택적, 값: 1~4]
│   └── 의미: 회계 분기 (1, 2, 3, 4)
│   └── 용도: 분기별 데이터 식별 (연간 데이터는 생략)
│   └── 예시: Q1 2024 매출 = hasFiscalYear "2024", hasQuarter 1
│
├── hasPeriodType: xsd:string [값: "duration" | "instant"]
├── hasPeriodEnd: xsd:date [함수형]
│   └── 의미: 관측 데이터의 시간적 경계 (종료일)
│   └── 주의: Filing의 filingDate(보고 시점)와 구별됨
│
├── hasNumericValue: xsd:decimal [함수형]
├── isDerived: xsd:boolean [파생 여부]
└── hasSourceNote: xsd:string [계산 과정 메모]
```

**시간 속성 구분**:
- **관측 시간** (`hasFiscalYear`, `hasPeriodEnd`): 재무 데이터가 "언제에 대한" 것인지
- **보고 시간** (`filingDate`, `acceptanceDateTime`): 데이터가 "언제 SEC에 제출되었는지"
- 예시: 2023 회계연도 재무제표가 2024년 2월에 10-K로 제출됨
  - `hasFiscalYear`: 2023
  - `filingDate`: 2024-02-15

#### 2.3 Filing 속성

```
Filing 문서 속성
├── accessionNumber: xsd:string [함수형, 고유 식별자]
│   └── 예시: "0000320193-23-000106"
│   └── 역할: SEC가 부여하는 문서의 고유 ID
│
├── filingDate: xsd:date [함수형]
│   └── 예시: 2024-11-01
│   └── 역할: SEC 공식 제출일자
│
├── fiscalPeriod: xsd:string [함수형]
│   └── 값: "FY" (연간), "Q1", "Q2", "Q3", "Q4" (분기)
│   └── 역할: 문서가 다루는 회계 기간
│
├── documentUrl: xsd:anyURI [함수형]
│   └── 예시: https://www.sec.gov/Archives/edgar/data/320193/...
│   └── 역할: SEC EDGAR 시스템의 원본 문서 링크
│
└── acceptanceDateTime: xsd:dateTime [함수형]
    └── 예시: 2024-11-01T16:30:00Z
    └── 역할: SEC 접수 정확한 타임스탬프 (filingDate보다 정밀)
```

#### 2.4 메트릭 메타데이터

```
Metric 속성
└── hasFormulaNote: xsd:string
    └── 예시: "NetIncome / Average(Equity_t, Equity_{t-1})"
    └── 역할: 파생 메트릭의 계산 공식 기술
```

#### 2.5 벤치마크 통계 속성

```
Benchmark 속성
├── forFiscalYear: xsd:gYear [기준 연도]
├── hasAverageValue: xsd:decimal [산술평균]
├── hasMedianValue: xsd:decimal [중앙값, 이상치에 강건]
├── hasMaxValue: xsd:decimal
├── hasMinValue: xsd:decimal
├── hasPercentile25: xsd:decimal [1사분위수]
├── hasPercentile75: xsd:decimal [3사분위수]
└── hasSampleSize: xsd:integer [통계 신뢰도 지표]
```

#### 2.6 랭킹 속성

```
TopRanking 속성
├── forFiscalYear: xsd:gYear
├── hasRankingType: xsd:string ["Top10" | "Top50" | "Top100" | "Composite"]
├── hasRank: xsd:integer [1부터 시작]
├── hasRankingValue: xsd:decimal [단일 메트릭 기준값]
└── hasCompositeScore: xsd:decimal [복합 메트릭 종합 점수]
```

#### 2.7 XBRL 메타데이터

```
XBRLConcept 속성
├── hasQName: xsd:string [예: "us-gaap:Revenue"]
├── hasNamespace: xsd:anyURI [예: "http://fasb.org/us-gaap/2023"]
└── hasConceptLabel: xsd:string [사람이 읽을 수 있는 설명]
```

---

## 제약 조건 및 공리

### 1. 분리 제약 (Disjointness)

```turtle
# 기본 메트릭과 파생 메트릭은 상호 배타적
BaseMetric ⊓ DerivedMetric = ∅

# Duration과 Instant 관측은 상호 배타적
DurationObservation ⊓ InstantObservation = ∅
```

**의미**: 동일 개체가 두 클래스에 동시에 속할 수 없음

### 2. 완전 분할 (Complete Coverage)

```turtle
# 모든 메트릭은 반드시 BaseMetric 또는 DerivedMetric 중 하나
Metric ≡ BaseMetric ⊔ DerivedMetric
```

**의미**: 중간 상태가 없는 완전한 분류 체계

### 3. 카디널리티 제약

```turtle
# MetricObservation의 필수 속성 (minCardinality = 1)
MetricObservation ⊑ (≥1 ofCompany)
MetricObservation ⊑ (≥1 observesMetric)
MetricObservation ⊑ (≥1 hasFiscalYear)
MetricObservation ⊑ (≥1 hasNumericValue)
MetricObservation ⊑ (≥1 hasPeriodType)
```

**의미**: 모든 관측값은 반드시 이 5가지 속성을 가져야 함

### 4. 값 기반 클래스 정의

```turtle
# hasPeriodType 값에 따른 자동 분류
DurationObservation ≡ MetricObservation ⊓ (hasPeriodType value "duration")
InstantObservation ≡ MetricObservation ⊓ (hasPeriodType value "instant")
```

**의미**: 추론 엔진이 `hasPeriodType` 값을 보고 자동으로 클래스 분류

### 5. 역 속성 (Inverse Properties)

```turtle
hasObservation ≡ inverse(ofCompany)
observedBy ≡ inverse(observesMetric)
containsObservation ≡ inverse(fromFiling)
```

**의미**: 양방향 탐색 가능
- `company1 hasObservation obs1` ⇔ `obs1 ofCompany company1`
- `metric1 observedBy obs1` ⇔ `obs1 observesMetric metric1`
- `filing1 containsObservation obs1` ⇔ `obs1 fromFiling filing1`

### 6. 복합 키 제약

```turtle
MetricObservation hasKey (ofCompany, observesMetric, hasFiscalYear)
```

**의미**: (회사, 메트릭, 회계연도) 조합이 각 관측값을 고유하게 식별

---

## 데이터 흐름 및 관계

### 1. 데이터 생성 흐름

```
XBRL 원시 데이터
    ↓
[추출 과정]
    ↓
BaseMetric 관측값 생성
    ├→ MetricObservation
    │   ├─ ofCompany → Company
    │   ├─ observesMetric → BaseMetric
    │   ├─ hasFiscalYear → 2023
    │   ├─ hasNumericValue → 1000000
    │   ├─ hasPeriodType → "duration"
    │   ├─ hasXbrlConcept → XBRLConcept
    │   └─ isDerived → false
    │
    ↓
[계산 과정]
    ↓
DerivedMetric 관측값 생성
    └→ MetricObservation
        ├─ observesMetric → DerivedMetric (예: ROE)
        ├─ isDerived → true
        ├─ computedFromMetric → NetIncome, Equity
        ├─ computedFromObservation → [NetIncome 관측값, Equity 관측값]
        └─ hasSourceNote → "NetIncome(1000000) / Avg(Equity_2023, Equity_2022)"
    ↓
[집계 과정]
    ↓
벤치마크 및 랭킹 생성
    ├→ IndustryBenchmark (산업 통계)
    └→ TopRanking (상위 순위)
```

### 2. 쿼리 패턴 예시

#### 패턴 1: 특정 회사의 시계열 데이터

```sparql
# Apple의 2020-2023년 매출 추이
SELECT ?year ?revenue
WHERE {
  ?company efin:hasTicker "AAPL" .
  ?obs efin:ofCompany ?company ;
       efin:observesMetric efin:Revenue ;
       efin:hasFiscalYear ?year ;
       efin:hasNumericValue ?revenue .
  FILTER(?year >= 2020 && ?year <= 2023)
}
ORDER BY ?year
```

#### 패턴 2: 산업 벤치마크와 비교

```sparql
# 소프트웨어 산업의 ROE 중앙값과 Apple 비교
SELECT ?appleROE ?industryMedian
WHERE {
  # Apple의 ROE
  ?company efin:hasTicker "AAPL" .
  ?obs efin:ofCompany ?company ;
       efin:observesMetric efin:ROE ;
       efin:hasFiscalYear 2023 ;
       efin:hasNumericValue ?appleROE .

  # 산업 벤치마크
  ?benchmark a efin:IndustryBenchmark ;
             efin:forIndustry efin:IndustryServicesPrepackagedSoftware ;
             efin:forMetric efin:ROE ;
             efin:forFiscalYear 2023 ;
             efin:hasMedianValue ?industryMedian .
}
```

#### 패턴 3: 파생 관측값의 계보 추적

```sparql
# ROIC 계산에 사용된 모든 기본 메트릭 추적
SELECT ?baseMetric ?value
WHERE {
  ?company efin:hasTicker "MSFT" .
  ?roicObs efin:ofCompany ?company ;
           efin:observesMetric efin:ROIC ;
           efin:hasFiscalYear 2023 ;
           efin:computedFromObservation+ ?baseObs .

  ?baseObs efin:observesMetric ?baseMetric ;
           efin:hasNumericValue ?value ;
           efin:isDerived false .

  ?baseMetric a efin:BaseMetric .
}
```

#### 패턴 4: 자동 클래스 분류 활용

```sparql
# 2023년의 모든 Duration 관측값 (손익계산서 항목)
SELECT ?company ?metric ?value
WHERE {
  ?obs a efin:DurationObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear 2023 ;
       efin:hasNumericValue ?value .
}
```

#### 패턴 5: Filing 문서에서 데이터 추출

```sparql
# Apple의 특정 10-K 문서에서 추출된 모든 재무 지표
SELECT ?metric ?value ?fiscalYear ?periodEnd
WHERE {
  ?filing a efin:TenK ;
          efin:accessionNumber "0000320193-23-000106" ;
          efin:containsObservation ?obs .

  ?obs efin:observesMetric ?metric ;
       efin:hasNumericValue ?value ;
       efin:hasFiscalYear ?fiscalYear ;
       efin:hasPeriodEnd ?periodEnd .
}
```

#### 패턴 6: 관측 시점 vs 보고 시점 분석

```sparql
# 2023 회계연도 데이터가 언제 보고되었는지 추적
SELECT ?company ?metric ?fiscalYear ?filingDate ?lag
WHERE {
  ?obs efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear ?fiscalYear ;
       efin:fromFiling ?filing .

  ?filing efin:filingDate ?filingDate .

  FILTER(?fiscalYear = 2023)

  # 보고 시차 계산 (년 단위)
  BIND(YEAR(?filingDate) - ?fiscalYear AS ?lag)
}
ORDER BY ?filingDate
```

#### 패턴 7: 문서 유형별 데이터 비교

```sparql
# 동일 회사의 10-K(연간)와 10-Q(분기) 데이터 비교
SELECT ?filingType ?fiscalPeriod ?revenue ?filingDate
WHERE {
  ?company efin:hasTicker "MSFT" .

  ?filing efin:filedBy ?company ;
          efin:fiscalPeriod ?fiscalPeriod ;
          efin:filingDate ?filingDate ;
          efin:containsObservation ?obs .

  ?filing a ?filingType .
  FILTER(?filingType IN (efin:TenK, efin:TenQ))

  ?obs efin:observesMetric efin:Revenue ;
       efin:hasNumericValue ?revenue .

  FILTER(YEAR(?filingDate) = 2024)
}
ORDER BY ?filingDate
```

#### 패턴 8: 분기별 데이터 조회

```sparql
# Apple의 2024년 분기별 매출 추이
SELECT ?quarter ?revenue ?periodEnd
WHERE {
  ?company efin:hasTicker "AAPL" .

  ?obs efin:ofCompany ?company ;
       efin:observesMetric efin:Revenue ;
       efin:hasFiscalYear 2024 ;
       efin:hasQuarter ?quarter ;
       efin:hasNumericValue ?revenue ;
       efin:hasPeriodEnd ?periodEnd .
}
ORDER BY ?quarter
```

```sparql
# 특정 메트릭의 연간 vs 분기 데이터 구분
SELECT ?fiscalYear ?quarter ?netIncome
WHERE {
  ?company efin:hasTicker "MSFT" .

  ?obs efin:ofCompany ?company ;
       efin:observesMetric efin:NetIncome ;
       efin:hasFiscalYear ?fiscalYear ;
       efin:hasNumericValue ?netIncome .

  OPTIONAL { ?obs efin:hasQuarter ?quarter }

  FILTER(?fiscalYear = 2023)
}
ORDER BY ?quarter
# hasQuarter가 없으면 연간 데이터, 있으면 분기 데이터
```

### 3. 추론 예시

온톨로지의 제약 조건을 통한 자동 추론:

```
입력 데이터:
  obs1 ofCompany company1
  obs1 observesMetric efin:Revenue
  obs1 hasPeriodType "duration"

추론 결과:
  1. obs1 rdf:type efin:MetricObservation (도메인 제약)
  2. obs1 rdf:type efin:DurationObservation (값 제약)
  3. company1 hasObservation obs1 (역속성)
  4. efin:Revenue observedBy obs1 (역속성)
  5. efin:Revenue rdf:type efin:Metric (범위 제약)
```

---

## 확장성 및 유지보수 고려사항

### 1. 새로운 메트릭 추가

**BaseMetric 추가**:
```turtle
efin:ResearchAndDevelopment
  a owl:Class ;
  rdfs:subClassOf efin:BaseMetric ;
  rdfs:label "Research and Development"@en ;
  rdfs:comment "연구개발비. XBRL의 ResearchAndDevelopmentExpense에서 추출."@ko .
```

**DerivedMetric 추가**:
```turtle
efin:RnDIntensity
  a owl:Class ;
  rdfs:subClassOf efin:DerivedRatio ;
  rdfs:label "R&D Intensity"@en ;
  rdfs:comment "연구개발 집약도."@ko ;
  efin:hasFormulaNote "ResearchAndDevelopment / Revenue"@en .
```

### 2. 새로운 벤치마크 유형 추가

```turtle
efin:RegionalBenchmark
  a owl:Class ;
  rdfs:label "Regional Benchmark"@en ;
  rdfs:comment "지역별 벤치마크 통계."@ko .

efin:forRegion
  a owl:ObjectProperty ;
  rdfs:domain efin:RegionalBenchmark ;
  rdfs:range efin:Region ;
  rdfs:label "forRegion"@en .
```

### 3. 버전 관리 전략

- **온톨로지 버전**: `owl:versionInfo`로 관리
- **XBRL 택소노미 버전**: `XBRLConcept.hasNamespace`의 연도로 식별
- **메트릭 정의 변경**: 새로운 클래스 생성 + `owl:deprecated` 마킹

---

## 부록: 주요 설계 결정 요약

| 설계 결정 | 이유 | 영향 |
|---------|------|------|
| BaseMetric과 DerivedMetric 분리 | XBRL 직접 추출 데이터와 계산된 데이터의 명확한 구분 | 데이터 계보 추적 용이 |
| MetricObservation 복합키 | (회사, 메트릭, 연도) 조합의 고유성 보장 | 데이터 무결성 강화 |
| hasPeriodType 기반 자동 분류 | 손익계산서(duration)와 재무상태표(instant) 항목의 의미론적 차이 표현 | 추론 엔진 활용 가능 |
| 전이적 computedFromObservation | 다단계 파생 메트릭의 전체 계보 추적 | ROIC → NOPAT → NetIncome 경로 추적 |
| FIBO-BE 연동 | 금융 산업 표준 온톨로지와의 상호운용성 | 엔터프라이즈 통합 용이 |
| QUDT/OM 단위 정렬 | 표준 단위 시스템 활용 | 단위 변환 및 검증 가능 |
| 벤치마크 다층 구조 | Industry(세분화) + Sector(거시적) 이중 비교 | 유연한 비교 분석 |

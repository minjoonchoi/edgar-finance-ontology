# EFIN Financial Ontology Schema 참조 문서

## 문서 목적

본 문서는 **EFIN Financial Ontology의 스키마 구조를 참조**하기 위한 문서입니다. 클래스, 프로퍼티, 제약 조건, 인스턴스 생성 규칙 등 스키마 관련 정보를 제공합니다.

**관련 문서:**
- [계층 구조 설명서](./hierarchy-structure.md): 온톨로지의 전체 계층 구조와 설계 의도 상세 설명
- [온톨로지 디자인 평가](./ontology_design_evaluation.md): 온톨로지 아키텍처 및 설계 평가
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [스키마 개발 과정](./schema_development_workflow.md): ODP 기반 온톨로지 개발 과정
- [인스턴스 통계](./instance_statistics.md): 현재 인스턴스 데이터의 클래스별/연도별 분포

---

## 개요

EFIN (EDGAR Financial) 온톨로지는 SEC EDGAR의 XBRL 데이터에서 추출한 재무 지표를 구조화하여 표현하는 OWL 온톨로지입니다. 기업(Company), 재무 지표(Metric), 관측값(MetricObservation)을 중심으로 구성되어 있으며, Sector/Industry 분류와 파생 지표 계산 관계를 지원합니다.

**네임스페이스**: `https://w3id.org/edgar-fin/2024#`  
**Prefix**: `efin:`  
**스키마 파일**: `ontology/efin_schema.ttl`

---

## 1. 클래스 계층 구조

### 1.1 핵심 클래스

| 클래스 | 부모 클래스 | 설명 |
|--------|------------|------|
| `efin:Company` | `fibo-be:LegalEntity` | 기업(법인) |
| `efin:Sector` | `owl:Thing` | 섹터 분류 (예: Information Technology, Financials) |
| `efin:Industry` | `owl:Thing` | 산업 분류 (예: Services-Prepackaged Software) |
| `efin:Metric` | `owl:Thing` | 재무 지표 개념 (추상 클래스) |
| `efin:BaseMetric` | `efin:Metric` | 직접 추출된 기초 지표 |
| `efin:DerivedMetric` | `efin:Metric` | 계산된 파생 지표 |
| `efin:DerivedRatio` | `efin:DerivedMetric` | 비율 형태의 파생 지표 |
| `efin:MetricObservation` | `owl:Thing` | 특정 기업·기간·지표에 대한 관측값 (Duration/Instant 하위 클래스). (회사, 메트릭, 회계연도, 분기) 복합키로 고유 식별 |
| `efin:DurationObservation` | `efin:MetricObservation` | 기간형(periodType=\"duration\") 관측값 |
| `efin:InstantObservation` | `efin:MetricObservation` | 시점형(periodType=\"instant\") 관측값 |
| `efin:FinancialReportingConcept` | `owl:Thing` | 재무 보고 표준 개념 상위 추상 클래스 |
| `efin:XBRLConcept` | `efin:FinancialReportingConcept` | XBRL 태그 개념 |
| `efin:Unit` | `owl:Thing` | 측정 단위 (QUDT Unit과 정렬) |
| `efin:Currency` | `owl:Thing` | 통화 단위 (QUDT CurrencyUnit과 정렬) |
| `efin:Filing` | `owl:Thing` | SEC 제출 문서 (10-K, 10-Q, 20-F, 8-K 등) |
| `efin:TenK` / `efin:TenQ` / `efin:TwentyF` / `efin:EightK` | `efin:Filing` | Filing의 서브타입 (폼 종류별) |
| `efin:IndustryBenchmark` | `owl:Thing` | 산업 수준 벤치마크 통계 |
| `efin:SectorBenchmark` | `owl:Thing` | 섹터 수준 벤치마크 통계 |
| `efin:TopRanking` | `owl:Thing` | 산업/섹터/전체 랭킹 인스턴스 |

### 1.2 Base Metrics (기초 지표)

**기간형 (Duration) 지표:**
- `efin:Revenue` - 매출
- `efin:OperatingIncome` - 영업이익
- `efin:NetIncome` - 순이익
- `efin:CFO` - 영업활동 현금흐름
- `efin:GrossProfit` - 매출총이익
- `efin:CapEx` - 자본지출
- `efin:InterestExpense` - 이자비용
- `efin:DepAmort` - 감가상각비
- `efin:CostOfGoodsSold` - 매출원가
- `efin:IncomeTaxExpense` - 소득세비용
- `efin:PreTaxIncome` - 세전이익
- `efin:EPSDiluted` - 희석 주당순이익
- `efin:DilutedShares` - 가중평균 희석주식수

**시점형 (Instant) 지표:**
- `efin:Assets` - 자산
- `efin:Liabilities` - 부채
- `efin:Equity` - 자본
- `efin:CashAndCashEquivalents` - 현금 및 현금성자산
- `efin:LongTermDebt` - 장기부채
- `efin:ShortTermDebt` - 단기부채
- `efin:DebtCurrent` - 당기부채 (ShortTermDebt와 동등, `owl:equivalentClass` 관계)
- `efin:CurrentAssets` - 유동자산
- `efin:CurrentLiabilities` - 유동부채
- `efin:Inventories` - 재고자산
- `efin:AccountsReceivable` - 매출채권

### 1.3 Derived Metrics (파생 지표)

**성장률 지표 (Growth):**
- `efin:RevenueGrowthYoY` - 매출 전년대비 성장률
- `efin:NetIncomeGrowthYoY` - 순이익 전년대비 성장률
- `efin:CFOGrowthYoY` - 영업현금흐름 전년대비 성장률
- `efin:AssetGrowthRate` - 자산 증가율

**수익성 지표 (Profitability):**
- `efin:GrossMargin` - 매출총이익률
- `efin:OperatingMargin` - 영업이익률
- `efin:NetProfitMargin` - 순이익률
- `efin:EBITDAMargin` - EBITDA 마진
- `efin:ROE` - 자기자본이익률
- `efin:ROIC` - 투하자본이익률

**현금흐름 지표:**
- `efin:FreeCashFlow` - 잉여현금흐름
- `efin:EBITDA` - EBITDA
- `efin:NOPAT` - 세후 영업이익

**레버리지 지표:**
- `efin:DebtToEquity` - 부채비율
- `efin:InterestCoverage` - 이자보상배수

**유동성 지표:**
- `efin:CurrentRatio` - 유동비율
- `efin:QuickRatio` - 당좌비율
- `efin:OperatingCashFlowRatio` - 영업현금흐름비율

**효율성 지표:**
- `efin:AssetTurnover` - 자산회전율
- `efin:InventoryTurnover` - 재고회전율
- `efin:ReceivablesTurnover` - 매출채권회전율
- `efin:EquityRatio` - 자기자본비율

**기타:**
- `efin:InvestedCapital` - 투하자본

---

## 2. Object Properties (객체 속성)

### 2.1 Company 관련

| 속성 | Domain | Range | 설명 |
|------|--------|-------|------|
| `efin:inSector` | `efin:Company` | `efin:Sector` | 기업이 속한 섹터 |
| `efin:inIndustry` | `efin:Company` | `efin:Industry` | 기업이 속한 산업 |
| `efin:hasObservation` | `efin:Company` | `efin:MetricObservation` | 회사가 가진 관측값 (ofCompany의 역관계) |

### 2.2 Industry-Sector 관계

| 속성 | Domain | Range | 설명 |
|------|--------|-------|------|
| `efin:inSectorOf` | `efin:Industry` | `efin:Sector` | 산업이 속한 섹터 |

### 2.3 MetricObservation 관련

| 속성 | Domain | Range | 설명 |
|------|--------|-------|------|
| `efin:ofCompany` | `efin:MetricObservation` | `efin:Company` | 관측값이 속한 기업 |
| `efin:observesMetric` | `efin:MetricObservation` | `efin:Metric` | 관측된 지표 |
| `efin:computedFromMetric` | `efin:MetricObservation` | `efin:Metric` | 파생 관측값의 입력 지표 개념 |
| `efin:computedFromObservation` | `efin:MetricObservation` | `efin:MetricObservation` | 파생 관측값의 입력 관측값 인스턴스 |
| `efin:hasXbrlConcept` | `efin:MetricObservation` | `efin:XBRLConcept` | 사용된 XBRL 태그 개념 |
| `efin:hasUnit` | `efin:MetricObservation` | `efin:Unit` | 관측값의 단위 (객체 속성) |
| `efin:hasCurrency` | `efin:MetricObservation` | `efin:Currency` | 관측값의 통화 단위 |
| `efin:fromFiling` | `efin:MetricObservation` | `efin:Filing` | 관측값이 추출된 원본 Filing |
| `efin:hasBenchmark` | `efin:MetricObservation` | `efin:IndustryBenchmark` ∪ `efin:SectorBenchmark` | 해당 관측값과 비교되는 벤치마크 |

### 2.4 Filing / Benchmark / Ranking 관련

| 속성 | Domain | Range | 설명 |
|------|--------|-------|------|
| `efin:filedBy` | `efin:Filing` | `efin:Company` | Filing을 제출한 회사 |
| `efin:containsObservation` | `efin:Filing` | `efin:MetricObservation` | Filing에서 추출된 관측값 |
| `efin:forIndustry` | `efin:IndustryBenchmark` | `efin:Industry` | 산업 벤치마크의 대상 산업 |
| `efin:forSector` | `efin:SectorBenchmark` | `efin:Sector` | 섹터 벤치마크의 대상 섹터 |
| `efin:forMetric` | `efin:IndustryBenchmark` ∪ `efin:SectorBenchmark` ∪ `efin:TopRanking` | `efin:Metric` | 벤치마크/랭킹의 대상 지표 |
| `efin:hasRanking` | `efin:Company` | `efin:TopRanking` | 회사가 포함된 랭킹 인스턴스 |

---

## 3. Datatype Properties (데이터 타입 속성)

### 3.1 Company 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:hasCIK` | `xsd:string` | SEC CIK 번호 (10자리) |
| `efin:hasTicker` | `xsd:string` | 티커 심볼 |
| `efin:hasCompanyName` | `xsd:string` | 회사명 |
| `efin:hasSIC` | `xsd:string` | SIC 코드 |
| `efin:hasSICDescription` | `xsd:string` | SIC 설명 |
| `efin:hasFiscalYearEnd` | `xsd:string` | 회계연도 종료일 (MMDD 형식, 예: \"1231\") |

### 3.2 MetricObservation 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:hasFiscalYear` | `xsd:integer` | 회계연도 |
| `efin:hasPeriodType` | `xsd:string` | 기간 타입 ("duration" 또는 "instant") |
| `efin:hasPeriodEnd` | `xsd:dateTime` | 기간 종료일 (시점 포함) |
| `efin:hasNumericValue` | `xsd:double` | 수치값 |
| `efin:isDerived` | `xsd:boolean` | 파생 지표 여부 |
| `efin:hasSourceType` | `xsd:string` | 데이터 소스 타입 (아래 참조) |
| `efin:hasSelectedTag` | `xsd:string` | 선택된 XBRL 태그 (QName) |
| `efin:hasCompositeName` | `xsd:string` | 복합 계산 이름 |
| `efin:hasSelectionReason` | `xsd:string` | 선택 이유 |
| `efin:hasConfidence` | `xsd:double` | 신뢰도 점수 (0.0-1.0) |
| `efin:hasComponentsText` | `xsd:string` | 구성 요소 (JSON 텍스트) |
| `efin:hasQuarter` | `xsd:integer` | 분기 (1~4, 분기 데이터에서만 사용) |

### 3.3 Benchmark / Ranking 속성

| 속성 | Domain | 타입 | 설명 |
|------|--------|------|------|
| `efin:forFiscalYear` | `efin:IndustryBenchmark` ∪ `efin:SectorBenchmark` ∪ `efin:TopRanking` | `xsd:integer` | 벤치마크/랭킹의 기준 회계연도 |
| `efin:hasAverageValue` | `efin:IndustryBenchmark` ∪ `efin:SectorBenchmark` | `xsd:double` | 평균값 |
| `efin:hasMedianValue` | 동일 | `xsd:double` | 중앙값 |
| `efin:hasMaxValue` | 동일 | `xsd:double` | 최대값 |
| `efin:hasMinValue` | 동일 | `xsd:double` | 최소값 |
| `efin:hasPercentile25` | 동일 | `xsd:double` | 25백분위수 |
| `efin:hasPercentile75` | 동일 | `xsd:double` | 75백분위수 |
| `efin:hasSampleSize` | 동일 | `xsd:integer` | 표본 개수(기업 수) |
| `efin:hasRankingType` | `efin:TopRanking` | `xsd:string` | 랭킹 유형 (Top10, Top50, Composite 등) |
| `efin:hasRank` | `efin:TopRanking` | `xsd:integer` | 순위 (1부터 시작) |
| `efin:hasRankingValue` | `efin:TopRanking` | `xsd:double` | 랭킹 산출에 사용된 값 |
| `efin:hasCompositeScore` | `efin:TopRanking` | `xsd:double` | 복합 점수 |

### 3.4 Metric 주석 속성

스키마에서는 계산 공식 관련 정보를 `owl:AnnotationProperty`로 분리하여 사용합니다.

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:hasFormulaNote` | Annotation | 계산식에 대한 자연어 설명 |
| `efin:hasFormulaMath` | Annotation | 수학 표기 공식(문자열) |

### 3.5 XBRLConcept 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:hasQName` | `xsd:string` | XBRL 태그 QName |
| `efin:hasNamespace` | `xsd:anyURI` | XBRL 네임스페이스 |
| `efin:hasConceptLabel` | `xsd:string` | 개념 레이블 |

### 3.6 Filing 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:accessionNumber` | `xsd:string` | SEC Accession Number (예: 0000320193-23-000106) |
| `efin:filingDate` | `xsd:dateTime` | 제출일자 |
| `efin:fiscalPeriod` | `xsd:string` | 회계 기간 ("FY", "Q1"~"Q4") |
| `efin:hasFormType` | `xsd:string` | SEC 제출 문서 형태 (예: \"10-K\", \"10-Q\") |
| `efin:documentUrl` | `xsd:anyURI` | EDGAR 문서 URL |
| `efin:acceptanceDateTime` | `xsd:dateTime` | SEC 접수 일시 |

---

## 4. sourceType 값 그룹화

`efin:hasSourceType`은 데이터 추출 방식을 나타내며, 다음과 같이 그룹화됩니다:

### 4.1 Base Extraction (기초 추출)
- `annual` - 연간 보고서(FY)에서 직접 추출
- `ytd-q4` - 분기 보고서의 4분기 누적값
- `instant` - 시점 데이터 (재무상태표)
- `lenient` - 완화된 기준으로 추출 (FP 태그 없이 날짜만 매칭)

### 4.2 Derived Computation (파생 계산)
- `derived` - 기초 지표로부터 계산된 파생 지표
- `derived-growth` - 전년도 대비 성장률 계산

### 4.3 Direct Growth (직접 성장률)
- `direct-growth` - XBRL에서 직접 추출한 성장률 (비율/퍼센트)
- `direct-growth-normalized` - 절대 증가액을 비율로 정규화한 성장률

---

## 5. Benchmark / Ranking 모델 개요

이 온톨로지는 산업/섹터 수준의 통계와 개별 기업 랭킹을 다음 세 클래스와 그 속성들로 모델링합니다.

### 5.1 Benchmark 클래스

| 클래스 | 설명 |
|--------|------|
| `efin:IndustryBenchmark` | 특정 산업 + 메트릭 + 연도에 대한 통계값 (평균, 중앙값, 백분위수 등) |
| `efin:SectorBenchmark` | 특정 섹터 + 메트릭 + 연도에 대한 통계값 |

주요 속성:

- **대상 지정**
  - `efin:forIndustry` / `efin:forSector` / `efin:forMetric`
  - `efin:forFiscalYear` (해당 통계가 어떤 회계연도 기준인지)
- **통계값**
  - `efin:hasAverageValue`, `efin:hasMedianValue`, `efin:hasMaxValue`, `efin:hasMinValue`
  - `efin:hasPercentile25`, `efin:hasPercentile75`
  - `efin:hasSampleSize` (통계에 포함된 기업 수)

MetricObservation는 `efin:hasBenchmark`로 관련 벤치마크(산업/섹터)를 참조할 수 있습니다.

### 5.2 TopRanking 클래스

| 클래스 | 설명 |
|--------|------|
| `efin:TopRanking` | 특정 메트릭과 범위(산업/섹터/전체)에 대한 개별 기업의 순위 정보 |

주요 속성:

- **범위와 대상**
  - `efin:forIndustry` / `efin:forSector` / `efin:forMetric`
  - `efin:forFiscalYear`
- **랭킹 지표**
  - `efin:hasRankingType` (예: `Top10`, `Top50`, `Composite`)
  - `efin:hasRank` (1부터 시작)
  - `efin:hasRankingValue` (순위를 매긴 기준 값)
  - `efin:hasCompositeScore` (복합 점수, 복수 지표 조합 시)

개별 회사는 `efin:hasRanking`을 통해 자신이 속한 랭킹 인스턴스를 참조합니다.

---

## 6. 인스턴스 생성 규칙

### 5.1 Company 인스턴스

**IRI 형식**: `efin:CIK{cik}` (CIK 10자리, 항상 사용)

**예시**:
```turtle
efin:CIK0000796343 a efin:Company ;
  efin:hasCIK "0000796343" ;
  efin:hasTicker "ADBE" ;
  efin:hasCompanyName "Adobe Inc." ;
  efin:hasSIC "7372" ;
  efin:hasSICDescription "Services-Prepackaged Software" ;
  efin:hasFiscalYearEnd "1128" ;
  efin:inSector efin:SectorInformationTechnology ;
  efin:inIndustry efin:IndustryServicesPrepackagedSoftware .
```

### 5.2 Sector/Industry 인스턴스

**IRI 형식**: 
- Sector: `efin:Sector{sector_name}` (CamelCase 형식)
- Industry: `efin:Industry{industry_name}` (CamelCase 형식)

**예시**:
```turtle
efin:SectorInformationTechnology a efin:Sector .

efin:IndustryServicesPrepackagedSoftware a efin:Industry .
efin:IndustryServicesPrepackagedSoftware efin:inSectorOf efin:SectorInformationTechnology .
```

### 5.3 MetricObservation 인스턴스

**IRI 형식**: `efin:obs-{cik}-{fy}-{metric}-{end}`

**예시 (기초 지표)**:
```turtle
efin:obs-0000796343-2024-Revenue-2024-11-29 a efin:DurationObservation ;
  efin:ofCompany efin:CIK0000796343 ;
  efin:observesMetric efin:Revenue ;
  efin:hasFiscalYear 2024 ;
  efin:hasPeriodType "duration" ;
  efin:hasPeriodEnd "2024-11-29T00:00:00"^^xsd:dateTime ;
  efin:hasUnit efin:UnitUSD ;
  efin:hasCurrency efin:CurrencyUSD ;
  efin:hasNumericValue "21505000000.0"^^xsd:double ;
  efin:isDerived false ;
  efin:hasSourceType "annual" ;
  efin:hasSelectedTag "us-gaap:Revenues" ;
  efin:hasConfidence "1.0"^^xsd:double ;
  efin:hasComponentsText "{}" ;
  efin:hasSelectionReason "primary-tag" .
```

### 5.4 Filing 인스턴스

**IRI 형식**: `efin:Filing{accessionNumber}` (하이픈 제거, 예: `efin:Filing000032019323000106`)

```turtle
efin:Filing000079634325000004 a efin:TenK ;
  efin:accessionNumber "0000796343-25-000004" ;
  efin:filedBy efin:CIK0000796343 ;
  efin:hasFormType "10-K" ;
  efin:fiscalPeriod "FY" ;
  efin:filingDate "2025-01-30T00:00:00"^^xsd:dateTime ;
  efin:acceptanceDateTime "2025-01-30T12:34:56"^^xsd:dateTime ;
  efin:documentUrl "https://www.sec.gov/Archives/edgar/data/796343/000079634325000004/..."^^xsd:anyURI .
```

**예시 (파생 지표)**:
```turtle
efin:obs-0000796343-2024-RevenueGrowthYoY-2024-11-29 a efin:MetricObservation ;
  efin:ofCompany efin:CIK0000796343 ;
  efin:observesMetric efin:RevenueGrowthYoY ;
  efin:hasFiscalYear "2024"^^xsd:gYear ;
  efin:hasPeriodType "duration" ;
  efin:hasPeriodEnd "2024-11-29"^^xsd:date ;
  efin:hasUnit "ratio" ;
  efin:hasNumericValue 0.107991 ;
  efin:isDerived true ;
  efin:hasSourceType "derived-growth" ;
  efin:hasConfidence 0.94 ;
  efin:hasSelectionReason "(cur - prior) / prior (Revenue)" ;
  efin:computedFromMetric efin:Revenue .
```

---

## 6. computed_from 처리

파생 지표의 `computed_from` 필드는 문자열로 저장되며, TTL 생성 시 `efin:computedFromMetric` ObjectProperty로 구조화됩니다.

### 6.1 파싱 규칙

`computed_from` 문자열은 쉼표(`,`) 또는 세미콜론(`;`)으로 구분되며, 괄호 안의 접미사 `(cur)`, `(prior)` 등은 제거됩니다.

**예시**:
- `"Revenue(cur),Revenue(prior)"` → `efin:computedFromMetric efin:Revenue`
- `"NetIncome;Revenue"` → `efin:computedFromMetric efin:NetIncome`, `efin:computedFromMetric efin:Revenue`
- `"direct-growth"` → 링크 생성 안 함

### 6.2 computedFromObservation

향후 확장 가능: 실제 관측값 인스턴스에 대한 링크는 `efin:computedFromObservation`을 사용할 수 있습니다.

---

## 7. OWL 제약 조건 요약

본 온톨로지는 OWL 제약 조건만 사용합니다 (SHACL 미사용). 주요 제약 조건:

### 7.1 Disjoint 제약
```turtle
efin:BaseMetric owl:disjointWith efin:DerivedMetric .
efin:DurationObservation owl:disjointWith efin:InstantObservation .
```

### 7.2 Functional Property
```turtle
efin:ofCompany a owl:FunctionalProperty .
efin:observesMetric a owl:FunctionalProperty .
efin:hasFiscalYear a owl:FunctionalProperty .
efin:hasPeriodEnd a owl:FunctionalProperty .
efin:hasNumericValue a owl:FunctionalProperty .
```

### 7.3 Cardinality 제약
```turtle
efin:MetricObservation rdfs:subClassOf [
  owl:onProperty efin:ofCompany ; owl:minCardinality 1
] .
efin:MetricObservation rdfs:subClassOf [
  owl:onProperty efin:observesMetric ; owl:minCardinality 1
] .
efin:MetricObservation rdfs:subClassOf [
  owl:onProperty efin:hasFiscalYear ; owl:minCardinality 1
] .
efin:MetricObservation rdfs:subClassOf [
  owl:onProperty efin:hasNumericValue ; owl:minCardinality 1
] .
efin:MetricObservation rdfs:subClassOf [
  owl:onProperty efin:hasPeriodType ; owl:minCardinality 1
] .
```

### 7.4 Key 제약
```turtle
efin:MetricObservation owl:hasKey (
  efin:ofCompany
  efin:observesMetric
  efin:hasFiscalYear
  efin:hasQuarter
) .
```

**참고**: `hasQuarter`는 선택적 속성이므로, 연간 데이터(분기 미지정)와 분기 데이터(분기 지정) 모두 지원됩니다. 동일한 (회사, 메트릭, 회계연도)를 가진 연간 데이터는 단일 관측값으로 간주되며, 동일한 (회사, 메트릭, 회계연도, 분기)를 가진 분기 데이터는 단일 관측값으로 간주됩니다.

### 7.5 정의 클래스 (Defined Classes)
```turtle
efin:DurationObservation owl:equivalentClass [
  owl:intersectionOf (
    efin:MetricObservation
    [ owl:onProperty efin:hasPeriodType ; owl:hasValue "duration" ]
  )
] .

efin:InstantObservation owl:equivalentClass [
  owl:intersectionOf (
    efin:MetricObservation
    [ owl:onProperty efin:hasPeriodType ; owl:hasValue "instant" ]
  )
] .
```

---

## 8. 참고사항

- 모든 메트릭은 클래스로 정의되어 있으며, 관측값은 `efin:observesMetric`으로 연결됩니다.
- Sector/Industry는 문자열 리터럴이 아닌 인스턴스로 생성되어 그래프 쿼리가 가능합니다.
- 파생 지표의 계산 관계는 `efin:computedFromMetric`으로 추적 가능합니다.
- 신뢰도 점수(`efin:hasConfidence`)는 데이터 품질을 나타내며, 1.0에 가까울수록 높은 신뢰도를 의미합니다.
- `efin:Company`는 `fibo-be:LegalEntity`의 하위 클래스로, FIBO와의 상호 운용성을 확보합니다.
- `efin:DebtCurrent`와 `efin:ShortTermDebt`는 `owl:equivalentClass` 관계로 동등하게 사용됩니다.

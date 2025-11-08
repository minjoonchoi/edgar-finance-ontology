# EFIN Financial Ontology Schema 참조 문서

## 문서 목적

본 문서는 **EFIN Financial Ontology의 스키마 구조를 참조**하기 위한 문서입니다. 클래스, 프로퍼티, 제약 조건, 인스턴스 생성 규칙 등 스키마 관련 정보를 제공합니다.

**다른 문서:**
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [스키마 개발 과정](./schema_development_workflow.md): ODP 기반 온톨로지 개발 과정
- [온톨로지 프로젝트 평가](./ontology_project_evaluation.md): 프로젝트 평가 기준 및 달성 사항
- [상호 운용성 가이드](./interoperability.md): FIBO 등 표준 온톨로지와의 통합

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
| `efin:Company` | `owl:Thing` | 기업(법인) |
| `efin:Sector` | `owl:Thing` | 섹터 분류 (예: Information Technology, Financials) |
| `efin:Industry` | `owl:Thing` | 산업 분류 (예: Services-Prepackaged Software) |
| `efin:Metric` | `owl:Thing` | 재무 지표 개념 (추상 클래스) |
| `efin:BaseMetric` | `efin:Metric` | 직접 추출된 기초 지표 |
| `efin:DerivedMetric` | `efin:Metric` | 계산된 파생 지표 |
| `efin:DerivedRatio` | `efin:DerivedMetric` | 비율 형태의 파생 지표 |
| `efin:MetricObservation` | `owl:Thing` | 특정 기업·기간·지표에 대한 관측값 |
| `efin:XBRLConcept` | `owl:Thing` | XBRL 태그 개념 |

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
- `efin:DebtCurrent` - 당기부채
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
| `efin:xbrlConcept` | `efin:MetricObservation` | `efin:XBRLConcept` | 사용된 XBRL 태그 개념 |

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
| `efin:hasFiscalYearEnd` | `xsd:string` | 회계연도 종료일 (MMDD 형식, 예: "1231") |

### 3.2 MetricObservation 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:hasFiscalYear` | `xsd:gYear` | 회계연도 |
| `efin:hasPeriodType` | `xsd:string` | 기간 타입 ("duration" 또는 "instant") |
| `efin:hasPeriodEnd` | `xsd:date` | 기간 종료일 |
| `efin:hasUnit` | `xsd:string` | 단위 (예: "USD", "ratio", "shares") |
| `efin:hasNumericValue` | `xsd:decimal` | 수치값 |
| `efin:isDerived` | `xsd:boolean` | 파생 지표 여부 |
| `efin:hasFormType` | `xsd:string` | SEC 제출 문서 형태 (예: "10-K", "10-Q") |
| `efin:hasAccessionId` | `xsd:string` | SEC 접수번호 |
| `efin:hasSourceType` | `xsd:string` | 데이터 소스 타입 (아래 참조) |
| `efin:hasSelectedTag` | `xsd:string` | 선택된 XBRL 태그 (QName) |
| `efin:hasCompositeName` | `xsd:string` | 복합 계산 이름 |
| `efin:hasSelectionReason` | `xsd:string` | 선택 이유 |
| `efin:hasConfidence` | `xsd:decimal` | 신뢰도 점수 (0.0-1.0) |
| `efin:hasComponentsText` | `xsd:string` | 구성 요소 (JSON 텍스트) |

### 3.3 Metric 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:formulaNote` | `xsd:string` | 수식 설명 (파생 지표용) |

### 3.4 XBRLConcept 속성

| 속성 | 타입 | 설명 |
|------|------|------|
| `efin:hasQName` | `xsd:string` | XBRL 태그 QName |
| `efin:hasNamespace` | `xsd:anyURI` | XBRL 네임스페이스 |
| `efin:conceptLabel` | `xsd:string` | 개념 레이블 |

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

## 5. 인스턴스 생성 규칙

### 5.1 Company 인스턴스

**IRI 형식**: `efin:CIK{cik}` (CIK가 있는 경우) 또는 `efin:Company-{symbol}`

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
efin:obs-0000796343-2024-Revenue-2024-11-29 a efin:MetricObservation ;
  efin:ofCompany efin:CIK0000796343 ;
  efin:observesMetric efin:Revenue ;
  efin:hasFiscalYear "2024"^^xsd:gYear ;
  efin:hasPeriodType "duration" ;
  efin:hasPeriodEnd "2024-11-29"^^xsd:date ;
  efin:hasUnit "USD" ;
  efin:hasNumericValue 21505000000.0 ;
  efin:isDerived false ;
  efin:hasFormType "10-K" ;
  efin:hasAccessionId "0000796343-25-000004" ;
  efin:hasSourceType "annual" ;
  efin:hasSelectedTag "us-gaap:Revenues" ;
  efin:hasConfidence 1.0 .
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
) .
```

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

**상세한 제약 조건 설명은** [온톨로지 프로젝트 평가 문서](./ontology_project_evaluation.md)를 참조하세요.

---

## 8. 파일 구조

- **스키마**: `ontology/efin_schema.ttl` - 온톨로지 클래스 및 속성 정의
- **인스턴스**: `data/instances_{fy}.ttl` - 실제 데이터 인스턴스 (스크립트로 생성)
- **CSV 출력**: 
  - `data/companies_{fy}.csv` - 기업 정보
  - `data/tags_{fy}.csv` - 관측값 정보
  - `data/benchmarks_{fy}.csv` - 벤치마크 통계
  - `data/rankings_{fy}.csv` - 랭킹 데이터

**데이터 추출 프로세스는** [전체 워크플로우 문서](./comprehensive_workflow.md)를 참조하세요.

---

## 9. 참고사항

- 모든 메트릭은 클래스로 정의되어 있으며, 관측값은 `efin:observesMetric`으로 연결됩니다.
- Sector/Industry는 문자열 리터럴이 아닌 인스턴스로 생성되어 그래프 쿼리가 가능합니다.
- 파생 지표의 계산 관계는 `efin:computedFromMetric`으로 추적 가능합니다.
- 신뢰도 점수(`efin:hasConfidence`)는 데이터 품질을 나타내며, 1.0에 가까울수록 높은 신뢰도를 의미합니다.
- `efin:Company`는 `fibo-be:LegalEntity`의 하위 클래스로, FIBO와의 상호 운용성을 확보합니다.

---

## 관련 문서

- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [스키마 개발 과정](./schema_development_workflow.md): ODP 기반 온톨로지 개발 과정
- [메트릭 추출 로직](./metric_extraction_logic.md): XBRL 태그 선택 및 메트릭 추출 상세 로직
- [온톨로지 프로젝트 평가](./ontology_project_evaluation.md): 프로젝트 평가 기준 및 달성 사항 (온톨로지 공학 수업 관점 포함)
- [상호 운용성 가이드](./interoperability.md): FIBO 등 표준 온톨로지와의 통합
- [투자 분석 쿼리](./investment_analysis_queries.md): SPARQL 쿼리 예시

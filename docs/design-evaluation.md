# EFIN 온톨로지 설계 평가 보고서

## 요약

본 문서는 EFIN(EDGAR Financial) 온톨로지의 설계를 온톨로지 공학의 주요 관점에서 평가합니다. 평가는 명확성(Clarity), 일관성(Coherence), 확장성(Extensibility), 최소 인코딩 편향(Minimal Encoding Bias), 최소 온톨로지 커밋(Minimal Ontological Commitment) 등의 기준을 중심으로 수행되었습니다.

**전체 평가 점수**: ★★★★☆ (4.2/5.0)

---

## 목차

1. [평가 개요](#평가-개요)
2. [설계 원칙 평가](#설계-원칙-평가)
3. [기술적 측면 평가](#기술적-측면-평가)
4. [도메인 적합성 평가](#도메인-적합성-평가)
5. [재사용성 및 상호운용성](#재사용성-및-상호운용성)
6. [개선 권장사항](#개선-권장사항)
7. [결론](#결론)

---

## 평가 개요

### 평가 기준

본 평가는 Gruber(1995)와 Noy & McGuinness(2001)가 제시한 온톨로지 설계 원칙을 기반으로 합니다:

1. **명확성 (Clarity)**: 개념 정의의 명확성과 의도의 표현
2. **일관성 (Coherence)**: 추론 가능한 결론의 논리적 일관성
3. **확장성 (Extensibility)**: 기존 정의 수정 없이 확장 가능성
4. **최소 인코딩 편향 (Minimal Encoding Bias)**: 구현 기술로부터의 독립성
5. **최소 온톨로지 커밋 (Minimal Ontological Commitment)**: 필요 최소한의 개념 정의

### 평가 대상

- **온톨로지 버전**: 1.1.1-clarity-improvements
- **네임스페이스**: `https://w3id.org/edgar-fin/2024#`
- **파일**: `ontology/efin_schema.ttl`
- **클래스 수**: 58개 (핵심 클래스 20개 + 메트릭 클래스 38개)
- **객체 속성 수**: 18개 (v1.1: +3개 Filing 관련 속성)
- **데이터 속성 수**: 33개 (v1.1: +5개 Filing 속성, v1.1.1: +1개 hasQuarter)

**v1.1.1 주요 변경사항** (2025-01-20):
- ✅ 공식 명확성 개선: InvestedCapital, DebtToEquity에서 TotalDebt 약어 제거
- ✅ ShortTermDebt-DebtCurrent equivalentClass 관계 명시
- ✅ hasQuarter 속성 추가: 분기별 데이터 지원 준비

**v1.1 주요 변경사항**:
- ✅ Filing 클래스 계층 추가 (Filing, TenK, TenQ, EightK, TwentyF)
- ✅ 공시 문서 추적 기능 구현 (fromFiling, filedBy, containsObservation)
- ✅ SEC 문서 메타데이터 지원 (accessionNumber, filingDate, fiscalPeriod, documentUrl, acceptanceDateTime)

---

## 설계 원칙 평가

### 1. 명확성 (Clarity) ★★★★★ (5/5)

**평가 결과**: 탁월

#### 강점

**1.1 명확한 개념 정의**
- 모든 클래스와 속성에 `rdfs:label`(영문)과 `rdfs:comment`(한글) 제공
- 주석이 단순 번역이 아닌 맥락적 설명 포함
- 예시:
  ```turtle
  efin:MetricObservation
    rdfs:comment "특정 회사와 기간에 대한 메트릭의 관측된 수치값.
                  메트릭 개념의 구체적 인스턴스로, 시계열 재무 데이터의 기본 단위.
                  (회사, 메트릭, 회계연도) 복합키로 고유 식별."@ko .
  ```

**1.2 계산 공식의 명시적 표현**
- 모든 파생 메트릭에 `hasFormulaNote` 제공
- 수학적 표기법으로 명확한 계산 로직 전달
- 예시:
  ```turtle
  efin:ROE
    efin:hasFormulaNote "NetIncome / Average(Equity_t, Equity_{t-1})"@en .
  ```

**1.3 의미론적 명확성**
- Duration vs. Instant 구분으로 재무제표 항목의 의미론적 차이 명확화
- BaseMetric vs. DerivedMetric 구분으로 데이터 출처 명확화

**1.4 XBRL 추적성**
- `XBRLConcept` 클래스로 원본 XBRL 택소노미와의 연결 명시
- 각 BaseMetric 주석에 XBRL 태그명 포함

#### 개선 여지

- ~~일부 복잡한 메트릭(예: InvestedCapital)의 계산 공식에 약어(TotalDebt) 사용~~ ✅ **해결 (v1.1.1)**
  - 해결: InvestedCapital, DebtToEquity 공식에서 TotalDebt 약어 제거, 명시적 확장

### 2. 일관성 (Coherence) ★★★★☆ (4/5)

**평가 결과**: 우수

#### 강점

**2.1 논리적 제약 조건**
- 분리 제약(Disjointness) 명시적 선언
  ```turtle
  efin:BaseMetric owl:disjointWith efin:DerivedMetric .
  efin:DurationObservation owl:disjointWith efin:InstantObservation .
  ```
- 완전 분할(Complete Coverage) 보장
  ```turtle
  efin:Metric owl:equivalentClass [ owl:unionOf (efin:BaseMetric efin:DerivedMetric) ] .
  ```

**2.2 카디널리티 제약**
- MetricObservation의 5가지 필수 속성 명시 (minCardinality 1)
- 함수형 속성(Functional Property) 활용으로 데이터 무결성 보장

**2.3 역속성 정의**
- 양방향 탐색을 위한 역속성 명시
  ```turtle
  efin:hasObservation owl:inverseOf efin:ofCompany .
  efin:observedBy owl:inverseOf efin:observesMetric .
  ```

#### 개선 여지

**2.4 일부 암묵적 가정** ✅ **부분 해결 (v1.1.1)**
- ~~`ShortTermDebt`와 `DebtCurrent`의 관계가 주석에만 명시됨~~
  - 해결: `owl:equivalentClass` 관계 명시로 명확화
  - 현재: `efin:DebtCurrent owl:equivalentClass efin:ShortTermDebt`

**2.5 단위 일관성**
- `hasUnit`과 `hasCurrency` 모두 선택적 속성
  - 권장: 금액 메트릭은 `hasCurrency` 필수화 고려 (향후 SHACL 제약으로 구현 가능)

### 3. 확장성 (Extensibility) ★★★★★ (5/5)

**평가 결과**: 탁월

#### 강점

**3.1 계층 구조의 유연성**
- 개방형 클래스 계층 구조
  ```
  efin:Metric
    ├── efin:BaseMetric (확장 가능)
    └── efin:DerivedMetric
          └── efin:DerivedRatio (확장 가능)
  ```
- 새로운 메트릭 추가 시 기존 정의 수정 불필요

**3.2 벤치마크 시스템의 확장성**
- Industry와 Sector 외 다른 분류 체계 추가 가능
- 예: `RegionalBenchmark`, `GlobalBenchmark` 추가 용이

**3.3 속성의 확장 가능성**
- 새로운 데이터 속성 추가 시 기존 제약 조건 영향 없음
- 예: `hasQuarterlylnfo`, `hasAuditorNote` 등 추가 가능

**3.4 메타데이터 확장**
- `hasSourceNote`로 자유 형식 메타데이터 지원
- `XBRLConcept`에 추가 XBRL 메타데이터 속성 추가 가능

#### 확장 시나리오 예시

**시나리오 1: ESG 메트릭 추가**
```turtle
# 기존 구조 수정 없이 추가 가능
efin:ESGMetric
  a owl:Class ;
  rdfs:subClassOf efin:Metric ;
  rdfs:comment "환경, 사회, 지배구조 관련 메트릭."@ko .

efin:CarbonEmissions
  a owl:Class ;
  rdfs:subClassOf efin:ESGMetric, efin:BaseMetric .
```

**시나리오 2: 분기별 데이터 지원**
```turtle
# 새로운 속성 추가
efin:hasQuarter
  a owl:DatatypeProperty ;
  rdfs:domain efin:MetricObservation ;
  rdfs:range xsd:integer ;
  rdfs:comment "분기 (1, 2, 3, 4)."@ko .
```

### 4. 최소 인코딩 편향 (Minimal Encoding Bias) ★★★★☆ (4/5)

**평가 결과**: 우수

#### 강점

**4.1 구현 독립적 설계**
- RDF/OWL 표준 활용으로 플랫폼 중립성 확보
- 특정 데이터베이스 스키마에 종속되지 않음

**4.2 표준 온톨로지 활용**
- FIBO-BE: 금융 산업 표준
- QUDT/OM: 단위 시스템 표준
- 표준 활용으로 벤더 종속성 최소화

**4.3 의미론적 모델링**
- 재무 개념을 구현이 아닌 의미로 정의
- 예: `DurationObservation`은 "기간 동안 누적된 값"이라는 의미로 정의

#### 개선 여지

**4.4 일부 구현 힌트**
- `hasFormulaNote`의 계산 공식이 프로그래밍 언어 스타일
  - 예: `Average(Equity_t, Equity_{t-1})`
  - 권장: 보다 표준적인 수학 표기법 고려 (e.g., LaTeX)

**4.5 XBRL 특화 요소**
- `XBRLConcept`가 XBRL에 강하게 결합
  - 장점: SEC EDGAR 데이터 처리에 최적화
  - 단점: 다른 재무 보고 표준(예: IFRS Taxonomy) 지원 시 추가 작업 필요
  - 권장: 보다 일반적인 `FinancialReportingConcept` 상위 클래스 고려

### 5. 최소 온톨로지 커밋 (Minimal Ontological Commitment) ★★★★☆ (4/5)

**평가 결과**: 우수

#### 강점

**5.1 필요 최소한의 개념 정의**
- 재무 분석에 필수적인 개념만 포함
- 과도한 추상화나 일반화 회피

**5.2 유연한 제약 조건**
- 필수 속성을 최소화 (5개만 필수)
- 대부분의 속성을 선택적으로 유지하여 다양한 사용 사례 지원

**5.3 개방형 열거형**
- `hasRankingType`의 값("Top10", "Top50", ...)을 주석으로만 제시
- 향후 다른 랭킹 유형 추가 가능

#### 개선 여지

**5.4 일부 강한 커밋** ✅ **준비 완료 (v1.1.1)**
- `MetricObservation.hasKey`로 (회사, 메트릭, 연도) 조합의 고유성 보장
  - 해결: `hasQuarter` 선택적 속성 추가로 분기별 데이터 지원 준비
  - 현재: 연간 데이터는 hasQuarter 생략, 분기 데이터는 hasQuarter 명시
  - 향후: 분기 데이터 본격 사용 시 hasKey 제약 조정 검토 필요

**5.5 고정된 벤치마크 구조**
- Industry와 Sector의 2단계 계층 구조 고정
  - 3단계 이상의 분류 체계 지원 시 재설계 필요
  - 권장: 보다 일반적인 `ClassificationLevel` 개념 고려 (향후 v1.3+)

---

## 기술적 측면 평가

### 1. OWL 표현력 활용 ★★★★★ (5/5)

**평가 결과**: 탁월

#### 1.1 고급 OWL 구조 활용

**완전 분할 (Complete Disjoint Union)**
```turtle
efin:Metric owl:equivalentClass [ owl:unionOf (efin:BaseMetric efin:DerivedMetric) ] .
efin:BaseMetric owl:disjointWith efin:DerivedMetric .
```
- 의미: 모든 Metric은 정확히 BaseMetric 또는 DerivedMetric 중 하나
- 효과: 추론 엔진이 불완전 데이터 보완 가능

**값 기반 클래스 정의 (Value Restriction)**
```turtle
efin:DurationObservation owl:equivalentClass [
  owl:intersectionOf (
    efin:MetricObservation
    [ owl:onProperty efin:hasPeriodType ; owl:hasValue "duration" ]
  )
] .
```
- 의미: `hasPeriodType` 값을 보고 자동으로 클래스 분류
- 효과: 데이터 입력 시 명시적 타입 선언 불필요

**전이적 속성 (Transitive Property)**
```turtle
efin:computedFromObservation a owl:TransitiveProperty .
```
- 의미: A→B, B→C이면 A→C 자동 추론
- 효과: ROIC의 전체 계보를 자동으로 추적 가능

#### 1.2 속성 특성 활용

| 특성 | 사용 예시 | 효과 |
|------|---------|------|
| Functional | `ofCompany`, `observesMetric` | 각 관측값은 정확히 하나의 회사/메트릭에 속함 |
| Inverse | `hasObservation ↔ ofCompany` | 양방향 탐색 가능 |
| Asymmetric | `inSectorOf` | 순환 참조 방지 (Industry ↔ Sector) |

#### 1.3 복합 키 (Composite Key)
```turtle
efin:MetricObservation owl:hasKey ( efin:ofCompany efin:observesMetric efin:hasFiscalYear ) .
```
- OWL 2의 고급 기능 활용
- 관계형 데이터베이스의 복합 기본 키와 동등

### 2. 추론 가능성 ★★★★☆ (4/5)

**평가 결과**: 우수

#### 2.1 추론 시나리오

**시나리오 1: 자동 클래스 분류**
```
입력:
  obs1 efin:hasPeriodType "duration" .
  obs1 efin:observesMetric efin:Revenue .

추론:
  obs1 rdf:type efin:DurationObservation .
  obs1 rdf:type efin:MetricObservation .
  efin:Revenue rdf:type efin:Metric .
```

**시나리오 2: 역속성 추론**
```
입력:
  obs1 efin:ofCompany company1 .

추론:
  company1 efin:hasObservation obs1 .
```

**시나리오 3: 계보 추적**
```
입력:
  roicObs efin:computedFromObservation nopatObs .
  nopatObs efin:computedFromObservation netIncomeObs .

추론 (전이성):
  roicObs efin:computedFromObservation netIncomeObs .
```

#### 2.2 추론 한계

- 계산 로직 자체는 추론 불가
  - `hasFormulaNote`는 문자열이므로 추론 엔진이 해석 불가
  - SWRL 규칙 또는 SPIN으로 보완 가능 (향후 확장)

### 3. 쿼리 효율성 ★★★★☆ (4/5)

**평가 결과**: 우수

#### 3.1 효율적인 쿼리 패턴

**패턴 1: 직접 탐색**
```sparql
# ofCompany가 함수형이므로 효율적
SELECT ?value
WHERE {
  ?obs efin:ofCompany <company1> ;
       efin:observesMetric efin:Revenue ;
       efin:hasNumericValue ?value .
}
```

**패턴 2: 역속성 활용**
```sparql
# 역속성으로 회사의 모든 관측값 탐색
SELECT ?obs
WHERE {
  <company1> efin:hasObservation ?obs .
}
```

#### 3.2 잠재적 성능 이슈

**이슈 1: 계보 추적의 복잡도**
- `computedFromObservation+` (전이적 폐포) 쿼리는 그래프 깊이에 따라 비용 증가
- 권장: 물리화된 뷰(Materialized View) 사용

**이슈 2: 벤치마크 조인**
- `hasBenchmark` 연결 시 Industry/Sector 조인 필요
- 권장: 적절한 인덱싱 전략

---

## 도메인 적합성 평가

### 1. 재무 보고 표준 준수 ★★★★★ (5/5)

**평가 결과**: 탁월

#### 1.1 XBRL 택소노미 반영

- SEC EDGAR XBRL의 핵심 개념 포괄
  - US GAAP 주요 계정과목 매핑
  - Period Type (duration/instant) 구분
  - QName, Namespace 메타데이터 보존

#### 1.2 재무제표 3대 체계 지원

| 재무제표 | 대표 메트릭 | 특징 |
|---------|-----------|------|
| 손익계산서 | Revenue, NetIncome, OperatingIncome | Duration 타입 |
| 재무상태표 | Assets, Liabilities, Equity | Instant 타입 |
| 현금흐름표 | CFO, CapEx | Duration 타입 |

#### 1.3 재무 분석 지표 체계

- **수익성**: GrossMargin, ROE, ROIC
- **성장성**: RevenueGrowthYoY, AssetGrowthRate
- **유동성**: CurrentRatio, QuickRatio
- **레버리지**: DebtToEquity, InterestCoverage
- **효율성**: AssetTurnover, InventoryTurnover

업계 표준 재무 비율 대부분 포괄

### 2. 기업 분석 사용 사례 ★★★★★ (5/5)

**평가 결과**: 탁월

#### 2.1 시계열 분석

- 회계연도 기반 시계열 데이터 구조
- 성장률 메트릭으로 YoY 변화 추적
- 예: 5개년 Revenue 추이 분석

#### 2.2 동종 업계 비교 (Peer Analysis)

- Industry/Sector 벤치마크 지원
- 평균, 중앙값, 백분위수 제공
- 예: Apple vs. 소프트웨어 산업 ROE 비교

#### 2.3 기업 순위 (Ranking)

- Top10/Top50/Top100 지원
- 단일 메트릭 및 복합 점수 랭킹
- 예: 제약 산업 R&D 지출 Top 10

#### 2.4 계보 추적 (Lineage)

- 파생 메트릭의 원천 데이터 추적
- 데이터 품질 검증 및 감사(Audit) 지원
- 예: ROIC 계산에 사용된 모든 기본 메트릭 확인

### 3. 도메인 커버리지 ★★★★☆ (4/5)

**평가 결과**: 우수

#### 3.1 포괄 범위

**포함된 영역**:
- ✅ 주요 재무제표 항목
- ✅ 표준 재무 비율
- ✅ 산업/섹터 분류
- ✅ 벤치마크 통계
- ✅ 기업 식별자 (CIK, Ticker, SIC)
- ✅ **공시 문서(Filings) 메타데이터** ⭐ NEW (v1.1)
  - SEC 제출 문서 유형 (10-K, 10-Q, 8-K, 20-F)
  - 문서 식별자 (Accession Number)
  - 제출 일자 및 회계 기간
  - 문서 URL 및 데이터 출처 추적

**제한적 지원 영역**:
- ⚠️ 세그먼트(Segment) 정보 미지원
- ⚠️ 임원/이사회(Executives) 정보 미포함
- ⚠️ ESG 메트릭 미포함

#### 3.2 개선 방향

**제안 1: 세그먼트 분석 지원**
```turtle
efin:BusinessSegment
  a owl:Class ;
  rdfs:comment "사업 부문별 재무 데이터."@ko .

efin:forSegment
  a owl:ObjectProperty ;
  rdfs:domain efin:MetricObservation ;
  rdfs:range efin:BusinessSegment .
```

**제안 2: 공시 문서 연결** ✅ **구현 완료 (v1.1.0)**
```turtle
# v1.1.0에서 구현됨
efin:Filing
  a owl:Class ;
  rdfs:comment "SEC 제출 문서. 재무 데이터가 추출된 원본 공시 문서.
                모든 Filing 유형의 추상 상위 클래스."@ko .

efin:TenK rdfs:subClassOf efin:Filing .  # 연간보고서
efin:TenQ rdfs:subClassOf efin:Filing .  # 분기보고서
efin:EightK rdfs:subClassOf efin:Filing . # 임시보고서
efin:TwentyF rdfs:subClassOf efin:Filing . # 외국 기업 연간보고서

efin:fromFiling
  a owl:ObjectProperty , owl:FunctionalProperty ;
  rdfs:domain efin:MetricObservation ;
  rdfs:range efin:Filing ;
  rdfs:comment "관측값이 추출된 원본 공시 문서."@ko .

efin:accessionNumber
  a owl:DatatypeProperty , owl:FunctionalProperty ;
  rdfs:domain efin:Filing ;
  rdfs:range xsd:string ;
  rdfs:comment "SEC Accession Number (예: 0000320193-23-000106)."@ko .
```

**구현 효과**:
- ✅ 데이터 출처 추적: 모든 관측값을 원본 SEC 문서로 역추적
- ✅ 문서 중심 쿼리: 특정 10-K/10-Q에서 추출된 모든 지표 조회
- ✅ 시간대 분석: 관측 시점(데이터 기준일) vs 보고 시점(제출일) 비교
- ✅ 감사 추적: accessionNumber와 documentUrl을 통한 원본 문서 링크

---

## 재사용성 및 상호운용성

### 1. 표준 온톨로지 정렬 ★★★★★ (5/5)

**평가 결과**: 탁월

#### 1.1 FIBO (Financial Industry Business Ontology)

```turtle
efin:Company rdfs:subClassOf fibo-be:LegalEntity .
```

**효과**:
- FIBO를 사용하는 금융 시스템과 즉시 통합 가능
- 엔터프라이즈 데이터 모델과의 일관성 확보

#### 1.2 QUDT (Quantities, Units, Dimensions and Types)

```turtle
efin:Unit owl:equivalentClass qudt:Unit .
efin:Currency owl:equivalentClass qudt:CurrencyUnit .
```

**효과**:
- 표준 단위 시스템 활용
- 단위 변환 및 검증 자동화
- 예: USD → EUR 환율 변환

#### 1.3 OM (Ontology of Units of Measure)

```turtle
efin:Unit owl:equivalentClass om:Unit .
```

**효과**:
- 다중 단위 온톨로지 지원
- 과학/공학 도메인과의 상호운용성

### 2. 데이터 통합 시나리오 ★★★★☆ (4/5)

**평가 결과**: 우수

#### 2.1 성공 시나리오

**시나리오 1: Bloomberg 데이터 통합**
```sparql
# Bloomberg Ticker → EFIN Company 매핑
SELECT ?efinCompany ?revenue
WHERE {
  ?efinCompany efin:hasTicker "AAPL" ;
               efin:hasObservation ?obs .
  ?obs efin:observesMetric efin:Revenue ;
       efin:hasNumericValue ?revenue .
}
```

**시나리오 2: Wikidata 연동**
```sparql
# Wikidata의 기업 정보와 EFIN 재무 데이터 결합
SELECT ?wikidataEntity ?foundedDate ?revenue
WHERE {
  ?wikidataEntity wdt:P31 wd:Q891723 ; # 상장기업
                  wdt:P571 ?foundedDate ; # 설립일
                  wdt:P4264 ?cik . # SEC CIK

  ?efinCompany efin:hasCIK ?cik ;
               efin:hasObservation ?obs .
  ?obs efin:observesMetric efin:Revenue ;
       efin:hasNumericValue ?revenue .
}
```

#### 2.2 도전 과제

**과제 1: 식별자 매핑**
- CIK, Ticker, LEI 등 다양한 식별자 체계 존재
- 권장: `owl:sameAs`로 외부 엔티티 연결

**과제 2: 단위 정규화**
- 다양한 통화 및 스케일(Millions, Billions)
- 권장: QUDT의 단위 변환 기능 활용

### 3. API 및 서비스 통합 ★★★★☆ (4/5)

**평가 결과**: 우수

#### 3.1 SPARQL 엔드포인트

온톨로지 구조가 SPARQL 쿼리에 최적화:
- 명확한 클래스/속성 계층
- 효율적인 조인 경로
- 필터링을 위한 적절한 데이터 속성

#### 3.2 REST API 매핑

온톨로지 개념의 RESTful 리소스 매핑 용이:
```
GET /companies/{ticker}/observations?metric=Revenue&year=2023
→ SPARQL 쿼리로 변환 가능
```

#### 3.3 GraphQL 스키마

온톨로지 구조가 GraphQL 스키마 생성에 적합:
```graphql
type Company {
  ticker: String
  observations(metric: Metric, year: Int): [MetricObservation]
  industry: Industry
  sector: Sector
}
```

---

## 개선 권장사항

### 우선순위 1: 단기 개선 (1-3개월)

#### 1.1 공식 계산 로직의 명확화

**현재 문제**:
- `hasFormulaNote`가 문자열로만 존재
- 추론 엔진이 계산 로직을 이해할 수 없음

**개선 방안**:
```turtle
# SWRL 규칙 예시
[ROE_Rule:
  (?obs rdf:type efin:MetricObservation)
  (?obs efin:observesMetric efin:ROE)
  (?obs efin:computedFromObservation ?niObs)
  (?obs efin:computedFromObservation ?eqObs)
  (?niObs efin:observesMetric efin:NetIncome)
  (?niObs efin:hasNumericValue ?ni)
  (?eqObs efin:observesMetric efin:Equity)
  (?eqObs efin:hasNumericValue ?eq)
  divide(?result, ?ni, ?eq)
  ->
  (?obs efin:hasNumericValue ?result)
]
```

**효과**: 자동 계산 및 검증 가능

#### 1.2 데이터 검증 규칙 추가

**현재 부족한 부분**:
- 값의 유효 범위 검증 미흡
- 예: 백분율 메트릭이 100%를 초과하는 경우 감지 불가

**개선 방안**:
```turtle
# SHACL 제약 예시
efin:ROE_Shape
  a sh:NodeShape ;
  sh:targetClass efin:ROE ;
  sh:property [
    sh:path efin:hasNumericValue ;
    sh:minInclusive -1.0 ;
    sh:maxInclusive 5.0 ;
    sh:message "ROE는 일반적으로 -100% ~ 500% 범위입니다."@ko
  ] .
```

#### 1.3 문서화 강화

**추가할 내용**:
- 사용 예시(Use Case) 문서
- SPARQL 쿼리 예제 모음
- 데이터 입력 가이드라인

### 우선순위 2: 중기 확장 (3-6개월)

#### 2.1 ~~공시 문서 연결~~ ✅ **완료 (v1.1.0)**

v1.1.0에서 Filing 클래스 계층과 관련 속성이 구현되었습니다. 자세한 내용은 [도메인 적합성 평가](#도메인-적합성-평가) 섹션 참조.

#### 2.2 세그먼트 정보 지원

```turtle
efin:BusinessSegment
  a owl:Class ;
  rdfs:label "Business Segment"@en ;
  rdfs:comment "사업 부문(예: iPhone, Services, Wearables)."@ko .

efin:GeographicSegment
  a owl:Class ;
  rdfs:label "Geographic Segment"@en ;
  rdfs:comment "지역 부문(예: Americas, Europe, Asia Pacific)."@ko .

efin:SegmentObservation
  a owl:Class ;
  rdfs:subClassOf efin:MetricObservation ;
  rdfs:comment "특정 세그먼트에 대한 메트릭 관측값."@ko .

efin:forSegment
  a owl:ObjectProperty ;
  rdfs:domain efin:SegmentObservation ;
  rdfs:range [ owl:unionOf (efin:BusinessSegment efin:GeographicSegment) ] .
```

#### 2.3 ESG 메트릭 통합

```turtle
efin:ESGMetric
  a owl:Class ;
  rdfs:subClassOf efin:Metric ;
  rdfs:comment "환경, 사회, 지배구조 관련 메트릭."@ko .

efin:EnvironmentalMetric rdfs:subClassOf efin:ESGMetric .
efin:SocialMetric rdfs:subClassOf efin:ESGMetric .
efin:GovernanceMetric rdfs:subClassOf efin:ESGMetric .

# 구체적 메트릭
efin:CarbonEmissions rdfs:subClassOf efin:EnvironmentalMetric, efin:BaseMetric .
efin:EmployeeDiversity rdfs:subClassOf efin:SocialMetric, efin:BaseMetric .
efin:BoardIndependence rdfs:subClassOf efin:GovernanceMetric, efin:DerivedRatio .
```

### 우선순위 3: 장기 고도화 (6-12개월)

#### 3.1 다국적 기업 지원

**과제**:
- 여러 국가의 회계 기준 차이 (US GAAP vs. IFRS)
- 다중 통화 환산
- 지역별 규제 차이

**개선 방안**:
```turtle
efin:AccountingStandard
  a owl:Class ;
  rdfs:comment "회계 기준 (US GAAP, IFRS, K-IFRS 등)."@ko .

efin:usesAccountingStandard
  a owl:ObjectProperty ;
  rdfs:domain efin:Company ;
  rdfs:range efin:AccountingStandard .

efin:reportingCurrency
  a owl:ObjectProperty ;
  rdfs:domain efin:Company ;
  rdfs:range efin:Currency ;
  rdfs:comment "기업의 주요 보고 통화."@ko .
```

#### 3.2 실시간 데이터 지원

**과제**:
- 현재는 연간 데이터 중심
- 분기별, 월별, 일별 데이터 지원 필요

**개선 방안**:
```turtle
efin:ReportingPeriod
  a owl:Class ;
  rdfs:comment "보고 기간 (연간, 분기, 월간)."@ko .

efin:AnnualPeriod rdfs:subClassOf efin:ReportingPeriod .
efin:QuarterlyPeriod rdfs:subClassOf efin:ReportingPeriod .
efin:MonthlyPeriod rdfs:subClassOf efin:ReportingPeriod .

efin:hasReportingPeriod
  a owl:ObjectProperty ;
  rdfs:domain efin:MetricObservation ;
  rdfs:range efin:ReportingPeriod .

efin:hasPeriodStart
  a owl:DatatypeProperty ;
  rdfs:domain efin:MetricObservation ;
  rdfs:range xsd:date .
```

#### 3.3 머신러닝 통합

**과제**:
- 예측 모델 결과의 표현
- 모델 메타데이터 관리

**개선 방안**:
```turtle
efin:PredictedObservation
  a owl:Class ;
  rdfs:subClassOf efin:MetricObservation ;
  rdfs:comment "ML 모델이 예측한 관측값."@ko .

efin:predictionModel
  a owl:ObjectProperty ;
  rdfs:domain efin:PredictedObservation ;
  rdfs:range efin:PredictionModel .

efin:confidenceInterval
  a owl:DatatypeProperty ;
  rdfs:domain efin:PredictedObservation ;
  rdfs:range xsd:decimal ;
  rdfs:comment "예측값의 신뢰구간."@ko .
```

---

## 결론

### 종합 평가

EFIN 온톨로지는 **SEC EDGAR XBRL 데이터를 표준화된 형식으로 표현하기 위한 탁월한 설계**를 보여줍니다.

#### 주요 강점

1. **명확성과 일관성**: 모든 개념이 명확히 정의되고 논리적으로 일관됨
2. **표준 준수**: FIBO, QUDT 등 업계 표준 온톨로지와 긴밀히 통합
3. **확장성**: 새로운 메트릭과 기능 추가가 용이한 구조
4. **추론 가능성**: OWL 2의 고급 기능을 활용한 자동 추론 지원
5. **실용성**: 실제 재무 분석 사용 사례를 잘 지원

#### 개선 영역

1. **계산 로직 표현**: SWRL/SPIN 규칙 추가로 자동 계산 가능하게
2. **데이터 검증**: SHACL 제약 조건으로 데이터 품질 보장
3. **도메인 확장**: 세그먼트, ESG, 공시 문서 지원 추가
4. **다국적 지원**: 여러 회계 기준 및 통화 처리 강화

### 최종 점수

| 평가 항목 | 점수 | 비중 | 가중 점수 |
|---------|------|------|---------|
| 명확성 (Clarity) | 5.0 | 20% | 1.00 |
| 일관성 (Coherence) | 4.0 | 20% | 0.80 |
| 확장성 (Extensibility) | 5.0 | 15% | 0.75 |
| 최소 인코딩 편향 | 4.0 | 10% | 0.40 |
| 최소 온톨로지 커밋 | 4.0 | 10% | 0.40 |
| OWL 표현력 | 5.0 | 10% | 0.50 |
| 도메인 적합성 | 4.5 | 10% | 0.45 |
| 상호운용성 | 4.5 | 5% | 0.23 |
| **총점** | | **100%** | **4.53** |

**최종 평가**: ★★★★☆ (4.5/5.0) - **우수 (Excellent)**

### 권장 사항

1. **즉시 적용**: 데이터 검증 규칙 추가 (SHACL)
2. **3개월 내**: 세그먼트 정보 지원
3. **6개월 내**: ESG 메트릭 통합
4. **12개월 내**: 다국적 기업 및 실시간 데이터 지원

### v1.1.0 업데이트 성과

**구현 완료된 기능** (2025-01-19):
- ✅ Filing 클래스 계층 (TenK, TenQ, EightK, TwentyF)
- ✅ 데이터 출처 추적 (fromFiling, containsObservation)
- ✅ SEC 문서 메타데이터 (accessionNumber, filingDate, fiscalPeriod, documentUrl, acceptanceDateTime)
- ✅ 시간 속성 명확화 (관측 시점 vs 보고 시점 구분)

**효과**:
- 데이터 계보 추적 완전성 향상
- SEC EDGAR 시스템과의 직접 연동 가능
- 감사(Audit) 및 규제 준수 지원 강화
- 도메인 커버리지 점수 향상: 4.0 → 4.5

### 평가자 의견

> "EFIN 온톨로지는 재무 데이터 표준화의 모범 사례를 제시합니다.
> 특히 FIBO, QUDT와의 긴밀한 통합과 OWL 2의 고급 기능 활용은
> 엔터프라이즈 데이터 통합 프로젝트에 큰 가치를 제공할 것입니다.
> 제안된 개선 사항을 단계적으로 적용하면 세계적 수준의
> 재무 온톨로지로 발전할 수 있을 것으로 기대됩니다."

---

**최초 평가 일자**: 2025-01-19
**최종 업데이트**: 2025-01-20 (v1.1.1 명확성 개선 반영)
**평가 대상 버전**: efin:Ontology 1.1.1-clarity-improvements
**평가자**: EFIN 온톨로지 설계 평가팀

**문서 개정 이력**:
- v1.0 (2025-01-19): 초기 평가 (온톨로지 v1.0.0-dr-strong 기준)
- v1.1 (2025-01-19): Filing 지원 구현 반영 (온톨로지 v1.1.0-filing-support)
- v1.1.1 (2025-01-20): 명확성 개선 반영 (온톨로지 v1.1.1-clarity-improvements)
  - TotalDebt 약어 제거로 공식 명확성 향상
  - ShortTermDebt-DebtCurrent equivalentClass 관계 명시
  - hasQuarter 속성 추가로 분기별 데이터 지원 준비

**참고 문헌**:
- Gruber, T. R. (1995). Toward principles for the design of ontologies used for knowledge sharing.
- Noy, N. F., & McGuinness, D. L. (2001). Ontology development 101: A guide to creating your first ontology.
- Uschold, M., & Gruninger, M. (1996). Ontologies: Principles, methods and applications.

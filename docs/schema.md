# EDGAR-FIN 2024 온톨로지

## 1) 재사용 온톨로지 요약

| 온톨로지 | Prefix | 포함 요소(주요) | 우리 스키마에서의 사용 방식 |
|---|---|---|---|
| FIBO-BE (Business Entities) | `fibo-be:` | `fibo-be:LegalEntity` | `efin:LegalEntity ⊑ fibo-be:LegalEntity` (상속) |
| FinRegOnt (Financial Regulation Ontology) | `fro:` | `fro:RegulatoryFiling` | `efin:RegulatoryFiling ⊑ fro:RegulatoryFiling` (상속) |

---

## 2) 클래스 시각화 (핵심 계층)

| 그룹 | 클래스 (우리 스키마) | 타입 | 부모(상속) | 메모 |
|---|---|---|---|---|
| 재사용 | `efin:LegalEntity` | 재사용 확장 | `fibo-be:LegalEntity` | 기업(법적 실체) |
| 재사용 | `efin:RegulatoryFiling` | 재사용 확장 | `fro:RegulatoryFiling` | SEC 10-K/20-F 등 |
| 핵심 | `efin:FinancialObservation` | **자체** | `owl:Thing` | 기업·지표·기간·통화별 관측값 중심 |
| 핵심 | `efin:CanonicalMetric` | **자체** | `owl:Thing` | Revenue, OperatingIncome, NetIncome, CFO, Assets, Liabilities… |
| 핵심 | `efin:XbrlConcept` | **자체** | `owl:Thing` | XBRL 태그(표준/확장) 개념 노드 |
| 핵심 | `efin:TagMapping` | **자체** | `owl:Thing` | XBRL → Canonical 매핑 엔티티 |
| 시간 | `efin:Period` | **자체** | `owl:Thing` | 공통 기간 상위 |
| 시간 | `efin:DurationPeriod` | **자체** | `efin:Period` | FY/반기/분기 등 기간형 |
| 시간 | `efin:InstantPeriod` | **자체** | `efin:Period` | 시점형(재무상태표) |
| 단위 | `efin:Currency` | **자체** | `owl:Thing` | USD 등 |
| 기준 | `efin:AccountingStandard` | **자체** | `owl:Thing` | US-GAAP / IFRS |
| 산업 | `efin:Industry` | **자체** | `owl:Thing` | SIC/GICS 매핑용 |
| 파생 | `efin:RevenueObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | `forMetric value efin:Revenue` 등으로 정의 |
| 파생 | `efin:OperatingIncomeObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 운영이익 관측 |
| 파생 | `efin:OperatingComparableObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 비교 가능한 운영이익 관측 |
| 파생 | `efin:NetIncomeObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 순이익 관측 |
| 파생 | `efin:CFOObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 영업활동 현금흐름 관측 |
| 파생 | `efin:CashAndCashEquivalentsObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 현금 및 현금성자산 관측 |
| 파생 | `efin:AssetsObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 자산 관측 |
| 파생 | `efin:LiabilitiesObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 부채 관측 |
| 파생 | `efin:EquityObservation` | **자체(정의 클래스)** | `efin:FinancialObservation` | 자본 관측 |

> **요약**: 재사용 클래스는 2개(`LegalEntity`, `RegulatoryFiling`)이고, 나머지 **핵심/시간/단위/기준/산업/파생 관측** 클래스는 전부 **자체 구축**입니다.

---

## 3) 핵심 오브젝트/데이터 프로퍼티 (시각 요약)

| 프로퍼티 | 타입 | Domain → Range | 특징 |
|---|---|---|---|
| `efin:forEntity` | Object | `FinancialObservation` → `LegalEntity` | Functional |
| `efin:forMetric` | Object | `FinancialObservation` → `CanonicalMetric` | Functional |
| `efin:hasPeriod` | Object | `FinancialObservation` → `Period` | Functional |
| `efin:hasCurrency` | Object | `FinancialObservation` → `Currency` | Functional |
| `efin:usesAccountingStandard` | Object | `FinancialObservation` → `AccountingStandard` | Functional |
| `efin:basedOnConcept` | Object | `FinancialObservation` → `XbrlConcept` |  |
| `efin:normalizedAs` | Object | `FinancialObservation` → `CanonicalMetric` | 정규화 대상 지표 |
| `efin:computedFrom` | Object | `FinancialObservation` → `FinancialObservation` | Transitive (파생계산 추적) |
| `efin:hasIndustry` | Object | `LegalEntity` → `Industry` |  |
| `efin:hasIndustryOfObservation` | Object | `FinancialObservation` → `Industry` | PropertyChain (forEntity ∘ hasIndustry) |
| `efin:hasFiling` | Object | `FinancialObservation` → `RegulatoryFiling` |  |
| `efin:mapsFrom` | Object | `TagMapping` → `XbrlConcept` | Functional |
| `efin:mapsTo` | Object | `TagMapping` → `CanonicalMetric` | Functional |
| `efin:hasValue` | Datatype | `FinancialObservation` → `xsd:decimal` | Functional |
| `efin:hasSourceType` | Datatype | `FinancialObservation` → `xsd:string` | 소스 타입 (annual, composite, derived 등) |
| `efin:hasConfidence` | Datatype | `FinancialObservation` → `xsd:decimal` | 신뢰도 점수 (0.0-1.0) |
| `efin:hasReason` | Datatype | `FinancialObservation` → `xsd:string` | 선택 이유 |
| `efin:hasCompositeName` | Datatype | `FinancialObservation` → `xsd:string` | Composite 계산 이름 |
| `efin:hasCIK` | Datatype | `LegalEntity` → `xsd:string` | SEC CIK 번호 |
| `efin:hasSymbol` | Datatype | `LegalEntity` → `xsd:string` | 티커 심볼 |
| `efin:hasName` | Datatype | `LegalEntity` → `xsd:string` | 회사명 |
| `efin:periodStart` | Datatype | `Period` → `xsd:date` |  |
| `efin:periodEnd` | Datatype | `Period` → `xsd:date` |  |
| `efin:fiscalYear` | Datatype | `Period` → `xsd:gYear` |  |
| `efin:fiscalYearEnd` | Datatype | `Period` → `xsd:string` | 회계연도 종료일 (MMDD 형식) |
| `efin:hasFormType` | Datatype | `RegulatoryFiling` → `xsd:string` | 제출 문서 형태 (10-K, 20-F 등) |
| `efin:hasAccessionNumber` | Datatype | `RegulatoryFiling` → `xsd:string` | SEC 접근 번호 |

---

## 4) 제약(Constraints) 시각 요약

| 제약 | 대상/표현 | 효과 |
|---|---|---|
| 필수 키 | `FinancialObservation` | `forEntity`, `forMetric`, `hasPeriod`, `hasCurrency`, `usesAccountingStandard`, `hasValue` 필요 |
| 상호배타 | `DurationPeriod ⊥ InstantPeriod` | 기간형/시점형 구분 강화 |
| 구분 | `CanonicalMetric AllDifferent` | 지표 개체 상호 구분 |
| 키(유일성) | `Key(FinancialObservation (forEntity, forMetric, hasPeriod, hasCurrency))` | 동일 기업·지표·기간·통화 조합은 1개 관측으로 유일 |

---

## 5) Canonical 지표(발췌)

| 카테고리 | 지표 (예시) | 설명 |
|---|---|---|
| 기간형 | `efin:Revenue`, `efin:OperatingIncome`, `efin:OperatingIncomeComparable`, `efin:NetIncome`, `efin:CFO` | 손익/현금흐름/성과 |
| 시점형 | `efin:Assets`, `efin:Liabilities`, `efin:Equity`, `efin:CashAndCashEquivalents` | 재무상태(시점) |
# EFIN Financial Ontology 상호 운용성 가이드

## 문서 목적

본 문서는 **EFIN Financial Ontology의 상호 운용성**을 설명합니다. FIBO 등 표준 온톨로지와의 통합 및 프로퍼티 매핑을 다룹니다.

**다른 문서:**
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티 등 스키마 구조 상세
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [온톨로지 프로젝트 평가](./ontology_project_evaluation.md): 프로젝트 평가 기준 및 달성 사항

---

## 목차

1. [개요](#1-개요)
2. [표준 온톨로지 통합](#2-표준-온톨로지-통합)
3. [프로퍼티 매핑](#3-프로퍼티-매핑)
4. [다른 온톨로지와의 연계](#4-다른-온톨로지와의-연계)
5. [사용 예시](#5-사용-예시)

---

## 1. 개요

EFIN Financial Ontology는 표준 온톨로지와의 상호 운용성을 확보하기 위해 다음과 같은 통합을 제공합니다:

- **FIBO-BE (Financial Industry Business Ontology - Business Entities)**: 법적 실체 모델링
- **표준 네임스페이스**: `https://w3id.org/edgar-fin/2024#`
- **온톨로지 import**: `owl:imports`를 통한 표준 온톨로지 통합

---

## 2. 표준 온톨로지 통합

### 2.1 FIBO-BE 통합

**통합 방식:**
```turtle
@prefix fibo-be: <https://spec.edmcouncil.org/fibo/ontology/BE/> .

efin:Company rdfs:subClassOf fibo-be:LegalEntity .
```

**의미:**
- `efin:Company`는 FIBO의 `LegalEntity` 개념을 상속받음
- FIBO의 모든 `LegalEntity` 프로퍼티를 자동으로 상속
- 다른 FIBO 기반 온톨로지와의 상호 운용성 확보

**장점:**
- 표준 재무 온톨로지와의 호환성
- 다른 FIBO 기반 시스템과의 데이터 교환 가능
- 재사용성 향상

### 2.2 온톨로지 Import 선언

```turtle
efin:Ontology owl:imports <https://spec.edmcouncil.org/fibo/ontology/BE/> .
```

**의미:**
- FIBO-BE 온톨로지를 명시적으로 import
- FIBO의 모든 클래스와 프로퍼티를 사용 가능
- 추론 엔진이 FIBO의 제약 조건도 함께 적용

---

## 3. 프로퍼티 매핑

### 3.1 FIBO 프로퍼티와의 매핑

| EFIN 프로퍼티 | FIBO 프로퍼티 | 매핑 관계 | 설명 |
|--------------|--------------|----------|------|
| `efin:hasCompanyName` | `fibo-be:hasLegalName` | 유사 | 회사 공식 명칭 |
| `efin:hasCIK` | `fibo-be:hasIdentifier` | 유사 | SEC CIK는 특화 식별자 |
| `efin:hasTicker` | - | EFIN 전용 | 거래소 티커 심볼 |

**매핑 예시:**
```turtle
# EFIN 인스턴스
efin:CIK0000320193 a efin:Company ;
  efin:hasCompanyName "Apple Inc." ;
  efin:hasCIK "0000320193" ;
  efin:hasTicker "AAPL" .

# FIBO 관점에서의 해석
efin:CIK0000320193 a fibo-be:LegalEntity ;
  fibo-be:hasLegalName "Apple Inc." .
  # hasCIK는 SEC 특화이므로 FIBO에는 직접 매핑되지 않음
```

### 3.2 매핑 활용 방법

**SPARQL 쿼리 예시:**
```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX fibo-be: <https://spec.edmcouncil.org/fibo/ontology/BE/>

# FIBO의 LegalEntity로도 쿼리 가능
SELECT ?company ?name
WHERE {
  ?company a fibo-be:LegalEntity ;
           efin:hasCompanyName ?name .
}
```

---

## 4. 다른 온톨로지와의 연계

### 4.1 XBRL 온톨로지

**연계 가능성:**
- XBRL 태그 정보는 `efin:selectedTag` 프로퍼티에 저장
- 향후 XBRL 온톨로지와의 직접 연계 가능

**예시:**
```turtle
# 향후 확장 가능
efin:Observation-xxx efin:hasSelectedTag "us-gaap:Revenues" .
# → XBRL 온톨로지의 Concept과 연결 가능
```

### 4.2 시간 온톨로지 (OWL-Time)

**현재 상태:**
- 시간 정보는 `xsd:date` 및 `xsd:gYear`로 표현
- OWL-Time 통합은 향후 개선 가능

**향후 개선 방향:**
```turtle
# OWL-Time 통합 예시 (향후)
@prefix time: <http://www.w3.org/2006/time#> .

efin:MetricObservation efin:hasTimeInterval [
  a time:Interval ;
  time:hasBeginning [ time:inXSDDate ?start ] ;
  time:hasEnd [ time:inXSDDate ?end ]
] .
```

### 4.3 다른 재무 온톨로지

**연계 가능한 온톨로지:**
- **FIBO-FND (Foundations)**: 재무 개념의 기초
- **FIBO-FBC (Financial Business and Commerce)**: 재무 비즈니스 개념
- **XBRL Taxonomy**: XBRL 표준 태그

**연계 방법:**
- `owl:equivalentClass` 또는 `owl:equivalentProperty` 사용
- 또는 별도 매핑 온톨로지 작성

---

## 5. 사용 예시

### 5.1 FIBO와 함께 사용하기

**온톨로지 로드:**
```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX fibo-be: <https://spec.edmcouncil.org/fibo/ontology/BE/>

# FIBO의 LegalEntity로도 쿼리 가능
SELECT ?company ?name ?revenue
WHERE {
  ?company a fibo-be:LegalEntity ;
           efin:hasCompanyName ?name .
  ?obs efin:ofCompany ?company ;
       efin:observesMetric efin:Revenue ;
       efin:hasNumericValue ?revenue .
}
```

### 5.2 다른 시스템과의 데이터 교환

**RDF 변환:**
```turtle
# EFIN 데이터를 FIBO 호환 형식으로 변환
efin:CIK0000320193 a fibo-be:LegalEntity ;
  fibo-be:hasLegalName "Apple Inc." ;
  efin:hasCIK "0000320193" ;
  efin:hasTicker "AAPL" .
```

**JSON-LD 변환:**
```json
{
  "@context": {
    "efin": "https://w3id.org/edgar-fin/2024#",
    "fibo-be": "https://spec.edmcouncil.org/fibo/ontology/BE/"
  },
  "@id": "efin:CIK0000320193",
  "@type": ["efin:Company", "fibo-be:LegalEntity"],
  "efin:hasCompanyName": "Apple Inc.",
  "efin:hasCIK": "0000320193",
  "efin:hasTicker": "AAPL"
}
```

---

## 참고 자료

- [FIBO 공식 사이트](https://spec.edmcouncil.org/fibo/)
- [FIBO-BE 문서](https://spec.edmcouncil.org/fibo/ontology/BE/)
- [온톨로지 스키마 문서](./schema.md)
- [전체 워크플로우 문서](./comprehensive_workflow.md)


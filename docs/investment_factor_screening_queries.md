## 투자 팩터·섹터 스크리닝 고급 질의 모음

본 문서는 EFIN 온톨로지의 **메트릭 계층(BaseMetric / DerivedMetric / DerivedRatio)** 과  
**Industry / Sector 계층**을 활용하여, 추론을 전제로 한 고급 스크리닝 질의들을 정리한 것입니다.

---

## 1. 메트릭 계층(DerivedRatio)을 “팩터 우주”로 쓰는 질의

### 1.1 CQ-M1: DerivedRatio 전체에서 다중 팩터 우수 기업 스크리닝

**Competency Question (한글)**: DerivedRatio 계층에 속한 모든 비율 지표 중, 업종 평균보다 우수한 지표가 4개 이상인 기업을 찾고 싶다.  
**Competency Question (English)**: Find companies that outperform their industry average on at least 4 different derived ratio metrics (DerivedRatio hierarchy).

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name ?industry
       ?numRatiosAboveAvg
WHERE {
  ####################################################################
  # DerivedRatio 중 업종 평균 이상인 지표가 4개 이상인 회사만 선별
  ####################################################################
  {
    SELECT ?company (COUNT(DISTINCT ?metric) AS ?numRatiosAboveAvg)
    WHERE {
      ?company efin:inIndustry ?industry .

      ?metric rdfs:subClassOf+ efin:DerivedRatio .

      ?obs a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric ?metric ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?value .

      {
        SELECT ?industry ?metric (AVG(?v) AS ?industryAvg)
        WHERE {
          ?c efin:inIndustry ?industry .
          ?o a efin:MetricObservation ;
             efin:ofCompany ?c ;
             efin:observesMetric ?metric ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?v .
          ?metric rdfs:subClassOf+ efin:DerivedRatio .
        }
        GROUP BY ?industry ?metric
      }

      FILTER (?value >= ?industryAvg)
    }
    GROUP BY ?company
    HAVING (COUNT(DISTINCT ?metric) >= 4)
  }

  # 회사 메타데이터 조인
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
}
ORDER BY DESC(?numRatiosAboveAvg) ?company
```

---

### 1.2 CQ-M2: DerivedRatio 팩터 커버리지 기반 유니버스 구축

**Competency Question (한글)**: DerivedRatio 계층에서 관측이 존재하는 비율 지표 수가 일정 이상인 기업만 골라, 팩터 분석·모형화에 적합한 기업 유니버스를 만들고 싶다.  
**Competency Question (English)**: Build a universe of companies that have sufficient coverage across the DerivedRatio factor space.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       (COUNT(DISTINCT ?metric) AS ?numDerivedRatios)
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear 2024 .

  ?metric rdfs:subClassOf+ efin:DerivedRatio .
}
GROUP BY ?company ?ticker ?name
HAVING (COUNT(DISTINCT ?metric) >= 8)
ORDER BY DESC(?numDerivedRatios)
```

---

### 1.3 CQ-M3: DerivedRatio 전체를 사용한 종합 팩터 스코어 기반 리더 스크리닝

**Competency Question (한글)**: DerivedRatio 계층 전체에서 업종 평균 대비 스코어를 합산해, 종합 팩터 스코어가 높은 기업을 리더로 스크리닝하고 싶다.  
**Competency Question (English)**: Use all DerivedRatio metrics to compute an aggregate factor score and screen leaders.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       (SUM(?normalizedScore) AS ?factorScore)
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?value .

  ?metric rdfs:subClassOf+ efin:DerivedRatio .

  {
    SELECT ?industry ?metric (AVG(?v) AS ?industryAvg)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric ?metric ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?v .
      ?metric rdfs:subClassOf+ efin:DerivedRatio .
    }
    GROUP BY ?industry ?metric
  }

  FILTER (?industryAvg != 0)
  BIND(?value / ?industryAvg AS ?normalizedScore)
}
GROUP BY ?company ?ticker ?name
HAVING (SUM(?normalizedScore) >= 5.0)
ORDER BY DESC(?factorScore)
```

---

### 1.4 CQ-M4: DerivedRatio 계층에서 “가장 차별화가 큰 팩터” 찾기

**Competency Question (한글)**: 특정 업종 내에서, 어떤 DerivedRatio 지표가 기업 간 분산이 가장 커서 팩터로서 차별력이 높은지 알고 싶다.  
**Competency Question (English)**: For a given industry, which DerivedRatio metrics have the highest cross-sectional spread?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?industry ?metric (AVG(?value) AS ?avgValue)
       (MAX(?value) - MIN(?value) AS ?spread)
WHERE {
  ?company efin:inIndustry ?industry .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?value .

  ?metric rdfs:subClassOf+ efin:DerivedRatio .
  FILTER (?industry = efin:IndustryPharmaceuticalPreparations)
}
GROUP BY ?industry ?metric
HAVING (COUNT(DISTINCT ?company) >= 5)
ORDER BY DESC(?spread)
LIMIT 20
```

---

### 1.5 CQ-M5: 수익성 vs 레버리지 신호 불일치 기반 스크리닝

**Competency Question (한글)**: DerivedRatio 계층에서 ROE·NetProfitMargin은 업종 상위지만, DebtToEquity는 업종 하위인 “레버리지 의존형 고수익” 기업을 찾고 싶다.  
**Competency Question (English)**: Find companies with strong profitability but weak leverage ratios within their industry.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name ?industry
       ?roe ?netMargin ?de
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  efin:ROE             rdfs:subClassOf+ efin:DerivedRatio .
  efin:NetProfitMargin rdfs:subClassOf+ efin:DerivedRatio .
  efin:DebtToEquity    rdfs:subClassOf+ efin:DerivedRatio .

  ?roeObs a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?roe .

  ?mObs a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?netMargin .

  ?deObs a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?de .

  {
    SELECT ?industry (AVG(?roeInd) AS ?avgROE)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:ROE ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?roeInd .
    }
    GROUP BY ?industry
  }

  {
    SELECT ?industry (AVG(?mInd) AS ?avgMargin)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:NetProfitMargin ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?mInd .
    }
    GROUP BY ?industry
  }

  {
    SELECT ?industry (AVG(?deInd) AS ?avgDE)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?deInd .
    }
    GROUP BY ?industry
  }

  FILTER (?roe       >= ?avgROE * 1.2)
  FILTER (?netMargin >= ?avgMargin * 1.2)
  FILTER (?de        >= ?avgDE * 1.3)
}
ORDER BY DESC(?roe)
```

---

### 1.6 CQ-M6: 강한 DerivedRatio 팩터(업종 평균의 1.5배 이상) 다수 보유 기업

**Competency Question (한글)**: DerivedRatio 계층에서 업종 평균의 1.5배 이상인 “강한 팩터”가 6개 이상인 기업을 찾고 싶다.  
**Competency Question (English)**: Find companies with at least 6 DerivedRatio metrics stronger than 1.5x the industry average.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       (COUNT(DISTINCT ?metric) AS ?numStrongFactors)
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  ?metric rdfs:subClassOf+ efin:DerivedRatio .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?value .

  {
    SELECT ?industry ?metric (AVG(?v) AS ?industryAvg)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric ?metric ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?v .
      ?metric rdfs:subClassOf+ efin:DerivedRatio .
    }
    GROUP BY ?industry ?metric
  }

  FILTER (?industryAvg != 0)
  FILTER (?value >= ?industryAvg * 1.5)
}
GROUP BY ?company ?ticker ?name
HAVING (COUNT(DISTINCT ?metric) >= 6)
ORDER BY DESC(?numStrongFactors)
```

---

### 1.7 CQ-M7: 약점 DerivedRatio 팩터(업종 평균 이하)가 적은 “전방위 우수” 기업

**Competency Question (한글)**: DerivedRatio 계층에서 업종 평균 이하인 약점 팩터가 3개 이하인 “전방위 우수” 기업을 찾고 싶다.  
**Competency Question (English)**: Find companies with at most 3 DerivedRatio metrics below their industry average.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       (COUNT(DISTINCT ?weakMetric) AS ?numWeakFactors)
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  # 약점 팩터만 세기
  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?weakMetric ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?value .

  ?weakMetric rdfs:subClassOf+ efin:DerivedRatio .

  {
    SELECT ?industry ?metric (AVG(?v) AS ?industryAvg)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric ?metric ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?v .
      ?metric rdfs:subClassOf+ efin:DerivedRatio .
    }
    GROUP BY ?industry ?metric
  }

  FILTER (?value < ?industryAvg)
}
GROUP BY ?company ?ticker ?name
HAVING (COUNT(DISTINCT ?weakMetric) <= 3)
ORDER BY ?numWeakFactors ASC ?company
```

---

### 1.8 CQ-M8: 회사별 가장 강한 / 가장 약한 DerivedRatio 팩터 식별

**Competency Question (한글)**: 각 회사에 대해 업종 평균 대비 가장 강한 DerivedRatio와 가장 약한 DerivedRatio를 알고 싶다.  
**Competency Question (English)**: For each company, find its strongest and weakest DerivedRatio metrics relative to the industry average.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       ?metric ?metricLabel ?score
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  ?metric rdfs:subClassOf+ efin:DerivedRatio .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?value .

  {
    SELECT ?industry ?metric (AVG(?v) AS ?industryAvg)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric ?metric ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?v .
      ?metric rdfs:subClassOf+ efin:DerivedRatio .
    }
    GROUP BY ?industry ?metric
  }

  FILTER (?industryAvg != 0)
  BIND(?value / ?industryAvg AS ?score)
  OPTIONAL { ?metric rdfs:label ?metricLabel . }
}
ORDER BY ?company DESC(?score)
```

> 참고: 실제로는 위 결과를 가져온 뒤, 클라이언트/서브쿼리에서 회사별 상위/하위 N개의 `?metric`만 선택해 사용할 수 있습니다.

---

### 1.9 CQ-M9: 성장 DerivedRatio vs 수익성 DerivedRatio 팩터 틸트 분석

**Competency Question (한글)**: 성장 계열 DerivedRatio(Revenue/NetIncome/CFO/Asset 성장률)는 강하지만, 수익성 계열 DerivedRatio(ROE, NetMargin)는 상대적으로 약한 “성장주 틸트” 기업을 찾고 싶다.  
**Competency Question (English)**: Find companies tilted towards growth ratios but relatively weak on profitability ratios.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?company ?ticker ?name
       ?revg ?nig ?cfog ?assetg ?roe ?netMargin
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  # 성장 계열 DerivedRatio
  ?obsRevg a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:RevenueGrowthYoY ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?revg .

  ?obsNig a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:NetIncomeGrowthYoY ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?nig .

  ?obsCFOg a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:CFOGrowthYoY ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?cfog .

  ?obsAg a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:AssetGrowthRate ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?assetg .

  # 수익성 계열 DerivedRatio
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?roe .

  ?obsMargin a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?netMargin .

  # 업종 평균 대비 성장률은 높고, 수익성은 평균 내/이하
  {
    SELECT ?industry
           (AVG(?revgI) AS ?avgRevg)
           (AVG(?nigI) AS ?avgNig)
           (AVG(?cfogI) AS ?avgCFOg)
           (AVG(?assetgI) AS ?avgAssetg)
           (AVG(?roeI) AS ?avgROE)
           (AVG(?marginI) AS ?avgMargin)
    WHERE {
      ?c efin:inIndustry ?industry .

      OPTIONAL {
        ?o1 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:RevenueGrowthYoY ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?revgI .
      }
      OPTIONAL {
        ?o2 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:NetIncomeGrowthYoY ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?nigI .
      }
      OPTIONAL {
        ?o3 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:CFOGrowthYoY ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?cfogI .
      }
      OPTIONAL {
        ?o4 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:AssetGrowthRate ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?assetgI .
      }
      OPTIONAL {
        ?o5 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:ROE ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?roeI .
      }
      OPTIONAL {
        ?o6 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:NetProfitMargin ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?marginI .
      }
    }
    GROUP BY ?industry
  }

  FILTER (?revg   > ?avgRevg   && ?nig   > ?avgNig &&
          ?cfog   > ?avgCFOg   && ?assetg > ?avgAssetg)
  FILTER (?roe    <= ?avgROE   || ?netMargin <= ?avgMargin)
}
ORDER BY DESC(?revg)
```

---

### 1.10 CQ-M10: DerivedRatio 기반 다중 팩터 “균형형” 기업 스크리닝

**Competency Question (한글)**: DerivedRatio 계층에서 너무 극단적인 팩터(업종 평균의 2배 이상/0.5배 이하)는 거의 없고, 대부분이 업종 평균 근처(±20%)에 위치한 “균형형” 기업을 찾고 싶다.  
**Competency Question (English)**: Find “balanced” companies whose DerivedRatio metrics mostly stay within ±20% of the industry average and have few extreme factors.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       ?numNearAvg ?numExtreme
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  {
    # 근처(±20%) 팩터 수
    SELECT ?company (COUNT(DISTINCT ?metric) AS ?numNearAvg)
    WHERE {
      ?company efin:inIndustry ?industry .

      ?metric rdfs:subClassOf+ efin:DerivedRatio .

      ?obs a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric ?metric ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?value .

      {
        SELECT ?industry ?metric (AVG(?v) AS ?industryAvg)
        WHERE {
          ?c efin:inIndustry ?industry .
          ?o a efin:MetricObservation ;
             efin:ofCompany ?c ;
             efin:observesMetric ?metric ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?v .
          ?metric rdfs:subClassOf+ efin:DerivedRatio .
        }
        GROUP BY ?industry ?metric
      }

      FILTER (?industryAvg != 0)
      BIND(?value / ?industryAvg AS ?score)
      FILTER (?score >= 0.8 && ?score <= 1.2)
    }
    GROUP BY ?company
  }

  {
    # 극단(2배 이상 또는 0.5배 이하) 팩터 수
    SELECT ?company (COUNT(DISTINCT ?extMetric) AS ?numExtreme)
    WHERE {
      ?company efin:inIndustry ?industry .

      ?extMetric rdfs:subClassOf+ efin:DerivedRatio .

      ?obs2 a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric ?extMetric ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?val2 .

      {
        SELECT ?industry ?metric (AVG(?v2) AS ?industryAvg2)
        WHERE {
          ?c2 efin:inIndustry ?industry .
          ?o2 a efin:MetricObservation ;
              efin:ofCompany ?c2 ;
              efin:observesMetric ?metric ;
              efin:hasFiscalYear 2024 ;
              efin:hasNumericValue ?v2 .
          ?metric rdfs:subClassOf+ efin:DerivedRatio .
        }
        GROUP BY ?industry ?metric
      }

      FILTER (?industryAvg2 != 0)
      BIND(?val2 / ?industryAvg2 AS ?score2)
      FILTER (?score2 >= 2.0 || ?score2 <= 0.5)
    }
    GROUP BY ?company
  }

  FILTER (?numNearAvg >= 6)
  FILTER (?numExtreme <= 1)
}
ORDER BY DESC(?numNearAvg) ?numExtreme
```

---

## 2. Industry / Sector 계층 기반 동종·인접 업종 스크리닝 질의

### 2.1 CQ-I1: 특정 회사 기준 동종 + 동일 섹터 인접 업종 피어 비교

**Competency Question (한글)**: 특정 회사와 동일 섹터에 속한 모든 회사(동종·인접 업종 포함)의 ROE/마진을 비교해, 해당 회사의 섹터 내 포지션을 알고 싶다.  
**Competency Question (English)**: Compare a company’s ROE and margin against all companies in the same sector (including adjacent industries).

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?peer ?peerTicker ?peerName ?peerIndustry ?roe ?netMargin
WHERE {
  # 기준 회사
  ?target efin:hasTicker "AAPL" ;
          efin:inSector ?sector .

  # 동일 섹터의 모든 회사
  ?peer efin:inSector ?sector ;
        efin:hasTicker ?peerTicker ;
        efin:hasCompanyName ?peerName ;
        efin:inIndustry ?peerIndustry .

  OPTIONAL {
    ?roeObs a efin:MetricObservation ;
            efin:ofCompany ?peer ;
            efin:observesMetric efin:ROE ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?roe .
  }
  OPTIONAL {
    ?mObs a efin:MetricObservation ;
          efin:ofCompany ?peer ;
          efin:observesMetric efin:NetProfitMargin ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?netMargin .
  }
}
ORDER BY DESC(?roe)
```

---

### 2.2 CQ-I2: Sector 내 “리더 업종” 식별 (Industry → Sector 계층 활용)

**Competency Question (한글)**: 각 섹터마다, 해당 섹터에 속한 업종들 중 평균 ROE가 가장 높은 업종을 찾고 싶다.  
**Competency Question (English)**: For each sector, find the industries with the highest average ROE.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?industry
       (AVG(?roe) AS ?avgROE)
WHERE {
  ?company efin:inIndustry ?industry .
  ?industry efin:inSectorOf ?sector .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric efin:ROE ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?roe .
}
GROUP BY ?sector ?industry
HAVING (COUNT(DISTINCT ?company) >= 5)
ORDER BY ?sector DESC(?avgROE)
```

---

### 2.3 CQ-I3: 섹터 평균 대비 강하지만 동종업계 대비 약한 기업 스크리닝

**Competency Question (한글)**: 섹터 평균보다 성과는 좋지만, 같은 Industry 평균에는 못 미치는 기업을 찾아 니치 포지션을 파악하고 싶다.  
**Competency Question (English)**: Find companies that outperform their sector but underperform their own industry.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?company ?ticker ?name ?industry ?sector
       ?roe ?sectorAvgROE ?industryAvgROE
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry ;
           efin:inSector ?sector .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric efin:ROE ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?roe .

  {
    SELECT ?sector (AVG(?roeS) AS ?sectorAvgROE)
    WHERE {
      ?c efin:inSector ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:ROE ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?roeS .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?industry (AVG(?roeI) AS ?industryAvgROE)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:ROE ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?roeI .
    }
    GROUP BY ?industry
  }

  FILTER (?roe > ?sectorAvgROE)
  FILTER (?roe < ?industryAvgROE)
}
ORDER BY DESC(?roe)
```

---

### 2.4 CQ-I4: 섹터 내 레버리지 테일 리스크 업종 및 기업 스크리닝

**Competency Question (한글)**: 각 섹터에서, DebtToEquity가 섹터 평균보다 유의미하게 높은 업종들과 그 안의 테일 기업들을 찾고 싶다.  
**Competency Question (English)**: Within each sector, identify industries with structurally high leverage and screen tail-risk companies.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?industry ?company ?ticker ?name ?de ?sectorAvgDE ?industryAvgDE
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  ?industry efin:inSectorOf ?sector .

  ?deObs a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?de .

  {
    SELECT ?sector (AVG(?deS) AS ?sectorAvgDE)
    WHERE {
      ?c efin:inIndustry ?ind .
      ?ind efin:inSectorOf ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?deS .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?industry (AVG(?deI) AS ?industryAvgDE)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?deI .
    }
    GROUP BY ?industry
  }

  FILTER (?industryAvgDE >= ?sectorAvgDE * 1.1)
  FILTER (?de >= ?industryAvgDE * 1.3)
}
ORDER BY ?sector DESC(?industryAvgDE) DESC(?de)
```

---

### 2.5 CQ-I5: 섹터 로테이션 후보 섹터 스크리닝

**Competency Question (한글)**: 섹터별로 주요 DerivedRatio(ROE, 순이익률, 부채비율)를 종합해, 섹터 로테이션 관점에서 매력적인 섹터를 찾고 싶다.  
**Competency Question (English)**: Aggregate key derived ratios by sector to identify attractive sectors for rotation.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector
       (AVG(?roe) AS ?avgROE)
       (AVG(?margin) AS ?avgNetMargin)
       (AVG(?de) AS ?avgDebtToEquity)
       ((AVG(?roe) + AVG(?margin) - AVG(?de)) AS ?sectorScore)
WHERE {
  ?company efin:inIndustry ?industry .
  ?industry efin:inSectorOf ?sector .

  OPTIONAL {
    ?o1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:ROE ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?roe .
  }
  OPTIONAL {
    ?o2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?margin .
  }
  OPTIONAL {
    ?o3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:DebtToEquity ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?de .
  }
}
GROUP BY ?sector
HAVING (COUNT(DISTINCT ?company) >= 5)
ORDER BY DESC(?sectorScore)
```

---

### 2.6 CQ-I6: 섹터 내 다중 비율 동시 상위(Top) 기업 스크리닝

**Competency Question (한글)**: 특정 섹터에서 ROE·순이익률·AssetTurnover·DebtToEquity 네 가지 비율 모두 섹터 평균보다 우수한 기업을 찾고 싶다.  
**Competency Question (English)**: Within a sector, find companies that outperform sector averages on ROE, net margin, asset turnover, and have lower leverage.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?company ?ticker ?name ?sector
       ?roe ?margin ?at ?de
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .

  FILTER (?sector = efin:SectorInformationTechnology)  # 필요시 변경

  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?roe .

  ?obsM a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?margin .

  ?obsAT a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:AssetTurnover ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?at .

  ?obsDE a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?de .

  {
    SELECT ?sector (AVG(?roeS) AS ?avgROE)
    WHERE {
      ?c efin:inSector ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:ROE ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?roeS .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?sector (AVG(?mS) AS ?avgMargin)
    WHERE {
      ?c efin:inSector ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:NetProfitMargin ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?mS .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?sector (AVG(?atS) AS ?avgAT)
    WHERE {
      ?c efin:inSector ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:AssetTurnover ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?atS .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?sector (AVG(?deS) AS ?avgDE)
    WHERE {
      ?c efin:inSector ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?deS .
    }
    GROUP BY ?sector
  }

  FILTER (?roe    >= ?avgROE)
  FILTER (?margin >= ?avgMargin)
  FILTER (?at     >= ?avgAT)
  FILTER (?de     <= ?avgDE)
}
ORDER BY DESC(?roe) DESC(?margin)
```

---

### 2.7 CQ-I7: 섹터 내 “핵심 업종” (섹터 매출 비중 상위) 및 해당 업종 리더 식별

**Competency Question (한글)**: 각 섹터에서, 섹터 매출의 대부분을 차지하는 핵심 업종과 그 업종 내 매출 상위 기업을 찾고 싶다.  
**Competency Question (English)**: In each sector, find industries that contribute most of the sector’s revenue and their top revenue companies.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?industry ?company ?ticker ?name ?revenue
WHERE {
  # 섹터-업종-회사
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  ?industry efin:inSectorOf ?sector .

  # 2024 매출
  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric efin:Revenue ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?revenue .

  # 섹터/업종 매출 합
  {
    SELECT ?sector (SUM(?revS) AS ?sectorRevenue)
    WHERE {
      ?c efin:inIndustry ?ind .
      ?ind efin:inSectorOf ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:Revenue ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?revS .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?sector ?industry (SUM(?revI) AS ?industryRevenue)
    WHERE {
      ?c efin:inIndustry ?industry .
      ?industry efin:inSectorOf ?sector .
      ?o a efin:MetricObservation ;
         efin:ofCompany ?c ;
         efin:observesMetric efin:Revenue ;
         efin:hasFiscalYear 2024 ;
         efin:hasNumericValue ?revI .
    }
    GROUP BY ?sector ?industry
  }

  # 업종이 섹터 매출의 20% 이상 차지하는 핵심 업종
  FILTER (?industryRevenue >= ?sectorRevenue * 0.2)
}
ORDER BY ?sector DESC(?industryRevenue) DESC(?revenue)
```

---

### 2.8 CQ-I8: 섹터 ROE 랭킹의 연간 변화(섹터 모멘텀) 스크리닝

**Competency Question (한글)**: 2023년 대비 2024년에 ROE 평균 랭킹이 많이 오른 섹터를 찾아 섹터 모멘텀 후보를 식별하고 싶다.  
**Competency Question (English)**: Identify sectors whose average ROE ranking improved significantly from 2023 to 2024.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?avgROE2023 ?avgROE2024
WHERE {
  {
    SELECT ?sector (AVG(?roe23) AS ?avgROE2023)
    WHERE {
      ?company efin:inIndustry ?industry .
      ?industry efin:inSectorOf ?sector .

      ?obs23 a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:ROE ;
             efin:hasFiscalYear 2023 ;
             efin:hasNumericValue ?roe23 .
    }
    GROUP BY ?sector
  }

  {
    SELECT ?sector (AVG(?roe24) AS ?avgROE2024)
    WHERE {
      ?company efin:inIndustry ?industry .
      ?industry efin:inSectorOf ?sector .

      ?obs24 a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:ROE ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?roe24 .
    }
    GROUP BY ?sector
  }
}
ORDER BY (?avgROE2024 - ?avgROE2023) DESC
```

---

### 2.9 CQ-I9: 섹터별 레버리지 분산(테일 위험도) 비교

**Competency Question (한글)**: 각 섹터에서 DebtToEquity 분포의 스프레드(최대–최소)가 큰 섹터를 찾아, 구조적으로 레버리지 테일 리스크가 큰 섹터를 식별하고 싶다.  
**Competency Question (English)**: Compare sectors by the spread of DebtToEquity to identify structurally risky sectors.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector
       (MIN(?de) AS ?minDE)
       (MAX(?de) AS ?maxDE)
       (MAX(?de) - MIN(?de) AS ?spreadDE)
WHERE {
  ?company efin:inIndustry ?industry .
  ?industry efin:inSectorOf ?sector .

  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric efin:DebtToEquity ;
       efin:hasFiscalYear 2024 ;
       efin:hasNumericValue ?de .
}
GROUP BY ?sector
HAVING (COUNT(DISTINCT ?company) >= 5)
ORDER BY DESC(?spreadDE)
```

---

### 2.10 CQ-I10: 섹터 내 고성장·고수익·저레버리지 “슈퍼 섹터 리더” 스크리닝

**Competency Question (한글)**: 특정 섹터에서 Revenue/NetIncome/CFO 성장률이 모두 양(+)이고, ROE·순이익률이 섹터 평균 이상이며, 부채비율이 섹터 평균 이하인 “슈퍼 섹터 리더” 기업을 찾고 싶다.  
**Competency Question (English)**: Within a sector, find companies with positive growth, above-average profitability, and below-average leverage.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?company ?ticker ?name ?sector
       ?revg ?nig ?cfog ?roe ?margin ?de
WHERE {
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .

  # 성장률
  ?o1 a efin:MetricObservation ;
      efin:ofCompany ?company ;
      efin:observesMetric efin:RevenueGrowthYoY ;
      efin:hasFiscalYear 2024 ;
      efin:hasNumericValue ?revg .

  ?o2 a efin:MetricObservation ;
      efin:ofCompany ?company ;
      efin:observesMetric efin:NetIncomeGrowthYoY ;
      efin:hasFiscalYear 2024 ;
      efin:hasNumericValue ?nig .

  ?o3 a efin:MetricObservation ;
      efin:ofCompany ?company ;
      efin:observesMetric efin:CFOGrowthYoY ;
      efin:hasFiscalYear 2024 ;
      efin:hasNumericValue ?cfog .

  # 수익성
  ?o4 a efin:MetricObservation ;
      efin:ofCompany ?company ;
      efin:observesMetric efin:ROE ;
      efin:hasFiscalYear 2024 ;
      efin:hasNumericValue ?roe .

  ?o5 a efin:MetricObservation ;
      efin:ofCompany ?company ;
      efin:observesMetric efin:NetProfitMargin ;
      efin:hasFiscalYear 2024 ;
      efin:hasNumericValue ?margin .

  # 레버리지
  ?o6 a efin:MetricObservation ;
      efin:ofCompany ?company ;
      efin:observesMetric efin:DebtToEquity ;
      efin:hasFiscalYear 2024 ;
      efin:hasNumericValue ?de .

  {
    SELECT ?sector
           (AVG(?roeS) AS ?avgROE)
           (AVG(?marginS) AS ?avgMargin)
           (AVG(?deS) AS ?avgDE)
    WHERE {
      ?c efin:inSector ?sector .

      OPTIONAL {
        ?p1 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:ROE ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?roeS .
      }
      OPTIONAL {
        ?p2 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:NetProfitMargin ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?marginS .
      }
      OPTIONAL {
        ?p3 a efin:MetricObservation ;
            efin:ofCompany ?c ;
            efin:observesMetric efin:DebtToEquity ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?deS .
      }
    }
    GROUP BY ?sector
  }

  FILTER (?revg > 0 && ?nig > 0 && ?cfog > 0)
  FILTER (?roe    >= ?avgROE)
  FILTER (?margin >= ?avgMargin)
  FILTER (?de     <= ?avgDE)
}
ORDER BY DESC(?roe) DESC(?margin)
```

---

## 3. 클래스 기반(리더/팩터) 추론 스크리닝 질의

이 섹션은 스키마에 정의된 **리더 클래스(TopRanking 기반)** 와  
GraphDB SPARQL 규칙으로 태깅된 **투자 개념 클래스(예: QualityFactorLeaderCompany)** 를 활용해,  
보다 선언적인 형태로 스크리닝하는 예시를 모았습니다.

### 3.1 CQ-C1: 업종별 매출 Top10 리더 기업 목록

**Competency Question (한글)**: 각 업종에서 매출 기준 Top10 리더(`efin:IndustryRevenueTop10LeaderCompany`)에 속한 기업들을 보고 싶다.  
**Competency Question (English)**: List companies that belong to the industry revenue Top10 leader class.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry ?company ?ticker ?name
WHERE {
  ?company a efin:IndustryRevenueTop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
}
ORDER BY ?industry ?ticker
```

---

### 3.2 CQ-C2: 섹터별 수익성(ROE, 순이익률) 동시 Top10 리더 기업

**Competency Question (한글)**: 동일 섹터에서 ROE와 순이익률이 모두 Top10인 리더 기업만 보고 싶다.  
**Competency Question (English)**: Within each sector, find companies that are Top10 both in ROE and net profit margin.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?company ?ticker ?name
WHERE {
  ?company a efin:SectorROETop10LeaderCompany ,
              efin:SectorNetProfitMarginTop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .
}
ORDER BY ?sector ?ticker
```

---

### 3.3 CQ-C3: 섹터별 매출·순이익·CFO 성장률 모두 Top10인 “성장 리더” 기업

**Competency Question (한글)**: 특정 섹터에서 매출/순이익/CFO 성장률이 모두 Top10에 속하는 고성장 리더 기업만 보고 싶다.  
**Competency Question (English)**: For each sector, find companies that are simultaneously Top10 in revenue, net income, and CFO growth.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?company ?ticker ?name
WHERE {
  ?company a efin:SectorCompositeTop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .
}
ORDER BY ?sector ?ticker
```

---

### 3.4 CQ-C4: 업종별 영업현금흐름비율 Top10 + ROE Top10 “현금 기반 고수익 리더” 기업

**Competency Question (한글)**: 업종 내에서 영업현금흐름비율과 ROE가 모두 Top10인 “현금 기반 고수익 리더” 기업을 보고 싶다.  
**Competency Question (English)**: Within each industry, find companies that are Top10 both in operating cash flow ratio and ROE.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry ?company ?ticker ?name
WHERE {
  ?company a efin:IndustryOperatingCashFlowRatioTop10LeaderCompany ,
              efin:IndustryROETop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
}
ORDER BY ?industry ?ticker
```

---

### 3.5 CQ-C5: 섹터별 종합점수 Top10 리더 + 성장률 리더 교집합

**Competency Question (한글)**: 섹터 종합점수(Composite) Top10 리더 중에서, 매출 성장률도 Top10에 속하는 기업만 보고 싶다.  
**Competency Question (English)**: Among sector composite Top10 leaders, find those that are also Top10 in revenue growth.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?company ?ticker ?name
WHERE {
  ?company a efin:SectorCompositeTop10LeaderCompany ,
              efin:SectorRevenueGrowthTop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .
}
ORDER BY ?sector ?ticker
```

---

### 3.6 CQ-C6: 업종별 “퀄리티 팩터 리더 + ROE 리더” 조합 스크리닝

> 이 CQ는 GraphDB SPARQL 규칙을 통해 `efin:QualityFactorLeaderCompany` 타입이 미리 태깅되어 있다는 것을 전제로 합니다.

**Competency Question (한글)**: 재무제표 기반 퀄리티 팩터 리더이면서, 업종 내 ROE Top10 리더 클래스에도 속하는 기업만 보고 싶다.  
**Competency Question (English)**: Within each industry, find companies that are both quality factor leaders and ROE Top10 leaders.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry ?company ?ticker ?name
WHERE {
  ?company a efin:QualityFactorLeaderCompany ,
              efin:IndustryROETop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
}
ORDER BY ?industry ?ticker
```

---

### 3.7 CQ-C7: 섹터별 복합 성장·수익성·현금흐름 리더 스크리닝

**Competency Question (한글)**: 섹터별로, ROE/순이익률/Composite 스코어/영업현금흐름비율이 모두 Top10인 슈퍼 리더 기업을 찾고 싶다.  
**Competency Question (English)**: For each sector, find “super leaders” that are Top10 in ROE, net margin, composite score, and operating cash flow ratio.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?company ?ticker ?name
WHERE {
  ?company a efin:SectorROETop10LeaderCompany ,
              efin:SectorNetProfitMarginTop10LeaderCompany ,
              efin:SectorCompositeTop10LeaderCompany ,
              efin:SectorOperatingCashFlowRatioTop10LeaderCompany ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .
}
ORDER BY ?sector ?ticker
```

---

## 4. 리더 클래스를 사용하지 않는 동등 스크리닝 질의

이 섹션은 3장에서 정의한 **클래스 기반 CQ**를,  
스키마에 정의된 리더 클래스를 사용하지 않고 `efin:hasRanking` / `efin:TopRanking` 구조만으로  
동일한 결과를 얻을 수 있도록 다시 작성한 버전입니다.

### 4.1 CQ-R1: 업종별 매출 Top10 리더 기업 (클래스 미사용 버전)

**대상 클래스**: `efin:IndustryRevenueTop10LeaderCompany`  
**동등 질의**: `TopRanking` 인스턴스를 직접 필터링하여 Industry × Revenue × Top10 조건을 만족하는 회사만 조회.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry ?company ?ticker ?name
WHERE {
  ?company a efin:Company ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry ;
           efin:hasRanking ?r .

  ?r a efin:IndustryTopRanking ;
     efin:forMetric efin:Revenue ;
     efin:forIndustry ?industry ;
     efin:forFiscalYear 2024 ;
     efin:hasRankingType "Top10" .
}
ORDER BY ?industry ?ticker
```

---

### 4.2 CQ-R2: 섹터별 ROE·순이익률 동시 Top10 리더 기업 (클래스 미사용 버전)

**대상 클래스**: `efin:SectorROETop10LeaderCompany`, `efin:SectorNetProfitMarginTop10LeaderCompany`  
**동등 질의**: 동일 섹터에서 ROE와 NetProfitMargin 기준 Top10 랭킹을 모두 가진 회사만 조회.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?company ?ticker ?name
WHERE {
  ?company a efin:Company ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .

  # ROE Top10 랭킹
  ?company efin:hasRanking ?roeRank .
  ?roeRank a efin:SectorTopRanking ;
           efin:forMetric efin:ROE ;
           efin:forSector ?sector ;
           efin:forFiscalYear 2024 ;
           efin:hasRankingType "Top10" .

  # NetProfitMargin Top10 랭킹
  ?company efin:hasRanking ?npmRank .
  ?npmRank a efin:SectorTopRanking ;
           efin:forMetric efin:NetProfitMargin ;
           efin:forSector ?sector ;
           efin:forFiscalYear 2024 ;
           efin:hasRankingType "Top10" .
}
ORDER BY ?sector ?ticker
```

---

### 4.3 CQ-R3: 섹터별 매출·순이익·CFO 성장률 모두 Top10인 “성장 리더” 기업 (클래스 미사용 버전)

**대상 클래스**:  
- `efin:SectorRevenueGrowthTop10LeaderCompany`  
- `efin:SectorNetIncomeGrowthTop10LeaderCompany`  
- `efin:SectorCFOGrowthTop10LeaderCompany`

**동등 질의**: 동일 섹터에서 RevenueGrowthYoY, NetIncomeGrowthYoY, CFOGrowthYoY 기준 Top10 랭킹을 모두 가진 기업 조회.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?sector ?company ?ticker ?name
WHERE {
  ?company a efin:Company ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .

  # RevenueGrowthYoY Top10
  ?company efin:hasRanking ?revRank .
  ?revRank a efin:SectorTopRanking ;
           efin:forMetric efin:RevenueGrowthYoY ;
           efin:forSector ?sector ;
           efin:forFiscalYear 2024 ;
           efin:hasRankingType "Top10" .

  # NetIncomeGrowthYoY Top10
  ?company efin:hasRanking ?niRank .
  ?niRank a efin:SectorTopRanking ;
          efin:forMetric efin:NetIncomeGrowthYoY ;
          efin:forSector ?sector ;
          efin:forFiscalYear 2024 ;
          efin:hasRankingType "Top10" .

  # CFOGrowthYoY Top10
  ?company efin:hasRanking ?cfoRank .
  ?cfoRank a efin:SectorTopRanking ;
           efin:forMetric efin:CFOGrowthYoY ;
           efin:forSector ?sector ;
           efin:forFiscalYear 2024 ;
           efin:hasRankingType "Top10" .
}
ORDER BY ?sector ?ticker
```

---

### 4.4 CQ-R4: 업종별 영업현금흐름비율 Top10 + ROE Top10 “현금 기반 고수익 리더” 기업 (클래스 미사용 버전)

**대상 클래스**:  
- `efin:IndustryOperatingCashFlowRatioTop10LeaderCompany`  
- `efin:IndustryROETop10LeaderCompany`

**동등 질의**: 동일 업종에서 OperatingCashFlowRatio와 ROE 기준 Top10 랭킹을 모두 가진 기업 조회.

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry ?company ?ticker ?name
WHERE {
  ?company a efin:Company ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  # OperatingCashFlowRatio Top10
  ?company efin:hasRanking ?ocfRank .
  ?ocfRank a efin:IndustryTopRanking ;
           efin:forMetric efin:OperatingCashFlowRatio ;
           efin:forIndustry ?industry ;
           efin:forFiscalYear 2024 ;
           efin:hasRankingType "Top10" .

  # ROE Top10
  ?company efin:hasRanking ?roeRank .
  ?roeRank a efin:IndustryTopRanking ;
           efin:forMetric efin:ROE ;
           efin:forIndustry ?industry ;
           efin:forFiscalYear 2024 ;
           efin:hasRankingType "Top10" .
}
ORDER BY ?industry ?ticker
```



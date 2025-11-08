
## Reasoner가 필요한 질의

### 업종 Top10 기업 추론 (정의 클래스 기반)

- **의도**: 업종별로 가장 투자 매력도가 높은 상위 10개 기업을 한 번에 뽑아내는 핵심 리더십 스크리닝용 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry ?ticker ?name
WHERE {
  ?company a efin:IndustryCompositeTop10LeaderCompany ;  # OWL equivalentClass + restriction 기반 정의 클래스
           efin:inIndustry ?industry ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
}
ORDER BY ?industry ?ticker
'''


### 전체 Top10 기업 추론 (정의 클래스 기반)

- **의도**: 업종 구분 없이 전체 시장에서 절대적인 리더십을 가진 기업군을 찾기 위한 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?ticker ?name
WHERE {
  ?company a efin:AllCompositeTop10LeaderCompany ;  # OWL 정의 클래스 (AllTopRanking / Composite Top10)
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
}
ORDER BY ?ticker
'''

### 전체 재무 지표 조회 (a efin:Metric, reasoner 필요)

- **의도**: 투자 분석에 활용 가능한 모든 재무·파생 지표 목록을 한 번에 확인해 메트릭 설계와 쿼리 설계를 돕는 질의입니다.

'''sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?label
WHERE {
  ?metric a efin:Metric ;  # efin:Metric ≡ BaseMetric ∪ DerivedMetric (OWL 추론 필요)
          rdfs:label ?label .
}
ORDER BY ?metric
'''


### 기업 재무 지표의 값 추론 (inverseOf 기반)

- **의도**: 개별 기업 관점에서 “이 회사가 어떤 지표에서 어떤 값을 갖고 있는지”를 reasoner 기반으로 빠르게 훑어보는 질의입니다.

'''sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?companyName ?label ?value
WHERE {
  ?company efin:hasObservation ?obs ;  # 역속성: ofCompany ↔ hasObservation (owl:inverseOf) 추론 필요
           efin:hasCompanyName ?companyName .
  ?obs     efin:observesMetric ?metric ;
           efin:hasNumericValue ?value .
  ?metric  rdfs:label ?label .
}
ORDER BY ?company ?metric
'''


### 재무 지표별 기업의 값 추론 (inverseOf 기반)

- **의도**: 특정 지표(ROE, 마진 등)별로 어떤 기업들이 어떤 값을 갖고 있는지, 메트릭 중심으로 reasoner 동작을 점검하는 질의입니다.

'''sparql
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?label ?companyName ?value
WHERE {
  ?metric efin:observedBy ?obs ;             # 역속성: observesMetric ↔ observedBy (owl:inverseOf) 추론 필요
			rdfs:label ?label .
  ?obs    efin:ofCompany ?company ;
          efin:hasNumericValue ?value .
  ?company efin:hasCompanyName ?companyName .
}
ORDER BY ?label ?company
'''


### 기간 유형별 관측값 조회 (Duration/InstantObservation 정의 클래스 기반)

- **의도**: 기간 타입(duration/instant) 정의 클래스가 제대로 추론되는지 확인하면서, 기간 구조를 활용한 시계열/스냅샷 분석 준비를 위한 질의입니다.

'''sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?companyName ?metricLabel?value
WHERE {
  # DurationObservation: MetricObservation ∧ hasPeriodType "duration"
  ?obs a efin:DurationObservation ;  # OWL equivalentClass + hasValue 제약 기반 추론 필요
       efin:ofCompany ?company ;
       efin:observesMetric ?metric ;
       efin:hasNumericValue ?value .
  ?company efin:hasCompanyName ?companyName .
  ?metric rdfs:label ?metricLabel .
}
ORDER BY ?company ?metric
'''


## Reasoner 없이도 동작하는 질의

### DerivedRatio 다중 팩터 우수 기업

- **의도**: 여러 파생 지표에서 동시에 업종 평균 이상인 멀티팩터 우수 기업을 찾는, 가장 강한 알파 후보 발굴용 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?ticker ?name ?industry ?numRatiosAboveAvg
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
'''


### 강한 DerivedRatio 팩터 다수 보유 기업

- **의도**: 다양한 DerivedRatio에서 업종 평균 대비 크게 우위(예: 1.5배 이상)를 보이는 ‘팩터 다수 보유’ 슈퍼 종목을 찾는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?ticker ?name
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
'''


### 레버리지 의존형 고수익 기업

- **의도**: 높은 수익성을 보이긴 하지만 부채 의존도가 높은, 레버리지 리스크를 동반한 고수익 종목을 식별하기 위한 경계/모니터링용 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?ticker ?name ?industry
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
'''


### 성장 틸트 기업

- **의도**: 성장률은 높지만 수익성이 아직 충분히 따라오지 않은, 전형적인 ‘성장주/턴어라운드 후보’ 기업을 찾는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?ticker ?name
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
'''


### 수익성 평균 이상 기업

- **의도**: ROE와 마진 등 수익성 측면에서 평균 이상인 기업을 필터링해 ‘퀄리티/가치’ 측면의 우수 기업을 찾는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT DISTINCT ?ticker ?name
WHERE {
  # 회사 기본 정보 + 업종
  ?company a efin:Company ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .

  # 공통 회계연도
  ?obsNPM efin:ofCompany ?company ;
          efin:observesMetric efin:NetProfitMargin ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?npm .
  ?benchNPM a efin:AllBenchmark ;
            efin:forSector efin:SectorAll ;
            efin:forMetric efin:NetProfitMargin ;
            efin:forFiscalYear ?fy ;
            efin:hasAverageValue ?avgNpm .
  FILTER (?npm >= ?avgNpm)

  ?obsROE efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?roe .
  ?benchROE a efin:AllBenchmark ;
            efin:forSector efin:SectorAll ;
            efin:forMetric efin:ROE ;
            efin:forFiscalYear ?fy ;
            efin:hasAverageValue ?avgRoe .
  FILTER (?roe >= ?avgRoe)
}
ORDER BY ?ticker
'''


### 성장성 평균 이상 기업

- **의도**: 매출·순이익·CFO 성장률이 평균 이상인 기업을 골라내, 성장 드라이버가 강한 종목을 선별하는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT DISTINCT ?ticker ?name
WHERE {
  ?company a efin:Company ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .

  # RevenueGrowthYoY
  ?obsRevG efin:ofCompany ?company ;
           efin:observesMetric efin:RevenueGrowthYoY ;
           efin:hasFiscalYear ?fy ;
           efin:hasNumericValue ?revG .
  ?benchRevG a efin:AllBenchmark ;
             efin:forSector efin:SectorAll ;
             efin:forMetric efin:RevenueGrowthYoY ;
             efin:forFiscalYear ?fy ;
             efin:hasAverageValue ?avgRevG .
  FILTER (?revG >= ?avgRevG)

  # CFOGrowthYoY
  ?obsCfoG efin:ofCompany ?company ;
           efin:observesMetric efin:CFOGrowthYoY ;
           efin:hasFiscalYear ?fy ;
           efin:hasNumericValue ?cfoG .
  ?benchCfoG a efin:AllBenchmark ;
             efin:forSector efin:SectorAll ;
             efin:forMetric efin:CFOGrowthYoY ;
             efin:forFiscalYear ?fy ;
             efin:hasAverageValue ?avgCfoG .
  FILTER (?cfoG >= ?avgCfoG)
}
ORDER BY ?ticker
'''


### 수익성 업종 평균 이상 기업

- **의도**: ROE와 마진 등 수익성 측면에서 업종 평균 이상인 기업을 필터링해 ‘퀄리티/가치’ 측면의 우수 기업을 찾는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT DISTINCT ?ticker ?name
WHERE {
  # 회사 기본 정보 + 업종
  ?company a efin:Company ;
           efin:inIndustry ?industry ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .

  # 공통 회계연도
  ?obsNPM efin:ofCompany ?company ;
          efin:observesMetric efin:NetProfitMargin ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?npm .
  ?benchNPM a efin:IndustryBenchmark ;
            efin:forIndustry ?industry ;
            efin:forMetric efin:NetProfitMargin ;
            efin:forFiscalYear ?fy ;
            efin:hasAverageValue ?avgNpm .
  FILTER (?npm >= ?avgNpm)

  ?obsROE efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?roe .
  ?benchROE a efin:IndustryBenchmark ;
            efin:forIndustry ?industry ;
            efin:forMetric efin:ROE ;
            efin:forFiscalYear ?fy ;
            efin:hasAverageValue ?avgRoe .
  FILTER (?roe >= ?avgRoe)
}
ORDER BY ?ticker
'''


### 성장성 업종 평균 이상 기업

- **의도**: 매출·순이익·CFO 성장률이 업종 평균 이상인 기업을 골라내, 성장 드라이버가 강한 종목을 선별하는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT DISTINCT ?ticker ?name
WHERE {
  ?company a efin:Company ;
           efin:inIndustry ?industry ;
           efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .

  # RevenueGrowthYoY
  ?obsRevG efin:ofCompany ?company ;
           efin:observesMetric efin:RevenueGrowthYoY ;
           efin:hasFiscalYear ?fy ;
           efin:hasNumericValue ?revG .
  ?benchRevG a efin:IndustryBenchmark ;
             efin:forIndustry ?industry ;
             efin:forMetric efin:RevenueGrowthYoY ;
             efin:forFiscalYear ?fy ;
             efin:hasAverageValue ?avgRevG .
  FILTER (?revG >= ?avgRevG)

  # CFOGrowthYoY
  ?obsCfoG efin:ofCompany ?company ;
           efin:observesMetric efin:CFOGrowthYoY ;
           efin:hasFiscalYear ?fy ;
           efin:hasNumericValue ?cfoG .
  ?benchCfoG a efin:IndustryBenchmark ;
             efin:forIndustry ?industry ;
             efin:forMetric efin:CFOGrowthYoY ;
             efin:forFiscalYear ?fy ;
             efin:hasAverageValue ?avgCfoG .
  FILTER (?cfoG >= ?avgCfoG)
}
ORDER BY ?ticker
'''


### 업종 로테이션 후보 업종

- **의도**: ROE·마진·부채비율을 종합한 업종 스코어로, 포트폴리오 레벨에서 업종 로테이션 후보를 찾는 매크로/섹터 전략용 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?industry
       (AVG(?roe) AS ?avgROE)
       (AVG(?margin) AS ?avgNetMargin)
       (AVG(?de) AS ?avgDebtToEquity)
       ((AVG(?roe) + AVG(?margin) - AVG(?de)) AS ?industryScore)
WHERE {
  ?company efin:inIndustry ?industry .

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
GROUP BY ?industry
HAVING (COUNT(DISTINCT ?company) >= 5)
ORDER BY DESC(?industryScore)
'''


### 동일 업종 피어 비교

- **의도**: 특정 종목(AAPL 등)을 기준으로 동일 업종 내 피어들의 수익성을 비교해 상대적 위치를 직관적으로 파악하는 질의입니다.

'''sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>

SELECT ?peerTicker ?peerName ?industry ?roe ?netMargin
WHERE {
  # 기준 회사
  ?target efin:hasTicker "AAPL" ;
          efin:inIndustry ?industry .

  # 동일 업종의 모든 회사
  ?peer efin:inIndustry ?industry ;
        efin:hasTicker ?peerTicker ;
        efin:hasCompanyName ?peerName ;
        efin:inIndustry ?industry .

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
'''
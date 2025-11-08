# 투자자 관점 재무 분석 질의문 가이드

## 문서 목적

본 문서는 **EFIN 온톨로지 그래프를 활용한 투자 분석 SPARQL 질의문**을 제공합니다. 특정 기업에 대한 투자 의사결정을 내리기 위한 질의문들을 정리했습니다.

**다른 문서:**
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티 등 스키마 구조 상세
- [계층 구조 설명서](./hierarchy-structure.md): 온톨로지의 전체 계층 구조와 설계 의도 상세 설명
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [상호 운용성 가이드](./interoperability.md): FIBO 등 표준 온톨로지와의 통합
- [인스턴스 통계](./instance_statistics.md): 현재 인스턴스 데이터의 클래스별/연도별 분포

---

본 문서는 EFIN 온톨로지 그래프를 활용하여 **특정 기업에 대한 투자 의사결정**을 내리기 위한 SPARQL 질의문들을 정리한 것입니다. 

각 질의문은 그래프의 관계를 활용하여 특정 기업의 재무 지표를 동종업계와 비교하거나, 시계열 추이를 분석하거나, 여러 지표 간의 관계를 종합적으로 평가하는 데 초점을 맞추고 있습니다.

## 목차

1. [핵심 투자 의사결정 질의 (필수 확인 항목)](#1-핵심-투자-의사결정-질의-필수-확인-항목)
2. [동종업계 비교 분석](#2-동종업계-비교-분석)
3. [시계열 추이 분석](#3-시계열-추이-분석)
4. [종합 평가 및 리스크 분석](#4-종합-평가-및-리스크-분석)
5. [추후 개선 방향 (현재 스키마로 불가능한 유명 분석)](#5-추후-개선-방향-현재-스키마로-불가능한-유명-분석)
6. [고급 (추론 기반) CQ 모음](#6-고급-추론-기반-cq-모음)

---

## 1. 핵심 투자 의사결정 질의 (필수 확인 항목)

투자 결정 전 반드시 확인해야 하는 핵심 질의문들입니다. 특정 기업의 재무 건전성을 종합적으로 평가합니다.

### 1.1 특정 기업의 핵심 재무 지표 종합 평가

#### CQ1.1.1: 특정 기업의 핵심 재무 지표는 무엇이며, 동종업계 대비 위치는 어디인가?
**Competency Question (한글)**: 특정 기업(예: AAPL)의 핵심 재무 지표(ROE, ROIC, 순이익률, 부채비율, 유동비율)는 무엇이며, 동종업계 평균 대비 위치는 어디인가?  
**Competency Question (English)**: What are the key financial metrics (ROE, ROIC, net profit margin, debt-to-equity, current ratio) of a specific company (e.g., AAPL) and how do they compare to the industry average?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?industry ?sector
       ?roe ?roic ?netMargin ?debtToEquity ?currentRatio
       ?industryAvgROE ?industryAvgROIC ?industryAvgMargin
WHERE {
  # 특정 기업 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry ;
           efin:inSector ?sector .
  
  # 해당 기업의 핵심 지표
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?roe .
  
  ?obsROIC a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:ROIC ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?roic .
  
  ?obsMargin a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?netMargin .
  
  ?obsDebt a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:DebtToEquity ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?debtToEquity .
  
  ?obsCurrent a efin:MetricObservation ;
              efin:ofCompany ?company ;
              efin:observesMetric efin:CurrentRatio ;
              efin:hasFiscalYear 2024 ;
              efin:hasNumericValue ?currentRatio .
  
  # 동종업계 평균 계산
  {
    SELECT ?industry (AVG(?roeInd) AS ?industryAvgROE)
           (AVG(?roicInd) AS ?industryAvgROIC)
           (AVG(?marginInd) AS ?industryAvgMargin)
    WHERE {
      ?compInd efin:inIndustry ?industry .
      
      ?obsROEInd a efin:MetricObservation ;
                 efin:ofCompany ?compInd ;
                 efin:observesMetric efin:ROE ;
                 efin:hasFiscalYear 2024 ;
                 efin:hasNumericValue ?roeInd .
      
      ?obsROICInd a efin:MetricObservation ;
                  efin:ofCompany ?compInd ;
                  efin:observesMetric efin:ROIC ;
                  efin:hasFiscalYear 2024 ;
                  efin:hasNumericValue ?roicInd .
      
      ?obsMarginInd a efin:MetricObservation ;
                    efin:ofCompany ?compInd ;
                    efin:observesMetric efin:NetProfitMargin ;
                    efin:hasFiscalYear 2024 ;
                    efin:hasNumericValue ?marginInd .
    }
    GROUP BY ?industry
  }
}
```

### 1.2 재무 건전성 종합 평가

#### CQ1.2.1: 특정 기업의 재무 건전성은 어느 정도인가? (Piotroski F-Score 기반)
**Competency Question (한글)**: 특정 기업의 재무 건전성은 어느 정도인가? Piotroski F-Score를 통해 평가할 수 있는가?  
**Competency Question (English)**: What is the financial health of a specific company? Can it be assessed using Piotroski F-Score?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name 
       ((IF(?roa > 0, 1, 0) + 
         IF(?cfo > 0, 1, 0) + 
         IF(?roa > ?roaPrior, 1, 0) + 
         IF(?cfo > ?netIncome, 1, 0) + 
         IF(?debtRatio < ?debtRatioPrior, 1, 0) + 
         IF(?currentRatio > ?currentRatioPrior, 1, 0) + 
         IF(?grossMargin > ?grossMarginPrior, 1, 0) + 
         IF(?assetTurnover > ?assetTurnoverPrior, 1, 0)) AS ?piotroskiScore)
       ?roa ?cfo ?currentRatio ?grossMargin ?assetTurnover
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  # 2024년 데이터
  ?obsNetIncome a efin:MetricObservation ;
                efin:ofCompany ?company ;
                efin:observesMetric efin:NetIncome ;
                efin:hasFiscalYear 2024 ;
                efin:hasNumericValue ?netIncome .
  
  ?obsAssets a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:Assets ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?assets .
  BIND ((?netIncome / ?assets) AS ?roa)
  
  ?obsCFO a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:CFO ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?cfo .
  
  ?obsCurrentRatio a efin:MetricObservation ;
                   efin:ofCompany ?company ;
                   efin:observesMetric efin:CurrentRatio ;
                   efin:hasFiscalYear 2024 ;
                   efin:hasNumericValue ?currentRatio .
  
  ?obsGrossMargin a efin:MetricObservation ;
                  efin:ofCompany ?company ;
                  efin:observesMetric efin:GrossMargin ;
                  efin:hasFiscalYear 2024 ;
                  efin:hasNumericValue ?grossMargin .
  
  ?obsAssetTurnover a efin:MetricObservation ;
                    efin:ofCompany ?company ;
                    efin:observesMetric efin:AssetTurnover ;
                    efin:hasFiscalYear 2024 ;
                    efin:hasNumericValue ?assetTurnover .
  
  ?obsLiabilities a efin:MetricObservation ;
                  efin:ofCompany ?company ;
                  efin:observesMetric efin:Liabilities ;
                  efin:hasFiscalYear 2024 ;
                  efin:hasNumericValue ?liabilities .
  BIND ((?liabilities / ?assets) AS ?debtRatio)
  
  # 2023년 데이터 (전년 대비 비교)
  ?obsNetIncomePrior a efin:MetricObservation ;
                     efin:ofCompany ?company ;
                     efin:observesMetric efin:NetIncome ;
                     efin:hasFiscalYear 2023 ;
                     efin:hasNumericValue ?netIncomePrior .
  
  ?obsAssetsPrior a efin:MetricObservation ;
                  efin:ofCompany ?company ;
                  efin:observesMetric efin:Assets ;
                  efin:hasFiscalYear 2023 ;
                  efin:hasNumericValue ?assetsPrior .
  BIND ((?netIncomePrior / ?assetsPrior) AS ?roaPrior)
  
  ?obsCurrentRatioPrior a efin:MetricObservation ;
                        efin:ofCompany ?company ;
                        efin:observesMetric efin:CurrentRatio ;
                        efin:hasFiscalYear 2023 ;
                        efin:hasNumericValue ?currentRatioPrior .
  
  ?obsGrossMarginPrior a efin:MetricObservation ;
                       efin:ofCompany ?company ;
                       efin:observesMetric efin:GrossMargin ;
                       efin:hasFiscalYear 2023 ;
                       efin:hasNumericValue ?grossMarginPrior .
  
  ?obsAssetTurnoverPrior a efin:MetricObservation ;
                         efin:ofCompany ?company ;
                         efin:observesMetric efin:AssetTurnover ;
                         efin:hasFiscalYear 2023 ;
                         efin:hasNumericValue ?assetTurnoverPrior .
  
  ?obsLiabilitiesPrior a efin:MetricObservation ;
                       efin:ofCompany ?company ;
                       efin:observesMetric efin:Liabilities ;
                       efin:hasFiscalYear 2023 ;
                       efin:hasNumericValue ?liabilitiesPrior .
  BIND ((?liabilitiesPrior / ?assetsPrior) AS ?debtRatioPrior)
}
```

**참고**: 실제 SPARQL 엔진에 따라 `IF` 함수가 다를 수 있습니다. 일부 엔진은 `CASE WHEN` 구문을 사용합니다.

### 1.3 성장의 질 평가

#### CQ1.3.1: 특정 기업의 성장은 수익성 있는 성장인가?
**Competency Question (한글)**: 특정 기업의 매출 성장률과 순이익 성장률의 관계는 어떠한가? 수익성 있는 성장을 하고 있는가?  
**Competency Question (English)**: What is the relationship between revenue growth rate and net income growth rate of a specific company? Is it profitable growth?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?revenueGrowth ?netIncomeGrowth 
       ((?netIncomeGrowth - ?revenueGrowth) AS ?growthQuality)
       ?netMargin ?roe
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obs1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:RevenueGrowthYoY ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?revenueGrowth .
  
  ?obs2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetIncomeGrowthYoY ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?netIncomeGrowth .
  
  ?obs3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?netMargin .
  
  ?obs4 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:ROE ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?roe .
}
```

### 1.4 현금흐름 품질 평가

#### CQ1.4.1: 특정 기업의 현금흐름 품질은 어느 정도인가?
**Competency Question (한글)**: 특정 기업의 영업현금흐름과 순이익의 관계는 어떠한가? 현금흐름 품질은 어느 정도인가?  
**Competency Question (English)**: What is the relationship between operating cash flow and net income of a specific company? What is the cash flow quality?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?cfo ?netIncome 
       ((?cfo / ?netIncome) AS ?cashFlowQuality)
       ?fcf ?cfoGrowth
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obs1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:CFO ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?cfo .
  
  ?obs2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetIncome ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?netIncome .
  
  ?obs3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:FreeCashFlow ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?fcf .
  
  ?obs4 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:CFOGrowthYoY ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?cfoGrowth .
  
  FILTER (?netIncome > 0)
}
```

### 1.5 추론 기반 스크리닝: 고품질 수익성 & 현금흐름 기업 선별

#### CQ1.5.1: DerivedRatio/계보를 이용한 고품질 수익성 & 현금창출 기업 스크리닝  
**Competency Question (한글)**: DerivedRatio 계층과 계보 정보를 활용해, ROE·순이익률·FCF가 모두 **기본 지표(NetIncome, Equity, Revenue, CFO, CapEx)** 에 잘 뒷받침되면서 업계 평균 대비 우수한 기업만 스크리닝할 수 있는가?  
**Competency Question (English)**: Using the DerivedRatio hierarchy and metric lineage, can we screen companies whose ROE, net margin, and FCF are supported by NetIncome/Equity/Revenue/CFO/CapEx and significantly above industry averages?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name ?industry
       ?roe ?netMargin ?fcf
       ?industryAvgROE ?industryAvgMargin
WHERE {
  # 회사 후보
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  ############################################################
  # ROE: DerivedRatio 계층 + NetIncome/Equity 계보 조건
  ############################################################
  efin:ROE rdfs:subClassOf+ efin:DerivedRatio .

  ?roeObs a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:isDerived true ;
          efin:hasNumericValue ?roe ;
          efin:hasConfidence ?roeConf .

  FILTER (EXISTS { ?roeObs efin:computedFromMetric efin:NetIncome } &&
          EXISTS { ?roeObs efin:computedFromMetric efin:Equity })

  ############################################################
  # 순이익률(NetProfitMargin): NetIncome/Revenue 계보 조건
  ############################################################
  efin:NetProfitMargin rdfs:subClassOf+ efin:DerivedRatio .

  ?marginObs a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear 2024 ;
             efin:isDerived true ;
             efin:hasNumericValue ?netMargin ;
             efin:hasConfidence ?marginConf .

  FILTER (EXISTS { ?marginObs efin:computedFromMetric efin:NetIncome } &&
          EXISTS { ?marginObs efin:computedFromMetric efin:Revenue })

  ############################################################
  # FCF: CFO / CapEx 계보 조건 (선택)
  ############################################################
  OPTIONAL {
    ?fcfObs a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:FreeCashFlow ;
            efin:hasFiscalYear 2024 ;
            efin:isDerived true ;
            efin:hasNumericValue ?fcf .

    FILTER (EXISTS { ?fcfObs efin:computedFromMetric efin:CFO } &&
            EXISTS { ?fcfObs efin:computedFromMetric efin:CapEx })
  }

  ############################################################
  # 업계 평균 벤치마크
  ############################################################
  {
    SELECT ?industry (AVG(?roeInd) AS ?industryAvgROE)
                     (AVG(?marginInd) AS ?industryAvgMargin)
    WHERE {
      ?compInd efin:inIndustry ?industry .

      ?obsRInd a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:ROE ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?roeInd .

      ?obsMInd a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:NetProfitMargin ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?marginInd .
    }
    GROUP BY ?industry
  }

  ############################################################
  # 스크리닝 조건
  ############################################################
  FILTER (
    ?roe > ?industryAvgROE + 0.05 &&
    ?netMargin > ?industryAvgMargin + 0.05 &&
    ?roeConf >= 0.9 &&
    ?marginConf >= 0.9
  )
}
ORDER BY DESC(?roe)
```

---

## 2. 동종업계 비교 분석

특정 기업의 재무 지표를 동종업계(Industry) 또는 섹터(Sector)와 비교하여 상대적 위치를 파악합니다.

### 2.1 수익성 비교

#### CQ2.1.1: 특정 기업의 ROE는 동종업계 대비 어느 정도 수준인가?
**Competency Question (한글)**: 특정 기업의 ROE는 동종업계 평균 대비 어느 정도 수준인가? 상위 몇 퍼센트에 위치하는가?  
**Competency Question (English)**: What is the ROE of a specific company compared to the industry average? What percentile does it rank in?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?industry ?roe 
       ?industryAvgROE ?industryMaxROE ?industryMinROE
       ((?roe - ?industryAvgROE) AS ?vsIndustryAvg)
       ((?roe / ?industryAvgROE - 1) AS ?vsIndustryPercent)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?roe .
  
  # 동종업계 통계
  {
    SELECT ?industry (AVG(?roeInd) AS ?industryAvgROE)
           (MAX(?roeInd) AS ?industryMaxROE)
           (MIN(?roeInd) AS ?industryMinROE)
    WHERE {
      ?compInd efin:inIndustry ?industry .
      ?obsROEInd a efin:MetricObservation ;
                 efin:ofCompany ?compInd ;
                 efin:observesMetric efin:ROE ;
                 efin:hasFiscalYear 2024 ;
                 efin:hasNumericValue ?roeInd .
    }
    GROUP BY ?industry
  }
}
```

#### CQ2.1.2: 특정 기업의 순이익률은 동종업계에서 몇 번째인가?
**Competency Question (한글)**: 특정 기업의 순이익률은 동종업계에서 몇 번째인가? 상위 몇 개 기업보다 높은가?  
**Competency Question (English)**: What is the rank of a specific company's net profit margin within its industry? How many companies rank higher?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?industry ?netMargin
       (COUNT(?higherMargin) AS ?rankInIndustry)
       (COUNT(DISTINCT ?compInd) AS ?totalCompaniesInIndustry)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsMargin a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?netMargin .
  
  # 동종업계의 다른 기업들
  ?compInd efin:inIndustry ?industry .
  FILTER (?compInd != ?company)
  
  ?obsMarginInd a efin:MetricObservation ;
                efin:ofCompany ?compInd ;
                efin:observesMetric efin:NetProfitMargin ;
                efin:hasFiscalYear 2024 ;
                efin:hasNumericValue ?marginInd .
  
  # 더 높은 순이익률을 가진 기업들
  OPTIONAL {
    ?obsMarginHigher a efin:MetricObservation ;
                     efin:ofCompany ?compHigher ;
                     efin:observesMetric efin:NetProfitMargin ;
                     efin:hasFiscalYear 2024 ;
                     efin:hasNumericValue ?higherMargin .
    ?compHigher efin:inIndustry ?industry .
    FILTER (?higherMargin > ?netMargin)
  }
}
GROUP BY ?company ?ticker ?name ?industry ?netMargin
ORDER BY ?rankInIndustry
```

### 2.2 효율성 비교

#### CQ2.2.1: 특정 기업의 자산 효율성은 동종업계 대비 어느 정도인가?
**Competency Question (한글)**: 특정 기업의 자산회전율과 자산 효율성 지표들은 동종업계 평균 대비 어느 정도인가?  
**Competency Question (English)**: What is the asset turnover and asset efficiency of a specific company compared to the industry average?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?industry
       ?assetTurnover ?inventoryTurnover ?receivablesTurnover
       ?industryAvgAssetTurnover ?industryAvgInventoryTurnover ?industryAvgReceivablesTurnover
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsAsset a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:AssetTurnover ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?assetTurnover .
  
  OPTIONAL {
    ?obsInv a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:InventoryTurnover ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?inventoryTurnover .
  }
  
  OPTIONAL {
    ?obsRec a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:ReceivablesTurnover ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?receivablesTurnover .
  }
  
  # 동종업계 평균
  {
    SELECT ?industry (AVG(?atInd) AS ?industryAvgAssetTurnover)
           (AVG(?itInd) AS ?industryAvgInventoryTurnover)
           (AVG(?rtInd) AS ?industryAvgReceivablesTurnover)
    WHERE {
      ?compInd efin:inIndustry ?industry .
      
      ?obsAT a efin:MetricObservation ;
             efin:ofCompany ?compInd ;
             efin:observesMetric efin:AssetTurnover ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?atInd .
      
      OPTIONAL {
        ?obsIT a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:InventoryTurnover ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?itInd .
      }
      
      OPTIONAL {
        ?obsRT a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:ReceivablesTurnover ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?rtInd .
      }
    }
    GROUP BY ?industry
  }
}
```

### 2.3 레버리지 및 리스크 비교

#### CQ2.3.1: 특정 기업의 부채 수준은 동종업계 대비 어느 정도인가?
**Competency Question (한글)**: 특정 기업의 부채비율과 이자보상배수는 동종업계 대비 어느 정도인가? 리스크 수준은?  
**Competency Question (English)**: What is the debt-to-equity ratio and interest coverage of a specific company compared to the industry? What is the risk level?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?industry
       ?debtToEquity ?interestCoverage
       ?industryAvgDebtToEquity ?industryAvgInterestCoverage
       ((?debtToEquity - ?industryAvgDebtToEquity) AS ?debtVsIndustry)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsDebt a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:DebtToEquity ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?debtToEquity .
  
  OPTIONAL {
    ?obsInt a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:InterestCoverage ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?interestCoverage .
  }
  
  # 동종업계 평균
  {
    SELECT ?industry (AVG(?dtInd) AS ?industryAvgDebtToEquity)
           (AVG(?icInd) AS ?industryAvgInterestCoverage)
    WHERE {
      ?compInd efin:inIndustry ?industry .
      
      ?obsDT a efin:MetricObservation ;
             efin:ofCompany ?compInd ;
             efin:observesMetric efin:DebtToEquity ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?dtInd .
      
      OPTIONAL {
        ?obsIC a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:InterestCoverage ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?icInd .
        FILTER (?icInd > 0)
      }
    }
    GROUP BY ?industry
  }
}
```

### 2.4 ROE vs ROIC 비교 (자본 구조 영향)

#### CQ2.3.2: 특정 기업의 ROE와 ROIC 차이는 동종업계 대비 어느 정도인가?
**Competency Question (한글)**: 특정 기업의 ROE와 ROIC 차이는 얼마이며, 자본 구조의 영향은 동종업계 대비 어느 정도인가?  
**Competency Question (English)**: What is the difference between ROE and ROIC of a specific company and how does the capital structure impact compare to the industry?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?industry
       ?roe ?roic ((?roe - ?roic) AS ?leverageEffect)
       ?industryAvgROE ?industryAvgROIC 
       ((?industryAvgROE - ?industryAvgROIC) AS ?industryAvgLeverageEffect)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:hasNumericValue ?roe .
  
  ?obsROIC a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:ROIC ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?roic .
  
  # 동종업계 평균
  {
    SELECT ?industry (AVG(?roeInd) AS ?industryAvgROE)
           (AVG(?roicInd) AS ?industryAvgROIC)
    WHERE {
      ?compInd efin:inIndustry ?industry .
      
      ?obsROEInd a efin:MetricObservation ;
                 efin:ofCompany ?compInd ;
                 efin:observesMetric efin:ROE ;
                 efin:hasFiscalYear 2024 ;
                 efin:hasNumericValue ?roeInd .
      
      ?obsROICInd a efin:MetricObservation ;
                  efin:ofCompany ?compInd ;
                  efin:observesMetric efin:ROIC ;
                  efin:hasFiscalYear 2024 ;
                  efin:hasNumericValue ?roicInd .
    }
    GROUP BY ?industry
  }
}
```

### 2.5 추론 기반 스크리닝: 동종업계 내 다중 비율 우수 기업

#### CQ2.5.1: DerivedRatio 계층을 이용한 다중 비율 우수 기업 스크리닝  
**Competency Question (한글)**: DerivedRatio 계층을 활용해, 특정 산업 내에서 **여러 핵심 비율(수익성·효율성·레버리지)이 동시에 업계 평균을 상회하는 기업**만 스크리닝할 수 있는가?  
**Competency Question (English)**: Using the DerivedRatio hierarchy, can we screen companies within an industry that simultaneously outperform industry averages across multiple key ratios (profitability, efficiency, leverage)?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name ?industry
       ?roe ?netMargin ?assetTurnover ?debtToEquity
       ?avgROE ?avgMargin ?avgAT ?avgDE
WHERE {
  # 동종업계 내 회사 후보
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  ############################################################
  # 1) 주요 비율 지표들이 DerivedRatio 계층에 속함 (계층 추론)
  ############################################################
  efin:ROE rdfs:subClassOf+ efin:DerivedRatio .
  efin:NetProfitMargin rdfs:subClassOf+ efin:DerivedRatio .
  efin:AssetTurnover rdfs:subClassOf+ efin:DerivedRatio .
  efin:DebtToEquity rdfs:subClassOf+ efin:DerivedRatio .

  ############################################################
  # 2) 회사별 2024년 비율 값
  ############################################################
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

  OPTIONAL {
    ?atObs a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:AssetTurnover ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?assetTurnover .
  }

  OPTIONAL {
    ?deObs a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:DebtToEquity ;
           efin:hasFiscalYear 2024 ;
           efin:hasNumericValue ?debtToEquity .
  }

  ############################################################
  # 3) 산업별 평균값 (동일 DerivedRatio 계층 메트릭 기준)
  ############################################################
  {
    SELECT ?industry
           (AVG(?roeInd) AS ?avgROE)
           (AVG(?marginInd) AS ?avgMargin)
           (AVG(?atInd) AS ?avgAT)
           (AVG(?deInd) AS ?avgDE)
    WHERE {
      ?compInd efin:inIndustry ?industry .

      ?obsR a efin:MetricObservation ;
            efin:ofCompany ?compInd ;
            efin:observesMetric efin:ROE ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?roeInd .

      ?obsM a efin:MetricObservation ;
            efin:ofCompany ?compInd ;
            efin:observesMetric efin:NetProfitMargin ;
            efin:hasFiscalYear 2024 ;
            efin:hasNumericValue ?marginInd .

      OPTIONAL {
        ?obsAT a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:AssetTurnover ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?atInd .
      }

      OPTIONAL {
        ?obsDE a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:DebtToEquity ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?deInd .
      }
    }
    GROUP BY ?industry
  }

  ############################################################
  # 4) 스크리닝 조건:
  #    - ROE, 순이익률, 자산회전율은 업계 평균 이상
  #    - 부채비율은 업계 평균 이하 (보수적으로)
  ############################################################
  FILTER (
    ?roe >= ?avgROE &&
    ?netMargin >= ?avgMargin &&
    (!BOUND(?assetTurnover) || ?assetTurnover >= ?avgAT) &&
    (!BOUND(?debtToEquity) || ?debtToEquity <= ?avgDE)
  )
}
ORDER BY ?industry DESC(?roe)
```

---

## 3. 시계열 추이 분석

특정 기업의 재무 지표가 시간에 따라 어떻게 변화했는지 분석하여 성장 추세와 안정성을 평가합니다.

### 3.1 수익성 추이 분석

#### CQ3.1.1: 특정 기업의 ROE 추이는 어떻게 변화했는가?
**Competency Question (한글)**: 특정 기업의 ROE 추이는 어떻게 변화했는가? 지속적으로 개선되고 있는가?  
**Competency Question (English)**: How has the ROE trend changed for a specific company? Is it consistently improving?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?fy ?roe
       ((?roe - ?roePrior) AS ?roeChange)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?roe .
  
  # 전년도 ROE (변화량 계산용)
  OPTIONAL {
    ?obsROEPrior a efin:MetricObservation ;
                 efin:ofCompany ?company ;
                 efin:observesMetric efin:ROE ;
                 efin:hasFiscalYear ?fyPrior ;
                 efin:hasNumericValue ?roePrior .
    BIND (xsd:integer(str(?fy)) - 1 AS ?fyMinusOne)
    FILTER (xsd:integer(str(?fyPrior)) = ?fyMinusOne)
  }
  
  FILTER (?fy >= 2020 && ?fy <= 2024)
}
ORDER BY ?fy
```

#### CQ3.1.2: 특정 기업의 수익성 지표들(마진) 추이는 어떻게 변화했는가?
**Competency Question (한글)**: 특정 기업의 매출총이익률, 영업이익률, 순이익률 추이는 어떻게 변화했는가? 수익성 구조는 개선되고 있는가?  
**Competency Question (English)**: How have the gross margin, operating margin, and net profit margin trends changed for a specific company? Is the profitability structure improving?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?fy 
       ?grossMargin ?operatingMargin ?netMargin
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obsGross a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:GrossMargin ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?grossMargin .
  
  ?obsOp a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:OperatingMargin ;
         efin:hasFiscalYear ?fy ;
         efin:hasNumericValue ?operatingMargin .
  
  ?obsNet a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:NetProfitMargin ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?netMargin .
  
  FILTER (?fy >= 2020 && ?fy <= 2024)
}
ORDER BY ?fy
```

### 3.2 성장률 추이 분석

#### CQ3.2.1: 특정 기업의 성장률 추이는 안정적인가?
**Competency Question (한글)**: 특정 기업의 매출 성장률과 순이익 성장률 추이는 어떻게 변화했는가? 성장이 안정적인가?  
**Competency Question (English)**: How have the revenue growth rate and net income growth rate trends changed for a specific company? Is the growth stable?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?fy
       ?revenueGrowth ?netIncomeGrowth ?cfoGrowth
       ((?netIncomeGrowth - ?revenueGrowth) AS ?growthQuality)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obsRev a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:RevenueGrowthYoY ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?revenueGrowth .
  
  OPTIONAL {
    ?obsNet a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:NetIncomeGrowthYoY ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?netIncomeGrowth .
  }
  
  OPTIONAL {
    ?obsCFO a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:CFOGrowthYoY ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?cfoGrowth .
  }
  
  FILTER (?fy >= 2020 && ?fy <= 2024)
}
ORDER BY ?fy
```

### 3.3 효율성 추이 분석

#### CQ3.3.1: 특정 기업의 자산 효율성은 개선되고 있는가?
**Competency Question (한글)**: 특정 기업의 자산회전율 추이는 어떻게 변화했는가? 자산 효율성이 개선되고 있는가?  
**Competency Question (English)**: How has the asset turnover trend changed for a specific company? Is asset efficiency improving?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?fy
       ?assetTurnover ?inventoryTurnover ?receivablesTurnover
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obsAsset a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:AssetTurnover ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?assetTurnover .
  
  OPTIONAL {
    ?obsInv a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:InventoryTurnover ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?inventoryTurnover .
  }
  
  OPTIONAL {
    ?obsRec a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:ReceivablesTurnover ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?receivablesTurnover .
  }
  
  FILTER (?fy >= 2020 && ?fy <= 2024)
}
ORDER BY ?fy
```

### 3.4 추론 기반 스크리닝: 일관된 성장·수익성·현금흐름 개선 기업

#### CQ3.4.1: 성장률/마진/현금흐름 파생 계층을 이용한 장기 추세 스크리닝  
**Competency Question (한글)**: 성장률/마진/현금흐름 파생 지표 계층을 활용해, 최근 5년 동안 **매출·순이익·CFO 성장률이 전반적으로 양수이고 순이익률·ROE도 개선된 기업**만 스크리닝할 수 있는가?  
**Competency Question (English)**: Using the hierarchy of growth, margin, and cash-flow derived metrics, can we screen companies whose revenue, net income, and CFO growth rates have been mostly positive over the last 5 years and whose net margin and ROE have improved?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name
       (AVG(?revGrowth) AS ?avgRevenueGrowth)
       (AVG(?niGrowth) AS ?avgNetIncomeGrowth)
       (AVG(?cfoGrowth) AS ?avgCfoGrowth)
       (AVG(?margin) AS ?avgNetMargin)
       ((MAX(?roe) - MIN(?roe)) AS ?roeImprovement)
WHERE {
  # 성장률/마진/ROE가 모두 DerivedMetric/DerivedRatio 계층에 속함 (계층 추론)
  efin:RevenueGrowthYoY rdfs:subClassOf+ efin:DerivedRatio .
  efin:NetIncomeGrowthYoY rdfs:subClassOf+ efin:DerivedRatio .
  efin:CFOGrowthYoY rdfs:subClassOf+ efin:DerivedRatio .
  efin:NetProfitMargin rdfs:subClassOf+ efin:DerivedRatio .
  efin:ROE rdfs:subClassOf+ efin:DerivedRatio .

  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .

  ############################################################
  # 최근 5개 연도(예: 2020~2024)의 성장률/마진/ROE 관측 수집
  ############################################################
  # 매출 성장률
  ?obsRevG a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:RevenueGrowthYoY ;
           efin:hasFiscalYear ?fy ;
           efin:hasNumericValue ?revGrowth .

  # 순이익 성장률 (있으면)
  OPTIONAL {
    ?obsNIG a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:NetIncomeGrowthYoY ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?niGrowth .
  }

  # CFO 성장률 (있으면)
  OPTIONAL {
    ?obsCFOG a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:CFOGrowthYoY ;
             efin:hasFiscalYear ?fy ;
             efin:hasNumericValue ?cfoGrowth .
  }

  # 순이익률
  OPTIONAL {
    ?obsM a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:NetProfitMargin ;
          efin:hasFiscalYear ?fy ;
          efin:hasNumericValue ?margin .
  }

  # ROE
  OPTIONAL {
    ?obsROE a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:ROE ;
            efin:hasFiscalYear ?fy ;
            efin:hasNumericValue ?roe .
  }

  FILTER (?fy >= 2020 && ?fy <= 2024)
}
GROUP BY ?company ?ticker ?name
HAVING (
  # 평균 성장률이 모두 양수 또는 거의 0 이상
  AVG(?revGrowth) > 0.0 &&
  ( !BOUND(AVG(?niGrowth)) || AVG(?niGrowth) > 0.0 ) &&
  ( !BOUND(AVG(?cfoGrowth)) || AVG(?cfoGrowth) > 0.0 ) &&
  # 순이익률 평균이 양수
  ( !BOUND(AVG(?margin)) || AVG(?margin) > 0.0 ) &&
  # ROE가 기간 동안 개선(최소값 대비 최대값이 양수 차이)
  ( !BOUND(MAX(?roe)) || (MAX(?roe) - MIN(?roe)) > 0.0 )
)
ORDER BY DESC(?avgRevenueGrowth)
```

---

## 부록: 그래프 질의 vs 정규화된 RDB 질의 비교

### A. 현재 상태: “전개된(expanded)” 그래프 인스턴스 구조

현재 `efin_instances.ttl`는 다음과 같이 **이미 많은 파생 정보를 전개한 상태**로 저장되어 있습니다.

- **관측 단위 중심 구조**  
  - `efin:MetricObservation` 인스턴스가 중심이며, 각 관측은 다음을 직접 가집니다.
    - `efin:ofCompany` → 회사 인스턴스 (`efin:CIK0000...`)
    - `efin:observesMetric` → 메트릭 클래스 (`efin:ROE`, `efin:NetProfitMargin` 등)
    - `efin:hasFiscalYear`, `efin:hasQuarter`, `efin:hasNumericValue`
    - `efin:isDerived`, `efin:hasSourceType`, `efin:hasConfidence`
    - `efin:fromFiling` → `efin:Filing...`
- **파생 계보 정보가 인스턴스에 포함**  
  - `efin:computedFromMetric`를 통해 파생 관측이 어떤 기반 메트릭들(`NetIncome`, `Equity`, `Revenue`, `CFO`, `CapEx` 등)에서 나왔는지가 인스턴스 레벨에서 직접 명시됩니다.
- **클래스 계층과 제약조건은 스키마(`efin_schema.ttl`)에 있음**  
  - `BaseMetric` / `DerivedMetric` / `DerivedRatio` 계층  
  - `Company` / `Industry` / `Sector` 구조 (`inIndustry`, `inSector`)  
  - `Filing`과 `MetricObservation` 간 관계 (`fromFiling`, `containsObservation` 등, 일부는 온톨로지 상의 inverse 정의)

즉, **값 계산 자체는 미리 해 두고(ROE, 마진, 성장률 등), 그것이 무엇으로부터 나왔는지, 어떤 계층에 속하는지는 그래프 구조로 표현**된 상태입니다.

---

### B. 동일 데이터를 정규화 RDB로 옮겼을 때의 기본 그림

동일한 정보를 RDB에 정규화해서 저장한다고 가정하면, 전형적으로는 다음과 같은 스키마가 됩니다 (의사 구조):

- **차원 테이블**
  - `Company(cik, ticker, name, sic, sector_id, industry_id, ...)`
  - `Sector(id, name, ...)`
  - `Industry(id, name, sector_id, ...)`
  - `Metric(id, name, type, is_derived, base_class, ...)`
  - `Filing(id, accession, form_type, company_id, filing_date, ...)`
- **사실(관측) 테이블**
  - `Observation(id, company_id, metric_id, fiscal_year, quarter, value, is_derived, confidence, filing_id, ...)`
- **계보/관계 테이블**
  - `MetricLineage(metric_id, source_metric_id)`  
    (그래프의 `computedFromMetric`에 대응)
  - 추가로 필요 시 `CompanyIndustry`, `CompanySector` 등 연결 테이블

이 구조에서도 **단일 메트릭 조회, 단일 지표 비교, 단순 집계**는 SQL 조인으로 충분히 처리할 수 있습니다.  
예: “특정 기업의 2024년 ROE와 업계 평균 ROE 비교”는 `Observation` + `Company` + `Industry` + `Metric` 조인으로 구현 가능합니다.

---

### C. CQ 관점에서 그래프 질의 vs RDB 질의의 차이

#### 1. 계층(Hierarchy) 활용

- **그래프 (SPARQL + RDFS/OWL)**  
  - 메트릭 계층이 명시적으로 정의됨:  
    - `efin:ROE rdfs:subClassOf efin:DerivedRatio`  
    - `efin:NetProfitMargin rdfs:subClassOf efin:DerivedRatio` 등
  - CQ에서 **“모든 DerivedRatio 메트릭”** 을 가져오고 싶을 때:
    - `?metric rdfs:subClassOf+ efin:DerivedRatio .`  
    - 새 DerivedRatio 클래스를 온톨로지에만 추가하면, 기존 CQ들이 자동으로 그 메트릭까지 포함.
- **RDB (SQL)**  
  - 계층을 사용하려면 `Metric` 테이블에 `parent_metric_id` 또는 `type`/`category` 컬럼을 두고,  
    - 재귀 CTE (`WITH RECURSIVE`)나 애플리케이션 로직에서 계층을 구현해야 함.
  - “DerivedRatio 전체”를 대상으로 하는 CQ는:
    - `WHERE metric.type = 'DerivedRatio'` 식의 **명시적 카테고리 필터**에 의존하고,
    - 새 비율을 추가할 때마다 `type` 값을 올바르게 채워야 하며,
    - 계층이 깊어질수록 쿼리가 복잡해짐.

→ **그래프의 장점**:  
계층 구조가 “1급 개념”이라, **계층을 타고 올라가거나 내려가는 질의(rdfs:subClassOf+)를 스키마 레벨에서 표준화**할 수 있습니다.  
CQ 입장에서는 **“DerivedRatio 전체”**, “BaseMetric 전체” 같은 추상적인 질의를 직접 표현할 수 있고, **새 메트릭 추가 시 CQ를 거의 건드리지 않아도 됨**.

#### 2. 계보(Lineage) 활용

- **그래프**
  - 각 파생 관측은 `efin:computedFromMetric`으로 여러 기반 메트릭을 참조하여 계보를 추적 가능.
  - 예: “ROE 관측이 NetIncome과 Equity에서 실제로 계산된 기업만”:
    - `FILTER (EXISTS { ?roeObs efin:computedFromMetric efin:NetIncome } && EXISTS { ?roeObs efin:computedFromMetric efin:Equity })`
  - “이 ROE가 궁극적으로 어떤 BaseMetric들에 의존하는가?” →  
    - `computedFromMetric`을 따라가며 필요 시 애플리케이션 레벨에서 재귀적으로 추적.
- **RDB**
  - 계보는 `MetricLineage`(또는 `ObservationLineage`) 테이블에 저장하고,  
    - `JOIN` + (필요하면) 재귀 CTE로 여러 단계 의존성을 따라가야 함.
  - “NetIncome과 Equity 모두를 기반으로 하는 ROE 관측만”을 찾으려면:
    - `MetricLineage`에 대해 `GROUP BY metric_id HAVING COUNT(DISTINCT source_metric_id) ...` 같은 로직이 필요하고,
    - 계보 단계가 깊어질수록 다단계 조인/재귀 CTE가 급격히 복잡해짐.

→ **그래프의 장점**:  
**관계 자체가 1급 객체(트리플)** 이기 때문에, 계보 추적은 단순한 패턴 매칭으로 표현 가능하고,  
`computedFromMetric`를 표준화해 두면 **메트릭 계보를 일관된 CQ로 다룰 수 있습니다.**

#### 3. 구조 확장성과 CQ 유지 비용

- **그래프**
  - 새 메트릭/관계를 추가해도 스키마에 조그만 클래스를 추가하고 몇 개 트리플을 더 넣으면 끝.  
  - 기존 CQ들은 대개 **계층/관계 패턴**(`rdfs:subClassOf+`, `computedFromMetric`, `inIndustry` 등)에 의존하므로,  
    - 새 메트릭이 올바른 계층에만 붙어 있으면 자연스럽게 CQ 범위에 들어옴.
- **RDB**
  - 새 유형의 메트릭이나 관계를 다룰 때:
    - 스키마 변경(컬럼 추가, 새 테이블 추가)이 필요한 경우가 많고,
    - 기존 SQL을 수정하거나 새로운 뷰/조인을 만들어야 하는 일이 잦음.

→ **그래프의 장점**:  
**스키마/데이터 확장이 CQ에 미치는 영향이 작고, CQ 재사용성이 높음**.  
특히 “DerivedRatio 전체”, “모든 파생 성장률 지표”, “모든 레버리지 지표”처럼 **타입/계층 기반 CQ** 는  
새 지표를 추가해도 쿼리가 그대로 유지되는 경우가 많습니다.

#### 4. 다중 관계·다중 도메인 연결

- **그래프**
  - 한 엔티티(예: Company)가 Industry, Sector, Filing, Benchmark, Ranking, XBRLConcept 등  
    여러 도메인과 마음껏 연결될 수 있음 (`inIndustry`, `inSector`, `hasBenchmark`, `hasRanking`, `hasXbrlConcept` 등).
  - CQ는 이 관계들을 **필요한 만큼만 조합해서** 사용하는 식으로 자연스럽게 확장:
    - “특정 Industry에서, ROE·마진·레버리지 모두 상위인 기업 중, 10-K Filing에서 나오는 값만” 등.
- **RDB**
  - 다중 도메인 연결은 조인 테이블/외래키를 계속 추가하는 방식으로 모델링되며,  
    복잡한 질의일수록 **조인 수가 많아지고 SQL 가독성이 떨어짐**.

→ **그래프의 장점**:  
복잡한 도메인(재무 지표 + 공시 문서 + 산업 분류 + 파생 계보)을 **한 그래프 위에 자연스럽게 얹을 수 있고**,  
CQ는 “경로 패턴”만 추가하면서 점진적으로 풍부해질 수 있습니다.

---

### D. 투자 분석 관점에서 그래프의 실질적 장점 (이 프로젝트 기준)

이 프로젝트에서 그래프를 쓰는 **실질적인 이득**은 다음처럼 정리할 수 있습니다.

- **1) 메트릭 계층을 활용한 “열려 있는” 스크리닝 로직**  
  - 예를 들어, “모든 DerivedRatio 계층의 비율 지표 중,  
    수익성(마진), 효율성(회전율), 레버리지(부채비율)를 동시에 고려해 기업을 스크리닝”하는 로직은  
    - 그래프에서는 계층 + 관계 패턴(CQ4.3.1, CQ2.5.1 등)으로 한 번 정의해 두면,  
    - 새 비율이 추가돼도 자동으로 포함되거나, 아주 작게 수정하면 됩니다.
  - RDB에서는 비율 리스트를 **SQL 쿼리 안에 하드코딩**해야 하는 경우가 많고,  
    신규 지표마다 쿼리를 수정해야 할 가능성이 큽니다.

- **2) 계보 기반의 “품질 조건이 걸린” 스크리닝**  
  - 그래프에서는 “ROE가 NetIncome/Equity에서 실제로 계산된 경우만”  
    `EXISTS { ?roeObs efin:computedFromMetric efin:NetIncome }` 같은 패턴으로 쉽게 필터링할 수 있습니다.
  - 이것은 **값만 높은 기업이 아니라, 계보상으로도 신뢰할 수 있는 기업만**을 골라내는 스크리닝으로,  
    투자 의사결정에서 “이 수치가 얼마나 믿을 만한가?”를 정량적으로 반영하는 데 유용합니다.
  - RDB에서도 가능하지만, 별도의 계보 테이블과 복잡한 조인이 필요해 쿼리 복잡도가 훨씬 높습니다.

- **3) 도메인 확장성: FIBO 및 외부 온톨로지와의 정합**  
  - `efin:Company rdfs:subClassOf fibo-be:LegalEntity` 처럼,  
    이미 FIBO와 정렬된 클래스/프로퍼티가 존재하기 때문에,  
    - 향후 채권/금리/파생상품 등 FIBO의 다른 도메인과 **그래프 레벨에서 자연스럽게 연결**할 수 있습니다.
  - RDB에서는 이런 외부 온톨로지와의 정합을 보통 **문서 레벨(설명서)** 로만 유지하거나,  
    별도의 매핑 테이블을 계속 관리해야 합니다.

- **4) CQ 문서와 스키마/인스턴스가 “그대로 실행 가능한 하나의 자산”**  
  - 지금 작성한 `investment_analysis_queries.md`의 SPARQL들은  
    - `efin_schema.ttl` + `efin_instances.ttl`를 올려 둔 어떤 SPARQL 엔드포인트에서든  
      거의 그대로 실행 가능하며,  
    - 온톨로지에 새 클래스를 추가하면 CQ가 **자동으로 그 구조를 활용**할 수 있습니다.
  - 이 프로젝트의 문서(CQ)는 단순한 예시 코드가 아니라,  
    **온톨로지와 함께 진짜 “실행 가능한 투자 분석 사양(specification)”** 이 되는 것이 그래프의 가장 큰 장점 중 하나입니다.

정리하면, **지금처럼 인스턴스를 많이 전개해 둔 상태에서도**,  
계층(`rdfs:subClassOf+`)과 계보(`computedFromMetric`/`computedFromObservation`)를 적극 사용하는 CQ는  
정규화된 RDB 위의 SQL 보다 **확장성·표현력·도메인 정합성 면에서 장기적으로 훨씬 유리**합니다.  
특히, 새로운 파생 지표나 분석 아이디어를 실험하면서 “쿼리/모델을 함께 진화”시키고자 할 때,  
그래프 모델이 이 프로젝트에 잘 맞는 선택입니다.

---

## 4. 종합 평가 및 리스크 분석

여러 재무 지표를 종합하여 특정 기업의 투자 가치와 리스크를 평가합니다.

### 4.1 DuPont 분석 (ROE 분해)

#### CQ4.1.1: 특정 기업의 ROE는 어떤 요인으로 구성되어 있는가?
**Competency Question (한글)**: 특정 기업의 ROE는 수익성, 효율성, 레버리지 중 어떤 요인이 주도하는가? (DuPont 분석)  
**Competency Question (English)**: Which factor (profitability, efficiency, leverage) drives the ROE of a specific company? (DuPont Analysis)
```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?roe ?netMargin ?assetTurnover ?equityRatio
       ((?netMargin * ?assetTurnover / ?equityRatio) AS ?calculatedROE)
       ((?netMargin * ?assetTurnover / ?equityRatio) - ?roe AS ?roeDifference)
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obs1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:ROE ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?roe .
  
  ?obs2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?netMargin .
  
  ?obs3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:AssetTurnover ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?assetTurnover .
  
  ?obs4 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:EquityRatio ;
        efin:hasFiscalYear 2024 ;
        efin:hasNumericValue ?equityRatio .
}
```

### 4.2 파생 지표 계산 관계 추적 (추론 없이도 사용 가능)

#### CQ4.2.1: 특정 기업의 파생 지표는 어떤 기본 지표로부터 계산되었는가?
**Competency Question (한글)**: 특정 기업의 파생 지표는 어떤 기본 지표로부터 계산되었는가? 계산 근거를 추적할 수 있는가?  
**Competency Question (English)**: Which base metrics are used to calculate derived metrics for a specific company? Can the calculation rationale be traced?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?derivedMetric ?sourceMetric ?formula
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name .
  
  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?derivedMetric ;
       efin:hasFiscalYear 2024 ;
       efin:isDerived true ;
       efin:computedFromMetric ?sourceMetric .
  
  OPTIONAL {
    ?derivedMetric efin:hasFormulaNote ?formula .
  }
}
ORDER BY ?derivedMetric
```

### 4.3 계층 구조/계보 추론을 활용한 기업 스크리닝

#### CQ4.3.1: 동종 업계 내 고품질 수익성 & 현금창출 기업 스크리닝  
**Competency Question (한글)**: DerivedRatio 계층과 데이터 계보를 활용해, 동종 업계 내에서 **ROE와 순이익률이 업계 평균 대비 높고, 그 값이 NetIncome/Equity/Revenue/FCF 계보에 의해 뒷받침되는 기업**만 스크리닝할 수 있는가?  
**Competency Question (English)**: Using the DerivedRatio hierarchy and data lineage, can we screen companies whose ROE and net profit margin are significantly above industry averages and whose values are supported by NetIncome/Equity/Revenue/FCF observations?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name ?industry
       ?roe ?netMargin ?fcf
       ?industryAvgROE ?industryAvgMargin
WHERE {
  # 모든 회사 후보 (동종 업계 스크리닝)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .

  ######################################################################
  # 1) ROE: DerivedRatio 계층 + NetIncome/Equity 계보 조건
  ######################################################################
  # ROE 메트릭이 DerivedRatio 계층에 속함 (계층 추론 사용)
  efin:ROE rdfs:subClassOf+ efin:DerivedRatio .

  ?roeObs a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear 2024 ;
          efin:isDerived true ;
          efin:hasNumericValue ?roe ;
          efin:hasConfidence ?roeConf .

  # ROE 관측이 NetIncome, Equity 메트릭을 실제로 계보에 포함하는지 확인
  FILTER (EXISTS { ?roeObs efin:computedFromMetric efin:NetIncome } &&
          EXISTS { ?roeObs efin:computedFromMetric efin:Equity })

  ######################################################################
  # 2) 순이익률(NetProfitMargin): DerivedRatio 계층 + NetIncome/Revenue 계보 조건
  ######################################################################
  efin:NetProfitMargin rdfs:subClassOf+ efin:DerivedRatio .

  ?marginObs a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear 2024 ;
             efin:isDerived true ;
             efin:hasNumericValue ?netMargin ;
             efin:hasConfidence ?marginConf .

  FILTER (EXISTS { ?marginObs efin:computedFromMetric efin:NetIncome } &&
          EXISTS { ?marginObs efin:computedFromMetric efin:Revenue })

  ######################################################################
  # 3) FCF(FreeCashFlow): CFO / CapEx 계보 조건 (선택)
  ######################################################################
  OPTIONAL {
    ?fcfObs a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:FreeCashFlow ;
            efin:hasFiscalYear 2024 ;
            efin:isDerived true ;
            efin:hasNumericValue ?fcf .

    FILTER (EXISTS { ?fcfObs efin:computedFromMetric efin:CFO } &&
            EXISTS { ?fcfObs efin:computedFromMetric efin:CapEx })
  }

  ######################################################################
  # 4) 동종업계 벤치마크 (ROE / 순이익률 평균)
  ######################################################################
  {
    SELECT ?industry (AVG(?roeInd) AS ?industryAvgROE)
                     (AVG(?marginInd) AS ?industryAvgMargin)
    WHERE {
      ?compInd efin:inIndustry ?industry .

      ?obsRInd a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:ROE ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?roeInd .

      ?obsMInd a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:NetProfitMargin ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?marginInd .
    }
    GROUP BY ?industry
  }

  ######################################################################
  # 5) 스크리닝 조건:
  #    - ROE, 순이익률 모두 업계 평균 대비 일정 수준 이상 초과
  #    - 계보 기반 ROE/마진이고, 신뢰도도 일정 수준 이상
  ######################################################################
  FILTER (
    ?roe > ?industryAvgROE + 0.05 &&          # 업계 평균 대비 +5%p 이상
    ?netMargin > ?industryAvgMargin + 0.05 && # 업계 평균 대비 +5%p 이상
    ?roeConf >= 0.9 &&
    ?marginConf >= 0.9
  )
}
ORDER BY DESC(?roe)
```

> **설명**: 단순히 값이 높은 기업이 아니라, **(1) DerivedRatio 계층에 속하는 파생 지표**이고, **(2) NetIncome/Equity/Revenue/FCF와 같은 기본 지표 계보를 실제로 참조하며**, **(3) 업계 평균 대비 초과 수익성을 보이는 기업만** 필터링합니다. 즉, 계층 구조와 데이터 계보를 동시에 만족하는 “고품질 수익성 스크리닝”입니다.

#### CQ4.3.2: 섹터 단위 저레버리지·고커버리지 기업 스크리닝  
**Competency Question (한글)**: DerivedRatio 계층과 레버리지 관련 데이터 계보를 활용해, 특정 섹터 내에서 **부채비율(DebtToEquity)은 낮고 이자보상배수(InterestCoverage)는 높은 기업**만 스크리닝할 수 있는가?  
**Competency Question (English)**: Using the DerivedRatio hierarchy and leverage-related lineage, can we screen companies within a sector that have low debt-to-equity and high interest coverage?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?company ?ticker ?name ?sector
       ?debtToEquity ?interestCoverage
       ?sectorAvgDebtToEquity ?sectorAvgInterestCoverage
WHERE {
  # 섹터 내 모든 회사 후보 (예: Information Technology 섹터)
  ?company efin:hasTicker ?ticker ;
           efin:hasCompanyName ?name ;
           efin:inSector ?sector .
  # 필요시 특정 섹터 필터
  # FILTER (?sector = efin:SectorInformationTechnology)

  ######################################################################
  # 1) 부채비율(DebtToEquity): DerivedRatio 계층 + Debt/Equity 계보 조건
  ######################################################################
  efin:DebtToEquity rdfs:subClassOf+ efin:DerivedRatio .

  ?deObs a efin:MetricObservation ;
         efin:ofCompany ?company ;
         efin:observesMetric efin:DebtToEquity ;
         efin:hasFiscalYear 2024 ;
         efin:isDerived true ;
         efin:hasNumericValue ?debtToEquity .

  FILTER (
    EXISTS { ?deObs efin:computedFromMetric efin:LongTermDebt } ||
    EXISTS { ?deObs efin:computedFromMetric efin:ShortTermDebt } ||
    EXISTS { ?deObs efin:computedFromMetric efin:DebtCurrent }
  )
  FILTER (EXISTS { ?deObs efin:computedFromMetric efin:Equity })

  ######################################################################
  # 2) 이자보상배수(InterestCoverage): DerivedRatio 계층 + EBIT/Interest 계보 (선택)
  ######################################################################
  efin:InterestCoverage rdfs:subClassOf+ efin:DerivedRatio .

  OPTIONAL {
    ?icObs a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:InterestCoverage ;
           efin:hasFiscalYear 2024 ;
           efin:isDerived true ;
           efin:hasNumericValue ?interestCoverage .

    FILTER (EXISTS { ?icObs efin:computedFromMetric efin:InterestExpense } &&
            EXISTS { ?icObs efin:computedFromMetric efin:OperatingIncome })
  }

  ######################################################################
  # 3) 섹터 벤치마크 (부채비율/이자보상배수 평균)
  ######################################################################
  {
    SELECT ?sector (AVG(?deInd) AS ?sectorAvgDebtToEquity)
                   (AVG(?icInd) AS ?sectorAvgInterestCoverage)
    WHERE {
      ?compInd efin:inSector ?sector .

      ?obsDT a efin:MetricObservation ;
             efin:ofCompany ?compInd ;
             efin:observesMetric efin:DebtToEquity ;
             efin:hasFiscalYear 2024 ;
             efin:hasNumericValue ?deInd .

      OPTIONAL {
        ?obsIC a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:InterestCoverage ;
               efin:hasFiscalYear 2024 ;
               efin:hasNumericValue ?icInd .
      }
    }
    GROUP BY ?sector
  }

  ######################################################################
  # 4) 스크리닝 조건:
  #    - 부채비율은 섹터 평균보다 충분히 낮고
  #    - (가능하다면) 이자보상배수는 섹터 평균 이상
  ######################################################################
  FILTER (
    ?debtToEquity < ?sectorAvgDebtToEquity * 0.7 &&  # 섹터 평균의 70% 미만
    (!BOUND(?interestCoverage) || ?interestCoverage >= ?sectorAvgInterestCoverage)
  )
}
ORDER BY ?debtToEquity DESC(?interestCoverage)
```

> **설명**: 부채 관련 비율이 **DerivedRatio 계층에 속하고**, 관측 계보 상에서 실제로 LongTermDebt/ShortTermDebt/Equity, InterestExpense/OperatingIncome 등의 기본 지표에 의존하는 기업만을 대상으로, 섹터 평균 대비 **저레버리지·고커버리지 기업**을 스크리닝합니다. 이처럼 **계층 구조(비율 계층)와 데이터 계보(부채/이자 원천)** 를 동시에 활용해 투자 의사결정에 바로 쓸 수 있는 스크리닝 질의를 구성했습니다.

---

## 5. 추후 개선 방향 (현재 스키마로 불가능한 유명 분석)

다음은 널리 알려진 투자 분석 방법이지만, 현재 스키마에는 필요한 데이터가 없어 구현할 수 없는 항목들입니다.

### 5.1 밸류에이션 지표

#### ❌ P/E Ratio (주가수익비율)
**필요 데이터**: 주가(Price), 주당순이익(EPS) - EPS는 있지만 주가 데이터 없음
**공식**: P/E = 주가 / EPS
**개선 방향**: 
- 주가 데이터를 추가하는 `efin:stockPrice` DatatypeProperty 추가
- 또는 외부 주가 API와 연동하는 별도 서비스 구축

#### ❌ PEG Ratio (주가수익성장비율)
**필요 데이터**: P/E Ratio, EPS 성장률
**공식**: PEG = P/E / EPS 성장률
**개선 방향**: P/E Ratio 구현 후 가능

#### ❌ EV/EBITDA (기업가치 대 EBITDA 비율)
**필요 데이터**: 기업가치(Enterprise Value), EBITDA - EBITDA는 있지만 시가총액, 부채, 현금 데이터 필요
**공식**: EV = 시가총액 + 순부채, EV/EBITDA = EV / EBITDA
**개선 방향**:
- 시가총액(`efin:marketCap`) DatatypeProperty 추가
- 또는 주가 데이터와 발행주식수로 계산

#### ❌ Price-to-Book Ratio (P/B Ratio)
**필요 데이터**: 주가, 장부가치(BVPS) - 장부가치는 Equity/주식수로 계산 가능하지만 주가 필요
**공식**: P/B = 주가 / (자본 / 발행주식수)
**개선 방향**: 주가 데이터 추가

### 5.2 고급 리스크 지표

#### ❌ Altman Z-Score (부도 예측 모델)
**필요 데이터**: 
- 일부는 가능: Working Capital, Retained Earnings, EBIT, Sales, Total Assets
- 부족: 시가총액(Market Value of Equity)
**공식**: Z = 1.2*(WC/TA) + 1.4*(RE/TA) + 3.3*(EBIT/TA) + 0.6*(MVE/TL) + 1.0*(S/TA)
**개선 방향**: 시가총액 데이터 추가

#### ❌ Beta (시장 대비 변동성)
**필요 데이터**: 주가 수익률, 시장 수익률 (시간 시리즈 데이터)
**개선 방향**: 
- 주가 시계열 데이터 추가
- 시장 지수(예: S&P 500) 데이터 추가

### 5.3 배당 관련 지표

#### ❌ Dividend Yield (배당수익률)
**필요 데이터**: 주당배당금, 주가
**개선 방향**: 
- 배당금 데이터(`efin:dividendsPerShare`) 추가
- 주가 데이터 추가

#### ❌ Payout Ratio (배당성향)
**필요 데이터**: 배당금, 순이익
**개선 방향**: 배당금 데이터 추가

### 5.4 성장률 예측 지표

#### ❌ DCF (Discounted Cash Flow) Valuation
**필요 데이터**: 
- 현재 가능: Free Cash Flow (있음)
- 부족: 예측된 미래 FCF, 성장률 가정, 할인율(WACC)
**개선 방향**: 
- 예측 데이터 모델 추가
- WACC 계산을 위한 자본비용 데이터 추가

### 5.5 효율성 지표 확장

#### ⚠️ ROA (자산이익률) - 부분 가능
**현재 상태**: NetIncome와 Assets는 있지만, 직접 ROA 메트릭이 없음
**해결 방법**: 쿼리에서 계산 가능하지만, 파생 메트릭으로 추가 권장
```sparql
# 현재 가능한 방법 (계산)
SELECT ?company ?ticker ((?netIncome / ?assets) AS ?roa)
WHERE {
  ?obs1 efin:observesMetric efin:NetIncome ; efin:hasNumericValue ?netIncome .
  ?obs2 efin:observesMetric efin:Assets ; efin:hasNumericValue ?assets .
}
```

### 5.6 추천 개선 사항 요약

1. **주가 데이터 추가**
   - `efin:stockPrice` (DatatypeProperty)
   - `efin:marketCap` (DatatypeProperty)
   - `efin:sharesOutstanding` (이미 `DilutedShares`가 있지만 시점 데이터 필요)

2. **배당 데이터 추가**
   - `efin:dividendsPerShare` (DatatypeProperty)
   - `efin:dividendsPaid` (DatatypeProperty)

3. **추가 파생 메트릭 정의**
   - `efin:ROA` (자산이익률)
   - `efin:PERatio` (주가수익비율) - 주가 데이터 추가 후
   - `efin:PBRatio` (주가순자산비율) - 주가 데이터 추가 후

4. **시계열 데이터 지원**
   - 주가 시계열을 위한 별도 구조 고려
   - 또는 외부 API 연동

5. **예측 데이터 모델**
   - 분석가 예측 데이터를 위한 별도 클래스 구조
   - `efin:Forecast` 클래스 추가 고려

---

## 사용 방법

### SPARQL 엔드포인트 설정

본 질의문들은 SPARQL 1.1 표준을 따르며, 다음과 같은 SPARQL 엔드포인트에서 실행할 수 있습니다:

- **Apache Jena Fuseki**: `http://localhost:3030/ds/query`
- **Virtuoso**: `http://localhost:8890/sparql`
- **GraphDB**: `http://localhost:7200/repositories/efin`

### 예시 실행

```bash
# curl을 사용한 예시
curl -X POST \
  -H "Content-Type: application/sparql-query" \
  -H "Accept: application/sparql-results+json" \
  --data-binary @query1.rq \
  http://localhost:3030/ds/query
```

### 주의사항

1. **IRI 형식**: 실제 인스턴스 파일의 IRI 형식에 맞게 수정 필요
2. **함수 지원**: SPARQL 엔진에 따라 `IF`, `COALESCE` 등 함수 지원이 다를 수 있음
3. **성능**: 복잡한 쿼리는 인덱싱 및 최적화 필요
4. **데이터 완전성**: 일부 회사는 특정 메트릭이 없을 수 있으므로 `OPTIONAL` 사용 고려

---

## 참고 자료

- [SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/)
- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [재무제표 분석 기법](https://www.investopedia.com/financial-analysis-4689757)


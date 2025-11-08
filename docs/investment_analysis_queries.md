# 투자자 관점 재무 분석 질의문 가이드

## 문서 목적

본 문서는 **EFIN 온톨로지 그래프를 활용한 투자 분석 SPARQL 질의문**을 제공합니다. 특정 기업에 대한 투자 의사결정을 내리기 위한 질의문들을 정리했습니다.

**다른 문서:**
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티 등 스키마 구조 상세
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [상호 운용성 가이드](./interoperability.md): FIBO 등 표준 온톨로지와의 통합

---

본 문서는 EFIN 온톨로지 그래프를 활용하여 **특정 기업에 대한 투자 의사결정**을 내리기 위한 SPARQL 질의문들을 정리한 것입니다. 

각 질의문은 그래프의 관계를 활용하여 특정 기업의 재무 지표를 동종업계와 비교하거나, 시계열 추이를 분석하거나, 여러 지표 간의 관계를 종합적으로 평가하는 데 초점을 맞추고 있습니다.

## 목차

1. [핵심 투자 의사결정 질의 (필수 확인 항목)](#1-핵심-투자-의사결정-질의-필수-확인-항목)
2. [동종업계 비교 분석](#2-동종업계-비교-분석)
3. [시계열 추이 분석](#3-시계열-추이-분석)
4. [종합 평가 및 리스크 분석](#4-종합-평가-및-리스크-분석)
5. [추후 개선 방향 (현재 스키마로 불가능한 유명 분석)](#5-추후-개선-방향-현재-스키마로-불가능한-유명-분석)

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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry ;
           efin:inSector ?sector .
  
  # 해당 기업의 핵심 지표
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear "2024"^^xsd:gYear ;
          efin:hasNumericValue ?roe .
  
  ?obsROIC a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:ROIC ;
           efin:hasFiscalYear "2024"^^xsd:gYear ;
           efin:hasNumericValue ?roic .
  
  ?obsMargin a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear "2024"^^xsd:gYear ;
             efin:hasNumericValue ?netMargin .
  
  ?obsDebt a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:DebtToEquity ;
           efin:hasFiscalYear "2024"^^xsd:gYear ;
           efin:hasNumericValue ?debtToEquity .
  
  ?obsCurrent a efin:MetricObservation ;
              efin:ofCompany ?company ;
              efin:observesMetric efin:CurrentRatio ;
              efin:hasFiscalYear "2024"^^xsd:gYear ;
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
                 efin:hasFiscalYear "2024"^^xsd:gYear ;
                 efin:hasNumericValue ?roeInd .
      
      ?obsROICInd a efin:MetricObservation ;
                  efin:ofCompany ?compInd ;
                  efin:observesMetric efin:ROIC ;
                  efin:hasFiscalYear "2024"^^xsd:gYear ;
                  efin:hasNumericValue ?roicInd .
      
      ?obsMarginInd a efin:MetricObservation ;
                    efin:ofCompany ?compInd ;
                    efin:observesMetric efin:NetProfitMargin ;
                    efin:hasFiscalYear "2024"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name .
  
  # 2024년 데이터
  ?obsNetIncome a efin:MetricObservation ;
                efin:ofCompany ?company ;
                efin:observesMetric efin:NetIncome ;
                efin:hasFiscalYear "2024"^^xsd:gYear ;
                efin:hasNumericValue ?netIncome .
  
  ?obsAssets a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:Assets ;
             efin:hasFiscalYear "2024"^^xsd:gYear ;
             efin:hasNumericValue ?assets .
  BIND ((?netIncome / ?assets) AS ?roa)
  
  ?obsCFO a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:CFO ;
          efin:hasFiscalYear "2024"^^xsd:gYear ;
          efin:hasNumericValue ?cfo .
  
  ?obsCurrentRatio a efin:MetricObservation ;
                   efin:ofCompany ?company ;
                   efin:observesMetric efin:CurrentRatio ;
                   efin:hasFiscalYear "2024"^^xsd:gYear ;
                   efin:hasNumericValue ?currentRatio .
  
  ?obsGrossMargin a efin:MetricObservation ;
                  efin:ofCompany ?company ;
                  efin:observesMetric efin:GrossMargin ;
                  efin:hasFiscalYear "2024"^^xsd:gYear ;
                  efin:hasNumericValue ?grossMargin .
  
  ?obsAssetTurnover a efin:MetricObservation ;
                    efin:ofCompany ?company ;
                    efin:observesMetric efin:AssetTurnover ;
                    efin:hasFiscalYear "2024"^^xsd:gYear ;
                    efin:hasNumericValue ?assetTurnover .
  
  ?obsLiabilities a efin:MetricObservation ;
                  efin:ofCompany ?company ;
                  efin:observesMetric efin:Liabilities ;
                  efin:hasFiscalYear "2024"^^xsd:gYear ;
                  efin:hasNumericValue ?liabilities .
  BIND ((?liabilities / ?assets) AS ?debtRatio)
  
  # 2023년 데이터 (전년 대비 비교)
  ?obsNetIncomePrior a efin:MetricObservation ;
                     efin:ofCompany ?company ;
                     efin:observesMetric efin:NetIncome ;
                     efin:hasFiscalYear "2023"^^xsd:gYear ;
                     efin:hasNumericValue ?netIncomePrior .
  
  ?obsAssetsPrior a efin:MetricObservation ;
                  efin:ofCompany ?company ;
                  efin:observesMetric efin:Assets ;
                  efin:hasFiscalYear "2023"^^xsd:gYear ;
                  efin:hasNumericValue ?assetsPrior .
  BIND ((?netIncomePrior / ?assetsPrior) AS ?roaPrior)
  
  ?obsCurrentRatioPrior a efin:MetricObservation ;
                        efin:ofCompany ?company ;
                        efin:observesMetric efin:CurrentRatio ;
                        efin:hasFiscalYear "2023"^^xsd:gYear ;
                        efin:hasNumericValue ?currentRatioPrior .
  
  ?obsGrossMarginPrior a efin:MetricObservation ;
                       efin:ofCompany ?company ;
                       efin:observesMetric efin:GrossMargin ;
                       efin:hasFiscalYear "2023"^^xsd:gYear ;
                       efin:hasNumericValue ?grossMarginPrior .
  
  ?obsAssetTurnoverPrior a efin:MetricObservation ;
                         efin:ofCompany ?company ;
                         efin:observesMetric efin:AssetTurnover ;
                         efin:hasFiscalYear "2023"^^xsd:gYear ;
                         efin:hasNumericValue ?assetTurnoverPrior .
  
  ?obsLiabilitiesPrior a efin:MetricObservation ;
                       efin:ofCompany ?company ;
                       efin:observesMetric efin:Liabilities ;
                       efin:hasFiscalYear "2023"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name .
  
  ?obs1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:RevenueGrowthYoY ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?revenueGrowth .
  
  ?obs2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetIncomeGrowthYoY ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?netIncomeGrowth .
  
  ?obs3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?netMargin .
  
  ?obs4 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:ROE ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name .
  
  ?obs1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:CFO ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?cfo .
  
  ?obs2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetIncome ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?netIncome .
  
  ?obs3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:FreeCashFlow ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?fcf .
  
  ?obs4 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:CFOGrowthYoY ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?cfoGrowth .
  
  FILTER (?netIncome > 0)
}
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear "2024"^^xsd:gYear ;
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
                 efin:hasFiscalYear "2024"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsMargin a efin:MetricObservation ;
             efin:ofCompany ?company ;
             efin:observesMetric efin:NetProfitMargin ;
             efin:hasFiscalYear "2024"^^xsd:gYear ;
             efin:hasNumericValue ?netMargin .
  
  # 동종업계의 다른 기업들
  ?compInd efin:inIndustry ?industry .
  FILTER (?compInd != ?company)
  
  ?obsMarginInd a efin:MetricObservation ;
                efin:ofCompany ?compInd ;
                efin:observesMetric efin:NetProfitMargin ;
                efin:hasFiscalYear "2024"^^xsd:gYear ;
                efin:hasNumericValue ?marginInd .
  
  # 더 높은 순이익률을 가진 기업들
  OPTIONAL {
    ?obsMarginHigher a efin:MetricObservation ;
                     efin:ofCompany ?compHigher ;
                     efin:observesMetric efin:NetProfitMargin ;
                     efin:hasFiscalYear "2024"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsAsset a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:AssetTurnover ;
            efin:hasFiscalYear "2024"^^xsd:gYear ;
            efin:hasNumericValue ?assetTurnover .
  
  OPTIONAL {
    ?obsInv a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:InventoryTurnover ;
            efin:hasFiscalYear "2024"^^xsd:gYear ;
            efin:hasNumericValue ?inventoryTurnover .
  }
  
  OPTIONAL {
    ?obsRec a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:ReceivablesTurnover ;
            efin:hasFiscalYear "2024"^^xsd:gYear ;
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
             efin:hasFiscalYear "2024"^^xsd:gYear ;
             efin:hasNumericValue ?atInd .
      
      OPTIONAL {
        ?obsIT a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:InventoryTurnover ;
               efin:hasFiscalYear "2024"^^xsd:gYear ;
               efin:hasNumericValue ?itInd .
      }
      
      OPTIONAL {
        ?obsRT a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:ReceivablesTurnover ;
               efin:hasFiscalYear "2024"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsDebt a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:DebtToEquity ;
           efin:hasFiscalYear "2024"^^xsd:gYear ;
           efin:hasNumericValue ?debtToEquity .
  
  OPTIONAL {
    ?obsInt a efin:MetricObservation ;
            efin:ofCompany ?company ;
            efin:observesMetric efin:InterestCoverage ;
            efin:hasFiscalYear "2024"^^xsd:gYear ;
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
             efin:hasFiscalYear "2024"^^xsd:gYear ;
             efin:hasNumericValue ?dtInd .
      
      OPTIONAL {
        ?obsIC a efin:MetricObservation ;
               efin:ofCompany ?compInd ;
               efin:observesMetric efin:InterestCoverage ;
               efin:hasFiscalYear "2024"^^xsd:gYear ;
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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name ;
           efin:inIndustry ?industry .
  
  ?obsROE a efin:MetricObservation ;
          efin:ofCompany ?company ;
          efin:observesMetric efin:ROE ;
          efin:hasFiscalYear "2024"^^xsd:gYear ;
          efin:hasNumericValue ?roe .
  
  ?obsROIC a efin:MetricObservation ;
           efin:ofCompany ?company ;
           efin:observesMetric efin:ROIC ;
           efin:hasFiscalYear "2024"^^xsd:gYear ;
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
                 efin:hasFiscalYear "2024"^^xsd:gYear ;
                 efin:hasNumericValue ?roeInd .
      
      ?obsROICInd a efin:MetricObservation ;
                  efin:ofCompany ?compInd ;
                  efin:observesMetric efin:ROIC ;
                  efin:hasFiscalYear "2024"^^xsd:gYear ;
                  efin:hasNumericValue ?roicInd .
    }
    GROUP BY ?industry
  }
}
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
  ?company efin:hasTicker "AAPL" ;
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
  
  FILTER (?fy >= "2020"^^xsd:gYear && ?fy <= "2024"^^xsd:gYear)
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
  ?company efin:hasTicker "AAPL" ;
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
  
  FILTER (?fy >= "2020"^^xsd:gYear && ?fy <= "2024"^^xsd:gYear)
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
  ?company efin:hasTicker "AAPL" ;
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
  
  FILTER (?fy >= "2020"^^xsd:gYear && ?fy <= "2024"^^xsd:gYear)
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
  ?company efin:hasTicker "AAPL" ;
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
  
  FILTER (?fy >= "2020"^^xsd:gYear && ?fy <= "2024"^^xsd:gYear)
}
ORDER BY ?fy
```

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
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name .
  
  ?obs1 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:ROE ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?roe .
  
  ?obs2 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:NetProfitMargin ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?netMargin .
  
  ?obs3 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:AssetTurnover ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?assetTurnover .
  
  ?obs4 a efin:MetricObservation ;
        efin:ofCompany ?company ;
        efin:observesMetric efin:EquityRatio ;
        efin:hasFiscalYear "2024"^^xsd:gYear ;
        efin:hasNumericValue ?equityRatio .
}
```

### 4.2 파생 지표 계산 관계 추적

#### CQ4.2.1: 특정 기업의 파생 지표는 어떤 기본 지표로부터 계산되었는가?
**Competency Question (한글)**: 특정 기업의 파생 지표는 어떤 기본 지표로부터 계산되었는가? 계산 근거를 추적할 수 있는가?  
**Competency Question (English)**: Which base metrics are used to calculate derived metrics for a specific company? Can the calculation rationale be traced?

```sparql
PREFIX efin: <https://w3id.org/edgar-fin/2024#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?company ?ticker ?name ?derivedMetric ?sourceMetric ?formula
WHERE {
  # 특정 기업 지정 (예: AAPL)
  ?company efin:hasTicker "AAPL" ;
           efin:hasCompanyName ?name .
  
  ?obs a efin:MetricObservation ;
       efin:ofCompany ?company ;
       efin:observesMetric ?derivedMetric ;
       efin:hasFiscalYear "2024"^^xsd:gYear ;
       efin:isDerived true ;
       efin:computedFromMetric ?sourceMetric .
  
  OPTIONAL {
    ?derivedMetric efin:formulaNote ?formula .
  }
}
ORDER BY ?derivedMetric
```

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


## 투자 인사이트용 Company 개념 클래스 정의

이 문서는 EFIN 인스턴스(2024 + YoY 파생 지표)를 바탕으로  
GraphDB SPARQL 규칙으로 태깅할 **투자 개념 클래스**들의 정의를 정리한 것입니다.

각 클래스는 `efin:Company`의 파생 개념이며, 스키마에는 클래스 선언을 두지 않고  
실제 멤버십은 SPARQL CONSTRUCT/INSERT 규칙으로 유도됩니다.

### HighQualityCompounderCompany

- **의미**: 수익성과 성장성이 동시에 동종 업종 평균을 상회하는 고품질 컴파운더.
- **정의(비공식)**:  
  - 2024년 기준, `ROE`(efin:ROE), `ROIC`(efin:ROIC), `NetProfitMargin`(efin:NetProfitMargin), `OperatingMargin`(efin:OperatingMargin)이 동일 업종 평균 이상이고  
  - `RevenueGrowthYoY`(efin:RevenueGrowthYoY), `NetIncomeGrowthYoY`(efin:NetIncomeGrowthYoY), `CFOGrowthYoY`(efin:CFOGrowthYoY)가 0 이상 또는 동일 업종 평균 이상인 회사.

### CapitalLightCompounderCompany

- **의미**: 자본집약도가 낮으면서 자본 효율성이 높은 컴파운더.
- **정의(비공식)**:  
  - 2024년 기준, `ROIC`(efin:ROIC)와 `AssetTurnover`(efin:AssetTurnover)가 동일 업종 평균 이상이고  
  - `CapEx`(efin:CapEx) / `Revenue`(efin:Revenue) 비율은 업종 평균 이하이며  
  - `FreeCashFlow`(efin:FreeCashFlow) / `Revenue` 가 양(+)이고 업종 평균 이상인 회사.

### WideMoatFranchiseCompany

- **의미**: 장기간 높은 수익성을 유지하는 광의의 경제적 해자를 가진 프랜차이즈 기업.
- **정의(비공식)**:  
  - 2024년 기준, `GrossMargin`(efin:GrossMargin), `OperatingMargin`(efin:OperatingMargin), `NetProfitMargin`(efin:NetProfitMargin), `ROE`(efin:ROE), `ROIC`(efin:ROIC)가  
    모두 해당 업종 분포의 상위 구간(예: 상위 25% 이내)에 위치하는 회사.

### HighFreeCashFlowConversionCompany

- **의미**: 회계 이익을 현금으로 잘 전환하고 잉여현금 창출력이 높은 기업.
- **정의(비공식)**:  
  - 2024년 기준, `CFO`(efin:CFO) / `NetIncome`(efin:NetIncome) 비율이 동일 업종 평균 이상이고  
  - `FreeCashFlow`(efin:FreeCashFlow) / `NetIncome` 비율이 양(+)이며 업종 평균 이상인 회사.

### SecularGrowerLikeCompany

- **의미**: 구조적 성장주에 가까운 특성을 가진 기업.
- **정의(비공식)**:  
  - 2024년 기준, `RevenueGrowthYoY`(efin:RevenueGrowthYoY), `NetIncomeGrowthYoY`(efin:NetIncomeGrowthYoY), `CFOGrowthYoY`(efin:CFOGrowthYoY)가 모두 0 이상이며  
  - 각 지표가 동일 업종 평균 이상인 회사.

### BalancedGrowthAndProfitabilityCompany

- **의미**: 성장과 수익성이 모두 우수한 균형형 기업.
- **정의(비공식)**:  
  - 2024년 기준, `RevenueGrowthYoY`, `NetIncomeGrowthYoY`, `CFOGrowthYoY` 성장률이 모두 동일 업종 평균 이상이고  
  - 동시에 `ROE`, `NetProfitMargin`, `ROIC` 수익성 지표도 업종 평균 이상인 회사.

### ProfitableGrowthCompany

- **의미**: 매출 성장보다 이익·현금흐름 성장이 더 빠른 수익성 있는 성장 기업.
- **정의(비공식)**:  
  - 2024년 기준, `NetIncomeGrowthYoY` 또는 `CFOGrowthYoY`가 `RevenueGrowthYoY`보다 크고  
  - `NetProfitMargin`과 `ROE`가 동일 업종 평균 이상인 회사.

### CFODrivenGrowthCompany

- **의미**: 외부 차입보다 내부 영업현금흐름으로 성장이 뒷받침되는 기업.
- **정의(비공식)**:  
  - 2024년 기준, `CFOGrowthYoY`가 `RevenueGrowthYoY`보다 크고  
  - `OperatingCashFlowRatio`(efin:OperatingCashFlowRatio = CFO / CurrentLiabilities)가 동일 업종 평균 이상인 회사.

### HighEarningsQualityCompany

- **의미**: 이익의 질이 높고 일회성·조정 요인이 적은 기업.
- **정의(비공식)**:  
  - 2024년 기준, `NetIncome`과 `CFO` 차이(Accruals = NetIncome - CFO)의 절대값 또는 |Accruals|/|NetIncome| 비율이 동일 업종 평균보다 작고  
  - `CFO / NetIncome` 비율이 업종 평균 이상이며  
  - `FreeCashFlow`가 양(+)인 회사.

### QualityFactorLeaderCompany

- **의미**: 재무제표 기반 퀄리티 팩터 관점에서 동종 내 선도적인 기업.
- **정의(비공식)**:  
  - 2024년 기준, `ROE`, `ROIC`, `NetProfitMargin`, `OperatingMargin`, `FreeCashFlow/Revenue`(FreeCashFlow ÷ Revenue), `CFO/NetIncome`(CFO ÷ NetIncome) 등  
    핵심 퀄리티 지표들이 업종 또는 섹터 상위 구간에 위치하고  
  - 동시에 `DebtToEquity`(efin:DebtToEquity)가 업종 평균 이하인 회사.

> 위 정의들은 OWL 공리가 아니라 **SPARQL CONSTRUCT/INSERT 규칙**으로 구현되는 것을 전제로 합니다.  
> 스키마에는 개념 이름만 두고, 실제 멤버십은 GraphDB 규칙에서 계산하여 태깅합니다.





# 메트릭 추출 로직 문서

## 문서 목적

본 문서는 **XBRL 태그 선택 및 메트릭 추출 로직**을 상세히 설명합니다. `select_xbrl_tags.py`에서 구현된 다단계 폴백 전략과 메트릭별 추출 로직을 다룹니다.

**다른 문서:**
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티 등 스키마 구조 상세

---

본 문서는 `select_xbrl_tags.py`에서 구현된 재무 메트릭의 추출 로직을 상세히 설명합니다.

---

## 1. 개요

### 1.1 메트릭 추출 시스템 아키텍처

메트릭 추출 시스템은 **다단계 폴백 전략(Multi-tier Fallback Strategy)**을 사용하여 다양한 기업과 업종의 이질적인 XBRL 태그를 표준화된 Canonical Metric으로 변환합니다.

#### 추출 전략 계층 구조

```
1. Direct Selection (정적 후보)
   ├─ Static Candidates (CANDIDATES)
   ├─ Dynamic Mining (패턴 기반)
   ├─ Extension Hints (회사별 힌트)
   └─ Suggestions (JSONL 기반)

2. Composite Calculation (복합 계산)
   └─ 업종별 복합 수식 (COMPOSITES)

3. Derived Calculation (파생 계산)
   └─ 회계 등식 기반 (예: Assets = Liabilities + Equity)

4. Segment/Quarter Aggregation (집계)
   ├─ Segment 합산 (sum-of-segments)
   └─ Quarter 합산 (sum-of-quarters)

5. Lenient Fallback (관대한 폴백)
   └─ Tolerance 확장 + 패턴 마이닝

6. Ultimate Fallback (최종 폴백)
   └─ 날짜 제약 완화 + 모든 후보 스캔
```

### 1.2 업종 추론 메커니즘

업종은 **SIC 코드**와 **텍스트 분석**을 결합하여 추론됩니다 (`infer_industry_set()` 함수).

#### 업종 분류 체계

| SIC 범위 | 업종 태그 | 설명 |
|---------|---------|------|
| 6000-6199 | Banking, Financials | 상업은행 |
| 6200-6299 | BrokerDealer, Financials | 증권사, 거래소 |
| 6300-6499 | Insurance | 보험사 |
| 6500-6799 | REITs, RealEstate, Financials | 부동산 투자신탁 |
| 4900-4999 | Utilities | 전기/가스 공공사업 |
| 1300-1399, 2900-2999 | Energy | 석유/가스 |
| 1000-1099 | Materials | 원자재 |
| 2000-2099 | Consumer | 소비재 |
| 7300-7399 | SoftwareServices | 소프트웨어/SaaS |
| 4500-4799 | Transportation, Logistics | 운송/물류 |
| 7000-7099 | HotelsRestaurantsLeisure | 호텔/레저 |
| 4800-4899 | Media, CommunicationServices | 미디어/통신 |

#### 텍스트 기반 보강

SIC 코드 외에도 회사명, SIC 설명에서 키워드를 추출하여 업종을 보강합니다:
- "bank", "banking" → Banking, Financials
- "reit", "real estate" → REITs, RealEstate
- "oil", "gas", "petroleum" → Energy
- "software", "saas" → SoftwareServices
- 등등

### 1.3 점수 계산 체계

각 후보는 **base_score**와 **조정 점수(score_adj)**의 합으로 평가됩니다.

#### Base Score 범위

| Origin | Base Score | 설명 |
|--------|-----------|------|
| Static (일반) | 0.94 - 1.00 | 사전 정의된 표준 태그 |
| Static (업종별) | 0.90 - 0.96 | 업종 특화 태그 |
| Mined (표준) | 0.86 | 패턴 매칭으로 발견된 표준 태그 |
| Extension | 0.90 | 회사 확장 태그 (ext: prefix) |
| Suggestion | 0.945 | JSONL 제안 태그 |
| Composite | 0.88 - 0.96 | 복합 계산식 |
| Derived | 0.82 - 0.90 | 파생 계산 |

#### Score Adjustment (`score_adj()`)

```python
score_adj(form, unit, fp, has_seg, industry_hit)
```

| 요소 | 보정값 | 설명 |
|------|--------|------|
| form = "10-K" / "20-F" | +0.06 | 연간 보고서 |
| form = 기타 | -0.01 | 분기 보고서 등 |
| unit = "USD" | +0.03 | 미국 달러 |
| unit = 기타 | -0.02 | 다른 통화 |
| fp = "FY" / "CY" / "FYR" | +0.03 | 회계연도 |
| has_seg = True | -0.01 | 세그먼트 데이터 (합산 필요) |
| industry_hit = True | +0.02 | 업종 특화 태그 매칭 |

#### Tolerance 확장 패널티

날짜 매칭 실패 시 tolerance를 확장하면서 점수를 감점합니다:

| Tolerance 확장 | Penalty | 적용 메트릭 |
|---------------|---------|------------|
| +0 days | 0.00 | 기본 |
| +60 days | -0.02 | 대부분 메트릭 |
| +120 days | -0.04 | OperatingIncome |
| +150 days | -0.00 | Revenue (lenient) |
| +240 days | -0.02 | Revenue (lenient) |
| +365 days | -0.04 | Revenue (lenient) |

---

## 2. 메트릭별 상세 분석

### 2.1 Revenue (매출)

**함수**: `select_revenue()` (1114-1293행)  
**기간 유형**: Annual (Duration)  
**기본 Tolerance**: 90일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax` | 1.00 | 없음 |
| 2 | `us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax` | 0.985 | 없음 |
| 3 | `us-gaap:Revenues` | 0.975 | 없음 |
| 4 | `us-gaap:SalesRevenueNet` | 0.970 | 없음 |
| 5 | `us-gaap:NetSales` | 0.960 | 없음 |
| 6 | `us-gaap:OperatingRevenue` | 0.955 | 없음 |

#### 업종별 특화 태그

**Utilities (공공사업)**:
- `us-gaap:UtilityRevenue` (0.960)
- `us-gaap:ElectricUtilityRevenue` (0.955)
- `us-gaap:GasUtilityRevenue` (0.945)
- `us-gaap:RegulatedAndUnregulatedOperatingRevenue` (0.940)

**REITs/RealEstate**:
- `us-gaap:RealEstateRevenueNet` (0.950)
- `us-gaap:RentalRevenue` (0.945)
- `us-gaap:OperatingLeasesIncomeStatementLeaseRevenue` (0.940)

**Energy**:
- `us-gaap:OilAndGasRevenue` (0.950)
- `us-gaap:RefiningAndMarketingRevenue` (0.940)

**SoftwareServices**:
- `us-gaap:SubscriptionRevenue` (0.940)
- `us-gaap:SoftwareLicensesRevenue` (0.930)

#### Composite 전략

업종별 복합 계산식:

**Banking/Financials** (`BankRevenue_NetInterestPlusNoninterest`):
```
RevenueComparable = InterestIncomeExpenseNet + NoninterestIncome
Base Score: 0.96
```

**BrokerDealer** (`ExchangeRevenue_FeesAndData`):
```
Revenue = TransactionAndExchangeFeeRevenue + MarketDataRevenue + AccessAndCapacityFeeRevenue
Base Score: 0.92
```

**REITs/RealEstate** (`REITRevenue_RentalLeasePlusOther`):
```
Revenue = RentalRevenue + OperatingLeasesIncomeStatementLeaseRevenue 
        + ext:ResidentialRentalRevenue + ext:RentalIncome + ext:LeaseIncome
        + ext:RentalAndOtherIncome + ext:PropertyAndOtherIncome
Base Score: 0.91
```

**HotelsRestaurantsLeisure** (`CruiseRevenue_TicketPlusOnboard`):
```
Revenue = ext:PassengerTicketRevenue + ext:OnboardAndOtherRevenue
Base Score: 0.91
```

**HotelsRestaurantsLeisure** (`CasinoResortRevenue_CasinoRoomFandB`):
```
Revenue = ext:CasinoRevenue + ext:RoomRevenue + ext:FoodAndBeverageRevenue
Base Score: 0.90
```

**Media/CommunicationServices** (`MediaRevenue_AdsAffiliateLicensing`):
```
Revenue = ext:AdvertisingRevenue + ext:AffiliateRevenue + ext:LicensingAndOtherRevenue
Base Score: 0.90
```

#### Segment 합산 전략

특정 Revenue 태그는 세그먼트별 값의 합산이 허용됩니다 (`ADDITIVE_QNAMES`):

- `us-gaap:Revenues`
- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
- `us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax`
- `us-gaap:SalesRevenueNet`
- `us-gaap:NetSales`
- `us-gaap:UtilityRevenue`
- `us-gaap:ElectricUtilityRevenue`
- `us-gaap:GasUtilityRevenue`
- `us-gaap:OperatingLeasesIncomeStatementLeaseRevenue`
- `us-gaap:RealEstateRevenueNet`
- `us-gaap:OperatingRevenue`
- `us-gaap:RentalRevenue`

**Generic Segment Sum**: `us-gaap` 네임스페이스의 `*Revenue*` 패턴 태그도 세그먼트 합산을 시도합니다 (단, 제외어 없을 경우).

#### Quarter 합산 폴백

Direct/Composite 실패 시, 분기별 값을 합산:
- Q1 + Q2 + Q3 + Q4 = Annual Revenue
- 대상 태그: `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, `SalesRevenueNet`, `OperatingRevenue`

#### Lenient Fallback

Tolerance를 점진적으로 확장 (+150, +240, +365일)하여 매칭을 시도합니다.

#### Dynamic Mining

정규식 패턴으로 Revenue 관련 태그를 자동 발견:

**Include Patterns**:
- `Revenue(?:s)?$`
- `NetSales$`
- `SalesRevenue(?:Goods|Services)?Net$`
- `OperatingRevenue(?:s)?$`
- `RealEstate.*Revenue`
- `RentalRevenue$` / `RentalIncome$`
- `UtilityRevenue$`
- `OilAndGas.*Revenue`
- `SubscriptionRevenue$`
- 등등 (50+ 패턴)

**Exclude Substrings**:
- DeferredRevenue, UnearnedRevenue, Allowance, Receivable, Liability, Tax, ExciseTax, Contra, VAT, Accrual, Refund

#### Extension Hints

특정 CIK에 대한 회사별 힌트가 정의되어 있습니다 (`EXTENSION_HINTS`):
- CIK 1513761 (Cruise): `PassengerTicketRevenue`, `OnboardAndOtherRevenue`
- CIK 1174922 (Casino): `CasinoRevenue`, `RoomRevenue`, `FoodAndBeverageRevenue`
- CIK 1374310 (Exchange): `TransactionAndExchangeFeeRevenue`, `MarketDataRevenue`
- CIK 2041610 (Media): `AdvertisingRevenue`, `AffiliateRevenue`
- CIK 906107 (REIT): `ResidentialRentalRevenue`, `RentalAndOtherIncome`
- CIK 1841666 (Energy): `OilAndGasRevenue`, `CrudeOilRevenue`, `NaturalGasRevenue` 등

---

### 2.2 OperatingIncome (영업이익)

**함수**: `select_operating_income()` (1475-1653행)  
**기간 유형**: Annual (Duration)  
**기본 Tolerance**: 90일 (+60, +120일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:OperatingIncomeLoss` | 1.00 | 없음 |
| 2 | `us-gaap:EarningsBeforeInterestAndTaxes` | 0.96 | 없음 |
| 3 | `us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` | 0.94 | 없음 |
| 4 | `ifrs-full:ProfitLossFromOperatingActivities` | 0.98 | IFRS |
| 5 | `ifrs-full:ProfitLossBeforeFinanceCostsAndTax` | 0.96 | IFRS |

#### 업종별 특화 태그

**Insurance**:
- `us-gaap:UnderwritingIncomeLoss` (0.90) → OperatingIncomeComparable

**Banking/Financials**:
- `us-gaap:IncomeLossFromContinuingOperationsBeforeInterestExpenseInterestIncomeIncomeTaxesExtraordinaryItemsNoncontrollingInterestsNet` (0.90) → OperatingIncomeComparable

**REITs/RealEstate**:
- `us-gaap:RealEstateOperatingIncomeLoss` (0.92)
- `us-gaap:IncomeFromOperations` (0.91)

**일반**:
- `us-gaap:IncomeFromOperationsBeforeTax` (0.91)
- `us-gaap:OperatingEarnings` (0.90)

#### Composite 전략

**Banking/Financials/BrokerDealer** (`BankOperatingComparable_PPNRminusPLL`):
```
OperatingIncomeComparable = InterestIncomeExpenseNet + NoninterestIncome 
                           - NoninterestExpense - ProvisionForLoanLeaseAndOtherLosses
Base Score: 0.93
```

**Insurance** (`InsuranceOperatingComparable`):
```
OperatingIncomeComparable = UnderwritingIncomeLoss + NetInvestmentIncome
Base Score: 0.91
```

**일반** (`GenericOperating_GrossMinusOpex`):
```
OperatingIncome = GrossProfit - OperatingExpenses
Base Score: 0.90
```

**REITs/RealEstate** (`REITOperating_RentalRevenueMinusOperatingExpenses`):
```
OperatingIncome = RentalRevenue + OperatingLeasesIncomeStatementLeaseRevenue 
                 + ext:RentalIncome + ext:RentalAndOtherIncome
                 - OperatingExpenses - RealEstateOperatingExpenses
Base Score: 0.89
```

**REITs/RealEstate** (`REITOperating_TotalRevenueMinusOperatingExpenses`):
```
OperatingIncome = RealEstateRevenueNet + RentalRevenue + ext:RentalAndOtherIncome
                 - OperatingExpenses
Base Score: 0.88
```

#### Derived 전략

**일반 기업**:
1. **GrossProfit - OperatingExpenses** (tol+30, +60, +120)
   - Base Score: 0.90 (감점: tol+60=-0.01, tol+120=-0.02)

2. **Revenue - (CostOfRevenue + SG&A + R&D + Restructuring + Impairment)** (tol+30, +60, +120)
   - Base Score: 0.87
   - Revenue 태그 우선순위: `RevenueFromContractWithCustomerExcludingAssessedTax` → `Revenues` → `SalesRevenueNet` → `OperatingRevenue` → `OperatingLeasesIncomeStatementLeaseRevenue` → `UtilityRevenue` → `ElectricUtilityRevenue`

3. **Revenue - CostOfRevenue** (단순화 버전, tol+30, +60, +120)
   - Base Score: 0.85

**REITs 특화**:
- **REIT Revenue - OperatingExpenses** (tol+30, +60, +120)
  - Base Score: 0.82
  - Revenue 태그: `RevenueFromContractWithCustomerIncludingAssessedTax`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `RentalRevenue`, `RealEstateRevenueNet`, `OperatingLeasesIncomeStatementLeaseRevenue`, `Revenues`
  - OperatingExpenses 태그: `RealEstateOperatingExpenses`, `OperatingExpenses`, `CostsAndExpenses`, `OperatingCostsAndExpenses`

#### Ultimate Fallback

모든 날짜 제약을 완화하고 OperatingIncome 관련 태그를 스캔합니다:
- Base Score: 0.70 - (거리/365.0) * 0.1
- REITs의 경우 extension 태그도 포함: `ext:RealEstateOperatingIncome`, `ext:OperatingIncome`, `ext:IncomeFromOperations`

#### Pattern Mining Fallback (REITs)

REITs의 경우 패턴 기반 마이닝도 시도:
- `RealEstate.*Operating.*Income`
- `Operating.*Income.*RealEstate`
- `Income.*Operations`
- `Operating.*Income`
- Base Score: 0.65 - (거리/365.0) * 0.1

---

### 2.3 NetIncome (순이익)

**함수**: `select_net_income()` (1436-1473행)  
**기간 유형**: Annual (Duration)  
**기본 Tolerance**: 90일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:NetIncomeLoss` | 1.00 | 없음 |
| 2 | `us-gaap:IncomeLossIncludingPortionAttributableToNoncontrollingInterest` | 0.965 | 없음 |
| 3 | `us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic` | 0.955 | 없음 |
| 4 | `us-gaap:NetIncomeLossAttributableToParent` | 0.955 | 없음 |
| 5 | `ifrs-full:ProfitLoss` | 0.980 | IFRS |
| 6 | `us-gaap:ProfitLoss` | 0.940 | IFRS |
| 7 | `us-gaap:IncomeLossFromContinuingOperations` | 0.925 | 없음 |

#### Derived 전략

Direct 실패 시 파생 계산을 시도합니다:

**방법 1: PreTax - Tax (±Disc) - NCI** (tol+30):
```
NetIncome = IncomeBeforeIncomeTaxes 
          - IncomeTaxExpenseBenefit
          + IncomeLossFromDiscontinuedOperationsNetOfTax (if exists)
          - NetIncomeLossAttributableToNoncontrollingInterest (if exists)
Base Score: 0.90
```

**방법 2: ContOps ± Disc - NCI** (tol+30):
```
NetIncome = IncomeLossFromContinuingOperationsAfterTax
          + IncomeLossFromDiscontinuedOperationsNetOfTax (if exists)
          - NetIncomeLossAttributableToNoncontrollingInterest (if exists)
Base Score: 0.88
```

---

### 2.4 CashAndCashEquivalents (현금 및 현금성 자산)

**함수**: `select_cash_instant()` (1413-1434행)  
**기간 유형**: Instant (시점)  
**기본 Tolerance**: 120일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:CashAndCashEquivalentsAtCarryingValue` | 1.00 | 없음 |
| 2 | `us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` | 0.94 | 없음 |
| 3 | `ifrs-full:CashAndCashEquivalents` | 0.98 | IFRS |
| 4 | `us-gaap:CashAndShortTermInvestments` | 0.90 | 없음 |
| 5 | `us-gaap:CashAndDueFromBanks` | 0.90 | Banking |

#### Dynamic Mining

패턴 기반 자동 발견:
- `Cash.*(Cash)?Equivalents` (대소문자 무시)
- `CashAndShortTermInvestments`

**Origin 구분**:
- 표준 네임스페이스 (`us-gaap`, `ifrs-full` 등): origin="mined", base=0.86
- 확장 네임스페이스 (`ext:` 등): origin="extension", base=0.90

#### 선택 로직

Instant 메트릭이므로 가장 최근 날짜의 값을 선택합니다 (tolerance 내).

---

### 2.5 CFO (영업활동 현금흐름)

**함수**: `select_cfo()` (1655-1666행)  
**기간 유형**: Annual (Duration)  
**기본 Tolerance**: 90일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:NetCashProvidedByUsedInOperatingActivities` | 1.00 | 없음 |
| 2 | `us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations` | 0.96 | 없음 |
| 3 | `ifrs-full:NetCashFlowsFromUsedInOperatingActivities` | 0.98 | IFRS |

CFO는 비교적 단순한 메트릭으로, Direct 선택만 시도합니다 (Composite/Derived 없음).

---

### 2.6 Assets (자산)

**함수**: `select_assets()` (1345-1369행)  
**기간 유형**: Instant (시점)  
**기본 Tolerance**: 120일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:Assets` | 1.00 | 없음 |
| 2 | `ifrs-full:Assets` | 0.985 | IFRS |
| 3 | `us-gaap:LiabilitiesAndStockholdersEquity` | 0.92 | 없음 (대리값, 감점) |
| 4 | `ifrs-full:EquityAndLiabilities` | 0.92 | IFRS (대리값, 감점) |

#### Dynamic Mining

패턴 기반 자동 발견:
- `Assets$`
- `TotalAssets$`

**Exclude Substrings**:
- Current, Noncurrent, HeldForSale, FairValue, NetOf

#### Derived 전략

Direct 실패 시 회계 등식 기반 파생:

**Assets = Liabilities + Equity**:
```
Assets = Liabilities + StockholdersEquity
Base Score: 0.89
```

**Date Alignment**: Liabilities와 Equity의 end 날짜가 다를 경우, anchor에 더 가까운 날짜를 선택합니다.

---

### 2.7 Liabilities (부채)

**함수**: `select_liabilities()` (1371-1391행)  
**기간 유형**: Instant (시점)  
**기본 Tolerance**: 120일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:Liabilities` | 1.00 | 없음 |
| 2 | `ifrs-full:Liabilities` | 0.985 | IFRS |

#### Dynamic Mining

패턴 기반 자동 발견:
- `Liabilities$`
- `TotalLiabilities$`

**Exclude Substrings**:
- Current, Noncurrent, andStockholdersEquity, HeldForSale, FairValue

#### Derived 전략

Direct 실패 시 회계 등식 기반 파생:

**Liabilities = Assets - Equity**:
```
Liabilities = Assets - StockholdersEquity
Base Score: 0.88
```

또는:

**Liabilities = LiabilitiesAndStockholdersEquity - Equity**:
```
Liabilities = LiabilitiesAndStockholdersEquity - Equity
Base Score: 0.88
```

**Date Alignment**: Assets와 Equity의 end 날짜가 다를 경우, anchor에 더 가까운 날짜를 선택합니다.

---

### 2.8 Equity (자기자본)

**함수**: `select_equity()` (1393-1411행)  
**기간 유형**: Instant (시점)  
**기본 Tolerance**: 120일 (+60일 확장 가능)

#### 일반적 추출 전략

**Static Candidates 우선순위**:

| 순위 | XBRL 태그 | Base Score | 업종 제한 |
|------|-----------|-----------|----------|
| 1 | `us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest` | 1.00 | 없음 |
| 2 | `us-gaap:StockholdersEquity` | 0.98 | 없음 |
| 3 | `ifrs-full:Equity` | 0.98 | IFRS |

#### Dynamic Mining

패턴 기반 자동 발견:
- `StockholdersEquity(?:IncludingPortionAttributableToNoncontrollingInterest)?$`
- `Equity$`

**Exclude Substrings**:
- EquityMethod, EquitySecurities, EquityClass

#### Derived 전략

Direct 실패 시 회계 등식 기반 파생:

**Equity = Assets - Liabilities**:
```
Equity = Assets - Liabilities
Base Score: 0.88
```

또는:

**Equity = LiabilitiesAndStockholdersEquity - Liabilities**:
```
Equity = LiabilitiesAndStockholdersEquity - Liabilities
Base Score: 0.88
```

**Date Alignment**: Assets와 Liabilities의 end 날짜가 다를 경우, anchor에 더 가까운 날짜를 선택합니다.

---

## 3. 업종별 특화 패턴

### 3.1 Banking/Financials

#### Revenue 추출

**일반 태그**: 표준 Revenue 태그 사용

**Composite**: `BankRevenue_NetInterestPlusNoninterest`
```
RevenueComparable = InterestIncomeExpenseNet + NoninterestIncome
```

#### OperatingIncome 추출

**특화 태그**: 없음 (일반 태그 사용)

**Composite**: `BankOperatingComparable_PPNRminusPLL`
```
OperatingIncomeComparable = InterestIncomeExpenseNet + NoninterestIncome 
                           - NoninterestExpense - ProvisionForLoanLeaseAndOtherLosses
```

**특징**: 은행은 전통적인 OperatingIncome 개념이 없으므로, PPNR (Pre-Provision Net Revenue)에서 대출손실준비금을 차감한 값을 OperatingIncomeComparable로 사용합니다.

#### Cash 추출

**특화 태그**: `us-gaap:CashAndDueFromBanks` (0.90)

---

### 3.2 BrokerDealer (증권사/거래소)

#### Revenue 추출

**일반 태그**: 표준 Revenue 태그 사용

**Composite**: `ExchangeRevenue_FeesAndData`
```
Revenue = TransactionAndExchangeFeeRevenue + MarketDataRevenue + AccessAndCapacityFeeRevenue
```

**특징**: 거래소는 수수료 수익과 데이터 판매 수익을 합산합니다.

#### OperatingIncome 추출

**Composite**: Banking과 동일 (`BankOperatingComparable_PPNRminusPLL`)

---

### 3.3 Insurance (보험)

#### OperatingIncome 추출

**특화 태그**: `us-gaap:UnderwritingIncomeLoss` (0.90) → OperatingIncomeComparable

**Composite**: `InsuranceOperatingComparable`
```
OperatingIncomeComparable = UnderwritingIncomeLoss + NetInvestmentIncome
```

**특징**: 보험사는 보험업무 손익(Underwriting)과 투자 수익을 합산합니다.

---

### 3.4 REITs/RealEstate

#### Revenue 추출

**특화 태그**:
- `us-gaap:RealEstateRevenueNet` (0.950)
- `us-gaap:RentalRevenue` (0.945)
- `us-gaap:OperatingLeasesIncomeStatementLeaseRevenue` (0.940)

**Composite**: `REITRevenue_RentalLeasePlusOther`
```
Revenue = RentalRevenue + OperatingLeasesIncomeStatementLeaseRevenue 
        + ext:ResidentialRentalRevenue + ext:RentalIncome + ext:LeaseIncome
        + ext:RentalAndOtherIncome + ext:PropertyAndOtherIncome
```

**Extension Hints**: CIK 906107에 대한 패턴 힌트가 정의되어 있습니다.

#### OperatingIncome 추출

**특화 태그**:
- `us-gaap:RealEstateOperatingIncomeLoss` (0.92)
- `us-gaap:IncomeFromOperations` (0.91)

**Composite**:
1. `REITOperating_RentalRevenueMinusOperatingExpenses`
2. `REITOperating_TotalRevenueMinusOperatingExpenses`

**Derived**: REITs 특화 Revenue - OperatingExpenses 계산 (Base Score: 0.82)

**Ultimate Fallback**: Extension 태그 포함 (`ext:RealEstateOperatingIncome`, `ext:OperatingIncome`, `ext:IncomeFromOperations`)

**Pattern Mining**: REITs의 경우 패턴 기반 마이닝도 시도합니다.

---

### 3.5 Utilities (공공사업)

#### Revenue 추출

**특화 태그**:
- `us-gaap:UtilityRevenue` (0.960)
- `us-gaap:ElectricUtilityRevenue` (0.955)
- `us-gaap:GasUtilityRevenue` (0.945)
- `us-gaap:RegulatedAndUnregulatedOperatingRevenue` (0.940)

**특징**: 전기/가스 공공사업은 규제 수익과 비규제 수익을 구분하여 보고합니다.

#### OperatingIncome 추출

**일반 태그**: 표준 OperatingIncome 태그 사용

---

### 3.6 Energy (석유/가스)

#### Revenue 추출

**특화 태그**:
- `us-gaap:OilAndGasRevenue` (0.950)
- `us-gaap:RefiningAndMarketingRevenue` (0.940)

**Dynamic Mining**: 다양한 에너지 관련 패턴을 포함:
- `OilAndGas.*Revenue`
- `CrudeOil.*Revenue`
- `NaturalGas.*Revenue`
- `NGL.*Revenue`
- `Hydrocarbon.*Revenue`
- `Marketing.*Revenue`
- `Midstream.*Revenue`
- `Upstream.*Revenue`

**Extension Hints**: CIK 1841666 (APA 등)에 대한 상세한 패턴 힌트가 정의되어 있습니다.

#### OperatingIncome 추출

**일반 태그**: 표준 OperatingIncome 태그 사용

---

### 3.7 SoftwareServices (소프트웨어/SaaS)

#### Revenue 추출

**특화 태그**:
- `us-gaap:SubscriptionRevenue` (0.940)
- `us-gaap:SoftwareLicensesRevenue` (0.930)

**특징**: SaaS 기업은 구독 수익과 라이선스 수익을 구분합니다.

#### OperatingIncome 추출

**일반 태그**: 표준 OperatingIncome 태그 사용

---

### 3.8 HotelsRestaurantsLeisure (호텔/레저)

#### Revenue 추출

**Composite**: `CruiseRevenue_TicketPlusOnboard`
```
Revenue = ext:PassengerTicketRevenue + ext:OnboardAndOtherRevenue
```

**Composite**: `CasinoResortRevenue_CasinoRoomFandB`
```
Revenue = ext:CasinoRevenue + ext:RoomRevenue + ext:FoodAndBeverageRevenue
```

**Extension Hints**: 
- CIK 1513761 (Cruise): `PassengerTicketRevenue`, `OnboardAndOtherRevenue`
- CIK 1174922 (Casino): `CasinoRevenue`, `RoomRevenue`, `FoodAndBeverageRevenue`

#### OperatingIncome 추출

**일반 태그**: 표준 OperatingIncome 태그 사용

---

### 3.9 Media/CommunicationServices (미디어/통신)

#### Revenue 추출

**Composite**: `MediaRevenue_AdsAffiliateLicensing`
```
Revenue = ext:AdvertisingRevenue + ext:AffiliateRevenue + ext:LicensingAndOtherRevenue
```

**Extension Hints**: CIK 2041610에 대한 패턴 힌트가 정의되어 있습니다.

#### OperatingIncome 추출

**일반 태그**: 표준 OperatingIncome 태그 사용

---

### 3.10 Transportation/Logistics (운송/물류)

#### Revenue 추출

**Dynamic Mining**: `CargoAndFreightRevenue`, `Transportation.*Revenue` 패턴 포함

#### OperatingIncome 추출

**일반 태그**: 표준 OperatingIncome 태그 사용

---

## 4. 특수 케이스 처리

### 4.1 Extension 태그 처리

**Extension 태그**는 회사별 확장 네임스페이스(`ext:` prefix)를 사용하는 비표준 태그입니다.

#### 처리 방식

1. **Static Candidates**: Extension 태그는 base_score가 약간 낮습니다 (0.90-0.94).

2. **Dynamic Mining**: Extension 네임스페이스의 태그도 패턴 매칭으로 발견됩니다 (origin="extension", base=0.90).

3. **Extension Hints**: 특정 CIK에 대한 회사별 힌트가 정의되어 있습니다 (`EXTENSION_HINTS`).

4. **Composite Resolution**: Composite 정의에서 `ext:Foo` 같은 placeholder는 실제 네임스페이스로 확장됩니다:
   - 회사 확장 네임스페이스에서 먼저 검색
   - 대소문자 불일치 보정
   - 실패 시 `us-gaap`에서도 검색

#### 예시

```python
# Composite 정의
CompositeCandidate("REITRevenue_RentalLeasePlusOther",
                   [("ext:RentalIncome", 1.0), ...])

# 실제 확장 과정
# 1. 회사 네임스페이스에서 "RentalIncome" 검색
# 2. 예: "apollo:RentalIncome" 발견 → "apollo:RentalIncome" 사용
# 3. 실패 시 대소문자 보정: "apollo:rentalincome" → "apollo:RentalIncome"
# 4. 실패 시 us-gaap에서도 검색
```

### 4.2 Segment 합산 (Sum-of-Segments)

일부 Revenue 태그는 세그먼트별 값의 합산이 허용됩니다.

#### 처리 로직 (`sum_segments_if_allowed()`)

1. **화이트리스트 확인**: 태그가 `ADDITIVE_QNAMES`에 있는지 확인
2. **세그먼트별 집계**: 같은 (end, form) 조합의 세그먼트 값들을 합산
3. **Tolerance 확인**: end 날짜가 fiscal year anchor의 tolerance 내에 있는지 확인
4. **최신 값 선택**: 여러 (end, form) 조합 중 가장 최신 end 날짜 선택

#### Generic Segment Sum

`us-gaap` 네임스페이스의 `*Revenue*` 패턴 태그도 세그먼트 합산을 시도합니다 (`try_sum_of_segments_generic()`):
- "Revenue" 또는 "Revenues"가 이름에 포함
- 제외어 없음: DeferredRevenue, UnearnedRevenue, Allowance, Receivable, Liability, Tax, ExciseTax

**Base Score**: 원래 base_score - 0.012

### 4.3 Quarter 합산 (Sum-of-Quarters)

Direct/Composite 실패 시 분기별 값을 합산합니다.

#### 처리 로직 (`sum_quarter_increments()`)

1. **Q1-Q4 확인**: 같은 회계연도 내 Q1, Q2, Q3, Q4 값이 모두 있는지 확인
2. **합산**: Q1 + Q2 + Q3 + Q4 = Annual Value
3. **End 날짜**: Q4의 end 날짜 사용

**Base Score**: 0.88 + score_adj

**대상 메트릭**: Revenue (주로)

### 4.4 Date Alignment (날짜 정렬)

**Instant Balance Sheet 메트릭** (Assets, Liabilities, Equity)의 경우, 파생 계산 시 두 구성 요소의 end 날짜가 다를 수 있습니다.

#### 처리 로직 (`align_pair_instant()`, `grab_instant_best()`)

**방법 1: Anchor 거리 비교**
- 두 날짜 중 fiscal year anchor에 더 가까운 날짜를 선택
- 선택된 날짜의 unit, form, fp를 사용

**방법 2: 날짜 차이 확인**
- 두 날짜의 차이가 45일 이내면 더 가까운 날짜로 정렬
- 45일 초과면 그대로 사용

#### 예시

```python
# Assets = Liabilities + Equity
# Liabilities end: 2024-12-31 (anchor 거리: 0일)
# Equity end: 2025-01-15 (anchor 거리: 15일)
# → 선택: 2024-12-31 (더 가까움)
```

### 4.5 Tolerance 확장 전략

날짜 매칭 실패 시 tolerance를 점진적으로 확장합니다.

#### 메트릭별 Tolerance 전략

| 메트릭 | 기본 | 확장 1 | 확장 2 | 확장 3 | 확장 4 |
|--------|------|--------|--------|--------|--------|
| Revenue | 90일 | +60일 | +150일 | +240일 | +365일 |
| OperatingIncome | 90일 | +60일 | +120일 | - | - |
| NetIncome | 90일 | +60일 | - | - | - |
| CashAndCashEquivalents | 120일 | +60일 | - | - | - |
| CFO | 90일 | +60일 | - | - | - |
| Assets | 120일 | +60일 | - | - | - |
| Liabilities | 120일 | +60일 | - | - | - |
| Equity | 120일 | +60일 | - | - | - |

#### Penalty 적용

Tolerance 확장 시 점수 감점:
- +60일: -0.02
- +120일: -0.04
- +150일: 0.00 (Revenue lenient)
- +240일: -0.02 (Revenue lenient)
- +365일: -0.04 (Revenue lenient)

### 4.6 Annual vs Instant 선택

#### Annual 메트릭 (Duration)

- Revenue, OperatingIncome, NetIncome, CFO
- `pick_best_annual()` 함수 사용
- **Pass 1**: FY/CY/FYR fp 우선
- **Pass 2**: YTD Q4 (qtrs=4)
- **Pass 3**: Lenient (any fp, accept_missing_fp=True)

#### Instant 메트릭 (Point in Time)

- CashAndCashEquivalents, Assets, Liabilities, Equity
- `pick_best_instant()` 함수 사용
- 가장 최근 날짜의 값 선택 (tolerance 내)

### 4.7 Smart Pick 로직

`smart_pick()` 함수는 여러 후보 중 최적의 레코드를 선택합니다.

#### 점수 계산

```python
score = -end_distance + (5 if fp in ("FY","CY","FYR") else 0)
```

- **end_distance**: end 날짜와 fiscal year anchor의 최소 거리 (일 단위)
- **fp 보너스**: FY/CY/FYR인 경우 +5점

#### 선택 기준

1. **Tolerance 확인**: end 날짜가 tolerance 내에 있는지 확인
2. **점수 비교**: score가 높을수록 우선
3. **동점 처리**: 점수가 같으면 더 최신 end 날짜 선택

---

## 5. 요약

### 5.1 메트릭별 복잡도

| 메트릭 | 복잡도 | 주요 특징 |
|--------|--------|----------|
| Revenue | 매우 높음 | Composite 많음, Segment 합산, Quarter 합산, Lenient 폴백 |
| OperatingIncome | 높음 | Composite 많음, Derived 계산 다양, REITs 특화 |
| NetIncome | 중간 | Derived 계산 (PreTax-Tax) |
| CashAndCashEquivalents | 낮음 | Direct 선택만 |
| CFO | 낮음 | Direct 선택만 |
| Assets | 중간 | Derived 계산 (Liabilities+Equity) |
| Liabilities | 중간 | Derived 계산 (Assets-Equity) |
| Equity | 중간 | Derived 계산 (Assets-Liabilities) |

### 5.2 업종별 특화 정도

| 업종 | 특화 정도 | 주요 특화 메트릭 |
|------|----------|-----------------|
| Banking/Financials | 높음 | Revenue (Composite), OperatingIncome (Composite) |
| BrokerDealer | 중간 | Revenue (Composite) |
| Insurance | 중간 | OperatingIncome (Composite) |
| REITs/RealEstate | 매우 높음 | Revenue (Composite), OperatingIncome (Composite, Derived, Pattern Mining) |
| Utilities | 중간 | Revenue (특화 태그) |
| Energy | 중간 | Revenue (특화 태그, Extension Hints) |
| SoftwareServices | 낮음 | Revenue (특화 태그) |
| HotelsRestaurantsLeisure | 중간 | Revenue (Composite, Extension Hints) |
| Media/CommunicationServices | 중간 | Revenue (Composite, Extension Hints) |

### 5.3 폴백 전략 요약

모든 메트릭은 다음 순서로 폴백합니다:

1. **Direct Selection** (Static + Mined + Hints + Suggestions)
2. **Composite Calculation** (업종별 복합 수식)
3. **Derived Calculation** (회계 등식 기반)
4. **Aggregation** (Segment/Quarter 합산)
5. **Lenient Fallback** (Tolerance 확장)
6. **Ultimate Fallback** (날짜 제약 완화)

이러한 다단계 전략을 통해 다양한 기업과 업종의 이질적인 XBRL 태그를 표준화된 Canonical Metric으로 안정적으로 변환할 수 있습니다.


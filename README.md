# EDGAR-FIN 2024 Financial Ontology

EDGAR-FIN 2024은 SEC EDGAR의 XBRL 데이터를 표준화된 재무 온톨로지로 변환하는 프로젝트입니다. 기업별·업종별로 다른 XBRL 태그를 사용하더라도 Canonical(표준화)된 지표로 통합하여 의미적으로 일관된 재무 데이터를 제공합니다.

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [프로젝트 구조](#프로젝트-구조)
- [설치 및 설정](#설치-및-설정)
- [사용 방법](#사용-방법)
- [온톨로지 스키마](#온톨로지-스키마)
- [메트릭 추출 로직](#메트릭-추출-로직)
- [문서](#문서)
- [기여](#기여)

## 🎯 개요

### 프로젝트 목적

미국 S&P500 기업의 FY2024 재무제표 데이터를 SEC EDGAR XBRL 형식에서 추출하여, 동일한 재무지표에 대해 기업별·업종별로 다른 태그를 사용하더라도 표준화된 Canonical Metric으로 통합 표현합니다.

### 핵심 특징

- **표준화된 재무 지표**: Revenue, OperatingIncome, NetIncome, CFO, CashAndCashEquivalents, Assets, Liabilities, Equity
- **업종별 특화 처리**: Banking, REITs, Insurance, Utilities, Energy 등 업종별 특화 태그 및 복합 계산식 지원
- **다단계 폴백 전략**: Direct Selection → Composite Calculation → Derived Calculation → Aggregation → Lenient Fallback
- **OWL 온톨로지**: RDF/OWL 기반 의미 웹 표준 준수
- **재사용 온톨로지**: FIBO-BE, FinRegOnt 통합

## ✨ 주요 기능

### 1. XBRL 태그 선택 (`select_xbrl_tags.py`)

SEC EDGAR Company Facts API를 통해 XBRL 데이터를 추출하고, 다단계 전략을 사용하여 최적의 태그를 선택합니다.

**지원 메트릭**:
- Revenue (매출)
- OperatingIncome (영업이익)
- NetIncome (순이익)
- CFO (영업활동 현금흐름)
- CashAndCashEquivalents (현금 및 현금성 자산)
- Assets (자산)
- Liabilities (부채)
- Equity (자기자본)

**추출 전략**:
1. **Static Candidates**: 사전 정의된 표준 태그 (US-GAAP, IFRS)
2. **Dynamic Mining**: 패턴 기반 자동 태그 발견
3. **Composite Calculation**: 업종별 복합 계산식 (예: Revenue = RentalRevenue + OperatingLeasesRevenue)
4. **Derived Calculation**: 회계 등식 기반 파생 (예: Assets = Liabilities + Equity)
5. **Segment/Quarter Aggregation**: 세그먼트 합산, 분기 합산
6. **Lenient Fallback**: 날짜 tolerance 확장

### 2. 인스턴스 생성 (`create_instance_ttl.py`)

선택된 태그 데이터를 RDF/OWL 형식의 온톨로지 인스턴스로 변환합니다.

**생성되는 RDF 개체**:
- `efin:FinancialObservation`: 재무 관측값
- `efin:LegalEntity`: 기업 개체
- `efin:CanonicalMetric`: 표준화된 지표
- `efin:XbrlConcept`: XBRL 태그 개념
- `efin:TagMapping`: XBRL → Canonical 매핑
- `efin:Period`: 기간 (Duration/Instant)
- `efin:Currency`: 통화

## 📁 프로젝트 구조

```
edgar-finance-ontology/
├── ontology/                    # 온톨로지 파일
│   ├── efin_schema.ttl         # 스키마 정의 (클래스, 프로퍼티, 제약)
│   ├── efin_instances.ttl      # 인스턴스 데이터
│   └── catalog-v001.xml        # 온톨로지 카탈로그
├── scripts/                     # Python 스크립트
│   ├── select_xbrl_tags.py     # XBRL 태그 선택 및 추출
│   └── create_instance_ttl.py  # RDF 인스턴스 생성
├── data/                        # 데이터 파일
│   └── tags.csv                # 추출된 태그 데이터 (CSV)
├── docs/                        # 문서
│   ├── schema.md               # 온톨로지 스키마 요약
│   ├── schema_development_workflow.md  # 개발 워크플로우 (ODP 기반)
│   ├── metric_extraction_logic.md      # 메트릭 추출 로직 상세
│   └── visualization/          # 시각화 파일
│       ├── ontology_viewer.html
│       └── presentation.html
├── Makefile                     # 빌드 자동화
├── pyproject.toml              # Python 프로젝트 설정
├── requirements.txt            # Python 의존성
└── README.md                   # 이 파일
```

## 🚀 설치 및 설정

### 요구사항

- Python 3.11 이상
- `uv` 또는 `pip` (패키지 관리자)

### 설치

```bash
# uv 사용 (권장)
make setup

# 또는 pip 사용
pip install -r requirements.txt
```

### 환경 변수 설정

SEC EDGAR API 사용을 위해 User-Agent를 설정해야 합니다:

```bash
export SEC_USER_AGENT="YourApp/1.0 your-email@example.com"
```

또는 `.env` 파일에 추가:

```
SEC_USER_AGENT=YourApp/1.0 your-email@example.com
```

## 📖 사용 방법

### 기본 워크플로우

```bash
# 1. XBRL 태그 선택 및 추출
make select-tags FY=2024

# 2. RDF 인스턴스 생성
make create-instances

# 또는 한 번에 실행
make workflow
```

### 고급 사용법

#### 특정 기업만 추출

```bash
make select-tags FY=2024 TICKERS="AAPL MSFT GOOGL"
```

#### 특정 메트릭만 추출

```bash
make select-tags FY=2024 METRICS="Revenue OperatingIncome NetIncome"
```

#### CIK로 추출

```bash
make select-tags FY=2024 CIKS="320193 789019"
```

#### 디버그 모드

```bash
make select-tags FY=2024 DEBUG=1 DEBUG_FILE=debug.log
```

#### 출력 파일 지정

```bash
make select-tags FY=2024 OUT=data/my_tags.csv
make create-instances CSV=data/my_tags.csv OUT=ontology/my_instances.ttl
```

### Makefile 명령어

| 명령어 | 설명 |
|--------|------|
| `make setup` | Python 의존성 설치 |
| `make select-tags` | XBRL 태그 선택 및 추출 |
| `make create-instances` | RDF 인스턴스 생성 |
| `make workflow` | select-tags → create-instances 순차 실행 |
| `make clean` | 캐시 및 임시 파일 정리 |
| `make help` | 사용 가능한 모든 명령어 표시 |

### Python 스크립트 직접 실행

```bash
# select_xbrl_tags.py
python scripts/select_xbrl_tags.py \
    --fy 2024 \
    --use-api \
    --tickers AAPL MSFT \
    --metrics Revenue OperatingIncome \
    --fy-tol-days 120 \
    --out data/tags.csv \
    --debug

# create_instance_ttl.py
python scripts/create_instance_ttl.py \
    --csv data/tags.csv \
    --out ontology/efin_instances.ttl \
    --base https://w3id.org/edgar-fin/2024# \
    --min-confidence 0.0 \
    --import-schema https://w3id.org/edgar-fin/2024
```

## 🏗️ 온톨로지 스키마

### 핵심 클래스

| 클래스 | 설명 | 상속 |
|--------|------|------|
| `efin:FinancialObservation` | 재무 관측값 (기업·지표·기간·통화별 값) | `owl:Thing` |
| `efin:CanonicalMetric` | 표준화된 지표 (Revenue, OperatingIncome 등) | `owl:Thing` |
| `efin:XbrlConcept` | XBRL 태그 개념 (us-gaap:Revenues 등) | `owl:Thing` |
| `efin:TagMapping` | XBRL → Canonical 매핑 | `owl:Thing` |
| `efin:LegalEntity` | 기업 (법적 실체) | `fibo-be:LegalEntity` |
| `efin:RegulatoryFiling` | 규제 제출서 (10-K, 20-F 등) | `fro:RegulatoryFiling` |
| `efin:Period` | 기간 (공통 상위) | `owl:Thing` |
| `efin:DurationPeriod` | 기간형 (FY, 분기 등) | `efin:Period` |
| `efin:InstantPeriod` | 시점형 (재무상태표 날짜) | `efin:Period` |
| `efin:Currency` | 통화 (USD 등) | `owl:Thing` |
| `efin:AccountingStandard` | 회계 기준 (US-GAAP, IFRS) | `owl:Thing` |
| `efin:Industry` | 산업 분류 (SIC, GICS) | `owl:Thing` |

### 핵심 프로퍼티

| 프로퍼티 | 타입 | Domain → Range | 설명 |
|----------|------|----------------|------|
| `efin:forEntity` | Object | `FinancialObservation` → `LegalEntity` | 관측값의 기업 |
| `efin:forMetric` | Object | `FinancialObservation` → `CanonicalMetric` | 관측값의 지표 |
| `efin:hasPeriod` | Object | `FinancialObservation` → `Period` | 관측값의 기간 |
| `efin:hasCurrency` | Object | `FinancialObservation` → `Currency` | 관측값의 통화 |
| `efin:usesAccountingStandard` | Object | `FinancialObservation` → `AccountingStandard` | 회계 기준 |
| `efin:basedOnConcept` | Object | `FinancialObservation` → `XbrlConcept` | 기반 XBRL 태그 |
| `efin:normalizedAs` | Object | `FinancialObservation` → `CanonicalMetric` | 정규화 대상 지표 |
| `efin:computedFrom` | Object | `FinancialObservation` → `FinancialObservation` | 파생 계산 추적 |
| `efin:hasValue` | Datatype | `FinancialObservation` → `xsd:decimal` | 관측값 (숫자) |
| `efin:periodStart` | Datatype | `Period` → `xsd:date` | 기간 시작일 |
| `efin:periodEnd` | Datatype | `Period` → `xsd:date` | 기간 종료일 |
| `efin:fiscalYear` | Datatype | `Period` → `xsd:gYear` | 회계연도 |

### 제약 조건

- **필수 키**: `FinancialObservation`은 `forEntity`, `forMetric`, `hasPeriod`, `hasCurrency`, `usesAccountingStandard`, `hasValue` 필수
- **유일성**: 동일 (기업, 지표, 기간, 통화) 조합은 1개 관측으로 유일 (`HasKey` 제약)
- **상호배타**: `DurationPeriod`와 `InstantPeriod`는 상호 배타적
- **정의 클래스**: `RevenueObservation`, `OperatingIncomeObservation` 등은 `forMetric` 값으로 자동 분류

자세한 내용은 [`docs/schema.md`](docs/schema.md)를 참조하세요.

## 🔍 메트릭 추출 로직

각 메트릭은 다단계 폴백 전략을 사용하여 추출됩니다:

1. **Direct Selection**: 정적 후보, 동적 마이닝, 확장 힌트, 제안
2. **Composite Calculation**: 업종별 복합 수식
3. **Derived Calculation**: 회계 등식 기반 파생
4. **Aggregation**: 세그먼트/분기 합산
5. **Lenient Fallback**: 날짜 tolerance 확장
6. **Ultimate Fallback**: 날짜 제약 완화

### 업종별 특화 예시

**Banking/Financials**:
- Revenue: `InterestIncomeExpenseNet + NoninterestIncome`
- OperatingIncome: `PPNR - ProvisionForLoanLeaseAndOtherLosses`

**REITs/RealEstate**:
- Revenue: `RentalRevenue + OperatingLeasesRevenue + ext:RentalIncome`
- OperatingIncome: `RealEstateOperatingIncomeLoss` 또는 `RentalRevenue - OperatingExpenses`

**Insurance**:
- OperatingIncome: `UnderwritingIncomeLoss + NetInvestmentIncome`

자세한 내용은 [`docs/metric_extraction_logic.md`](docs/metric_extraction_logic.md)를 참조하세요.

## 📚 문서

- **[온톨로지 스키마 요약](docs/schema.md)**: 클래스, 프로퍼티, 제약 조건 요약
- **[개발 워크플로우](docs/schema_development_workflow.md)**: ODP 기반 온톨로지 개발 과정
- **[메트릭 추출 로직](docs/metric_extraction_logic.md)**: 각 메트릭의 상세 추출 전략

## 🛠️ 기술 스택

- **Python 3.11+**: 주요 프로그래밍 언어
- **RDFLib**: RDF/OWL 처리
- **Requests**: HTTP API 호출
- **BeautifulSoup4**: HTML/XML 파싱
- **PyYAML**: YAML 설정 파일 처리

---

**EDGAR-FIN 2024 Financial Ontology** - SEC EDGAR XBRL 데이터의 의미적 표준화


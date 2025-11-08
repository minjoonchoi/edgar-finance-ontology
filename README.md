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

### 2. 벤치마크 및 랭킹 계산

산업별, 섹터별, 전체 통계를 계산하고 TopN 랭킹을 생성합니다.

**벤치마크 통계**:
- 평균값, 중앙값, 최대값, 최소값
- 25백분위수, 75백분위수
- 샘플 크기

**랭킹 유형**:
- Top10, Top50, Top100 (개별 메트릭별)
- Composite Score 기반 종합 랭킹

### 3. 인스턴스 생성 (`emit_efin_ttl()`)

`select_xbrl_tags.py`의 `emit_efin_ttl()` 함수가 선택된 태그 데이터를 RDF/OWL 형식의 온톨로지 인스턴스로 변환합니다.

**생성되는 RDF 개체**:
- `efin:Company`: 기업 개체 (fibo-be:LegalEntity 상속)
- `efin:Sector`, `efin:Industry`: 섹터/산업 분류
- `efin:MetricObservation`: 재무 관측값
- `efin:Metric` (BaseMetric/DerivedMetric): 표준화된 지표
- `efin:XBRLConcept`: XBRL 태그 개념
- `efin:IndustryBenchmark`, `efin:SectorBenchmark`: 벤치마크 통계
- `efin:TopRanking`: 랭킹 데이터

## 📁 프로젝트 구조

```
edgar-finance-ontology/
├── ontology/                    # 온톨로지 파일
│   └── efin_schema.ttl         # 스키마 정의 (클래스, 프로퍼티, 제약)
├── scripts/                     # Python 스크립트
│   └── select_xbrl_tags.py     # XBRL 태그 선택, 추출 및 TTL 생성
├── data/                        # 데이터 파일
│   ├── tags_{fy}.csv           # 추출된 태그 데이터 (CSV)
│   ├── companies_{fy}.csv      # 기업 정보 (CSV)
│   ├── benchmarks_{fy}.csv     # 벤치마크 통계 (CSV)
│   ├── rankings_{fy}.csv       # 랭킹 데이터 (CSV)
│   └── instances_{fy}.ttl     # RDF/TTL 인스턴스 데이터
├── docs/                        # 문서
│   ├── schema.md               # 온톨로지 스키마 참조 문서
│   ├── comprehensive_workflow.md  # 전체 워크플로우
│   ├── schema_development_workflow.md  # 개발 워크플로우 (ODP 기반)
│   ├── metric_extraction_logic.md      # 메트릭 추출 로직 상세
│   ├── ontology_project_evaluation.md  # 프로젝트 평가
│   ├── investment_analysis_queries.md  # 투자 분석 쿼리 예시
│   ├── interoperability.md    # 상호 운용성 가이드
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
# XBRL 태그 선택, 추출 및 TTL 인스턴스 생성 (한 번에 실행)
make select-tags FY=2024

# 또는 Python 스크립트 직접 실행
python scripts/select_xbrl_tags.py \
    --fy 2024 \
    --use-api \
    --include-derived \
    --emit-ttl data/instances_2024.ttl
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
make select-tags FY=2024 \
  OUT_TAGS=data/tags_2024.csv \
  OUT_COMPANIES=data/companies_2024.csv \
  OUT_BENCHMARKS=data/benchmarks_2024.csv \
  OUT_RANKINGS=data/rankings_2024.csv \
  EMIT_TTL=data/instances_2024.ttl
```

### Makefile 명령어

| 명령어 | 설명 |
|--------|------|
| `make setup` | Python 의존성 설치 |
| `make select-tags` | XBRL 태그 선택, 추출 및 TTL 인스턴스 생성 |
| `make clean` | 캐시 및 임시 파일 정리 |
| `make help` | 사용 가능한 모든 명령어 표시 |

### Python 스크립트 직접 실행

```bash
# select_xbrl_tags.py (모든 기능 포함)
python scripts/select_xbrl_tags.py \
    --fy 2024 \
    --use-api \
    --tickers AAPL MSFT \
    --metrics Revenue OperatingIncome \
    --include-derived \
    --fy-tol-days 120 \
    --out-tags data/tags_2024.csv \
    --out-companies data/companies_2024.csv \
    --out-benchmarks data/benchmarks_2024.csv \
    --out-rankings data/rankings_2024.csv \
    --emit-ttl data/instances_2024.ttl \
    --debug
```

## 🏗️ 온톨로지 스키마

### 핵심 클래스

| 클래스 | 설명 | 상속 |
|--------|------|------|
| `efin:Company` | 기업 (법적 실체) | `fibo-be:LegalEntity` |
| `efin:Sector` | 섹터 분류 (예: Information Technology, Financials) | `owl:Thing` |
| `efin:Industry` | 산업 분류 (예: Services-Prepackaged Software) | `owl:Thing` |
| `efin:Metric` | 재무 지표 개념 (추상 클래스) | `owl:Thing` |
| `efin:BaseMetric` | 직접 추출된 기초 지표 | `efin:Metric` |
| `efin:DerivedMetric` | 계산된 파생 지표 | `efin:Metric` |
| `efin:DerivedRatio` | 비율 형태의 파생 지표 | `efin:DerivedMetric` |
| `efin:MetricObservation` | 특정 기업·기간·지표에 대한 관측값 | `owl:Thing` |
| `efin:DurationObservation` | 기간형 관측값 (periodType="duration") | `efin:MetricObservation` |
| `efin:InstantObservation` | 시점형 관측값 (periodType="instant") | `efin:MetricObservation` |
| `efin:XBRLConcept` | XBRL 태그 개념 | `owl:Thing` |
| `efin:IndustryBenchmark` | 산업별 벤치마크 통계 | `owl:Thing` |
| `efin:SectorBenchmark` | 섹터별 벤치마크 통계 | `owl:Thing` |
| `efin:TopRanking` | 상위 랭킹 (Top10, Top50, Top100) | `owl:Thing` |

### 핵심 프로퍼티

| 프로퍼티 | 타입 | Domain → Range | 설명 |
|----------|------|----------------|------|
| `efin:ofCompany` | Object | `MetricObservation` → `Company` | 관측값의 기업 |
| `efin:observesMetric` | Object | `MetricObservation` → `Metric` | 관측값의 지표 |
| `efin:inSector` | Object | `Company` → `Sector` | 기업의 섹터 |
| `efin:inIndustry` | Object | `Company` → `Industry` | 기업의 산업 |
| `efin:inSectorOf` | Object | `Industry` → `Sector` | 산업의 상위 섹터 |
| `efin:computedFromMetric` | Object | `MetricObservation` → `Metric` | 파생 계산의 입력 메트릭 |
| `efin:computedFromObservation` | Object | `MetricObservation` → `MetricObservation` | 파생 계산의 입력 관측값 |
| `efin:hasCIK` | Datatype | `Company` → `xsd:string` | SEC CIK 번호 |
| `efin:hasTicker` | Datatype | `Company` → `xsd:string` | 티커 심볼 |
| `efin:hasCompanyName` | Datatype | `Company` → `xsd:string` | 회사명 |
| `efin:hasFiscalYear` | Datatype | `MetricObservation` → `xsd:gYear` | 회계연도 |
| `efin:hasPeriodType` | Datatype | `MetricObservation` → `xsd:string` | 기간 타입 ("duration" 또는 "instant") |
| `efin:hasPeriodEnd` | Datatype | `MetricObservation` → `xsd:date` | 기간 종료일 |
| `efin:hasNumericValue` | Datatype | `MetricObservation` → `xsd:decimal` | 관측값 (숫자) |
| `efin:hasUnit` | Datatype | `MetricObservation` → `xsd:string` | 단위 (예: "USD", "ratio") |
| `efin:hasSourceType` | Datatype | `MetricObservation` → `xsd:string` | 데이터 소스 타입 |
| `efin:hasConfidence` | Datatype | `MetricObservation` → `xsd:decimal` | 신뢰도 점수 (0.0-1.0) |
| `efin:forIndustry` | Object | `IndustryBenchmark` → `Industry` | 벤치마크의 대상 산업 |
| `efin:forSector` | Object | `SectorBenchmark` → `Sector` | 벤치마크의 대상 섹터 |
| `efin:forMetric` | Object | `Benchmark/Ranking` → `Metric` | 벤치마크/랭킹의 대상 메트릭 |
| `efin:hasRanking` | Object | `Company` → `TopRanking` | 기업의 랭킹 |
| `efin:hasAverageValue` | Datatype | `Benchmark` → `xsd:decimal` | 평균값 |
| `efin:hasRankingType` | Datatype | `TopRanking` → `xsd:string` | 랭킹 유형 ("Top10", "Top50", "Top100", "Composite") |

### 제약 조건

- **필수 키**: `MetricObservation`은 `ofCompany`, `observesMetric`, `hasFiscalYear` 필수
- **유일성**: 동일 (기업, 지표, 회계연도) 조합은 1개 관측으로 유일 (`HasKey` 제약)
- **상호배타**: `BaseMetric`과 `DerivedMetric`는 상호 배타적
- **상호배타**: `DurationObservation`과 `InstantObservation`는 상호 배타적
- **함수 속성**: `ofCompany`, `observesMetric`, `hasFiscalYear`, `hasPeriodEnd`, `hasNumericValue`는 함수 속성 (단일 값)
- **전이 속성**: `computedFromObservation`은 전이 속성

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

### 스키마 및 설계 문서

- **[온톨로지 스키마 참조](docs/schema.md)**: 클래스, 프로퍼티, 제약 조건 상세 참조 문서
- **[전체 워크플로우](docs/comprehensive_workflow.md)**: 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- **[스키마 개발 과정](docs/schema_development_workflow.md)**: ODP 기반 온톨로지 개발 과정
- **[메트릭 추출 로직](docs/metric_extraction_logic.md)**: 각 메트릭의 상세 추출 전략

### 평가 및 분석 문서

- **[프로젝트 평가](docs/ontology_project_evaluation.md)**: 프로젝트 평가 기준 및 달성 사항
- **[투자 분석 쿼리](docs/investment_analysis_queries.md)**: SPARQL 쿼리 예시 및 투자 인사이트 분석 방법
- **[상호 운용성 가이드](docs/interoperability.md)**: FIBO 등 표준 온톨로지와의 통합

## 🛠️ 기술 스택

- **Python 3.11+**: 주요 프로그래밍 언어
- **RDFLib**: RDF/OWL 처리
- **Requests**: HTTP API 호출
- **BeautifulSoup4**: HTML/XML 파싱
- **PyYAML**: YAML 설정 파일 처리

---

**EDGAR-FIN 2024 Financial Ontology** - SEC EDGAR XBRL 데이터의 의미적 표준화


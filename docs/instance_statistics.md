## EFIN 인스턴스 통계 (스냅샷)

이 문서는 현재 저장된 `ontology/efin_instances.ttl` 스냅샷을 기준으로, 주요 클래스와 연도별 관측값의 대략적인 개수를 정리한 자료입니다.  
인스턴스 파일은 `scripts/select_xbrl_tags.py`를 사용해 SEC EDGAR XBRL 데이터에서 자동 생성되었습니다.

**관련 문서:**
- [스키마 참조 문서](./schema.md): 클래스, 프로퍼티, 제약 조건 등 스키마 구조 상세
- [전체 워크플로우](./comprehensive_workflow.md): 데이터 추출부터 인스턴스 생성까지의 전체 프로세스
- [계층 구조 설명서](./hierarchy-structure.md): 온톨로지의 전체 계층 구조와 설계 의도 상세 설명

---

## 1. 주요 클래스별 인스턴스 개수

`ontology/efin_instances.ttl` 전체를 스캔하여, 다음과 같이 주요 클래스별 인스턴스 수를 집계했습니다.

| 클래스 | 설명 | 개수 |
|--------|------|------|
| `efin:Company` | 기업 | 501 |
| `efin:Filing` (+ 서브클래스 `TenK`, `TenQ`, `TwentyF`, `EightK`) | Filing 계열 전체 | 745 |
| `efin:DurationObservation` | 기간형 관측값 | 13,128 |
| `efin:InstantObservation` | 시점형 관측값 | 5,081 |
| `efin:IndustryBenchmark` | 산업 벤치마크 | 806 |
| `efin:SectorBenchmark` | 섹터 벤치마크 | 108 |
| `efin:TopRanking` | 랭킹 인스턴스 | 153,597 |
| `efin:Unit` | 단위 인스턴스 | 7 |
| `efin:Currency` | 통화 인스턴스 | 1 |
| `efin:XBRLConcept` | XBRL 개념 | 40 |

관측값 총합은 `DurationObservation + InstantObservation = 18,209`개이며, 이는 아래 연도별 분포와도 일치합니다.

---

## 2. 회계연도별 관측값 분포

`efin:hasFiscalYear` 값을 기준으로 관측값 개수를 집계했습니다.

| 회계연도 (`hasFiscalYear`) | 관측값 개수 |
|---------------------------|-------------|
| 2024 | 18,209 |

현재 스냅샷은 2024 회계연도 데이터에 집중되어 있으며, 향후 다른 연도 데이터가 추가되면 이 표를 확장할 수 있습니다.

---

## 3. 스키마 설계와의 관계

- `MetricObservation`는 스키마에서 (ofCompany, observesMetric, hasFiscalYear, hasQuarter) 복합 키로 고유하게 식별되도록 설계되어 있습니다.  
  위 통계는 이 설계에 따라 생성된 18,209개의 관측값이 실제로 존재함을 보여줍니다.

- `IndustryBenchmark` / `SectorBenchmark` / `TopRanking` 인스턴스 수는, 각 산업·섹터·메트릭·연도 조합에 대해 통계와 랭킹이 폭넓게 생성되고 있음을 의미합니다.  
  예를 들어, `TopRanking` 15만 건 이상은 대부분 (산업/섹터/전체) × (메트릭) × (랭킹 유형) × (기업) 조합에서 나온 결과입니다.

- `Unit` / `Currency` / `XBRLConcept` 인스턴스 수는, 스키마에서 정의한 단위·통화·XBRL 개념 계층과 실제 관측값 간의 연결( `hasUnit`, `hasCurrency`, `hasXbrlConcept` )이 비교적 작은 폐쇄 집합 위에서 이루어진다는 점을 보여줍니다.

---

## 4. 재현 방법

동일한 통계를 재현하려면, 동일한 데이터 소스와 스크립트 옵션으로 인스턴스 파일을 재생성한 뒤, 다음과 유사한 Python 스니펫으로 TTL 파일을 스캔하면 됩니다.

```python
from collections import Counter
from pathlib import Path

path = Path("ontology/efin_instances.ttl")
cls_counts = Counter()
year_counts = Counter()

with path.open() as f:
    for line in f:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("efin:") and " a efin:" in s:
            if " a efin:Company" in s:
                cls_counts["Company"] += 1
            if " a efin:DurationObservation" in s:
                cls_counts["DurationObservation"] += 1
            if " a efin:InstantObservation" in s:
                cls_counts["InstantObservation"] += 1
            # ... (다른 클래스도 동일 패턴으로 카운트)
        if "efin:hasFiscalYear" in s:
            parts = s.split()
            for i, p in enumerate(parts):
                if p == "efin:hasFiscalYear" and i + 1 < len(parts):
                    val = parts[i + 1].rstrip(" ;.")
                    try:
                        year_counts[int(val)] += 1
                    except ValueError:
                        pass
```

보다 세부적인 통계(산업/섹터별 벤치마크 개수, 특정 메트릭 기준 랭킹 분포 등)가 필요하면, 위 스니펫을 확장하거나 SPARQL/OWLReasoner를 활용할 수 있습니다.



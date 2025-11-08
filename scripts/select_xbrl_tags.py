#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
select_xbrl_tags_full.py  (모든 기능 포함 롱버전)
----------------------------------------------------------------
WHAT'S NEW vs. 이전 롱버전
- CSV 스키마 원복(tags.csv/companies.csv)
- Growth 4종(RevenueGrowthYoY, NetIncomeGrowthYoY, CFOGrowthYoY, AssetGrowthRate) 전용 개선:
  (1) direct-growth(비율/퍼센트) 우선 사용
  (2) direct-growth가 '절대증가액(USD)'이면 전년도 값으로 나눠 '비율'로 정규화
  (3) 전년도 값이 없던 기업은 FY-1에도 기존 선택로직(관용 tol 확대, 분기/세그먼트 보조) 반복 적용하여 결측 보완
  (4) 10-Q 활용 시 reason/confidence에 반영
- 나머지 메트릭 로직은 '그대로 유지'

USAGE (예)
  export SEC_USER_AGENT="MyApp/1.0 you@org.com"
  python select_xbrl_tags_full.py --fy 2024 --use-api --limit 50 \
    --out-tags data/tags_2024.csv --out-companies data/companies_2024.csv \
    --include-derived --emit-ttl data/instances_2024.ttl \
    --debug --debug-file logs/debug.log
"""
from __future__ import annotations
import os, re, csv, math, json, argparse, pathlib, sys, time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import tempfile
import shutil
import dotenv

dotenv.load_dotenv()

try:
    import requests
except Exception:
    requests = None

# ================= RDF/TTL 내보내기 (인스턴스만) =================
def _ttl_escape(s: str) -> str:
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"')

def _iri_safe(s: str) -> str:
    import re as _re
    return _re.sub(r"[^A-Za-z0-9._-]", "-", s or "")

def _iri_camel_case(s: str) -> str:
    """
    문자열을 CamelCase로 변환하여 IRI-safe하게 만듦.
    하이픈, 공백, 언더스코어를 제거하고 각 단어의 첫 글자를 대문자로 변환.
    예: "Information Technology" -> "InformationTechnology"
        "Services-Prepackaged Software" -> "ServicesPrepackagedSoftware"
        "Top10" -> "Top10"
    """
    if not s:
        return ""
    import re as _re
    # 특수 문자를 공백으로 변환
    s = _re.sub(r"[^A-Za-z0-9]", " ", s)
    # 단어로 분리하고 각 단어의 첫 글자를 대문자로 변환
    words = s.split()
    if not words:
        return ""
    # 첫 단어는 그대로, 나머지는 첫 글자만 대문자
    result = words[0].capitalize()
    for word in words[1:]:
        result += word.capitalize()
    return result

def _parse_computed_from(computed_from: str) -> List[str]:
    """
    computed_from 문자열을 파싱하여 메트릭 이름 리스트 반환
    예: "Revenue(cur),Revenue(prior)" -> ["Revenue"]
         "NetIncome;Revenue" -> ["NetIncome", "Revenue"]
         "direct-growth" -> []
    """
    if not computed_from or computed_from == "direct-growth":
        return []
    
    # 쉼표나 세미콜론으로 분리
    parts = re.split(r'[,;]', computed_from)
    metrics = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # "(cur)", "(prior)" 같은 접미사 제거
        part = re.sub(r'\([^)]*\)', '', part).strip()
        if part and part not in metrics:
            metrics.append(part)
    return metrics

def emit_efin_ttl(
    companies: List[dict],
    observations: List[dict],
    outfile: str,
    benchmarks: List[dict] = None,
    rankings: List[dict] = None,
    include_industry_scope: bool = False,
    include_sector_scope: bool = False,
):
    """
    스키마(ttl)는 입력으로 받는 외부 파일을 사용하고, 여기서는 '인스턴스'만 생성한다.
    prefix는 예시 네임스페이스(efin:)로 고정. 필요시 외부에서 prefix 매핑.
    
    efin_schema.ttl 기준으로:
    - Sector/Industry를 인스턴스로 생성하고 ObjectProperty로 연결
    - computed_from를 파싱하여 computedFromMetric으로 구조화
    - 벤치마크 및 랭킹 인스턴스 생성
    """
    # 인스턴스 파일은 스키마를 import하므로 최소한의 prefix만 선언
    # 스키마에서 정의된 모든 prefix는 스키마 import를 통해 사용 가능
    prefixes = [
        '@prefix efin: <https://w3id.org/edgar-fin/2024#> .',
        '@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .',
        '@prefix owl:  <http://www.w3.org/2002/07/owl#> .',
        '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .',
    ]
    lines = []
    lines.append("# select_xbrl_tags_full.py에 의해 자동 생성된 인스턴스")
    lines.append("# 이 파일은 efin_schema.ttl을 import하여 스키마의 클래스와 속성을 사용합니다.")
    lines.extend(prefixes)
    lines.append("")
    # 인스턴스 파일을 별도 온톨로지로 선언하고 스키마를 import
    lines.append("#################################################################")
    lines.append("# Ontology Header for Instances")
    lines.append("#################################################################")
    lines.append("")
    lines.append("<https://w3id.org/edgar-fin/2024/instances>")
    lines.append("  a owl:Ontology ;")
    lines.append("  rdfs:label \"EFIN Financial Instances\"@en ;")
    lines.append("  rdfs:comment \"EFIN 재무 온톨로지의 인스턴스 데이터. 스키마 온톨로지에서 정의된 클래스와 속성을 사용하여 실제 재무 데이터를 표현함. 스키마의 모든 prefix와 import는 스키마 import를 통해 상속됨.\"@ko ;")
    lines.append("  owl:imports <https://w3id.org/edgar-fin/2024#> .")
    lines.append("")

    # Sector/Industry 인스턴스 추적 (중복 방지)
    sectors_seen: Set[str] = set()
    industries_seen: Set[str] = set()
    industry_sector_map: Dict[str, str] = {}  # industry -> sector
    
    # Unit 인스턴스 추적 (중복 방지)
    units_seen: Set[str] = set()
    currencies_seen: Set[str] = set()
    
    # XBRLConcept 인스턴스 추적 (중복 방지)
    xbrl_concepts_seen: Dict[str, dict] = {}  # qname -> {iri, namespace}

    # 회사들
    for c in companies:
        cik = str(c.get("cik","")).zfill(10)
        sym = (c.get("symbol","") or "").upper()
        name = c.get("name","") or c.get("companyName","")
        sector = c.get("sector","").strip()
        industry = c.get("industry","").strip()
        sic = c.get("sic","")
        sic_desc = c.get("sic_description","")
        fye = c.get("fye","")

        # CIK는 EDGAR 상장사 데이터에서 항상 존재하도록 가정하므로,
        # fallback인 efin:Company-... IRI 분기는 제거하고 CIK 기반 IRI만 사용
        comp_iri = f"efin:CIK{cik}"
        lines.append(f"{comp_iri} a efin:Company ;")
        if cik:
            lines.append(f'  efin:hasCIK "{cik}" ;')
        if sym:
            lines.append(f'  efin:hasTicker "{_ttl_escape(sym)}" ;')
        if name:
            lines.append(f'  efin:hasCompanyName "{_ttl_escape(name)}" ;')
        if sic:
            lines.append(f'  efin:hasSIC "{_ttl_escape(str(sic))}" ;')
        if sic_desc:
            lines.append(f'  efin:hasSICDescription "{_ttl_escape(sic_desc)}" ;')
        if fye:
            lines.append(f'  efin:hasFiscalYearEnd "{_ttl_escape(fye)}" ;')
        
        # Sector/Industry를 ObjectProperty로 연결 (인스턴스는 나중에 생성)
        if sector:
            sector_iri = f"efin:Sector{_iri_camel_case(sector)}"
            if sector not in sectors_seen:
                sectors_seen.add(sector)
            lines.append(f"  efin:inSector {sector_iri} ;")
        
        if industry:
            industry_iri = f"efin:Industry{_iri_camel_case(industry)}"
            if industry not in industries_seen:
                industries_seen.add(industry)
                # Industry-Sector 관계 저장 (나중에 출력)
                if sector:
                    industry_sector_map[industry] = sector
            lines.append(f"  efin:inIndustry {industry_iri} ;")
        
        lines[-1] = lines[-1].rstrip(" ;")
        lines.append(".")

    # 전체 벤치마크/랭킹을 위한 Sector-All 인스턴스 필요 여부 확인
    needs_sector_all = False
    if benchmarks:
        for b in benchmarks:
            if not b.get("industry", "").strip() and not b.get("sector", "").strip():
                needs_sector_all = True
                break
    if not needs_sector_all and rankings:
        for r in rankings:
            if not r.get("industry", "").strip() and not r.get("sector", "").strip():
                needs_sector_all = True
                break
    
    # Sector 인스턴스 생성
    if sectors_seen or needs_sector_all:
        lines.append("")
        for sector in sorted(sectors_seen):
            sector_iri = f"efin:Sector{_iri_camel_case(sector)}"
            lines.append(f"{sector_iri} a efin:Sector .")
        
        # 전체 벤치마크/랭킹을 위한 Sector-All 인스턴스 생성
        if needs_sector_all:
            lines.append("efin:SectorAll a efin:Sector .")

    # Industry 인스턴스 생성 및 Industry-Sector 관계 설정
    if industries_seen:
        lines.append("")
        for industry in sorted(industries_seen):
            industry_iri = f"efin:Industry{_iri_camel_case(industry)}"
            lines.append(f"{industry_iri} a efin:Industry .")
            if industry in industry_sector_map:
                sector = industry_sector_map[industry]
                sector_iri = f"efin:Sector{_iri_camel_case(sector)}"
                lines.append(f"{industry_iri} efin:inSectorOf {sector_iri} .")

    # 관측값들 (메트릭 수준)
    lines.append("")
    for o in observations:
        cik = str(o.get("cik","")).zfill(10)
        fy = str(o.get("fy",""))
        metric = o.get("metric","")
        end = o.get("end","")
        period_type = o.get("period_type","")
        is_derived = str(o.get("is_derived","")).lower() in ("1","true","yes")
        unit = o.get("unit","")
        value = o.get("value","")
        form = o.get("form","")
        accn = o.get("accn","")
        source_type = o.get("source_type","")
        selected_tag = o.get("selected_tag","")
        composite_name = o.get("composite_name","")
        reason = o.get("reason","")
        confidence = o.get("confidence","")
        components = o.get("components","")  # JSON 텍스트
        computed_from = o.get("computed_from","")

        # 필수 속성 검증: 스키마 제약에 따라 필수 속성이 없으면 건너뛰기
        if not cik or not metric or not fy or not period_type or str(value) == "":
            continue  # 필수 속성이 없으면 이 관측값은 건너뛰기

        # periodType 검증: 스키마 제약에 따라 "duration" 또는 "instant"만 허용
        if period_type not in ("duration", "instant"):
            continue  # 유효하지 않은 period_type은 스키마 제약 위반

        # numericValue 타입 검증: 스키마에서 xsd:decimal로 정의되어 있으므로 숫자로 변환 가능한지 확인
        try:
            v = float(value)
        except Exception:
            continue  # 숫자로 변환 실패 시 스키마 제약 위반이므로 관측값을 건너뜀

        obs_end_key = end or "NA"
        obs_id_core = f"{cik}-{fy}-{metric}-{obs_end_key}"
        obs_iri = f"efin:obs-{_iri_safe(obs_id_core)}"

        # 관측 타입: MetricObservation만 명시하고,
        # hasPeriodType 값("duration"/"instant")에 따라
        # OWL 정의 클래스(DurationObservation/InstantObservation)로 reasoner가 분류하도록 함.
        lines.append(f"{obs_iri} a efin:MetricObservation ;")
        
        # 필수 속성: ofCompany (항상 존재)
        lines.append(f"  efin:ofCompany efin:CIK{cik} ;")
        
        # 필수 속성: observesMetric (검증 완료)
        lines.append(f"  efin:observesMetric efin:{_iri_safe(metric)} ;")
        
        # 필수 속성: hasFiscalYear (검증 완료, Key 제약에 포함)
        # 스키마에서는 xsd:integer로 정의 (HermiT OWL 2 datatype map 호환)
        lines.append(f"  efin:hasFiscalYear {int(fy)} ;")
        
        # 필수 속성: periodType (검증 완료)
        lines.append(f'  efin:hasPeriodType "{_ttl_escape(period_type)}" ;')
        
        # periodEnd: 선택적 (스키마는 xsd:dateTime, 인스턴스는 00:00:00 기준으로 기록)
        if end:
            # end는 YYYY-MM-DD 형식으로 가정
            lines.append(f'  efin:hasPeriodEnd "{_ttl_escape(end)}T00:00:00"^^xsd:dateTime ;')
        
        # hasQuarter: 분기 정보 처리 (선택적)
        # form이 "10-Q"이고 end date에서 분기를 추론 가능한 경우 설정
        quarter = None
        if form and "10-Q" in form.upper() and end:
            try:
                # end date에서 월 추출하여 분기 결정
                end_date = parse_date(end)
                if end_date:
                    month = end_date.month
                    if 1 <= month <= 3:
                        quarter = 1
                    elif 4 <= month <= 6:
                        quarter = 2
                    elif 7 <= month <= 9:
                        quarter = 3
                    elif 10 <= month <= 12:
                        quarter = 4
            except Exception:
                pass
        if quarter is not None:
            lines.append(f"  efin:hasQuarter {quarter} ;")
        
        # Unit 인스턴스 생성 및 연결 (ObjectProperty)
        if unit:
            unit_iri = f"efin:Unit{_iri_camel_case(unit)}"
            if unit not in units_seen:
                units_seen.add(unit)
            lines.append(f"  efin:hasUnit {unit_iri} ;")
            
            # 통화 단위인 경우 Currency 인스턴스도 생성
            unit_upper = unit.upper()
            if unit_upper in ("USD", "EUR", "KRW", "JPY", "GBP", "CNY", "AUD", "CAD", "CHF", "HKD", "SGD"):
                currency_iri = f"efin:Currency{unit_upper}"
                if unit_upper not in currencies_seen:
                    currencies_seen.add(unit_upper)
                lines.append(f"  efin:hasCurrency {currency_iri} ;")
        
        # 필수 속성: numericValue (검증 완료, 이미 숫자로 변환됨)
        # 스키마는 xsd:double이므로 명시적으로 double 타입 리터럴로 기록
        lines.append(f'  efin:hasNumericValue "{v}"^^xsd:double ;')
        
        # isDerived: 선택적 불린값
        if is_derived:
            lines.append(f"  efin:isDerived true ;")
        elif o.get('is_derived',"") != "":
            lines.append(f"  efin:isDerived false ;")
        
        # XBRLConcept 인스턴스 생성 및 연결
        if selected_tag:
            qname = selected_tag.strip()
            if qname and qname not in xbrl_concepts_seen:
                # QName에서 namespace 추출
                namespace = ""
                if ":" in qname:
                    prefix = qname.split(":")[0]
                    # 일반적인 namespace 매핑
                    namespace_map = {
                        "us-gaap": "http://fasb.org/us-gaap/",
                        "ifrs-full": "http://xbrl.ifrs.org/taxonomy/",
                        "dei": "http://xbrl.sec.gov/dei/",
                        "srt": "http://fasb.org/srt/"
                    }
                    namespace = namespace_map.get(prefix, f"http://example.org/{prefix}/")
                
                concept_iri = f"efin:XBRLConcept{_iri_safe(qname)}"
                xbrl_concepts_seen[qname] = {
                    "iri": concept_iri,
                    "namespace": namespace
                }
            
            if qname in xbrl_concepts_seen:
                concept_iri = xbrl_concepts_seen[qname]["iri"]
                lines.append(f"  efin:hasXbrlConcept {concept_iri} ;")
        
        # 나머지 optional 속성들 (슬림 TTL: 핵심 프로퍼티만 유지)
        if source_type:
            lines.append(f'  efin:hasSourceType "{_ttl_escape(source_type)}" ;')
        # selected_tag, reason, confidence, components 등은 TTL에서 제외 (CSV에만 유지)
        
        # computed_from 파싱하여 computedFromMetric으로 구조화
        # 스키마에 정의된 메트릭만 참조하도록 검증
        if computed_from and is_derived:
            parsed_metrics = _parse_computed_from(computed_from)
            # 스키마에 정의된 메트릭만 사용 (TotalDebt, Debt, Cash 등은 스키마에 없으므로 제외)
            # 실제로는 스키마를 파싱하여 검증해야 하지만, 여기서는 일반적인 메트릭 이름만 허용
            valid_metrics = [
                "Revenue", "NetIncome", "CFO", "GrossProfit", "EPSDiluted", "CapEx",
                "InterestExpense", "DepAmort", "LongTermDebt", "ShortTermDebt", "DebtCurrent",
                "DilutedShares", "CurrentAssets", "CurrentLiabilities", "Inventories",
                "AccountsReceivable", "CostOfGoodsSold", "IncomeTaxExpense", "PreTaxIncome",
                "Assets", "Equity", "Liabilities", "CashAndCashEquivalents",
                "OperatingIncome", "RevenueGrowthYoY", "GrossMargin", "OperatingMargin",
                "NetProfitMargin", "ROE", "FreeCashFlow", "EBITDA", "EBITDAMargin",
                "InterestCoverage", "DebtToEquity", "NOPAT", "InvestedCapital",
                "CurrentRatio", "QuickRatio", "InventoryTurnover", "ReceivablesTurnover",
                "OperatingCashFlowRatio", "EquityRatio", "AssetTurnover", "NetIncomeGrowthYoY",
                "CFOGrowthYoY", "AssetGrowthRate", "ROIC"
            ]
            for metric_name in parsed_metrics:
                if metric_name in valid_metrics:
                    metric_iri = f"efin:{_iri_safe(metric_name)}"
                    lines.append(f"  efin:computedFromMetric {metric_iri} ;")
                # 스키마에 정의되지 않은 메트릭(TotalDebt, Debt, Cash 등)은 무시

        lines[-1] = lines[-1].rstrip(" ;")
        lines.append(".")

    # Unit 인스턴스 생성
    if units_seen:
        lines.append("")
        lines.append("# Unit 인스턴스")
        for unit in sorted(units_seen):
            unit_iri = f"efin:Unit{_iri_camel_case(unit)}"
            lines.append(f"{unit_iri} a efin:Unit .")

    # Currency 인스턴스 생성
    if currencies_seen:
        lines.append("")
        lines.append("# Currency 인스턴스")
        for currency in sorted(currencies_seen):
            currency_iri = f"efin:Currency{currency}"
            lines.append(f"{currency_iri} a efin:Currency .")

    # XBRLConcept 인스턴스 생성
    if xbrl_concepts_seen:
        lines.append("")
        lines.append("# XBRLConcept 인스턴스")
        for qname, concept_info in sorted(xbrl_concepts_seen.items()):
            concept_iri = concept_info["iri"]
            namespace = concept_info["namespace"]
            lines.append(f"{concept_iri} a efin:XBRLConcept ;")
            lines.append(f'  efin:hasQName "{_ttl_escape(qname)}" ;')
            if namespace:
                # hasNamespace는 DatatypeProperty(xsd:anyURI) 이므로 리터럴로 기록
                lines.append(f'  efin:hasNamespace "{_ttl_escape(namespace)}"^^xsd:anyURI ;')
            lines[-1] = lines[-1].rstrip(" ;")
            lines.append(".")

    # 벤치마크 인스턴스 생성
    if benchmarks:
        lines.append("")
        lines.append("# 벤치마크 통계")
        for b in benchmarks:
            industry = b.get("industry", "").strip()
            sector = b.get("sector", "").strip()
            metric = b.get("metric", "").strip()
            fy = str(b.get("fy", ""))
            
            if not metric or not fy:
                continue
            
            if industry:
                # 업종(Industry) 스코프 벤치마크: 플래그가 켜진 경우에만 생성
                if not include_industry_scope:
                    continue
                # 산업별 벤치마크
                bench_iri = f"efin:IndustryBenchmark{_iri_camel_case(industry)}{_iri_camel_case(metric)}{fy}"
                lines.append(f"{bench_iri} a efin:IndustryBenchmark ;")
                lines.append(f"  efin:forIndustry efin:Industry{_iri_camel_case(industry)} ;")
                lines.append(f"  efin:forMetric efin:{_iri_safe(metric)} ;")
                lines.append(f"  efin:forFiscalYear {int(fy)} ;")
            else:
                # 전체 벤치마크 (industry와 sector가 모두 빈 값) - AllBenchmark 클래스 사용
                bench_iri = f"efin:AllBenchmark{_iri_camel_case(metric)}{fy}"
                lines.append(f"{bench_iri} a efin:AllBenchmark ;")
                lines.append(f"  efin:forSector efin:SectorAll ;")
                lines.append(f"  efin:forMetric efin:{_iri_safe(metric)} ;")
                lines.append(f"  efin:forFiscalYear {int(fy)} ;")
            
            # 통계값 추가
            avg = b.get("average_value")
            median = b.get("median_value")
            max_val = b.get("max_value")
            min_val = b.get("min_value")
            p25 = b.get("percentile25")
            p75 = b.get("percentile75")
            sample_size = b.get("sample_size")
            
            if avg is not None:
                lines.append(f'  efin:hasAverageValue "{float(avg)}"^^xsd:double ;')
            if median is not None:
                lines.append(f'  efin:hasMedianValue "{float(median)}"^^xsd:double ;')
            if max_val is not None:
                lines.append(f'  efin:hasMaxValue "{float(max_val)}"^^xsd:double ;')
            if min_val is not None:
                lines.append(f'  efin:hasMinValue "{float(min_val)}"^^xsd:double ;')
            if p25 is not None:
                lines.append(f'  efin:hasPercentile25 "{float(p25)}"^^xsd:double ;')
            if p75 is not None:
                lines.append(f'  efin:hasPercentile75 "{float(p75)}"^^xsd:double ;')
            if sample_size is not None:
                lines.append(f"  efin:hasSampleSize {sample_size} ;")
            
            lines[-1] = lines[-1].rstrip(" ;")
            lines.append(".")

    # 랭킹 인스턴스 생성
    if rankings:
        lines.append("")
        lines.append("# 랭킹")
        
        # fy 추출 (첫 번째 랭킹에서)
        fy_ranking = ""
        if rankings:
            first_r = rankings[0]
            if isinstance(first_r, dict):
                fy_ranking = str(first_r.get("fy", ""))
        
        # fy가 없으면 observations에서 추출 시도
        if not fy_ranking and observations:
            first_obs = observations[0]
            if isinstance(first_obs, dict):
                fy_ranking = str(first_obs.get("fy", ""))
        
        if not fy_ranking:
            fy_ranking = ""  # 빈 문자열로 처리
        
        # 각 랭킹 레코드에 대해 개별 TopRanking 인스턴스 생성
        for r in rankings:
            if not isinstance(r, dict):
                continue
            industry = r.get("industry", "").strip()
            sector = r.get("sector", "").strip()
            metric = r.get("metric", "").strip()
            ranking_type = r.get("ranking_type", "").strip()
            cik = r.get("cik", "").strip()
            rank = r.get("rank")
            value = r.get("value")
            composite_score = r.get("composite_score")
            
            if not metric or not ranking_type or not cik:
                continue
            
            # TopRanking 인스턴스는 Top10 레코드만 대상으로 생성 (전체 순위 All 등은 CSV에만 유지)
            if ranking_type != "Top10":
                continue

            try:
                rank_int = int(rank) if rank else None
            except (ValueError, TypeError):
                continue
            
            if rank_int is None:
                continue
            
            # scope_type과 scope_value 결정
            if industry:
                # Industry별 랭킹
                scope_type = "industry"
                scope_value = industry
                ranking_iri = f"efin:TopRanking{_iri_camel_case(scope_value)}{_iri_camel_case(metric)}{ranking_type}{fy_ranking}{cik.zfill(10)}"
            elif sector:
                # Sector별 랭킹
                scope_type = "sector"
                scope_value = sector
                ranking_iri = f"efin:TopRankingSector{_iri_camel_case(scope_value)}{_iri_camel_case(metric)}{ranking_type}{fy_ranking}{cik.zfill(10)}"
            else:
                # 전체 랭킹
                scope_type = "all"
                scope_value = "All"
                ranking_iri = f"efin:TopRankingAll{_iri_camel_case(metric)}{ranking_type}{fy_ranking}{cik.zfill(10)}"

            # 업종/섹터 스코프 TopRanking는 Composite 지표에 대해서는 항상 생성
            # (Composite Top10 리더 Company 클래스 추론에 필요)
            # 기타 지표는 기존 플래그 동작을 유지
            if scope_type == "industry" and not include_industry_scope and metric != "Composite":
                continue
            if scope_type == "sector" and not include_sector_scope and metric != "Composite":
                continue

            # TopRanking 인스턴스 생성 (스코프별 서브클래스 사용)
            if scope_type == "industry":
                ranking_class = "efin:IndustryTopRanking"
            else:
                # scope_type == "all"
                ranking_class = "efin:AllTopRanking"
            lines.append(f"{ranking_iri} a {ranking_class} ;")
            
            # scope_type에 따라 적절한 속성 추가
            if scope_type == "industry":
                lines.append(f"  efin:forIndustry efin:Industry{_iri_camel_case(scope_value)} ;")
            elif scope_type == "sector":
                lines.append(f"  efin:forSector efin:Sector{_iri_camel_case(scope_value)} ;")
            else:  # scope_type == "all"
                lines.append(f"  efin:forSector efin:SectorAll ;")
            
            lines.append(f"  efin:forMetric efin:{_iri_safe(metric)} ;")
            if fy_ranking:
                lines.append(f"  efin:forFiscalYear {int(fy_ranking)} ;")
            lines.append(f'  efin:hasRankingType "{_ttl_escape(ranking_type)}" ;')
            lines.append(f"  efin:hasRank {rank_int} ;")
            
            # value 또는 composite_score 추가
            if value is not None:
                try:
                    value_float = float(value)
                    if not (math.isnan(value_float) or math.isinf(value_float)):
                        lines.append(f'  efin:hasRankingValue "{value_float}"^^xsd:double ;')
                except (ValueError, TypeError):
                    pass
            
            if composite_score is not None:
                try:
                    score_float = float(composite_score)
                    if not (math.isnan(score_float) or math.isinf(score_float)):
                        lines.append(f'  efin:hasCompositeScore "{score_float}"^^xsd:double ;')
                except (ValueError, TypeError):
                    pass
            
            lines[-1] = lines[-1].rstrip(" ;")
            lines.append(".")
            
            # 회사를 랭킹에 연결
            comp_iri = f"efin:CIK{cik.zfill(10)}"
            lines.append(f"{comp_iri} efin:hasRanking {ranking_iri} .")

    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def compute_benchmarks(tags_csv_path: str, fy: int) -> List[dict]:
    """
    tags_{fy}.csv를 읽어서 산업별/섹터별 벤치마크 통계를 계산
    
    핵심 지표: ROE, ROIC, NetProfitMargin, DebtToEquity, CurrentRatio,
              RevenueGrowthYoY, NetIncomeGrowthYoY, OperatingMargin, AssetTurnover
    
    Returns:
        List[dict]: 벤치마크 통계 리스트 (CSV로 저장할 형식)
    """
    import statistics
    
    # 벤치마크는 핵심 지표 세트(BENCHMARK_RANKING_METRICS)에 대해서만 계산
    KEY_METRICS = BENCHMARK_RANKING_METRICS
    
    benchmarks = []
    
    # CSV 읽기
    with open(tags_csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # 산업별/전체 그룹화
    industry_groups: Dict[Tuple[str, str], List[float]] = {}  # (industry, metric) -> values
    all_groups: Dict[str, List[float]] = {}  # metric -> values (전체 벤치마크용)
    
    for row in rows:
        industry = row.get("industry", "").strip()
        sector = row.get("sector", "").strip()
        metric = row.get("metric", "").strip()
        value_str = row.get("value", "").strip()
        
        if not industry or not metric or not value_str:
            continue
        
        if metric not in KEY_METRICS:
            continue
        
        try:
            value = float(value_str)
            if math.isnan(value) or math.isinf(value):
                continue
        except (ValueError, TypeError):
            continue
        
        # 산업별 통계
        key = (industry, metric)
        if key not in industry_groups:
            industry_groups[key] = []
        industry_groups[key].append(value)
        
        # 전체 통계 (모든 회사 데이터 집계)
        if metric not in all_groups:
            all_groups[metric] = []
        all_groups[metric].append(value)
    
    # 산업별 벤치마크 계산
    for (industry, metric), values in industry_groups.items():
        if len(values) < 2:  # 최소 2개 샘플 필요
            continue
        
        sector = industry_sector_map.get(industry, "")
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        benchmarks.append({
            "industry": industry,
            "sector": sector,
            "metric": metric,
            "fy": fy,
            "average_value": statistics.mean(values),
            "median_value": statistics.median(values),
            "max_value": max(values),
            "min_value": min(values),
            "percentile25": sorted_values[int(n * 0.25)] if n > 0 else None,
            "percentile75": sorted_values[int(n * 0.75)] if n > 0 else None,
            "sample_size": n
        })
    
    # 전체 벤치마크 계산 (모든 회사 데이터 집계)
    for metric, values in all_groups.items():
        if len(values) < 2:
            continue
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        benchmarks.append({
            "industry": "",  # 전체는 빈 값
            "sector": "",    # 전체는 빈 값
            "metric": metric,
            "fy": fy,
            "average_value": statistics.mean(values),
            "median_value": statistics.median(values),
            "max_value": max(values),
            "min_value": min(values),
            "percentile25": sorted_values[int(n * 0.25)] if n > 0 else None,
            "percentile75": sorted_values[int(n * 0.75)] if n > 0 else None,
            "sample_size": n
        })
    
    return benchmarks

def compute_rankings(tags_csv_path: str, benchmarks_csv_path: str, fy: int) -> List[dict]:
    """
    tags_{fy}.csv와 benchmarks_{fy}.csv를 읽어서 랭킹 계산
    
    각 지표별로 산업/섹터 내 상위 10/50/100 선정 및 전체 랭킹 계산
    종합 점수 기반 랭킹도 계산 (모든 핵심 지표의 정규화된 점수 합산)
    
    Returns:
        List[dict]: 랭킹 리스트 (CSV로 저장할 형식)
    """
    # 랭킹은 핵심 지표 세트(BENCHMARK_RANKING_METRICS)에 대해서만 계산
    KEY_METRICS = BENCHMARK_RANKING_METRICS
    
    rankings = []
    
    # tags CSV 읽기
    with open(tags_csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        tag_rows = list(reader)
    
    # 회사별 메트릭 값 수집
    company_metrics: Dict[Tuple[str, str, str], Dict[str, float]] = {}  # (cik, industry, sector) -> {metric: value}
    
    for row in tag_rows:
        cik = row.get("cik", "").strip()
        symbol = row.get("symbol", "").strip()
        industry = row.get("industry", "").strip()
        sector = row.get("sector", "").strip()
        metric = row.get("metric", "").strip()
        value_str = row.get("value", "").strip()
        
        if not cik or not industry or not metric or not value_str:
            continue
        
        if metric not in KEY_METRICS:
            continue
        
        try:
            value = float(value_str)
            if math.isnan(value) or math.isinf(value):
                continue
        except (ValueError, TypeError):
            continue
        
        key = (cik, industry, sector)
        if key not in company_metrics:
            company_metrics[key] = {"symbol": symbol}
        company_metrics[key][metric] = value
    
    # 산업별 랭킹 계산
    industry_groups: Dict[Tuple[str, str], List[Tuple[str, str, float]]] = {}  # (industry, metric) -> [(cik, symbol, value), ...]
    
    for (cik, industry, sector), metrics in company_metrics.items():
        symbol = metrics.get("symbol", "")
        for metric in KEY_METRICS:
            if metric not in metrics:
                continue
            value = metrics[metric]
            key = (industry, metric)
            if key not in industry_groups:
                industry_groups[key] = []
            industry_groups[key].append((cik, symbol, value))
    
    # 각 산업-메트릭 조합에 대해 랭킹 생성
    for (industry, metric), companies in industry_groups.items():
        # 값 기준 내림차순 정렬 (높은 값이 좋은 지표)
        # 단, DebtToEquity는 낮은 값이 좋으므로 오름차순
        reverse = metric != "DebtToEquity"
        sorted_companies = sorted(companies, key=lambda x: x[2], reverse=reverse)
        
        # 섹터 찾기
        sector = ""
        for (cik, ind, sec), _ in company_metrics.items():
            if ind == industry:
                sector = sec
                break
        
        # Top10만 생성 (Top50/Top100 제거)
        for top_n, ranking_type in [(10, "Top10")]:
            for rank, (cik, symbol, value) in enumerate(sorted_companies[:top_n], 1):
                rankings.append({
                    "cik": cik,
                    "symbol": symbol,
                    "industry": industry,
                    "sector": sector,
                    "metric": metric,
                    "ranking_type": ranking_type,
                    "rank": rank,
                    "value": value,
                    "composite_score": None  # 개별 메트릭 랭킹이므로 None
                })
        
        # 전체 랭킹 생성 (Industry별)
        for rank, (cik, symbol, value) in enumerate(sorted_companies, 1):
            rankings.append({
                "cik": cik,
                "symbol": symbol,
                "industry": industry,
                "sector": sector,
                "metric": metric,
                "ranking_type": "All",
                "rank": rank,
                "value": value,
                "composite_score": None
            })
    
    # 전체 랭킹 계산
    all_groups: Dict[str, List[Tuple[str, str, float]]] = {}  # metric -> [(cik, symbol, value), ...]
    
    for (cik, industry, sector), metrics in company_metrics.items():
        symbol = metrics.get("symbol", "")
        for metric in KEY_METRICS:
            if metric not in metrics:
                continue
            value = metrics[metric]
            if metric not in all_groups:
                all_groups[metric] = []
            all_groups[metric].append((cik, symbol, value))
    
    # 각 메트릭에 대해 전체 랭킹 생성
    for metric, companies in all_groups.items():
        # 값 기준 내림차순 정렬 (높은 값이 좋은 지표)
        # 단, DebtToEquity는 낮은 값이 좋으므로 오름차순
        reverse = metric != "DebtToEquity"
        sorted_companies = sorted(companies, key=lambda x: x[2], reverse=reverse)
        
        # Top10만 생성 (Top50/Top100 제거)
        for top_n, ranking_type in [(10, "Top10")]:
            for rank, (cik, symbol, value) in enumerate(sorted_companies[:top_n], 1):
                rankings.append({
                    "cik": cik,
                    "symbol": symbol,
                    "industry": "",  # 전체는 빈 값
                    "sector": "",   # 전체는 빈 값
                    "metric": metric,
                    "ranking_type": ranking_type,
                    "rank": rank,
                    "value": value,
                    "composite_score": None  # 개별 메트릭 랭킹이므로 None
                })
        
        # 전체 랭킹 생성 (All scope)
        for rank, (cik, symbol, value) in enumerate(sorted_companies, 1):
            rankings.append({
                "cik": cik,
                "symbol": symbol,
                "industry": "",  # 전체는 빈 값
                "sector": "",   # 전체는 빈 값
                "metric": metric,
                "ranking_type": "All",
                "rank": rank,
                "value": value,
                "composite_score": None
            })
    
    # 종합 점수 기반 랭킹 계산
    # 각 메트릭을 정규화(0-1)하여 합산
    industry_composite: Dict[str, List[Tuple[str, str, float]]] = {}  # industry -> [(cik, symbol, composite_score), ...]
    
    for (cik, industry, sector), metrics in company_metrics.items():
        symbol = metrics.get("symbol", "")
        
        # 해당 산업의 모든 회사 메트릭 값 수집 (정규화용)
        industry_values: Dict[str, List[float]] = {}
        for (cik2, ind, sec), metrics2 in company_metrics.items():
            if ind != industry:
                continue
            for metric in KEY_METRICS:
                if metric not in metrics2:
                    continue
                if metric not in industry_values:
                    industry_values[metric] = []
                industry_values[metric].append(metrics2[metric])
        
        # 정규화된 점수 계산
        composite_score = 0.0
        for metric in KEY_METRICS:
            if metric not in metrics or metric not in industry_values:
                continue
            
            value = metrics[metric]
            values = industry_values[metric]
            
            if not values or len(values) < 2:
                continue
            
            # 정규화: (value - min) / (max - min)
            min_val = min(values)
            max_val = max(values)
            
            if max_val == min_val:
                normalized = 0.5
            else:
                normalized = (value - min_val) / (max_val - min_val)
            
            # DebtToEquity는 낮은 값이 좋으므로 반전
            if metric == "DebtToEquity":
                normalized = 1.0 - normalized
            
            composite_score += normalized
        
        if industry not in industry_composite:
            industry_composite[industry] = []
        industry_composite[industry].append((cik, symbol, composite_score))
    
    # 종합 랭킹 생성 (Industry별)
    for industry, companies in industry_composite.items():
        sorted_companies = sorted(companies, key=lambda x: x[2], reverse=True)
        
        # 섹터 찾기
        sector = ""
        for (cik, ind, sec), _ in company_metrics.items():
            if ind == industry:
                sector = sec
                break
        
        # 종합 점수 Top10만 생성
        for top_n, ranking_type in [(10, "Top10")]:
            for rank, (cik, symbol, composite_score) in enumerate(sorted_companies[:top_n], 1):
                rankings.append({
                    "cik": cik,
                    "symbol": symbol,
                    "industry": industry,
                    "sector": sector,
                    "metric": "Composite",
                    "ranking_type": ranking_type,
                    "rank": rank,
                    "value": None,  # 종합 랭킹이므로 개별 값 없음
                    "composite_score": composite_score
                })
        
        # 전체 랭킹 생성 (Industry별 Composite)
        for rank, (cik, symbol, composite_score) in enumerate(sorted_companies, 1):
            rankings.append({
                "cik": cik,
                "symbol": symbol,
                "industry": industry,
                "sector": sector,
                "metric": "Composite",
                "ranking_type": "All",
                "rank": rank,
                "value": None,
                "composite_score": composite_score
            })
    
    # 전체 종합 점수 기반 랭킹 계산
    all_composite: List[Tuple[str, str, float]] = []  # [(cik, symbol, composite_score), ...]
    
    # 전체 회사 메트릭 값 수집 (정규화용)
    all_values: Dict[str, List[float]] = {}
    for (cik2, ind, sec), metrics2 in company_metrics.items():
        for metric in KEY_METRICS:
            if metric not in metrics2:
                continue
            if metric not in all_values:
                all_values[metric] = []
            all_values[metric].append(metrics2[metric])
    
    for (cik, industry, sector), metrics in company_metrics.items():
        symbol = metrics.get("symbol", "")
        
        # 정규화된 점수 계산
        composite_score = 0.0
        for metric in KEY_METRICS:
            if metric not in metrics or metric not in all_values:
                continue
            
            value = metrics[metric]
            values = all_values[metric]
            
            if not values or len(values) < 2:
                continue
            
            # 정규화: (value - min) / (max - min)
            min_val = min(values)
            max_val = max(values)
            
            if max_val == min_val:
                normalized = 0.5
            else:
                normalized = (value - min_val) / (max_val - min_val)
            
            # DebtToEquity는 낮은 값이 좋으므로 반전
            if metric == "DebtToEquity":
                normalized = 1.0 - normalized
            
            composite_score += normalized
        
        all_composite.append((cik, symbol, composite_score))
    
    # 전체 종합 랭킹 생성
    sorted_all_composite = sorted(all_composite, key=lambda x: x[2], reverse=True)
    
    # 전체 종합 점수 Top10만 생성
    for top_n, ranking_type in [(10, "Top10")]:
        for rank, (cik, symbol, composite_score) in enumerate(sorted_all_composite[:top_n], 1):
            rankings.append({
                "cik": cik,
                "symbol": symbol,
                "industry": "",  # 전체는 빈 값
                "sector": "",   # 전체는 빈 값
                "metric": "Composite",
                "ranking_type": ranking_type,
                "rank": rank,
                "value": None,  # 종합 랭킹이므로 개별 값 없음
                "composite_score": composite_score
            })
    
    # 전체 랭킹 생성 (All scope Composite)
    for rank, (cik, symbol, composite_score) in enumerate(sorted_all_composite, 1):
        rankings.append({
            "cik": cik,
            "symbol": symbol,
            "industry": "",  # 전체는 빈 값
            "sector": "",   # 전체는 빈 값
            "metric": "Composite",
            "ranking_type": "All",
            "rank": rank,
            "value": None,
            "composite_score": composite_score
        })
    
    return rankings

def create_wide_format_csv(tags_csv_path: str, rankings_csv_path: str, companies_csv_path: str, fy: int, output_path: str):
    """
    tags.csv와 rankings.csv를 읽어서 wide format CSV 생성
    
    기업당 하나의 row로 변환하며, 모든 메트릭을 컬럼으로 포함하고
    각 메트릭의 Industry/Sector/All 랭킹을 컬럼으로 추가합니다.
    
    Args:
        tags_csv_path: tags CSV 파일 경로
        rankings_csv_path: rankings CSV 파일 경로
        companies_csv_path: companies CSV 파일 경로
        fy: fiscal year
        output_path: 출력 파일 경로
    """
    # tags CSV 읽기 및 CIK별로 그룹화
    company_metrics: Dict[str, Dict[str, Optional[float]]] = {}  # cik -> {metric: value}
    company_info: Dict[str, dict] = {}  # cik -> {symbol, name, sector, industry, ...}
    all_metrics: Set[str] = set()
    
    with open(tags_csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cik = row.get("cik", "").strip()
            if not cik:
                continue
            
            metric = row.get("metric", "").strip()
            value_str = row.get("value", "").strip()
            
            if cik not in company_metrics:
                company_metrics[cik] = {}
                company_info[cik] = {
                    "cik": cik,
                    "symbol": row.get("symbol", "").strip(),
                    "name": row.get("name", "").strip(),
                    "sector": row.get("sector", "").strip(),
                    "industry": row.get("industry", "").strip(),
                    "sic": row.get("sic", "").strip(),
                    "sic_description": row.get("sic_description", "").strip(),
                    "fye": row.get("fye", "").strip(),
                }
            
            if metric:
                all_metrics.add(metric)
                if value_str:
                    try:
                        value = float(value_str)
                        if not (math.isnan(value) or math.isinf(value)):
                            company_metrics[cik][metric] = value
                    except (ValueError, TypeError):
                        company_metrics[cik][metric] = None
                else:
                    company_metrics[cik][metric] = None
    
    # rankings CSV 읽기 및 랭킹 정보 수집
    # 구조: {(cik, metric, scope): rank}
    # scope: "Industry", "Sector", "All"
    rankings_map: Dict[Tuple[str, str, str], int] = {}  # (cik, metric, scope) -> rank
    
    if os.path.exists(rankings_csv_path):
        with open(rankings_csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cik = row.get("cik", "").strip()
                metric = row.get("metric", "").strip()
                ranking_type = row.get("ranking_type", "").strip()
                rank_str = row.get("rank", "").strip()
                industry = row.get("industry", "").strip()
                sector = row.get("sector", "").strip()
                
                if not cik or not metric or not ranking_type or not rank_str:
                    continue
                
                # ranking_type이 "All"인 경우만 전체 랭킹으로 사용
                if ranking_type != "All":
                    continue
                
                try:
                    rank = int(rank_str)
                except (ValueError, TypeError):
                    continue
                
                # scope 결정: Industry, Sector, All
                if industry:
                    scope = "Industry"
                elif sector:
                    scope = "Sector"
                else:
                    scope = "All"
                
                rankings_map[(cik, metric, scope)] = rank
    
    # 모든 메트릭 정렬 (일관된 순서를 위해)
    sorted_metrics = sorted(all_metrics)
    
    # 컬럼 헤더 생성
    base_columns = ["cik", "symbol", "name", "sector", "industry", "sic", "sic_description", "fye"]
    metric_columns = sorted_metrics
    ranking_columns = []
    
    # 랭킹 컬럼 생성: {Metric}_Rank_Industry, {Metric}_Rank_Sector, {Metric}_Rank_All
    for metric in sorted_metrics:
        ranking_columns.extend([
            f"{metric}_Rank_Industry",
            f"{metric}_Rank_Sector",
            f"{metric}_Rank_All"
        ])
    
    all_columns = base_columns + metric_columns + ranking_columns
    
    # Wide format 데이터 생성
    wide_rows = []
    for cik in sorted(company_metrics.keys()):
        row = {}
        
        # 기본 정보
        info = company_info.get(cik, {})
        for col in base_columns:
            row[col] = info.get(col, "")
        
        # 메트릭 값
        metrics = company_metrics.get(cik, {})
        for metric in sorted_metrics:
            value = metrics.get(metric)
            if value is not None:
                row[metric] = f"{value:.6f}"
            else:
                row[metric] = ""
        
        # 랭킹 값
        for metric in sorted_metrics:
            for scope in ["Industry", "Sector", "All"]:
                rank = rankings_map.get((cik, metric, scope))
                col_name = f"{metric}_Rank_{scope}"
                if rank is not None:
                    row[col_name] = str(rank)
                else:
                    row[col_name] = ""
        
        wide_rows.append(row)
    
    # CSV 파일 쓰기
    output_path_obj = pathlib.Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_columns)
        writer.writeheader()
        for row in wide_rows:
            writer.writerow(row)
    
    print(f"[OK] wrote wide format CSV: {output_path}")

def emit_after_csv(args, companies, obs_rows):
    try:
        if not hasattr(args, "emit_ttl") or not args.emit_ttl:
            return
        # 대체: 비어있으면 CSV 파일 읽기
        if (not companies) or (not obs_rows):
            co_fp = getattr(args, "out_companies", None)
            obs_fp = getattr(args, "out_tags", None)
            if not co_fp or not obs_fp:
                return
            if (not companies) and os.path.exists(co_fp):
                with open(co_fp, newline="", encoding="utf-8") as f:
                    companies = list(csv.DictReader(f))
            if (not obs_rows) and os.path.exists(obs_fp):
                with open(obs_fp, newline="", encoding="utf-8") as f:
                    obs_rows = list(csv.DictReader(f))
        
        # 벤치마크 및 랭킹 CSV 읽기
        benchmarks = []
        rankings = []
        benchmarks_fp = getattr(args, "out_benchmarks", None)
        rankings_fp = getattr(args, "out_rankings", None)
        
        if benchmarks_fp and os.path.exists(benchmarks_fp):
            with open(benchmarks_fp, newline="", encoding="utf-8") as f:
                benchmarks = list(csv.DictReader(f))
        
        if rankings_fp and os.path.exists(rankings_fp):
            with open(rankings_fp, newline="", encoding="utf-8") as f:
                rankings = list(csv.DictReader(f))
        
        include_industry_scope = getattr(args, "include_industry_scope", False)
        include_sector_scope = getattr(args, "include_sector_scope", False)
        emit_efin_ttl(
            companies or [],
            obs_rows or [],
            args.emit_ttl,
            benchmarks,
            rankings,
            include_industry_scope=include_industry_scope,
            include_sector_scope=include_sector_scope,
        )
        print(f"[emit-ttl] wrote RDF Turtle to: {args.emit_ttl}")
    except Exception as e:
        print(f"[emit-ttl] failed: {e}")

# ──────────────────────────────────────────────────────────────
# API 속도 제한 상태
_last_api_call_time: Optional[float] = None
_api_rate_limit_delay: float = 0.1  # SEC 가이드라인에 따라 초당 10개 요청
_rate_limit_lock = threading.Lock()

# ──────────────────────────────────────────────────────────────
# 캐시 설정
_COMPANYFACTS_CACHE_DIR = ".cache/companyfacts"
_SUBMISSIONS_CACHE_DIR   = ".cache/submissions"
_DATE_FORMAT = "%Y%m%d"

# ------------------------ 메트릭 목록 ------------------------
# Base metrics (변경 금지 원칙)
BASE_METRICS = [
    "Revenue","OperatingIncome","NetIncome","CashAndCashEquivalents","CFO",
    "Assets","Liabilities","Equity",
    "EPSDiluted","CapEx","InterestExpense","DepAmort",
    "LongTermDebt","ShortTermDebt","DebtCurrent","GrossProfit",
    "DilutedShares","CurrentAssets","CurrentLiabilities","Inventories",
    "AccountsReceivable","CostOfGoodsSold","IncomeTaxExpense","PreTaxIncome"
]

# 파생 메트릭 (기존 + growth 4종 포함)
DERIVED_METRICS = [
    "RevenueGrowthYoY","GrossMargin","OperatingMargin","NetProfitMargin","ROE",
    "FreeCashFlow","EBITDA","EBITDAMargin","InterestCoverage","DebtToEquity",
    "CurrentRatio","QuickRatio","InventoryTurnover","ReceivablesTurnover",
    "OperatingCashFlowRatio","EquityRatio","AssetTurnover",
    "NetIncomeGrowthYoY","CFOGrowthYoY","AssetGrowthRate",
    "ROIC","NOPAT","InvestedCapital"
]

# Benchmarks/TopRanking에 사용할 핵심 투자 인사이트 지표 세트
# NetIncomeGrowthYoY(순이익 성장률)는 Benchmark/TopRanking에는 포함하지 않고,
# 필요 시 SPARQL에서 계산/필터로만 사용한다.
BENCHMARK_RANKING_METRICS = [
    "ROE",
    "NetProfitMargin",
    "DebtToEquity",
    "CurrentRatio",
    "RevenueGrowthYoY",
    "CFOGrowthYoY",
]

STD_PREFIXES = {"us-gaap","ifrs-full","dei","srt"}

@dataclass(frozen=True)
class Candidate:
    qname: str
    base_score: float = 1.0
    industry_only: Optional[Set[str]] = None
    normalized_as: str = "AUTO"
    notes: Optional[str] = None
    origin: str = "static"  # static|mined|extension|hint|suggestion (정적|채굴|확장|힌트|제안)

@dataclass(frozen=True)
class CompositeCandidate:
    name: str
    components: List[Tuple[str, float]]
    base_score: float = 1.0
    industry_only: Optional[Set[str]] = None
    normalized_as: str = "AUTO"
    notes: Optional[str] = None

# ------------------------- 디버거 ----------------------------
class Debugger:
    def __init__(self, enabled: bool = False, path: Optional[str] = None):
        self.enabled = enabled
        self.path = path
        self._fp = None
        if enabled and path:
            try:
                pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
                self._fp = open(path, "w", encoding="utf-8")
            except Exception as e:
                print(f"[WARN] Failed to open debug file {path}: {e}", file=sys.stderr)
                self._fp = None

    def log(self, msg: str):
        if not self.enabled: return
        if self._fp:
            try:
                self._fp.write(msg.rstrip() + "\\n")
                self._fp.flush()
            except ValueError:
                print(msg, file=sys.stderr)
        else:
            print(msg, file=sys.stderr)

    def close(self):
        if self._fp:
            self._fp.close()

# ----------------------- 제안 저장소 ---------------------
_SUGG: Dict[Tuple[str,str,str], dict] = {}
_sugg_lock = threading.Lock()

def record_suggestion(cik: Optional[str], metric: str, qname: str, origin: str, note: Optional[str]=None, ext_only: bool=False):
    if not cik: return
    try:
        tax = qname.split(":",1)[0]
    except Exception:
        tax = ""
    if ext_only and tax in STD_PREFIXES:
        return
    key = (str(int(cik)), metric, qname)
    with _sugg_lock:
        if key not in _SUGG:
            _SUGG[key] = {"cik": str(int(cik)), "metric": metric, "qname": qname, "origin": origin, "note": note or ""}

def dump_suggestions(path: str, append: bool=False):
    mode = "a" if append and os.path.exists(path) else "w"
    with open(path, mode, encoding="utf-8") as f:
        for v in _SUGG.values():
            f.write(json.dumps(v, ensure_ascii=False) + "\\n")

# ----------------------- HTTP 유틸리티 ----------------------------
def get_user_agent(args) -> str:
    return (args.user_agent or os.getenv("SEC_USER_AGENT") or "").strip()

def wait_for_rate_limit():
    global _last_api_call_time
    with _rate_limit_lock:
        if _last_api_call_time is not None:
            elapsed = time.time() - _last_api_call_time
            if elapsed < _api_rate_limit_delay:
                time.sleep(_api_rate_limit_delay - elapsed)
        _last_api_call_time = time.time()

def http_get(url: str, ua: Optional[str] = None, timeout: int = 45, max_retries: int = 3, dbg: Optional[Debugger] = None):
    if requests is None:
        raise RuntimeError("requests is required. pip install requests")
    headers = {}
    if "sec.gov" in url:
        ua = ua or os.getenv("SEC_USER_AGENT")
        if not ua:
            raise RuntimeError("SEC requests require --user-agent or SEC_USER_AGENT env")
        headers["User-Agent"] = ua
        wait_for_rate_limit()
    else:
        headers["User-Agent"] = ua or "Mozilla/5.0"
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (429, 503):
                wait_time = (2 ** attempt) * 2
                msg = f"[WARN] HTTP {e.response.status_code} for {url}, retry {attempt+1}/{max_retries} after {wait_time}s"
                print(msg, file=sys.stderr)
                if dbg: dbg.log(msg)
                time.sleep(wait_time); continue
            raise
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                msg = f"[WARN] {type(e).__name__} for {url}, retry {attempt+1}/{max_retries} after {wait_time}s"
                print(msg, file=sys.stderr)
                if dbg: dbg.log(msg)
                time.sleep(wait_time); continue
            raise
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries")

# ----------------------- 캐시 유틸리티 -----------------------
def _date_str():
    return datetime.now().strftime("%Y%m%d")

def cf_cache_path(cache_dir: str, cik: str) -> pathlib.Path:
    padded = str(cik).zfill(10)
    return pathlib.Path(cache_dir) / f"CIK{padded}_{_date_str()}.json"

def cf_find_existing(cache_dir: str, cik: str) -> Optional[pathlib.Path]:
    p = pathlib.Path(cache_dir)
    if not p.exists(): return None
    fname = cf_cache_path(cache_dir, cik).name
    want = p / fname
    return want if want.exists() else None

def cf_save(cache_dir: str, cik: str, data: dict):
    path = cf_cache_path(cache_dir, cik)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cf_cleanup(cache_dir: str, cik: str):
    p = pathlib.Path(cache_dir)
    if not p.exists(): return
    padded = str(cik).zfill(10)
    today = _date_str()
    for fp in sorted(p.glob(f"CIK{padded}_*.json")):
        if today not in fp.name:
            try: fp.unlink()
            except Exception: pass

# 제출물 캐시
def subs_cache_path(cache_dir: str, cik: str) -> pathlib.Path:
    padded = str(cik).zfill(10)
    return pathlib.Path(cache_dir) / f"submissions_CIK{padded}_{_date_str()}.json"

def subs_find_existing(cache_dir: str, cik: str) -> Optional[pathlib.Path]:
    p = pathlib.Path(cache_dir)
    if not p.exists(): return None
    want = subs_cache_path(cache_dir, cik)
    return want if want.exists() else None

def subs_save(cache_dir: str, cik: str, data: dict):
    path = subs_cache_path(cache_dir, cik)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def subs_cleanup(cache_dir: str, cik: str):
    p = pathlib.Path(cache_dir)
    if not p.exists(): return
    padded = str(cik).zfill(10)
    today = _date_str()
    for fp in sorted(p.glob(f"submissions_CIK{padded}_*.json")):
        if today not in fp.name:
            try: fp.unlink()
            except Exception: pass

# ----------------------- SEC 페처 --------------------------
def fetch_company_facts(cik: str, ua: Optional[str], dbg: Debugger) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    dbg.log(f"[HTTP] GET {url}")
    return http_get(url, ua=ua, dbg=dbg).json()

def fetch_sec_submissions(cik: str, ua: Optional[str], dbg: Debugger) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"
    dbg.log(f"[HTTP] GET {url}")
    return http_get(url, ua=ua, dbg=dbg).json()

# ----------------------- 팩트 헬퍼 -------------------------
def get_unit_records(facts_json: dict, qname: str) -> Dict[str, List[dict]]:
    try: tax, tag = qname.split(":")
    except ValueError: return {}
    return (facts_json.get("facts", {}).get(tax, {}) or {}).get(tag, {}).get("units", {}) or {}

def iter_all_facts(facts_json: dict, qname: str):
    for unit, arr in get_unit_records(facts_json, qname).items():
        for rec in arr:
            val = rec.get("val")
            if isinstance(val, (int, float)):
                yield unit, rec

# ----------------------- 회계연도 윈도우 ------------------------------
def parse_date(s: Optional[str]) -> Optional[date]:
    if not s: return None
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%m/%d/%Y"):
        try: return datetime.strptime(s, fmt).date()
        except Exception: pass
    return None

def anchors_for_fy(fy: int, submissions: dict) -> List[date]:
    fye = str(submissions.get("fiscalYearEnd") or "1231").strip()
    if not re.fullmatch(r"\d{4}", fye): fye = "1231"
    mm, dd = int(fye[:2]), int(fye[2:])
    return [date(fy, mm, dd), date(fy+1, mm, dd)]

def within_tolerance(d: date, anchors: List[date], tol_days: int) -> bool:
    return any(abs((d - a).days) <= tol_days for a in anchors)

def end_distance(d: date, anchors: List[date]) -> int:
    return min(abs((d - a).days) for a in anchors)

def smart_pick(records: List[dict], anchors: List[date], tol_days: int, dbg: Debugger) -> Optional[dict]:
    best=None; best_rec=None
    for rec in records:
        end = parse_date(rec.get("end"))
        if not end: continue
        if not within_tolerance(end, anchors, tol_days):
            dbg.log(f"[smart_pick] reject end={rec.get('end')} tol={tol_days}")
            continue
        dist = end_distance(end, anchors)
        fp   = (rec.get("fp") or "").upper()
        score = -dist + (5 if fp in ("FY","CY","FYR") else 0)
        cand = (score, end)
        if (best is None) or (cand > best):
            best=cand; best_rec=rec
    return best_rec

# ---------------- SIC에서 산업/섹터 매핑 -------------
def sic_to_sector(sic: Optional[int]) -> str:
    if sic is None: return "Unknown"
    s = int(sic)
    if 1300 <= s <= 1399 or 2900 <= s <= 2999: return "Energy"
    if 1000 <= s <= 1299 or 1400 <= s <= 1499 or 2800 <= s <= 2899: return "Materials"
    if 1500 <= s <= 1799 or 3300 <= s <= 3399 or 3400 <= s <= 3999: return "Industrials"
    if 4900 <= s <= 4999: return "Utilities"
    if 2000 <= s <= 2099: return "Consumer Staples"
    if 2300 <= s <= 2799 or 3100 <= s <= 3299: return "Consumer Discretionary"
    if 8000 <= s <= 8099 or 2830 <= s <= 2839 or 3840 <= s <= 3859: return "Health Care"
    if 6000 <= s <= 6999: return "Financials"
    if 3570 <= s <= 3579 or 7370 <= s <= 7379 or 3570 <= s <= 3699 or 7370 <= s <= 7399: return "Information Technology"
    if 4800 <= s <= 4899 or 2700 <= s <= 2799: return "Communication Services"
    if 6500 <= s <= 6799: return "Real Estate"
    return "Other"

def infer_sector_industry(subs: dict) -> Tuple[str, str, str, str]:
    sic = None; sic_desc = ""
    try:
        sic = int(subs.get("sic")) if subs.get("sic") else None
    except Exception:
        sic = None
    sic_desc = subs.get("sicDescription") or ""
    sector = sic_to_sector(sic)
    industry = sic_desc if sic_desc else sector
    return sector, industry, str(sic) if sic is not None else "", sic_desc

# ----------------------- 점수 조정 --------------------------
def score_adj(form: Optional[str], unit: Optional[str], fp: Optional[str], has_seg: bool, industry_hit: bool=True) -> float:
    s = 0.0
    if form in ("10-K","20-F","10-K/A","20-F/A"): s += 0.06
    elif form: s -= 0.01
    if unit == "USD": s += 0.03
    elif unit: s -= 0.02
    if (fp or "").upper() in ("FY","CY","FYR"): s += 0.03
    if has_seg: s -= 0.01
    if industry_hit: s += 0.02
    return s

# ----------------------- 정적 후보 (긴 목록) --------------
# (주요 표준 후보 + 산업별 후보 + IFRS 포함. 필요시 확장 태그는 채굴/힌트로 커버)
CANDIDATES: Dict[str, List[Candidate]] = {
    "Revenue": [
        Candidate("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", 1.00, None, "Revenue"),
        Candidate("us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax", 0.985, None, "Revenue"),
        Candidate("us-gaap:Revenues", 0.975, None, "Revenue"),
        Candidate("us-gaap:SalesRevenueNet", 0.970, None, "Revenue"),
        Candidate("us-gaap:NetSales", 0.960, None, "Revenue"),
        Candidate("us-gaap:OperatingRevenue", 0.955, None, "Revenue"),
        # 유틸리티
        Candidate("us-gaap:UtilityRevenue", 0.960, {"Utilities"}, "Revenue"),
        Candidate("us-gaap:ElectricUtilityRevenue", 0.955, {"Utilities"}, "Revenue"),
        Candidate("us-gaap:GasUtilityRevenue", 0.945, {"Utilities"}, "Revenue"),
        Candidate("us-gaap:RegulatedAndUnregulatedOperatingRevenue", 0.940, {"Utilities"}, "Revenue"),
        # 리츠(REIT)
        Candidate("us-gaap:RealEstateRevenueNet", 0.950, {"Real Estate"}, "Revenue"),
        Candidate("us-gaap:RentalRevenue", 0.945, {"Real Estate"}, "Revenue"),
        Candidate("us-gaap:OperatingLeasesIncomeStatementLeaseRevenue", 0.940, {"Real Estate"}, "Revenue"),
        # 에너지
        Candidate("us-gaap:OilAndGasRevenue", 0.950, {"Energy"}, "Revenue"),
        Candidate("us-gaap:RefiningAndMarketingRevenue", 0.940, {"Energy"}, "Revenue"),
        # 소프트웨어/SaaS
        Candidate("us-gaap:SubscriptionRevenue", 0.940, None, "Revenue"),
        Candidate("us-gaap:SoftwareLicensesRevenue", 0.930, None, "Revenue"),
        # 금융 기업
        Candidate("us-gaap:InterestAndFeeIncomeLoansAndLeases", 0.950, {"Financials"}, "Revenue"),
        Candidate("us-gaap:NoninterestIncome", 0.945, {"Financials"}, "Revenue"),
        Candidate("us-gaap:NetInterestIncome", 0.940, {"Financials"}, "Revenue"),
        Candidate("us-gaap:InvestmentBankingRevenue", 0.935, {"Financials"}, "Revenue"),
        Candidate("us-gaap:InterestAndDividendIncomeOperating", 0.930, {"Financials"}, "Revenue"),
        # IFRS
        Candidate("ifrs-full:Revenue", 0.985, {"IFRS"}, "Revenue"),
    ],
    "OperatingIncome": [
        Candidate("us-gaap:OperatingIncomeLoss", 1.00, None, "OperatingIncome"),
        Candidate("ifrs-full:ProfitLossFromOperatingActivities", 0.98, {"IFRS"}, "OperatingIncome"),
        Candidate("ifrs-full:ProfitLossBeforeFinanceCostsAndTax", 0.96, {"IFRS"}, "OperatingIncome"),
        Candidate("us-gaap:EarningsBeforeInterestAndTaxes", 0.955, None, "OperatingIncome"),
        Candidate("us-gaap:IncomeFromOperations", 0.940, None, "OperatingIncome"),
        Candidate("us-gaap:RealEstateOperatingIncomeLoss", 0.92, {"Real Estate"}, "OperatingIncome"),
        # 금융 기업 대체
        Candidate("us-gaap:IncomeLossFromContinuingOperations", 0.90, {"Financials"}, "OperatingIncome"),
        Candidate("us-gaap:IncomeBeforeIncomeTaxes", 0.88, {"Financials"}, "OperatingIncome"),
    ],
    "NetIncome": [
        Candidate("us-gaap:NetIncomeLoss", 1.00, None, "NetIncome"),
        Candidate("us-gaap:NetIncomeLossAttributableToParent", 0.955, None, "NetIncome"),
        Candidate("us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic", 0.945, None, "NetIncome"),
        Candidate("us-gaap:NetIncomeLossFromContinuingOperationsAvailableToCommonShareholdersBasic", 0.940, None, "NetIncome"),
        Candidate("ifrs-full:ProfitLoss", 0.98, {"IFRS"}, "NetIncome"),
    ],
    "CashAndCashEquivalents": [
        Candidate("us-gaap:CashAndCashEquivalentsAtCarryingValue", 1.00, None, "CashAndCashEquivalents"),
        Candidate("us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 0.94, None, "CashAndCashEquivalents"),
        Candidate("ifrs-full:CashAndCashEquivalents", 0.98, {"IFRS"}, "CashAndCashEquivalents"),
    ],
    "CFO": [
        Candidate("us-gaap:NetCashProvidedByUsedInOperatingActivities", 1.00, None, "CFO"),
        Candidate("us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", 0.96, None, "CFO"),
        Candidate("ifrs-full:NetCashFlowsFromUsedInOperatingActivities", 0.98, {"IFRS"}, "CFO"),
    ],
    "Assets": [
        Candidate("us-gaap:Assets", 1.00, None, "Assets"),
        Candidate("ifrs-full:Assets", 0.985, {"IFRS"}, "Assets"),
        Candidate("us-gaap:LiabilitiesAndStockholdersEquity", 0.92, None, "Assets"),
        Candidate("ifrs-full:EquityAndLiabilities", 0.92, {"IFRS"}, "Assets"),
    ],
    "Liabilities": [
        Candidate("us-gaap:Liabilities", 1.00, None, "Liabilities"),
        Candidate("ifrs-full:Liabilities", 0.985, {"IFRS"}, "Liabilities"),
    ],
    "Equity": [
        Candidate("us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", 1.00, None, "Equity"),
        Candidate("us-gaap:StockholdersEquity", 0.98, None, "Equity"),
        Candidate("ifrs-full:Equity", 0.98, {"IFRS"}, "Equity"),
    ],
    "EPSDiluted": [
        Candidate("us-gaap:EarningsPerShareDiluted", 1.00, None, "EPSDiluted"),
        Candidate("ifrs-full:DilutedEarningsLossPerShare", 0.98, {"IFRS"}, "EPSDiluted"),
    ],
    "DilutedShares": [
        Candidate("us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", 1.00, None, "DilutedShares"),
        Candidate("ifrs-full:WeightedAverageNumberOfDilutedSharesOutstanding", 0.98, {"IFRS"}, "DilutedShares"),
    ],
    "GrossProfit": [
        Candidate("us-gaap:GrossProfit", 1.00, None, "GrossProfit"),
        Candidate("ifrs-full:GrossProfit", 0.98, {"IFRS"}, "GrossProfit"),
    ],
    "CapEx": [
        Candidate("us-gaap:PaymentsToAcquirePropertyPlantAndEquipment", 1.00, None, "CapEx"),
        Candidate("us-gaap:PaymentsToAcquireProductiveAssets", 0.93, None, "CapEx"),
        Candidate("ifrs-full:PurchaseOfPropertyPlantAndEquipment", 0.96, {"IFRS"}, "CapEx"),
    ],
    "InterestExpense": [
        Candidate("us-gaap:InterestExpense", 1.00, None, "InterestExpense"),
        Candidate("us-gaap:InterestExpenseOperating", 0.94, None, "InterestExpense"),
        Candidate("ifrs-full:FinanceCosts", 0.90, {"IFRS"}, "InterestExpense"),
    ],
    "DepAmort": [
        Candidate("us-gaap:DepreciationAndAmortization", 1.00, None, "DepAmort"),
        Candidate("us-gaap:DepreciationDepletionAndAmortization", 0.98, None, "DepAmort"),
        Candidate("us-gaap:Depreciation", 0.94, None, "DepAmort"),
        Candidate("ifrs-full:DepreciationAndAmortisationExpense", 0.98, {"IFRS"}, "DepAmort"),
    ],
    "LongTermDebt": [
        Candidate("us-gaap:LongTermDebtNoncurrent", 1.00, None, "LongTermDebt"),
        Candidate("us-gaap:LongTermDebt", 0.98, None, "LongTermDebt"),
        Candidate("ifrs-full:BorrowingsNoncurrent", 0.96, {"IFRS"}, "LongTermDebt"),
    ],
    "ShortTermDebt": [
        Candidate("us-gaap:ShortTermBorrowings", 1.00, None, "ShortTermDebt"),
        Candidate("us-gaap:DebtCurrent", 0.96, None, "ShortTermDebt"),
        Candidate("ifrs-full:BorrowingsCurrent", 0.94, {"IFRS"}, "ShortTermDebt"),
    ],
    "DebtCurrent": [
        Candidate("us-gaap:DebtCurrent", 1.00, None, "DebtCurrent"),
    ],
    "CurrentAssets": [
        Candidate("us-gaap:AssetsCurrent", 1.00, None, "CurrentAssets"),
        Candidate("ifrs-full:CurrentAssets", 0.98, {"IFRS"}, "CurrentAssets"),
    ],
    "CurrentLiabilities": [
        Candidate("us-gaap:LiabilitiesCurrent", 1.00, None, "CurrentLiabilities"),
        Candidate("ifrs-full:CurrentLiabilities", 0.98, {"IFRS"}, "CurrentLiabilities"),
    ],
    "Inventories": [
        Candidate("us-gaap:InventoryNet", 1.00, None, "Inventories"),
        Candidate("us-gaap:Inventory", 0.97, None, "Inventories"),
        Candidate("ifrs-full:Inventories", 0.98, {"IFRS"}, "Inventories"),
    ],
    "AccountsReceivable": [
        Candidate("us-gaap:AccountsReceivableNetCurrent", 1.00, None, "AccountsReceivable"),
        Candidate("us-gaap:AccountsReceivableTradeNetCurrent", 0.96, None, "AccountsReceivable"),
        Candidate("us-gaap:ReceivablesNetCurrent", 0.95, None, "AccountsReceivable"),
        Candidate("ifrs-full:TradeAndOtherReceivablesCurrent", 0.93, {"IFRS"}, "AccountsReceivable"),
    ],
    "CostOfGoodsSold": [
        Candidate("us-gaap:CostOfGoodsSold", 1.00, None, "CostOfGoodsSold"),
        Candidate("us-gaap:CostOfRevenue", 0.98, None, "CostOfGoodsSold"),
        Candidate("ifrs-full:CostOfSales", 0.98, {"IFRS"}, "CostOfGoodsSold"),
    ],
    "IncomeTaxExpense": [
        Candidate("us-gaap:IncomeTaxExpenseBenefit", 1.00, None, "IncomeTaxExpense"),
        Candidate("ifrs-full:IncomeTaxExpense", 0.98, {"IFRS"}, "IncomeTaxExpense"),
    ],
    "PreTaxIncome": [
        Candidate("us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", 1.00, None, "PreTaxIncome"),
        Candidate("us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxes", 0.98, None, "PreTaxIncome"),
        Candidate("ifrs-full:ProfitLossBeforeTax", 0.98, {"IFRS"}, "PreTaxIncome"),
    ],
}

# --------------------- 직접 성장률 채굴 ------------------------
# 확장 태그에서 "성장률/증가율/증감률/변동"을 캡처하기 위한 패턴
# Tax, Reconciliation, Enacted 등 관련 없는 키워드는 제외
_DIRECT_GROWTH_PATS = {
    "RevenueGrowthYoY": [
        r"(?:^|:)Revenue(?!.*Tax)(?!.*Reconciliation).*(Growth|Increase|Change).*(YoY|YearOverYear|Percent|Percentage|Rate)$",
        r"(?:^|:)(YoY|YearOverYear).*Revenue(?!.*Tax)(?!.*Reconciliation).*(Percent|Percentage|Rate)$",
        r"(?:^|:)ChangeInRevenue$"  # 절대 증가액(USD)일 가능성 -> 후처리
    ],
    "NetIncomeGrowthYoY": [
        r"(?:^|:)(Net)?Income(Loss)?(?!.*Tax)(?!.*Reconciliation)(?!.*Enacted).*(Growth|Increase|Change).*(YoY|YearOverYear|Percent|Percentage|Rate)$",
        r"(?:^|:)(YoY|YearOverYear).*(Net)?Income(Loss)?(?!.*Tax)(?!.*Reconciliation)(?!.*Enacted).*(Percent|Percentage|Rate)$",
        r"(?:^|:)ChangeInNetIncome(Loss)?$"
    ],
    "CFOGrowthYoY": [
        r"(?:^|:)(Operating|Net)?Cash.*(Flow|Provided).*From.*Operating.*(Growth|Increase|Change).*(YoY|YearOverYear|Percent|Percentage|Rate)$",
        r"(?:^|:)ChangeInNetCashProvidedByUsedInOperatingActivities$"
    ],
    "AssetGrowthRate": [
        r"(?:^|:)Assets.*(Growth|Increase|Change).*(YoY|YearOverYear|Percent|Percentage|Rate)$",
        r"(?:^|:)ChangeInAssets$"
    ],
}

# direct-growth 태그 검증을 위한 블랙리스트 키워드
_DIRECT_GROWTH_BLACKLIST = [
    "Tax", "Reconciliation", "Enacted", "RateChange", "TaxRate", 
    "IncomeTax", "TaxExpense", "TaxBenefit", "TaxProvision"
]

def _is_valid_direct_growth_tag(qname: str, metric_name: str) -> bool:
    """
    direct-growth 태그가 실제로 해당 메트릭과 관련있는지 검증
    - Tax, Reconciliation, Enacted 등 관련 없는 키워드 블랙리스트 체크
    """
    qn_upper = qname.upper()
    for blacklisted in _DIRECT_GROWTH_BLACKLIST:
        if blacklisted.upper() in qn_upper:
            return False
    return True

def _mine_direct_growth_candidates(facts_json: dict, metric_name: str) -> List[str]:
    out=[]; facts=facts_json.get("facts") or {}
    pats = _DIRECT_GROWTH_PATS.get(metric_name, [])
    for tax, items in facts.items():
        for tag in items.keys():
            qn=f"{tax}:{tag}"
            if any(re.search(rx, qn, re.IGNORECASE) for rx in pats):
                if _is_valid_direct_growth_tag(qn, metric_name):
                    out.append(qn)
    return out

# --------------------- 간단한 유틸리티 -----------------------------
def safe_float(x) -> Optional[float]:
    try:
        if x is None: return None
        if isinstance(x, (int,float)): return float(x)
        s = str(x).strip()
        if s == "": return None
        return float(s)
    except Exception:
        return None

def add_row(rows: List[dict], company_meta: dict, fy: int, metric: str, is_derived: bool,
            value: Optional[float], unit: str, period_type: str, end: str, form: str, accn: str,
            source_type: str, selected_tag: str, composite_name: str, computed_from: str,
            confidence: Optional[float], reason: str, components_obj=None):
    """
    tags.csv(원복 스키마) 한 줄 추가
    """
    rows.append({
        "cik": company_meta.get("cik",""),
        "symbol": company_meta.get("symbol",""),
        "name": company_meta.get("name",""),
        "sector": company_meta.get("sector",""),
        "industry": company_meta.get("industry",""),
        "sic": company_meta.get("sic",""),
        "sic_description": company_meta.get("sic_description",""),
        "fye": company_meta.get("fye",""),
        "fy": str(fy),
        "metric": metric,
        "is_derived": "true" if is_derived else "false",
        "value": "" if value is None else f"{float(value):.6f}",
        "unit": unit or "",
        "period_type": period_type or "",
        "end": end or "",
        "form": form or "",
        "accn": accn or "",
        "source_type": source_type or "",
        "selected_tag": selected_tag or "",
        "composite_name": composite_name or "",
        "computed_from": computed_from or "",
        "confidence": "" if confidence is None else f"{float(confidence):.3f}",
        "reason": reason or "",
        "components": "[]" if not components_obj else json.dumps(components_obj, ensure_ascii=False)
    })

# --------------------- 선택기 (연간 / 시점) --------------
def pick_best_annual(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger,
                     prefer_unit="USD", tol_days=90, accept_missing_fp=True):
    unit_map = get_unit_records(facts_json, qname)
    if not unit_map:
        dbg.log(f"[annual] no units for {qname}")
        return None
    anchors = anchors_for_fy(fy, submissions)
    pool=[]; order=[prefer_unit]+[u for u in unit_map if u!=prefer_unit]
    for unit in order:
        for rec in unit_map.get(unit, []):
            if not isinstance(rec.get("val"), (int,float)): continue
            pool.append((unit, rec))

    pass1=[(u,r) for (u,r) in pool if (r.get("fp") or "").upper() in ("FY","CY","FYR")]
    chosen = smart_pick([r for (_,r) in pass1], anchors, tol_days, dbg)
    if chosen:
        chosen_unit = [u for (u,r) in pass1 if r is chosen][0]
        return ("annual", {"unit":chosen_unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":chosen.get("fp"),
                           "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")})

    pass2=[(u,r) for (u,r) in pool if r.get("qtrs")==4]
    chosen = smart_pick([r for (_,r) in pass2], anchors, tol_days, dbg)
    if chosen:
        chosen_unit = [u for (u,r) in pass2 if r is chosen][0]
        return ("ytd-q4", {"unit":chosen_unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":"FY",
                           "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")})

    if accept_missing_fp:
        chosen = smart_pick([r for (_,r) in pool], anchors, tol_days, dbg)
        if chosen:
            chosen_unit = [u for (u,r) in pool if r is chosen][0]
            return ("lenient", {"unit":chosen_unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":chosen.get("fp") or "",
                                "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")})
    return None

def pick_best_instant(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger,
                      prefer_unit="USD", tol_days=120):
    unit_map = get_unit_records(facts_json, qname)
    if not unit_map:
        dbg.log(f"[instant] no units for %s" % qname)
        return None
    anchors = anchors_for_fy(fy, submissions)
    pool=[]
    order=[prefer_unit]+[u for u in unit_map if u!=prefer_unit]
    for unit in order:
        for rec in unit_map.get(unit, []):
            if not isinstance(rec.get("val"), (int,float)): continue
            pool.append((unit, rec))
    chosen = smart_pick([r for (_,r) in pool], anchors, tol_days, dbg)
    if chosen:
        unit = [u for (u,r) in pool if r is chosen][0]
        return {"unit":unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":chosen.get("fp"),
                "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")}
    return None

# --------------------- 간단한 선택기 (기본) -----------------
def select_base_duration(facts, fy, submissions, dbg, metric_name, prefer_unit="USD", tol_days=90, sector=None):
    best=None
    # sector 정보 추출 (submissions에서)
    if sector is None:
        sector = infer_sector_industry(submissions)[0]
    
    for widen in (0, 60, 120, 180):
        for cand in CANDIDATES.get(metric_name, []):
            # industry_only 필터링: None이면 모든 섹터, 지정되면 해당 섹터만
            if cand.industry_only is not None and sector not in cand.industry_only:
                continue
            
            res = pick_best_annual(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen, accept_missing_fp=True)
            if res and res[1]:
                p=res[1]; typ=res[0]
                industry_hit = (cand.industry_only is None) or (sector in cand.industry_only)
                score=cand.base_score + (0.012 if typ=="annual" else (-0.004 if typ=="ytd-q4" else -0.01)) \
                      + score_adj(p["form"], p["unit"], p["fp"], bool(p["segment"]), industry_hit) - (0.02 if widen else 0.0)
                out={"source_type":typ,"qname":cand.qname,"normalized_as":metric_name,"value":p["val"],"unit":p["unit"],
                     "end":p["end"],"form":p["form"],"accn":p["accn"],"confidence":max(0,min(1,score))}
                if (best is None) or (score>best[0]) or (math.isclose(score,best[0]) and out["end"]>(best[1]["end"] or "")):
                    best=(score,out)
        if best: return best[1]
    return {"source_type":"none","reason":"no candidate matched"}

def select_base_instant(facts, fy, submissions, dbg, metric_name, prefer_unit="USD", tol_days=120, sector=None):
    best=None
    # sector 정보 추출 (submissions에서)
    if sector is None:
        sector = infer_sector_industry(submissions)[0]
    
    for widen in (0, 60, 120, 180):
        for cand in CANDIDATES.get(metric_name, []):
            # industry_only 필터링: None이면 모든 섹터, 지정되면 해당 섹터만
            if cand.industry_only is not None and sector not in cand.industry_only:
                continue
            
            p = pick_best_instant(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen)
            if p:
                industry_hit = (cand.industry_only is None) or (sector in cand.industry_only)
                score=cand.base_score + score_adj(p.get("form"), p.get("unit"), p.get("fp"), bool(p.get("segment")), industry_hit) - (0.02 if widen else 0.0)
                out={"source_type":"instant","qname":cand.qname,"normalized_as":metric_name,"value":p["val"],"unit":p["unit"],
                     "end":p["end"],"form":p["form"],"accn":p["accn"],"confidence":max(0,min(1,score))}
                if (best is None) or (score>best[0]) or (math.isclose(score,best[0]) and out["end"]>(best[1]["end"] or "")):
                    best=(score,out)
        if best: return best[1]
    return {"source_type":"none","reason":"no candidate matched"}

# 편의 래퍼 함수들
def select_revenue(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "Revenue", prefer_unit, tol_days)

def select_operating_income(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "OperatingIncome", prefer_unit, tol_days)

def select_net_income(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "NetIncome", prefer_unit, tol_days)

def select_cfo(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "CFO", prefer_unit, tol_days)

def select_gross_profit(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "GrossProfit", prefer_unit, tol_days)

def select_eps_diluted(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    res = select_base_duration(facts, fy, submissions, dbg, "EPSDiluted", prefer_unit, tol_days)
    if res.get("source_type") != "none":
        return res
    ni = select_net_income(facts, fy, submissions, dbg, prefer_unit, tol_days)
    sh = select_base_duration(facts, fy, submissions, dbg, "DilutedShares", prefer_unit, tol_days)
    if ni.get("source_type") != "none" and sh.get("source_type") != "none" and safe_float(sh.get("value")):
        eps = float(ni["value"]) / float(sh["value"])
        unit = "USDPerShare"
        return {"source_type":"derived","qname":"(NI/WeightedAvgDilutedShares)","normalized_as":"EPSDiluted","value":eps,"unit":unit,
                "end":ni["end"],"form":ni["form"],"accn":ni["accn"],"confidence":0.85}
    return {"source_type":"none","reason":"EPS not found"}

def select_capex(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "CapEx", prefer_unit, tol_days)

def select_interest_expense(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "InterestExpense", prefer_unit, tol_days)

def select_dep_amort(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "DepAmort", prefer_unit, tol_days)

def select_assets(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "Assets", prefer_unit, tol_days)

def select_liabilities(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "Liabilities", prefer_unit, tol_days)

def select_equity(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "Equity", prefer_unit, tol_days)

def select_longterm_debt(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "LongTermDebt", prefer_unit, tol_days)

def select_shortterm_debt(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    dc = select_base_instant(facts, fy, submissions, dbg, "DebtCurrent", prefer_unit, tol_days)
    if dc.get("source_type") != "none": return dc
    return select_base_instant(facts, fy, submissions, dbg, "ShortTermDebt", prefer_unit, tol_days)

def select_current_assets(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "CurrentAssets", prefer_unit, tol_days)

def select_current_liabilities(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "CurrentLiabilities", prefer_unit, tol_days)

def select_inventories(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "Inventories", prefer_unit, tol_days)

def select_accounts_receivable(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    return select_base_instant(facts, fy, submissions, dbg, "AccountsReceivable", prefer_unit, tol_days)

def select_cogs(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    res = select_base_duration(facts, fy, submissions, dbg, "CostOfGoodsSold", prefer_unit, tol_days)
    if res.get("source_type") != "none":
        return res
    rev = select_revenue(facts, fy, submissions, dbg, prefer_unit, tol_days)
    gp  = select_gross_profit(facts, fy, submissions, dbg, prefer_unit, tol_days)
    if rev.get("source_type") != "none" and gp.get("source_type") != "none":
        try:
            val = float(rev["value"]) - float(gp["value"])
            return {
                "source_type":"derived","qname":"derived:COGS","normalized_as":"CostOfGoodsSold",
                    "value": val, "unit": rev.get("unit",""), "end": rev.get("end",""),
                    "form": rev.get("form",""), "accn": rev.get("accn",""), "confidence": 0.60,
                "reason": "Derived as Revenue - GrossProfit", "components": ["Revenue","GrossProfit"]
            }
        except Exception:
            pass
    return {"source_type":"none","reason":"no COGS source or fallback"}

def select_income_tax_expense(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "IncomeTaxExpense", prefer_unit, tol_days)

def select_pretax_income(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    return select_base_duration(facts, fy, submissions, dbg, "PreTaxIncome", prefer_unit, tol_days)

# --------------------- 파생 헬퍼 -------------------------
def avg_two(a: float, b: float) -> Optional[float]:
    try: return (float(a) + float(b)) / 2.0
    except Exception: return None

def derive_total_debt(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=120):
    lt = select_longterm_debt(facts, fy, submissions, dbg, prefer_unit, tol_days)
    st = select_shortterm_debt(facts, fy, submissions, dbg, prefer_unit, tol_days)
    if lt.get("source_type") != "none" and st.get("source_type") != "none":
        val = float(lt["value"]) + float(st["value"])
        unit = lt["unit"] if lt["unit"] == st["unit"] else prefer_unit
        end = max(lt["end"], st["end"])
        return {"source_type":"derived","normalized_as":"TotalDebt","value":val,"unit":unit,"end":end,"form":lt["form"],"accn":None,"confidence":0.90}
    elif lt.get("source_type") != "none":
        return {"source_type":"partial","normalized_as":"TotalDebt","value":float(lt["value"]),"unit":lt["unit"],"end":lt["end"],"form":lt["form"],"accn":lt["accn"],"confidence":0.75}
    elif st.get("source_type") != "none":
        return {"source_type":"partial","normalized_as":"TotalDebt","value":float(st["value"]),"unit":st["unit"],"end":st["end"],"form":st["form"],"accn":st["accn"],"confidence":0.75}
    return {"source_type":"none","reason":"no debt components"}

# --------------------- Growth 전용 보강 ------------------------
def _pick_prior_year_relaxed(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger,
                              prefer_unit="USD", period_type="duration"):
    """
    전년도 데이터를 더 유연하게 추출하는 함수
    - Anchor 제약 완화: 전년도 전체 범위에서 가장 가까운 데이터 찾기
    - FY/FP 태그가 없어도 전년도 범위 내 데이터 수용
    - period_type이 "duration"이면 annual 데이터, "instant"이면 instant 데이터 검색
    """
    unit_map = get_unit_records(facts_json, qname)
    if not unit_map:
        dbg.log(f"[prior_year_relaxed] no units for {qname}")
        return None
    
    # 전년도 fiscal year end 기준으로 범위 계산
    fye = str(submissions.get("fiscalYearEnd") or "1231").strip()
    if not re.fullmatch(r"\d{4}", fye):
        fye = "1231"
    mm, dd = int(fye[:2]), int(fye[2:])
    
    # 전년도 범위: (fy-2, mm, dd) ~ (fy, mm, dd) ± 180일
    prior_fye = date(fy-1, mm, dd)
    prior_year_start = date(fy-2, mm, dd) + timedelta(days=1)
    prior_year_end = date(fy, mm, dd)
    
    # 더 넓은 범위 허용 (±180일)
    search_start = prior_year_start - timedelta(days=180)
    search_end = prior_year_end + timedelta(days=180)
    
    pool = []
    order = [prefer_unit] + [u for u in unit_map if u != prefer_unit]
    
    for unit in order:
        for rec in unit_map.get(unit, []):
            if not isinstance(rec.get("val"), (int, float)):
                continue
            rec_end = parse_date(rec.get("end"))
            if rec_end and search_start <= rec_end <= search_end:
                pool.append((unit, rec))
    
    if not pool:
        dbg.log(f"[prior_year_relaxed] no records in prior year range for {qname}")
        return None
    
    # instant 타입의 경우 간단하게 가장 가까운 것 선택
    if period_type == "instant":
        best = None
        best_dist = None
        for unit, rec in pool:
            rec_end = parse_date(rec.get("end"))
            if rec_end:
                dist = abs((rec_end - prior_fye).days)
                if best is None or dist < best_dist:
                    best = (unit, rec)
                    best_dist = dist
        if best:
            unit, rec = best
            return {"unit": unit, "end": rec.get("end"), "form": rec.get("form"),
                   "fp": rec.get("fp"), "val": float(rec.get("val")),
                   "accn": rec.get("accn"), "segment": rec.get("segment")}
        return None
    
    # duration 타입의 경우 FY/FP 태그 우선 선택
    # FY/FP 태그가 있는 레코드 우선 선택
    pass1 = [(u, r) for (u, r) in pool if (r.get("fp") or "").upper() in ("FY", "CY", "FYR")]
    if pass1:
        # 가장 가까운 end date 선택 (prior_fye에 가장 가까운 것)
        best = None
        best_dist = None
        for unit, rec in pass1:
            rec_end = parse_date(rec.get("end"))
            if rec_end:
                dist = abs((rec_end - prior_fye).days)
                if best is None or dist < best_dist:
                    best = (unit, rec)
                    best_dist = dist
        if best:
            unit, rec = best
            return ("annual", {"unit": unit, "end": rec.get("end"), "form": rec.get("form"),
                              "fp": rec.get("fp"), "val": float(rec.get("val")),
                              "accn": rec.get("accn"), "segment": rec.get("segment")})
    
    # qtrs==4인 레코드 선택
    pass2 = [(u, r) for (u, r) in pool if r.get("qtrs") == 4]
    if pass2:
        best = None
        best_dist = None
        for unit, rec in pass2:
            rec_end = parse_date(rec.get("end"))
            if rec_end:
                dist = abs((rec_end - prior_fye).days)
                if best is None or dist < best_dist:
                    best = (unit, rec)
                    best_dist = dist
        if best:
            unit, rec = best
            return ("ytd-q4", {"unit": unit, "end": rec.get("end"), "form": rec.get("form"),
                               "fp": "FY", "val": float(rec.get("val")),
                               "accn": rec.get("accn"), "segment": rec.get("segment")})
    
    # 모든 레코드 중 가장 가까운 것 선택
    best = None
    best_dist = None
    for unit, rec in pool:
        rec_end = parse_date(rec.get("end"))
        if rec_end:
            dist = abs((rec_end - prior_fye).days)
            if best is None or dist < best_dist:
                best = (unit, rec)
                best_dist = dist
    
    if best:
        unit, rec = best
        return ("lenient", {"unit": unit, "end": rec.get("end"), "form": rec.get("form"),
                            "fp": rec.get("fp") or "", "val": float(rec.get("val")),
                            "accn": rec.get("accn"), "segment": rec.get("segment")})
    
    return None

def _select_prior_year_with_fallback(facts, fy, submissions, dbg, metric_name, 
                                     prefer_unit="USD", base_tol_days=90, period_type="duration"):
    """
    전년도 데이터를 더 적극적으로 추출하는 헬퍼 함수
    - 먼저 _pick_prior_year_relaxed로 유연한 추출 시도
    - 실패 시 select_base_duration/select_base_instant로 fallback
    - tol_days를 단계적으로 증가 (base_tol_days+180, +240, +300, +360, +420, +540)
    """
    # 먼저 relaxed 방식으로 시도
    candidates = CANDIDATES.get(metric_name, [])
    if candidates:
        for cand in candidates:
            relaxed_result = _pick_prior_year_relaxed(facts, cand.qname, fy, submissions, dbg, prefer_unit, period_type)
            if relaxed_result:
                if period_type == "instant":
                    # instant 타입은 dict 직접 반환
                    p = relaxed_result
                    score = cand.base_score + score_adj(p.get("form"), p.get("unit"), p.get("fp"), bool(p.get("segment")), True) - 0.05
                    return {"source_type": "instant", "qname": cand.qname, "normalized_as": metric_name,
                           "value": p.get("val"), "unit": p.get("unit"), "end": p.get("end"),
                           "form": p.get("form"), "accn": p.get("accn"),
                           "confidence": max(0, min(1, score))}
                else:
                    # duration 타입은 (typ, dict) 튜플 반환
                    typ = relaxed_result[0]
                    p = relaxed_result[1]
                    score = cand.base_score + (0.012 if typ == "annual" else (-0.004 if typ == "ytd-q4" else -0.01)) \
                            + score_adj(p.get("form"), p.get("unit"), p.get("fp"), bool(p.get("segment")), True) - 0.05
                    return {"source_type": typ, "qname": cand.qname, "normalized_as": metric_name,
                           "value": p.get("val"), "unit": p.get("unit"), "end": p.get("end"),
                           "form": p.get("form"), "accn": p.get("accn"),
                           "confidence": max(0, min(1, score))}
    
    # relaxed 방식 실패 시 기존 로직으로 fallback
    if period_type == "duration":
        selector = select_base_duration
    elif period_type == "instant":
        selector = select_base_instant
    else:
        return {"source_type": "none", "reason": "invalid period_type"}
    
    # tol_days를 단계적으로 증가시키며 시도 (범위 확장)
    for tol_increment in (180, 240, 300, 360, 420, 540):
        result = selector(facts, fy-1, submissions, dbg, metric_name, prefer_unit, base_tol_days + tol_increment)
        if result.get("source_type") != "none" and safe_float(result.get("value")) is not None:
            return result
    
    return {"source_type": "none", "reason": "no prior year data found"}

def _direct_growth_pick(facts, fy, submissions, dbg, metric_name, prefer_unit="USD", tol_days=90):
    """
    direct-growth 후보를 캔 다음 최적 레코드를 고르고, (값, unit, end, form, accn, qname)을 반환
    """
    cands = _mine_direct_growth_candidates(facts, metric_name)
    best=None
    for qn in cands:
        res = pick_best_annual(facts, qn, fy, submissions, dbg, prefer_unit, tol_days, accept_missing_fp=True)
        if not res: 
            continue
        p = res[1]; typ=res[0]
        s = 0.90 + (0.012 if typ=="annual" else (-0.004 if typ=="ytd-q4" else -0.01)) \
            + score_adj(p["form"], p["unit"], p["fp"], bool(p["segment"]), True)
        item = {"qname": qn, "val": p["val"], "unit": p["unit"], "end": p["end"], "form": p["form"], "accn": p["accn"], "score": s, "fp": p.get("fp")}
        if (best is None) or (item["score"] > best["score"]):
            best = item
    return best

def _validate_direct_growth_value(dg_value: Optional[float], cur_base_value: Optional[float], metric_name: str) -> bool:
    """
    direct-growth 값이 비정상적으로 큰지 검증
    - 비정상 기준: 절대값 > 100 또는 현재 Base 메트릭 값의 10% 초과
    - 비정상 값이면 False 반환하여 derived-growth로 fallback
    """
    if dg_value is None or cur_base_value is None:
        return True  # None 값은 검증 통과 (다른 로직에서 처리)
    
    abs_value = abs(dg_value)
    # 절대값이 100보다 크면 비정상
    if abs_value > 100:
        return False
    
    # 현재 Base 메트릭 값의 10%를 초과하면 비정상
    if cur_base_value != 0 and abs_value > abs(cur_base_value) * 0.1:
        return False
    
    return True

def _normalize_direct_growth_ratio(dg: dict, tag_hint: str, cur_base_value: Optional[float] = None) -> Tuple[Optional[float], str, str]:
    """
    direct-growth 값 정규화:
      - unit이 ratio/pure/percent 계열이면 0~1 범위 비율로 환산(Percent면 /100)
      - 통화(USD) 등인 경우 None 반환(= 절대증가액으로 간주, 별도 처리)
      - 비정상적으로 큰 값은 None 반환하여 derived-growth로 fallback
    반환: (ratio_or_None, unit_out, reason_suffix)
    """
    if not dg: 
        return None, "", ""
    v = safe_float(dg.get("val"))
    if v is None: 
        return None, "", ""
    
    # 값 크기 검증 (cur_base_value가 제공된 경우)
    if cur_base_value is not None and not _validate_direct_growth_value(v, cur_base_value, tag_hint):
        return None, "", "invalid-direct-growth-value"
    
    unit = (dg.get("unit") or "").upper()
    qn   = dg.get("qname","")
    # ratio-like 판단
    if "PERCENT" in unit or re.search(r"Percent|Percentage|Rate", qn, re.IGNORECASE):
        # 50 (%), 12.3 (%) 등은 /100
        ratio = v/100.0 if abs(v) > 1.0 else v
        # 정규화 후에도 비정상 값인지 재검증
        if cur_base_value is not None and not _validate_direct_growth_value(ratio, cur_base_value, tag_hint):
            return None, "", "invalid-direct-growth-value"
        return ratio, "ratio", f"direct-growth({tag_hint}) percent→ratio"
    if unit in ("PURE","RATIO","X"):
        # 이미 비율로 가정
        # 단, 10 이상인 값은 퍼센트로 보고 /100
        ratio = v/100.0 if abs(v) > 5.0 else v
        # 정규화 후에도 비정상 값인지 재검증
        if cur_base_value is not None and not _validate_direct_growth_value(ratio, cur_base_value, tag_hint):
            return None, "", "invalid-direct-growth-value"
        return ratio, "ratio", f"direct-growth({tag_hint}) pure→ratio"
    if unit.startswith("USD"):  # USD, USD/share 등
        return None, unit, f"direct-growth({tag_hint}) absolute-delta"
    # 기타 단위: 값 범위를 보고 0~1 범위면 비율로 추정
    if abs(v) <= 5.0:
        return v, "ratio", f"direct-growth({tag_hint}) ratio(heuristic)"
    return None, unit or "", f"direct-growth({tag_hint}) absolute-delta-unknown"

def _compute_growth_from_base(cur_val: Optional[float], prev_val: Optional[float]) -> Optional[float]:
    try:
        if cur_val is None or prev_val is None:
            return None
        pv = float(prev_val)
        if pv == 0:
            return None
        return (float(cur_val) - pv) / pv
    except Exception:
        return None

def compute_growth_set(facts: dict, fy: int, submissions: dict, dbg: Debugger, prefer_unit="USD", tol_days=90):
    """
    Growth 4종만 계산하여 dict로 반환:
      {"RevenueGrowthYoY": {...}, "NetIncomeGrowthYoY": {...}, "CFOGrowthYoY": {...}, "AssetGrowthRate": {...}}
    각 항목은 None 또는 {value, unit, end, form, accn, source_type, selected_tag, reason, confidence, computed_from}
    """
    out = {}

    # helper: 현재/전년도 값 선택자들
    cur_rev = select_revenue(facts, fy, submissions, dbg, prefer_unit, tol_days)
    prv_rev = _select_prior_year_with_fallback(facts, fy, submissions, dbg, "Revenue", prefer_unit, tol_days, "duration")
    cur_ni  = select_net_income(facts, fy, submissions, dbg, prefer_unit, tol_days)
    prv_ni  = _select_prior_year_with_fallback(facts, fy, submissions, dbg, "NetIncome", prefer_unit, tol_days, "duration")
    cur_cfo = select_cfo(facts, fy, submissions, dbg, prefer_unit, tol_days)
    prv_cfo = _select_prior_year_with_fallback(facts, fy, submissions, dbg, "CFO", prefer_unit, tol_days, "duration")
    cur_as  = select_assets(facts, fy, submissions, dbg, prefer_unit, 120)
    prv_as  = _select_prior_year_with_fallback(facts, fy, submissions, dbg, "Assets", prefer_unit, 120, "instant")

    # 1) RevenueGrowthYoY
    try:
        dg = _direct_growth_pick(facts, fy, submissions, dbg, "RevenueGrowthYoY", prefer_unit, tol_days+30)
        cur_rev_val = safe_float(cur_rev.get("value"))
        ratio, unit_out, reason_sfx = _normalize_direct_growth_ratio(dg, "Revenue", cur_rev_val)
        
        # invalid-direct-growth-value인 경우 derived-growth로 fallback
        if reason_sfx == "invalid-direct-growth-value":
            dg = None
            ratio = None
        
        if ratio is None and dg is not None:
            # 절대증가액 -> 전년도로 나눠 비율화
            ratio = _compute_growth_from_base(cur_rev_val, safe_float(prv_rev.get("value")))
            unit_out = "ratio"
            reason = f"{reason_sfx}; normalized using current/prior revenue"
            conf = 0.88
            if (cur_rev.get("form") in ("10-K","20-F")) and (prv_rev.get("form") in ("10-K","20-F")): conf += 0.04
            out["RevenueGrowthYoY"] = {
                "value": ratio, "unit": unit_out, "end": cur_rev.get("end") or (dg.get("end") if dg else ""),
                "form": cur_rev.get("form") or (dg.get("form") if dg else ""), "accn": cur_rev.get("accn") or "",
                "source_type": "direct-growth-normalized", "selected_tag": dg.get("qname") if dg else "",
                "reason": reason, "confidence": conf, "computed_from":"Revenue(cur),Revenue(prior)"
            }
        elif ratio is not None:
            out["RevenueGrowthYoY"] = {
                "value": ratio, "unit": "ratio", "end": dg.get("end","") if dg else (cur_rev.get("end") or ""),
                "form": dg.get("form","") if dg else (cur_rev.get("form") or ""), "accn": dg.get("accn","") if dg else "",
                "source_type":"direct-growth", "selected_tag": dg.get("qname","") if dg else "",
                "reason": f"{reason_sfx}", "confidence": 0.94, "computed_from":"direct-growth"
            }
        else:
            # direct 없음 또는 invalid -> 기본식
            ratio = _compute_growth_from_base(cur_rev_val, safe_float(prv_rev.get("value")))
            if ratio is not None:
                conf = 0.90
                if (cur_rev.get("form") in ("10-K","20-F")) and (prv_rev.get("form") in ("10-K","20-F")): conf += 0.04
                out["RevenueGrowthYoY"] = {
                    "value": ratio, "unit": "ratio", "end": cur_rev.get("end") or "",
                    "form": cur_rev.get("form") or "", "accn": cur_rev.get("accn") or "",
                    "source_type":"derived-growth", "selected_tag": "",
                    "reason":"(cur - prior) / prior (Revenue)", "confidence": conf, "computed_from":"Revenue(cur),Revenue(prior)"
                }
            else:
                out["RevenueGrowthYoY"] = None
    except Exception as e:
        dbg.log(f"[growth] RevenueGrowthYoY fail: {e}")
        out["RevenueGrowthYoY"] = None

    # 2) NetIncomeGrowthYoY
    try:
        dg = _direct_growth_pick(facts, fy, submissions, dbg, "NetIncomeGrowthYoY", prefer_unit, tol_days+30)
        cur_ni_val = safe_float(cur_ni.get("value"))
        ratio, unit_out, reason_sfx = _normalize_direct_growth_ratio(dg, "NetIncome", cur_ni_val)
        
        # invalid-direct-growth-value인 경우 derived-growth로 fallback
        if reason_sfx == "invalid-direct-growth-value":
            dg = None
            ratio = None
        
        if ratio is None and dg is not None:
            ratio = _compute_growth_from_base(cur_ni_val, safe_float(prv_ni.get("value")))
            unit_out = "ratio"
            reason = f"{reason_sfx}; normalized using current/prior net income"
            conf = 0.88
            if (cur_ni.get("form") in ("10-K","20-F")) and (prv_ni.get("form") in ("10-K","20-F")): conf += 0.04
            out["NetIncomeGrowthYoY"] = {
                "value": ratio, "unit": unit_out, "end": cur_ni.get("end") or (dg.get("end") if dg else ""),
                "form": cur_ni.get("form") or (dg.get("form") if dg else ""), "accn": cur_ni.get("accn") or "",
                "source_type": "direct-growth-normalized", "selected_tag": dg.get("qname") if dg else "",
                "reason": reason, "confidence": conf, "computed_from":"NetIncome(cur),NetIncome(prior)"
            }
        elif ratio is not None:
            out["NetIncomeGrowthYoY"] = {
                "value": ratio, "unit": "ratio", "end": dg.get("end","") if dg else (cur_ni.get("end") or ""),
                "form": dg.get("form","") if dg else (cur_ni.get("form") or ""), "accn": dg.get("accn","") if dg else "",
                "source_type":"direct-growth", "selected_tag": dg.get("qname","") if dg else "",
                "reason": f"{reason_sfx}", "confidence": 0.94, "computed_from":"direct-growth"
            }
        else:
            # direct 없음 또는 invalid -> 기본식
            ratio = _compute_growth_from_base(cur_ni_val, safe_float(prv_ni.get("value")))
            if ratio is not None:
                conf = 0.90
                if (cur_ni.get("form") in ("10-K","20-F")) and (prv_ni.get("form") in ("10-K","20-F")): conf += 0.04
                out["NetIncomeGrowthYoY"] = {
                    "value": ratio, "unit": "ratio", "end": cur_ni.get("end") or "",
                    "form": cur_ni.get("form") or "", "accn": cur_ni.get("accn") or "",
                    "source_type":"derived-growth", "selected_tag": "",
                    "reason":"(cur - prior) / prior (NetIncome)", "confidence": conf, "computed_from":"NetIncome(cur),NetIncome(prior)"
                }
            else:
                out["NetIncomeGrowthYoY"] = None
    except Exception as e:
        dbg.log(f"[growth] NetIncomeGrowthYoY fail: {e}")
        out["NetIncomeGrowthYoY"] = None

    # 3) CFOGrowthYoY
    try:
        dg = _direct_growth_pick(facts, fy, submissions, dbg, "CFOGrowthYoY", prefer_unit, tol_days+30)
        cur_cfo_val = safe_float(cur_cfo.get("value"))
        ratio, unit_out, reason_sfx = _normalize_direct_growth_ratio(dg, "CFO", cur_cfo_val)
        
        # invalid-direct-growth-value인 경우 derived-growth로 fallback
        if reason_sfx == "invalid-direct-growth-value":
            dg = None
            ratio = None
        
        if ratio is None and dg is not None:
            ratio = _compute_growth_from_base(cur_cfo_val, safe_float(prv_cfo.get("value")))
            unit_out = "ratio"
            reason = f"{reason_sfx}; normalized using current/prior CFO"
            conf = 0.88
            if (cur_cfo.get("form") in ("10-K","20-F")) and (prv_cfo.get("form") in ("10-K","20-F")): conf += 0.04
            out["CFOGrowthYoY"] = {
                "value": ratio, "unit": unit_out, "end": cur_cfo.get("end") or (dg.get("end") if dg else ""),
                "form": cur_cfo.get("form") or (dg.get("form") if dg else ""), "accn": cur_cfo.get("accn") or "",
                "source_type": "direct-growth-normalized", "selected_tag": dg.get("qname") if dg else "",
                "reason": reason, "confidence": conf, "computed_from":"CFO(cur),CFO(prior)"
            }
        elif ratio is not None:
            out["CFOGrowthYoY"] = {
                "value": ratio, "unit": "ratio", "end": dg.get("end","") if dg else (cur_cfo.get("end") or ""),
                "form": dg.get("form","") if dg else (cur_cfo.get("form") or ""), "accn": dg.get("accn","") if dg else "",
                "source_type":"direct-growth", "selected_tag": dg.get("qname","") if dg else "",
                "reason": f"{reason_sfx}", "confidence": 0.94, "computed_from":"direct-growth"
            }
        else:
            # direct 없음 또는 invalid -> 기본식
            ratio = _compute_growth_from_base(cur_cfo_val, safe_float(prv_cfo.get("value")))
            if ratio is not None:
                conf = 0.90
                if (cur_cfo.get("form") in ("10-K","20-F")) and (prv_cfo.get("form") in ("10-K","20-F")): conf += 0.04
                out["CFOGrowthYoY"] = {
                    "value": ratio, "unit": "ratio", "end": cur_cfo.get("end") or "",
                    "form": cur_cfo.get("form") or "", "accn": cur_cfo.get("accn") or "",
                    "source_type":"derived-growth", "selected_tag": "",
                    "reason":"(cur - prior) / prior (CFO)", "confidence": conf, "computed_from":"CFO(cur),CFO(prior)"
                }
            else:
                out["CFOGrowthYoY"] = None
    except Exception as e:
        dbg.log(f"[growth] CFOGrowthYoY fail: {e}")
        out["CFOGrowthYoY"] = None

    # 4) AssetGrowthRate (instant)
    try:
        dg = _direct_growth_pick(facts, fy, submissions, dbg, "AssetGrowthRate", prefer_unit, 120)
        cur_as_val = safe_float(cur_as.get("value"))
        ratio, unit_out, reason_sfx = _normalize_direct_growth_ratio(dg, "Assets", cur_as_val)
        
        # invalid-direct-growth-value인 경우 derived-growth로 fallback
        if reason_sfx == "invalid-direct-growth-value":
            dg = None
            ratio = None
        
        if ratio is None and dg is not None:
            ratio = _compute_growth_from_base(cur_as_val, safe_float(prv_as.get("value")))
            unit_out = "ratio"
            reason = f"{reason_sfx}; normalized using current/prior assets"
            conf = 0.88
            if (cur_as.get("form") in ("10-K","20-F")) and (prv_as.get("form") in ("10-K","20-F")): conf += 0.04
            out["AssetGrowthRate"] = {
                "value": ratio, "unit": unit_out, "end": cur_as.get("end") or (dg.get("end") if dg else ""),
                "form": cur_as.get("form") or (dg.get("form") if dg else ""), "accn": cur_as.get("accn") or "",
                "source_type": "direct-growth-normalized", "selected_tag": dg.get("qname") if dg else "",
                "reason": reason, "confidence": conf, "computed_from":"Assets(cur),Assets(prior)"
            }
        elif ratio is not None:
            out["AssetGrowthRate"] = {
                "value": ratio, "unit": "ratio", "end": dg.get("end","") if dg else (cur_as.get("end") or ""),
                "form": dg.get("form","") if dg else (cur_as.get("form") or ""), "accn": dg.get("accn","") if dg else "",
                "source_type":"direct-growth", "selected_tag": dg.get("qname","") if dg else "",
                "reason": f"{reason_sfx}", "confidence": 0.94, "computed_from":"direct-growth"
            }
        else:
            # direct 없음 또는 invalid -> 기본식
            ratio = _compute_growth_from_base(cur_as_val, safe_float(prv_as.get("value")))
            if ratio is not None:
                conf = 0.90
                if (cur_as.get("form") in ("10-K","20-F")) and (prv_as.get("form") in ("10-K","20-F")): conf += 0.04
                out["AssetGrowthRate"] = {
                    "value": ratio, "unit": "ratio", "end": cur_as.get("end") or "",
                    "form": cur_as.get("form") or "", "accn": cur_as.get("accn") or "",
                    "source_type":"derived-growth", "selected_tag": "",
                    "reason":"(cur - prior) / prior (Assets)", "confidence": conf, "computed_from":"Assets(cur),Assets(prior)"
                }
            else:
                out["AssetGrowthRate"] = None

    except Exception as e:
        dbg.log(f"[growth] AssetGrowthRate fail: {e}")
        out["AssetGrowthRate"] = None

    return out

# --------------------- 기타 파생 메트릭 -------------------
def compute_other_derived(facts, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    rows = []
    rev  = select_revenue(facts, fy, submissions, dbg, prefer_unit, tol_days)
    rev1 = select_revenue(facts, fy-1, submissions, dbg, prefer_unit, tol_days+90)
    ni   = select_net_income(facts, fy, submissions, dbg, prefer_unit, tol_days)
    oi   = select_operating_income(facts, fy, submissions, dbg, prefer_unit, tol_days)
    gp   = select_gross_profit(facts, fy, submissions, dbg, prefer_unit, tol_days)
    cfo  = select_cfo(facts, fy, submissions, dbg, prefer_unit, tol_days)
    capex= select_capex(facts, fy, submissions, dbg, prefer_unit, tol_days)
    dpa  = select_dep_amort(facts, fy, submissions, dbg, prefer_unit, tol_days)
    iexp = select_interest_expense(facts, fy, submissions, dbg, prefer_unit, tol_days)
    eq   = select_equity(facts, fy, submissions, dbg, prefer_unit, 120)
    eq1  = select_equity(facts, fy-1, submissions, dbg, prefer_unit, 120)
    assets = select_assets(facts, fy, submissions, dbg, prefer_unit, 120)
    assets1= select_assets(facts, fy-1, submissions, dbg, prefer_unit, 180)

    # Margins
    if gp.get("source_type") != "none" and rev.get("source_type") != "none" and safe_float(rev["value"]):
        rows.append(("GrossMargin", float(gp["value"])/float(rev["value"]), "ratio", rev["end"], rev["form"], rev["accn"],
                     "derived", "", "GrossProfit;Revenue", 0.90, ""))

    if oi.get("source_type") != "none" and rev.get("source_type") != "none" and safe_float(rev["value"]):
        rows.append(("OperatingMargin", float(oi["value"])/float(rev["value"]), "ratio", rev["end"], rev["form"], rev["accn"],
                     "derived", "", "OperatingIncome;Revenue", 0.90, ""))

    if ni.get("source_type") != "none" and rev.get("source_type") != "none" and safe_float(rev["value"]):
        rows.append(("NetProfitMargin", float(ni["value"])/float(rev["value"]), "ratio", rev["end"], rev["form"], rev["accn"],
                     "derived", "", "NetIncome;Revenue", 0.90, ""))

    if ni.get("source_type") != "none" and eq.get("source_type") != "none" and eq1.get("source_type") != "none":
        avg_eq = avg_two(eq["value"], eq1["value"])
        if avg_eq and float(avg_eq) != 0:
            rows.append(("ROE", float(ni["value"])/float(avg_eq), "ratio", eq["end"], eq["form"], eq["accn"],
                         "derived", "", "NetIncome;Equity;Equity_Prior", 0.90, ""))

    if cfo.get("source_type") != "none" and capex.get("source_type") != "none":
        rows.append(("FreeCashFlow", float(cfo["value"]) - float(capex["value"]), cfo["unit"], cfo["end"], cfo["form"], cfo["accn"],
                     "derived", "", "CFO;CapEx", 0.88, ""))

    if oi.get("source_type") != "none" and dpa.get("source_type") != "none":
        ebitda_val = float(oi["value"]) + float(dpa["value"])
        rows.append(("EBITDA", ebitda_val, oi["unit"], oi["end"], oi["form"], oi["accn"],
                     "derived", "", "OperatingIncome;DepAmort", 0.88, ""))
        if rev.get("source_type") != "none" and safe_float(rev["value"]):
            rows.append(("EBITDAMargin", ebitda_val/float(rev["value"]), "ratio", rev["end"], rev["form"], rev["accn"],
                         "derived", "", "EBITDA;Revenue", 0.86, ""))

    if (oi.get("source_type") != "none" or (ni.get("source_type") != "none" and dpa.get("source_type") != "none")) \
        and iexp.get("source_type") != "none" and safe_float(iexp["value"]):
        ebit_approx = float(oi["value"]) if oi.get("source_type") != "none" else (float(ni["value"]) + float(dpa["value"]))
        rows.append(("InterestCoverage", ebit_approx/float(iexp["value"]), "x", iexp["end"], iexp["form"], iexp["accn"],
                     "derived", "", "OperatingIncome_or_NIplusDA;InterestExpense", 0.86, ""))

    td = derive_total_debt(facts, fy, submissions, dbg, prefer_unit, 120)
    if (td.get("source_type") != "none") and eq.get("source_type") != "none" and safe_float(eq["value"]):
        rows.append(("DebtToEquity", float(td["value"])/float(eq["value"]), "ratio", eq["end"], eq["form"], eq["accn"],
                     "derived", "", "TotalDebt;Equity", 0.86, ""))

    # Liquidity
    ca  = select_current_assets(facts, fy, submissions, dbg, prefer_unit, 120)
    cl  = select_current_liabilities(facts, fy, submissions, dbg, prefer_unit, 120)
    inv = select_inventories(facts, fy, submissions, dbg, prefer_unit, 120)
    if ca.get("source_type") != "none" and cl.get("source_type") != "none" and safe_float(cl["value"]):
        rows.append(("CurrentRatio", float(ca["value"])/float(cl["value"]), "ratio",
                     ca.get("end") or cl.get("end") or "", ca.get("form") or cl.get("form") or "", ca.get("accn") or cl.get("accn") or "",
                     "derived", "", "CurrentAssets;CurrentLiabilities", 0.86, ""))
    if ca.get("source_type") != "none" and inv.get("source_type") != "none" and cl.get("source_type") != "none" and safe_float(cl["value"]):
        try:
            quick = (float(ca["value"]) - float(inv["value"])) / float(cl["value"])
            rows.append(("QuickRatio", quick, "ratio",
                         ca.get("end") or cl.get("end") or "", ca.get("form") or cl.get("form") or "", ca.get("accn") or cl.get("accn") or "",
                         "derived", "", "CurrentAssets;Inventories;CurrentLiabilities", 0.86, ""))
        except Exception:
            pass

    # Turnover
    inv1 = select_inventories(facts, fy-1, submissions, dbg, prefer_unit, 120)
    ar   = select_accounts_receivable(facts, fy, submissions, dbg, prefer_unit, 120)
    ar1  = select_accounts_receivable(facts, fy-1, submissions, dbg, prefer_unit, 120)
    cogs = select_cogs(facts, fy, submissions, dbg, prefer_unit, 90)
    def _avg(v0, v1):
        try:
            a = float(v0); b = float(v1); d = (a + b)/2.0
            return d if d != 0 else None
        except Exception:
            return None
    if cogs.get("source_type") != "none" and inv.get("source_type") != "none":
        avg_inv = _avg(inv["value"], inv1.get("value", inv["value"]))
        if avg_inv:
            rows.append(("InventoryTurnover", float(cogs["value"])/avg_inv, "turns", cogs.get("end",""),
                         cogs.get("form",""), cogs.get("accn",""),
                         "derived", "", "CostOfGoodsSold;Inventories;Inventories_Prior", 0.84, ""))
    if rev.get("source_type") != "none" and ar.get("source_type") != "none":
        avg_ar = _avg(ar["value"], ar1.get("value", ar["value"]))
        if avg_ar:
            rows.append(("ReceivablesTurnover", float(rev["value"])/avg_ar, "turns", rev.get("end",""),
                         rev.get("form",""), rev.get("accn",""),
                         "derived", "", "Revenue;AccountsReceivable;AccountsReceivable_Prior", 0.84, ""))

    # Cash flow coverage
    if cfo.get("source_type") != "none" and cl.get("source_type") != "none" and safe_float(cl["value"]):
        rows.append(("OperatingCashFlowRatio", float(cfo["value"])/float(cl["value"]), "ratio", cfo.get("end",""),
                     cfo.get("form",""), cfo.get("accn",""),
                     "derived", "", "CFO;CurrentLiabilities", 0.84, ""))

    # Asset turnover, Equity ratio
    assets1 = assets1
    if assets.get("source_type") != "none" and assets1.get("source_type") != "none":
        avg_assets = avg_two(assets["value"], assets1.get("value", assets["value"]))
        if avg_assets:
            rows.append(("AssetTurnover", float(rev["value"])/avg_assets if (rev.get("source_type")!="none" and safe_float(rev["value"])) else None,
                        "ratio", rev.get("end",""), rev.get("form",""), rev.get("accn",""),
                        "derived", "", "Revenue;Assets;Assets_Prior", 0.84, ""))
    if select_equity and assets.get("source_type") != "none" and safe_float(assets["value"]):
        rows.append(("EquityRatio", float(eq["value"]) / float(assets["value"]) if (eq.get("source_type")!="none" and safe_float(eq["value"])) else None,
                    "ratio", assets.get("end",""),
                    assets.get("form",""), assets.get("accn",""), "derived", "", "Equity;Assets", 0.84, ""))

    # ROIC (NOPAT/InvestedCapital)
    pre_tax = select_pretax_income(facts, fy, submissions, dbg, prefer_unit, tol_days)
    tax_exp = select_income_tax_expense(facts, fy, submissions, dbg, prefer_unit, tol_days)
    lt_debt = select_longterm_debt(facts, fy, submissions, dbg, prefer_unit, 120)
    st_debt = select_shortterm_debt(facts, fy, submissions, dbg, prefer_unit, 120)
    cash    = select_base_instant(facts, fy, submissions, dbg, "CashAndCashEquivalents", prefer_unit, 120)

    tot_debt_val = 0.0
    for d in (lt_debt, st_debt):
        if d.get("source_type") != "none" and safe_float(d.get("value")) is not None:
            tot_debt_val += float(d["value"])

    if pre_tax.get("source_type") != "none" and tax_exp.get("source_type") != "none" and oi.get("source_type") != "none":
        try:
            tr = float(tax_exp["value"]) / float(pre_tax["value"]) if safe_float(pre_tax["value"]) not in (None, 0.0) else None
            if tr is not None and 0.0 <= tr <= 1.0 and safe_float(oi.get("value")) is not None:
                nopat = float(oi["value"]) * (1.0 - tr)
                invcap = tot_debt_val + (float(eq["value"]) if eq.get("source_type") != "none" and safe_float(eq.get("value")) is not None else 0.0) \
                         - (float(cash["value"]) if cash and cash.get("source_type") != "none" and safe_float(cash.get("value")) is not None else 0.0)
                if invcap and invcap != 0.0:
                    rows.append(("ROIC", nopat / invcap, "ratio", oi.get("end",""),
                                oi.get("form",""), oi.get("accn",""), "derived", "", "OperatingIncome;IncomeTaxExpense;PreTaxIncome;Debt;Equity;Cash", 0.84, ""))
                rows.append(("NOPAT", nopat, "USD", oi.get("end",""),
                             oi.get("form",""), oi.get("accn",""), "derived", "", "OperatingIncome;IncomeTaxExpense;PreTaxIncome", 0.82, ""))
                rows.append(("InvestedCapital", invcap, "USD", oi.get("end",""),
                             oi.get("form",""), oi.get("accn",""), "derived", "", "LongTermDebt;ShortTermDebt;Equity;Cash", 0.82, ""))
        except Exception:
            pass

    # 결과 필터: 값 None인 파생은 버림
    out_rows=[]
    for (metric, val, unit, end, form, accn, src, tag, computed_from, conf, reason) in rows:
        if safe_float(val) is None:
            continue
        out_rows.append((metric, float(val), unit, end or "", form or "", accn or "", src, tag, computed_from, conf, reason))
    return out_rows

# ----------------------- S&P500 유틸리티 --------------------------
def fetch_sp500_constituents(ua: Optional[str], dbg: Optional[Debugger] = None) -> List[dict]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    r = http_get(url, ua=ua, timeout=60, dbg=dbg)
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("BeautifulSoup4 required. pip install beautifulsoup4")
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"id":"constituents"}) or soup.select_one("table.wikitable")
    if not table:
        raise RuntimeError("S&P500 table not found on Wikipedia.")
    headers = [th.get_text(strip=True).lower() for th in table.select("thead th")]
    idx = {h:i for i,h in enumerate(headers)}
    isym = idx.get("symbol",0)
    iname = idx.get("security",1)
    isector = idx.get("gics sector") or idx.get("sector")
    isub = idx.get("gics sub-industry") or idx.get("sub-industry")
    rows = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 2: continue
        rows.append({
            "symbol": tds[isym].get_text(strip=True).upper(),
            "name": tds[iname].get_text(strip=True),
            "sector": tds[isector].get_text(strip=True) if isector is not None else "",
            "industry": tds[isub].get_text(strip=True) if isub is not None else ""
        })
    return rows

def normalize_ticker_key(t: str) -> str:
    return re.sub(r"[.\\-\\s]", "", t.upper().strip())

def fetch_sec_ticker_cik_map(ua: Optional[str], dbg: Optional[Debugger] = None) -> Dict[str, dict]:
    out = {}
    try:
        j = http_get("https://www.sec.gov/files/company_tickers.json", ua=ua, dbg=dbg).json()
        for _, rec in j.items():
            t = (rec.get("ticker") or "").upper()
            cik = str(rec.get("cik_str") or "").zfill(10)
            out[normalize_ticker_key(t)] = {"ticker": t, "cik": cik, "title": rec.get("title") or ""}
    except Exception:
        pass
    if not out:
        txt = http_get("https://www.sec.gov/include/ticker.txt", ua=ua, dbg=dbg).text
        for line in txt.splitlines():
            if "|" not in line: continue
            t, cik = line.strip().split("|", 1)
            out[normalize_ticker_key(t)] = {"ticker": t.upper(), "cik": str(cik).zfill(10), "title": ""}
    if not out:
        raise RuntimeError("SEC ticker→CIK mapping failed")
    return out

# --------------------------- CLI (명령줄 인터페이스) -------------------------------
def main():
    ap = argparse.ArgumentParser(description="EDGAR XBRL selector (Full) with growth normalization & CSV schema restored")
    ap.add_argument("--fy", type=int, default=2024, help="Fiscal year (default: 2024)")
    ap.add_argument("--metrics", nargs="+", choices=BASE_METRICS+DERIVED_METRICS+["base","derived","all"], default=["all"])
    ap.add_argument("--include-derived", action="store_true", help="Include derived metrics")
    ap.add_argument("--skip-derived", action="store_true", help="Skip derived metrics entirely")
    ap.add_argument("--use-api", action="store_true", help="Use SEC API (requires user-agent)")
    ap.add_argument("--ciks", help="Comma separated CIKs (with --use-api)")
    ap.add_argument("--tickers", nargs="+", help="Filter S&P500 by tickers (with --use-api, no --ciks)")
    ap.add_argument("--limit", type=int, help="Limit number of companies (with --use-api)")
    ap.add_argument("--facts", nargs="+", help="Local Company Facts JSON paths")
    ap.add_argument("--facts-dir", help="Directory containing Company Facts JSON files")
    ap.add_argument("--user-agent", help="SEC user-agent or env SEC_USER_AGENT")
    ap.add_argument("--prefer-unit", default="USD")
    ap.add_argument("--fy-tol-days", type=int, default=90)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--debug-file", help="Path to debug log file")
    ap.add_argument("--cache-dir", default=_COMPANYFACTS_CACHE_DIR, help="Company Facts cache dir")
    ap.add_argument("--subs-cache-dir", default=_SUBMISSIONS_CACHE_DIR, help="Submissions cache dir")
    ap.add_argument("--force", action="store_true", help="Force API fetch even if cache exists")
    ap.add_argument("--suggestions", help="JSONL file to load curated suggestions")
    ap.add_argument("--dump-suggestions", help="Path to dump mined/hinted/used qnames as JSONL")
    ap.add_argument("--dump-suggestions-append", action="store_true")
    ap.add_argument("--dump-ext-only", action="store_true")
    ap.add_argument("--out-tags", help="Output tags CSV path (default: data/tags_{fy}.csv)")
    ap.add_argument("--out-companies", help="Companies CSV path (default: data/companies_{fy}.csv)")
    ap.add_argument("--out-benchmarks", help="Output benchmarks CSV path (default: data/benchmarks_{fy}.csv)")
    ap.add_argument("--out-rankings", help="Output rankings CSV path (default: data/rankings_{fy}.csv)")
    ap.add_argument("--out-wide", help="Output wide format CSV path (default: data/companies_wide_{fy}.csv)")
    ap.add_argument("--emit-ttl", help="Write RDF Turtle aligned to EFIN ontology (instances only).")
    ap.add_argument(
        "--include-industry-scope",
        action="store_true",
        help="Include industry-scope Benchmark and TopRanking instances in TTL output.",
    )
    ap.add_argument(
        "--include-sector-scope",
        action="store_true",
        help="Include sector-scope Benchmark and TopRanking instances in TTL output.",
    )
    args = ap.parse_args()

    dbg = Debugger(enabled=args.debug, path=args.debug_file)
    ua = get_user_agent(args)

    # 회사 목록
    pairs = []

    def load_pair_from_facts_json(j: dict, subs_cache_dir: str) -> Tuple[dict, dict, dict]:
        cik=str(j.get("cik") or "").zfill(10)
        # submissions (cache)
        subs_path = subs_find_existing(args.subs_cache_dir, cik)
        if not subs_path:
            subs = fetch_sec_submissions(cik, ua, dbg) if args.use_api else {}
            if args.use_api and subs:
                subs_save(args.subs_cache_dir, cik, subs); subs_cleanup(args.subs_cache_dir, cik)
        else:
            subs = json.load(open(subs_path, "r", encoding="utf-8"))
        symbol = j.get("entityTicker") or ""
        if not symbol and subs:
            tickers = subs.get("tickers", [])
            symbol = tickers[0] if tickers else ""
        meta={"cik":cik,"symbol":symbol,"name":j.get("entityName") or ""}
        return (meta, j, subs)

    if args.facts:
        for f in args.facts:
            j=json.load(open(f,"r",encoding="utf-8"))
            pairs.append(load_pair_from_facts_json(j, args.subs_cache_dir))
    elif args.facts_dir:
        for fp in pathlib.Path(args.facts_dir).glob("*.json"):
            j=json.load(open(fp,"r",encoding="utf-8"))
            pairs.append(load_pair_from_facts_json(j, args.subs_cache_dir))
    elif args.use_api:
        if args.ciks:
            cik_list = [c.strip() for c in args.ciks.split(",") if c.strip()]
            total = len(cik_list)
            max_workers = min(10, total)
            print(f"[INFO] Processing {total} CIKs with {max_workers} workers...", file=sys.stderr)
            def fetch_one(cik_padded, idx):
                try:
                    cf_cached = cf_find_existing(args.cache_dir, cik_padded)
                    if not args.force and cf_cached:
                        facts = json.load(open(cf_cached, "r", encoding="utf-8"))
                    else:
                        facts = fetch_company_facts(cik_padded, ua, dbg)
                        cf_save(args.cache_dir, cik_padded, facts); cf_cleanup(args.cache_dir, cik_padded)
                    # submissions
                    subs_cached = subs_find_existing(args.subs_cache_dir, cik_padded)
                    if not args.force and subs_cached:
                        subs = json.load(open(subs_cached, "r", encoding="utf-8"))
                    else:
                        subs = fetch_sec_submissions(cik_padded, ua, dbg)
                        subs_save(args.subs_cache_dir, cik_padded, subs); subs_cleanup(args.subs_cache_dir, cik_padded)
                    symbol = facts.get("entityTicker") or (subs.get("tickers",[None])[0] if subs else "") or ""
                    name = facts.get("entityName") or ""
                    meta = {"cik":cik_padded, "symbol":symbol, "name":name}
                    return (meta, facts, subs)
                except Exception as e:
                    print(f"[ERROR] CIK{cik_padded} fetch failed: {e}", file=sys.stderr)
                    return None
            pairs=[]
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = [ex.submit(fetch_one, str(c).zfill(10), i+1) for i,c in enumerate(cik_list)]
                for fut in as_completed(futs):
                    r=fut.result()
                    if r: pairs.append(r)
        else:
            comps = fetch_sp500_constituents(ua, dbg)
            if args.tickers:
                want=set([t.upper() for t in args.tickers])
                comps=[c for c in comps if c["symbol"].upper() in want]
            if args.limit:
                comps = comps[:int(args.limit)]
            sec_map = fetch_sec_ticker_cik_map(ua, dbg)
            todo=[]
            for co in comps:
                rec = sec_map.get(normalize_ticker_key(co["symbol"]))
                if rec:
                    todo.append({"symbol": co["symbol"], "cik": rec["cik"], "name": co["name"] or rec.get("title","")})
            total=len(todo)
            max_workers=min(10,total)
            print(f"[INFO] Fetching {total} companies...", file=sys.stderr)
            def fetch_one(co, idx):
                cik=co["cik"]; symbol=co["symbol"]; name=co["name"]
                try:
                    cf_cached = cf_find_existing(args.cache_dir, cik)
                    if not args.force and cf_cached:
                        facts = json.load(open(cf_cached, "r", encoding="utf-8"))
                    else:
                        facts = fetch_company_facts(cik, ua, dbg)
                        cf_save(args.cache_dir, cik, facts); cf_cleanup(args.cache_dir, cik)
                    subs_cached = subs_find_existing(args.subs_cache_dir, cik)
                    if not args.force and subs_cached:
                        subs = json.load(open(subs_cached, "r", encoding="utf-8"))
                    else:
                        subs = fetch_sec_submissions(cik, ua, dbg)
                        subs_save(args.subs_cache_dir, cik, subs); subs_cleanup(args.subs_cache_dir, cik)
                    meta = {"cik":cik,"symbol":symbol,"name":name}
                    return (meta, facts, subs)
                except Exception as e:
                    print(f"[ERROR] {symbol} ({cik}) failed: {e}", file=sys.stderr)
                    return None
            pairs=[]
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs=[ex.submit(fetch_one, co, i+1) for i,co in enumerate(todo)]
                for fut in as_completed(futs):
                    r=fut.result()
                    if r: pairs.append(r)
    else:
        raise SystemExit("Provide --facts/--facts-dir or --use-api")

    # 파일 경로 준비 (fy 포함)
    fy = args.fy
    if args.out_tags:
        out_tags = pathlib.Path(args.out_tags)
    else:
        out_tags = pathlib.Path(f"data/tags_{fy}.csv")
    out_tags.parent.mkdir(parents=True, exist_ok=True)
    
    if args.out_companies:
        out_comp = pathlib.Path(args.out_companies)
    else:
        out_comp = pathlib.Path(f"data/companies_{fy}.csv")
    out_comp.parent.mkdir(parents=True, exist_ok=True)
    
    if args.out_benchmarks:
        out_benchmarks = pathlib.Path(args.out_benchmarks)
    else:
        out_benchmarks = pathlib.Path(f"data/benchmarks_{fy}.csv")
    out_benchmarks.parent.mkdir(parents=True, exist_ok=True)
    
    if args.out_rankings:
        out_rankings = pathlib.Path(args.out_rankings)
    else:
        out_rankings = pathlib.Path(f"data/rankings_{fy}.csv")
    out_rankings.parent.mkdir(parents=True, exist_ok=True)

    # 결과 누적
    tag_rows: List[dict] = []
    company_rows: List[dict] = []

    include_derived = (args.include_derived and not args.skip_derived) or (not args.skip_derived and ("all" in args.metrics or "derived" in args.metrics))
    base_wanted = (("all" in args.metrics) or ("base" in args.metrics)) or any(m in BASE_METRICS for m in args.metrics)
    derived_wanted = include_derived or any(m in DERIVED_METRICS for m in args.metrics)

    for (meta_base, facts, subs) in pairs:
        try:
            cik=meta_base.get("cik",""); symbol=meta_base.get("symbol",""); name=meta_base.get("name","")
            sector, industry, sic, sic_desc = infer_sector_industry(subs)
            fye = str(subs.get("fiscalYearEnd") or "")
            meta = {
                "cik": cik, "symbol": symbol, "name": name,
                "sector": sector, "industry": industry,
                "sic": sic, "sic_description": sic_desc, "fye": fye
            }
            company_rows.append({
                "symbol": symbol, "cik": cik, "name": name,
                "sector": sector, "industry": industry,
                "sic": sic, "sic_description": sic_desc, "fye": fye
            })

            # BASE
            if base_wanted:
                # duration-type
                for bm in ["Revenue","OperatingIncome","NetIncome","CFO","GrossProfit","EPSDiluted",
                           "CapEx","InterestExpense","DepAmort","CostOfGoodsSold","IncomeTaxExpense","PreTaxIncome","DilutedShares"]:
                    if ("all" in args.metrics) or ("base" in args.metrics) or (bm in args.metrics):
                        sel = {
                            "Revenue": select_revenue,
                            "OperatingIncome": select_operating_income,
                            "NetIncome": select_net_income,
                            "CFO": select_cfo,
                            "GrossProfit": select_gross_profit,
                            "EPSDiluted": select_eps_diluted,
                            "CapEx": select_capex,
                            "InterestExpense": select_interest_expense,
                            "DepAmort": select_dep_amort,
                            "CostOfGoodsSold": select_cogs,
                            "IncomeTaxExpense": select_income_tax_expense,
                            "PreTaxIncome": select_pretax_income,
                            "DilutedShares": lambda f, fy, s, d, **kw: select_base_duration(f, fy, s, d, "DilutedShares", **kw),
                        }[bm](facts, args.fy, subs, dbg, prefer_unit=args.prefer_unit, tol_days=args.fy_tol_days)
                        if sel.get("source_type") != "none" and safe_float(sel.get("value")) is not None:
                            add_row(tag_rows, meta, args.fy, bm, False, sel["value"], sel.get("unit",""),
                                    "duration", sel.get("end",""), sel.get("form",""), sel.get("accn",""),
                                    sel.get("source_type",""), sel.get("qname",""), sel.get("name",""),
                                    "", sel.get("confidence"), sel.get("reason",""), None)

                # instant-type
                for bm in ["Assets","Liabilities","Equity","LongTermDebt","ShortTermDebt","DebtCurrent",
                           "CurrentAssets","CurrentLiabilities","Inventories","AccountsReceivable"]:
                    if ("all" in args.metrics) or ("base" in args.metrics) or (bm in args.metrics):
                        sel = {
                            "Assets": select_assets,
                            "Liabilities": select_liabilities,
                            "Equity": select_equity,
                            "LongTermDebt": select_longterm_debt,
                            "ShortTermDebt": select_shortterm_debt,
                            "DebtCurrent": lambda f, fy, s, d, **kw: select_base_instant(f, fy, s, d, "DebtCurrent", **kw),
                            "CurrentAssets": select_current_assets,
                            "CurrentLiabilities": select_current_liabilities,
                            "Inventories": select_inventories,
                            "AccountsReceivable": select_accounts_receivable,
                        }[bm](facts, args.fy, subs, dbg, prefer_unit=args.prefer_unit, tol_days=120)
                        if sel.get("source_type") != "none" and safe_float(sel.get("value")) is not None:
                            add_row(tag_rows, meta, args.fy, bm, False, sel["value"], sel.get("unit",""),
                                    "instant", sel.get("end",""), sel.get("form",""), sel.get("accn",""),
                                    sel.get("source_type",""), sel.get("qname",""), sel.get("name",""),
                                    "", sel.get("confidence"), sel.get("reason",""), None)

            # DERIVED
            if derived_wanted:
                # (A) Growth 4종 – 이번 빌드에서만 로직 보강
                growth = compute_growth_set(facts, args.fy, subs, dbg, prefer_unit=args.prefer_unit, tol_days=args.fy_tol_days)
                for gname in ["RevenueGrowthYoY","NetIncomeGrowthYoY","CFOGrowthYoY","AssetGrowthRate"]:
                    if growth.get(gname) and (("all" in args.metrics) or ("derived" in args.metrics) or (gname in args.metrics)):
                        g = growth[gname]
                        if safe_float(g.get("value")) is not None:
                            add_row(tag_rows, meta, args.fy, gname, True, g["value"], g.get("unit",""),
                                    "duration" if gname!="AssetGrowthRate" else "instant",
                                    g.get("end",""), g.get("form",""), g.get("accn",""),
                                    g.get("source_type",""), g.get("selected_tag",""), "",
                                    g.get("computed_from",""), g.get("confidence",0.0), g.get("reason",""), None)

                # (B) 그 외 파생 – 기존 로직 유지
                others = compute_other_derived(facts, args.fy, subs, dbg, prefer_unit=args.prefer_unit, tol_days=args.fy_tol_days)
                for (metric, val, unit, end, form, accn, src, tag, computed_from, conf, reason) in others:
                    if ("all" in args.metrics) or ("derived" in args.metrics) or (metric in args.metrics):
                        add_row(tag_rows, meta, args.fy, metric, True, val, unit, 
                                "duration" if metric not in ("AssetTurnover","EquityRatio") else "instant", 
                                end, form, accn, src, tag, "", computed_from, conf, reason, None)

        except Exception as e:
            print(f"[WARN] {symbol or cik} processing failed: {e}", file=sys.stderr)
            continue

    # companies.csv 쓰기
    with open(out_comp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol","cik","name","sector","industry","sic","sic_description","fye"])
        w.writeheader()
        for r in company_rows:
            w.writerow(r)

    # tags_{fy}.csv 쓰기 (원복 스키마)
    with open(out_tags, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "cik","symbol","name","sector","industry","sic","sic_description","fye","fy",
            "metric","is_derived","value","unit","period_type","end","form","accn",
            "source_type","selected_tag","composite_name","computed_from","confidence","reason","components"
        ])
        w.writeheader()
        for row in tag_rows:
            w.writerow(row)

    print(f"[OK] wrote tags CSV: {out_tags}")
    print(f"[OK] wrote companies CSV: {out_comp}")

    # 벤치마크 계산 및 저장
    try:
        benchmarks = compute_benchmarks(str(out_tags), fy)
        with open(out_benchmarks, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "industry", "sector", "metric", "fy", "average_value", "median_value",
                "max_value", "min_value", "percentile25", "percentile75", "sample_size"
            ])
            w.writeheader()
            for b in benchmarks:
                w.writerow(b)
        print(f"[OK] wrote benchmarks CSV: {out_benchmarks}")
    except Exception as e:
        print(f"[WARN] benchmarks calculation failed: {e}", file=sys.stderr)

    # 랭킹 계산 및 저장
    try:
        rankings = compute_rankings(str(out_tags), str(out_benchmarks), fy)
        with open(out_rankings, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "cik", "symbol", "industry", "sector", "metric", "ranking_type",
                "rank", "value", "composite_score", "fy"
            ])
            w.writeheader()
            for r in rankings:
                r_with_fy = r.copy()
                r_with_fy["fy"] = fy
                w.writerow(r_with_fy)
        print(f"[OK] wrote rankings CSV: {out_rankings}")
    except Exception as e:
        print(f"[WARN] rankings calculation failed: {e}", file=sys.stderr)

    # Wide format CSV 생성
    try:
        if args.out_wide:
            out_wide = pathlib.Path(args.out_wide)
        else:
            out_wide = pathlib.Path(f"data/companies_wide_{fy}.csv")
        out_wide.parent.mkdir(parents=True, exist_ok=True)
        create_wide_format_csv(str(out_tags), str(out_rankings), str(out_comp), fy, str(out_wide))
    except Exception as e:
        print(f"[WARN] wide format CSV generation failed: {e}", file=sys.stderr)

    # TTL (옵션)
    try:
        if args.emit_ttl:
            # args에 파일 경로 추가
            args.out_benchmarks = str(out_benchmarks)
            args.out_rankings = str(out_rankings)
            emit_after_csv(args, company_rows, tag_rows)
    except Exception as e:
        print(f"[WARN] TTL generation failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

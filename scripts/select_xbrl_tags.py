#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
select_xbrl_tags.py
--------------------------------
Upgrades over v5:
 - **Dump Suggestions JSONL**: --dump-suggestions [--dump-suggestions-append] [--dump-ext-only]
   * Writes mined/hinted/used qnames per (CIK, metric) for later curation.
 - **New metrics**: Assets (instant), Liabilities (instant), Equity (instant).
 - **Dynamic miners** for Assets/Liabilities/Equity + derivations:
    * Assets := Liabilities + Equity  OR  LiabilitiesAndStockholdersEquity (penalized)
    * Liabilities := Assets - Equity  OR  LiabilitiesAndStockholdersEquity - Equity
    * Equity := Assets - Liabilities  OR  LiabilitiesAndStockholdersEquity - Liabilities
 - **Adaptive FY tolerance** reused for instant selectors (two-pass tol_days, tol_days+60)
 - **Debug traces** preserved; improved alignment for instant pairs.

Usage:
  export SEC_USER_AGENT="MyApp/1.0 you@org.com"
  python select_xbrl_tags.py --fy 2024 --use-api \
     --tickers APA EQR CBOE \
     --metrics Revenue OperatingIncome NetIncome CashAndCashEquivalents CFO Assets Liabilities Equity \
     --suggestions hints.jsonl \
     --dump-suggestions mined_v6.jsonl \
     --fy-tol-days 120 \
     --debug --debug-file debug.log \
     --out result.csv
"""
from __future__ import annotations
import os, re, csv, math, json, argparse, pathlib, sys, time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import date, datetime
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

# ──────────────────────────────────────────────────────────────
# API Rate Limiting State
_last_api_call_time: Optional[float] = None
_api_rate_limit_delay: float = 0.1  # 10 requests/second per SEC guidelines
_rate_limit_lock = threading.Lock()  # Thread-safe rate limiting

# ──────────────────────────────────────────────────────────────
# 캐시 설정
_CACHE_DIR = ".cache/companyfacts"
_DATE_FORMAT = "%Y%m%d"  # YYYYMMDD 형식

METRICS = [
    "Revenue", "OperatingIncome", "NetIncome", "CashAndCashEquivalents", "CFO",
    "Assets", "Liabilities", "Equity"
]

STD_PREFIXES = {"us-gaap","ifrs-full","dei","srt"}

@dataclass(frozen=True)
class Candidate:
    qname: str
    base_score: float = 1.0
    industry_only: Optional[Set[str]] = None
    normalized_as: str = "AUTO"
    notes: Optional[str] = None
    origin: str = "static"  # static|mined|extension|hint|suggestion

@dataclass(frozen=True)
class CompositeCandidate:
    name: str
    components: List[Tuple[str, float]]
    base_score: float = 1.0
    industry_only: Optional[Set[str]] = None
    normalized_as: str = "AUTO"
    notes: Optional[str] = None

# ------------------------- Debugger ----------------------------
class Debugger:
    def __init__(self, enabled: bool = False, path: Optional[str] = None):
        self.enabled = enabled
        self.path = path
        self._fp = None
        if enabled and path:
            try:
                # 디렉토리가 없으면 생성
                pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
                self._fp = open(path, "w", encoding="utf-8")
            except Exception as e:
                print(f"[WARN] Failed to open debug file {path}: {e}", file=sys.stderr)
                self._fp = None

    def log(self, msg: str):
        if not self.enabled: return
        if self._fp:
            try:
                self._fp.write(msg.rstrip() + "\n")
                self._fp.flush()
            except ValueError:
                # 파일이 이미 닫혔으면 stderr로 출력
                print(msg, file=sys.stderr)
        else:
            print(msg, file=sys.stderr)

    def close(self):
        if self._fp:
            self._fp.close()

# ----------------------- Suggestions store ---------------------
_SUGG: Dict[Tuple[str,str,str], dict] = {}
_sugg_lock = threading.Lock()  # Suggestions 전역 딕셔너리 보호용

def record_suggestion(cik: Optional[str], metric: str, qname: str, origin: str, note: Optional[str]=None, ext_only: bool=False):
    """Collect suggestion entries for later dump. ext_only=True => only when non-standard prefix."""
    if not cik: return
    try:
        tax = qname.split(":",1)[0]
    except Exception:
        tax = ""
    if ext_only and tax in STD_PREFIXES:
        return
    key = (str(int(cik)), metric, qname)
    with _sugg_lock:  # Thread-safe
        if key not in _SUGG:
            _SUGG[key] = {"cik": str(int(cik)), "metric": metric, "qname": qname, "origin": origin, "note": note or ""}

def dump_suggestions(path: str, append: bool=False):
    mode = "a" if append and os.path.exists(path) else "w"
    with open(path, mode, encoding="utf-8") as f:
        for v in _SUGG.values():
            f.write(json.dumps(v, ensure_ascii=False) + "\n")

# ----------------------- HTTP utils ----------------------------
def get_user_agent(args) -> str:
    return (args.user_agent or os.getenv("SEC_USER_AGENT") or "").strip()

def wait_for_rate_limit():
    """SEC API rate limit: 10 requests/second → 0.1초 간격 (thread-safe)"""
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

def fetch_sec_submissions(cik: str, ua: Optional[str], dbg: Debugger, cache_dir: Optional[str] = None) -> dict:
    # 캐시 확인
    if cache_dir:
        cached = find_existing_submissions_cache(cache_dir, cik)
        if cached:
            dbg.log(f"[CACHE] Submissions CIK{cik} - using cache {cached.name}")
            try:
                return json.load(open(cached, "r", encoding="utf-8"))
            except Exception as e:
                dbg.log(f"[CACHE][ERR] Submissions CIK{cik} cache load failed: {e}")
    
    url = f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"
    try:
        dbg.log(f"[HTTP] GET {url}")
        data = http_get(url, ua=ua, dbg=dbg).json()
        # 캐시 저장
        if cache_dir:
            save_submissions_to_cache(cache_dir, cik, data)
        return data
    except Exception as e:
        dbg.log(f"[HTTP][ERR] {url} -> {e}")
        return {}

def fetch_company_facts(cik: str, ua: Optional[str], dbg: Debugger) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(cik).zfill(10)}.json"
    dbg.log(f"[HTTP] GET {url}")
    return http_get(url, ua=ua, dbg=dbg).json()

# ----------------------- Cache Utilities -----------------------
def get_cache_path(cache_dir: str, cik: str) -> pathlib.Path:
    today_str = datetime.now().strftime(_DATE_FORMAT)
    padded_cik = str(cik).zfill(10)
    return pathlib.Path(cache_dir) / f"CIK{padded_cik}_{today_str}.json"

def find_existing_cache(cache_dir: str, cik: str) -> Optional[pathlib.Path]:
    cache_path = pathlib.Path(cache_dir)
    if not cache_path.exists():
        return None
    padded_cik = str(cik).zfill(10)
    # 오늘 날짜의 캐시 파일만 찾기
    today_str = datetime.now().strftime(_DATE_FORMAT)
    cache_file = cache_path / f"CIK{padded_cik}_{today_str}.json"
    return cache_file if cache_file.exists() else None

def cleanup_old_cache_files(cache_dir: str, cik: str, keep_latest: int = 1):
    cache_path = pathlib.Path(cache_dir)
    if not cache_path.exists():
        return
    padded_cik = str(cik).zfill(10)
    pattern = f"CIK{padded_cik}_*.json"
    matches = sorted(cache_path.glob(pattern), reverse=True)
    # 오늘 날짜가 아닌 모든 파일 삭제
    today_str = datetime.now().strftime(_DATE_FORMAT)
    for old_file in matches:
        if today_str not in old_file.name:
            try:
                old_file.unlink()
            except Exception:
                pass

def save_to_cache(cache_dir: str, cik: str, data: dict):
    cache_path = get_cache_path(cache_dir, cik)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    cleanup_old_cache_files(cache_dir, cik, keep_latest=1)

# Submissions 캐시 함수들
def get_submissions_cache_path(cache_dir: str, cik: str) -> pathlib.Path:
    today_str = datetime.now().strftime(_DATE_FORMAT)
    padded_cik = str(cik).zfill(10)
    return pathlib.Path(cache_dir) / f"submissions_CIK{padded_cik}_{today_str}.json"

def find_existing_submissions_cache(cache_dir: str, cik: str) -> Optional[pathlib.Path]:
    cache_path = pathlib.Path(cache_dir)
    if not cache_path.exists():
        return None
    padded_cik = str(cik).zfill(10)
    # 오늘 날짜의 캐시 파일만 찾기
    today_str = datetime.now().strftime(_DATE_FORMAT)
    cache_file = cache_path / f"submissions_CIK{padded_cik}_{today_str}.json"
    return cache_file if cache_file.exists() else None

def save_submissions_to_cache(cache_dir: str, cik: str, data: dict):
    cache_path = get_submissions_cache_path(cache_dir, cik)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    # 오늘 날짜가 아닌 모든 submissions 캐시 파일 삭제
    cache_path_dir = pathlib.Path(cache_dir)
    if cache_path_dir.exists():
        padded_cik = str(cik).zfill(10)
        pattern = f"submissions_CIK{padded_cik}_*.json"
        matches = sorted(cache_path_dir.glob(pattern), reverse=True)
        today_str = datetime.now().strftime(_DATE_FORMAT)
        for old_file in matches:
            if today_str not in old_file.name:
                try:
                    old_file.unlink()
                except Exception:
                    pass

# ----------------------- Date / FY window ----------------------
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
        dbg.log(f"[smart_pick] keep end={rec.get('end')} fp={fp} dist={dist} score={score:.3f}")
        if (best is None) or (cand > best):
            best=cand; best_rec=rec
    return best_rec

# ----------------------- Facts helpers -------------------------
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

# ----------------------- Industry inference -------------------
def word_hit(text: str, patterns: List[str]) -> bool:
    for p in patterns:
        if re.search(rf"\b{re.escape(p)}\b", text, re.IGNORECASE): return True
    return False

def sic_to_industries(sic: Optional[int]) -> Set[str]:
    s=set()
    if sic is None: return s
    if 6000 <= sic <= 6199: s.update({"Banking","Financials"})
    if 6200 <= sic <= 6299: s.update({"BrokerDealer","Financials"})
    if 6300 <= sic <= 6499: s.update({"Insurance"})
    if 6500 <= sic <= 6799: s.update({"REITs","RealEstate","Financials"})
    if 4900 <= sic <= 4999: s.update({"Utilities"})
    if 1300 <= sic <= 1399: s.update({"Energy"})
    if 2900 <= sic <= 2999: s.update({"Energy"})
    if 1000 <= sic <= 1099: s.update({"Materials"})
    if 2000 <= sic <= 2099: s.update({"Consumer"})
    if 7300 <= sic <= 7399: s.update({"SoftwareServices"})
    if 4500 <= sic <= 4799: s.update({"Transportation","Logistics"})
    if 7000 <= sic <= 7099: s.update({"HotelsRestaurantsLeisure"})
    if 4800 <= sic <= 4899: s.update({"Media","CommunicationServices"})
    return s

def infer_industry_set(meta: dict, facts_json: dict, subs: dict, dbg: Debugger) -> Set[str]:
    s=set()
    sic = None
    try: sic = int(subs.get("sic")) if subs.get("sic") else None
    except Exception: sic = None
    s.update(sic_to_industries(sic))
    text = " ".join([meta.get("industry") or "", subs.get("sicDescription") or ""]).lower()
    if word_hit(text, ["bank","banking"]): s.update({"Banking","Financials"})
    if word_hit(text, ["broker","exchange","securities"]): s.update({"BrokerDealer","Financials"})
    if word_hit(text, ["insurance","insurer"]): s.update({"Insurance"})
    if word_hit(text, ["reit","real estate"]): s.update({"REITs","RealEstate"})
    if word_hit(text, ["utility","electric","gas utility"]): s.update({"Utilities"})
    if word_hit(text, ["oil","gas","refining","petroleum","energy"]): s.update({"Energy"})
    if word_hit(text, ["software","saas"]): s.update({"SoftwareServices"})
    if word_hit(text, ["transportation","trucking","logistics","airline","marine"]): s.update({"Transportation","Logistics"})
    if word_hit(text, ["casino","resort","gaming","hotel"]): s.update({"HotelsRestaurantsLeisure"})
    if word_hit(text, ["media","broadcast","television","advertising"]): s.update({"Media","CommunicationServices"})
    if "ifrs-full" in (facts_json.get("facts") or {}): s.add("IFRS")
    else: s.add("USGAAP")
    if not s: s={"USGAAP"}
    dbg.log(f"[industry] -> {sorted(s)}")
    return s

def score_adj(form: Optional[str], unit: Optional[str], fp: Optional[str], has_seg: bool, industry_hit: bool) -> float:
    s = 0.0
    if form in ("10-K","20-F","10-K/A","20-F/A"): s += 0.06
    elif form: s -= 0.01
    if unit == "USD": s += 0.03
    elif unit: s -= 0.02
    if (fp or "").upper() in ("FY","CY","FYR"): s += 0.03
    if has_seg: s -= 0.01
    if industry_hit: s += 0.02
    return s

# ----------------------- Static candidates --------------------
CANDIDATES: Dict[str, List[Candidate]] = {
    "Revenue": [
        Candidate("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", 1.00, None, "Revenue", origin="static"),
        Candidate("us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax", 0.985, None, "Revenue", origin="static"),
        Candidate("us-gaap:Revenues", 0.975, None, "Revenue", origin="static"),
        Candidate("us-gaap:SalesRevenueNet", 0.970, None, "Revenue", origin="static"),
        Candidate("us-gaap:NetSales", 0.960, None, "Revenue", origin="static"),
        Candidate("us-gaap:OperatingRevenue", 0.955, None, "Revenue", origin="static"),
        # Utilities
        Candidate("us-gaap:UtilityRevenue", 0.960, {"Utilities"}, "Revenue", origin="static"),
        Candidate("us-gaap:ElectricUtilityRevenue", 0.955, {"Utilities"}, "Revenue", origin="static"),
        Candidate("us-gaap:GasUtilityRevenue", 0.945, {"Utilities"}, "Revenue", origin="static"),
        Candidate("us-gaap:RegulatedAndUnregulatedOperatingRevenue", 0.940, {"Utilities"}, "Revenue", origin="static"),
        # REIT/Real Estate
        Candidate("us-gaap:RealEstateRevenueNet", 0.950, {"REITs","RealEstate"}, "Revenue", origin="static"),
        Candidate("us-gaap:RentalRevenue", 0.945, {"REITs","RealEstate"}, "Revenue", origin="static"),
        Candidate("us-gaap:OperatingLeasesIncomeStatementLeaseRevenue", 0.940, {"REITs","RealEstate"}, "Revenue", origin="static"),
        # Energy
        Candidate("us-gaap:OilAndGasRevenue", 0.950, {"Energy"}, "Revenue", origin="static"),
        Candidate("us-gaap:RefiningAndMarketingRevenue", 0.940, {"Energy"}, "Revenue", origin="static"),
        # Software/SaaS
        Candidate("us-gaap:SubscriptionRevenue", 0.940, {"SoftwareServices"}, "Revenue", origin="static"),
        Candidate("us-gaap:SoftwareLicensesRevenue", 0.930, {"SoftwareServices"}, "Revenue", origin="static"),
    ],
    "OperatingIncome": [
        Candidate("us-gaap:OperatingIncomeLoss", 1.00, None, "OperatingIncome", origin="static"),
        Candidate("us-gaap:EarningsBeforeInterestAndTaxes", 0.96, None, "OperatingIncome", origin="static"),
        Candidate("us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest", 0.94, None, "OperatingIncome", origin="static"),
        Candidate("ifrs-full:ProfitLossFromOperatingActivities", 0.98, {"IFRS"}, "OperatingIncome", origin="static"),
        Candidate("ifrs-full:ProfitLossBeforeFinanceCostsAndTax", 0.96, {"IFRS"}, "OperatingIncome", origin="static"),
        Candidate("us-gaap:UnderwritingIncomeLoss", 0.90, {"Insurance"}, "OperatingIncomeComparable", origin="static"),
        Candidate("us-gaap:IncomeLossFromContinuingOperationsBeforeInterestExpenseInterestIncomeIncomeTaxesExtraordinaryItemsNoncontrollingInterestsNet",
                 0.90, {"Banking","Financials"}, "OperatingIncomeComparable", origin="static"),
        # REITs specific
        Candidate("us-gaap:RealEstateOperatingIncomeLoss", 0.92, {"REITs","RealEstate"}, "OperatingIncome", origin="static"),
        Candidate("us-gaap:IncomeFromOperations", 0.91, {"REITs","RealEstate"}, "OperatingIncome", origin="static"),
        # Retail/Consumer specific
        Candidate("us-gaap:IncomeFromOperationsBeforeTax", 0.91, None, "OperatingIncome", origin="static"),
        Candidate("us-gaap:OperatingEarnings", 0.90, None, "OperatingIncome", origin="static"),
    ],
    "NetIncome": [
        Candidate("us-gaap:NetIncomeLoss", 1.00, None, "NetIncome", origin="static"),
        Candidate("us-gaap:IncomeLossIncludingPortionAttributableToNoncontrollingInterest", 0.965, None, "NetIncome", origin="static"),
        Candidate("us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic", 0.955, None, "NetIncome", origin="static"),
        Candidate("us-gaap:NetIncomeLossAttributableToParent", 0.955, None, "NetIncome", origin="static"),
        Candidate("us-gaap:ProfitLoss", 0.940, {"IFRS"}, "NetIncome", origin="static"),
        Candidate("ifrs-full:ProfitLoss", 0.980, {"IFRS"}, "NetIncome", origin="static"),
        Candidate("us-gaap:IncomeLossFromContinuingOperations", 0.925, None, "NetIncome", origin="static"),
    ],
    "CashAndCashEquivalents": [
        Candidate("us-gaap:CashAndCashEquivalentsAtCarryingValue", 1.00, None, "CashAndCashEquivalents", origin="static"),
        Candidate("us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", 0.94, None, "CashAndCashEquivalents", origin="static"),
        Candidate("ifrs-full:CashAndCashEquivalents", 0.98, {"IFRS"}, "CashAndCashEquivalents", origin="static"),
        Candidate("us-gaap:CashAndShortTermInvestments", 0.90, None, "CashAndCashEquivalents", origin="static"),
        Candidate("us-gaap:CashAndDueFromBanks", 0.90, {"Banking"}, "CashAndCashEquivalents", origin="static"),
    ],
    "CFO": [
        Candidate("us-gaap:NetCashProvidedByUsedInOperatingActivities", 1.00, None, "CFO", origin="static"),
        Candidate("us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", 0.96, None, "CFO", origin="static"),
        Candidate("ifrs-full:NetCashFlowsFromUsedInOperatingActivities", 0.98, {"IFRS"}, "CFO", origin="static"),
    ],
    # New: Instant balance metrics
    "Assets": [
        Candidate("us-gaap:Assets", 1.00, None, "Assets", origin="static"),
        Candidate("ifrs-full:Assets", 0.985, None, "Assets", origin="static"),
        # Combined (penalized, used as proxy)
        Candidate("us-gaap:LiabilitiesAndStockholdersEquity", 0.92, None, "Assets", origin="static"),
        Candidate("ifrs-full:EquityAndLiabilities", 0.92, {"IFRS"}, "Assets", origin="static"),
    ],
    "Liabilities": [
        Candidate("us-gaap:Liabilities", 1.00, None, "Liabilities", origin="static"),
        Candidate("ifrs-full:Liabilities", 0.985, None, "Liabilities", origin="static"),
    ],
    "Equity": [
        Candidate("us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest", 1.00, None, "Equity", origin="static"),
        Candidate("us-gaap:StockholdersEquity", 0.98, None, "Equity", origin="static"),
        Candidate("ifrs-full:Equity", 0.98, {"IFRS"}, "Equity", origin="static"),
    ],
}

# ------------------ Composite candidates ----------------------
COMPOSITES: Dict[str, List[CompositeCandidate]] = {
    "Revenue": [
        CompositeCandidate("BankRevenue_NetInterestPlusNoninterest",
                           [("us-gaap:InterestIncomeExpenseNet", 1.0),
                            ("us-gaap:NoninterestIncome",       1.0)], 0.96, {"Banking","Financials"}, "RevenueComparable"),
        CompositeCandidate("ExchangeRevenue_FeesAndData",
                           [("us-gaap:TransactionAndExchangeFeeRevenue", 1.0),
                            ("us-gaap:MarketDataRevenue", 1.0),
                            ("us-gaap:AccessAndCapacityFeeRevenue", 1.0)], 0.92, {"BrokerDealer"}, "Revenue"),
        CompositeCandidate("REITRevenue_RentalLeasePlusOther",
                           [("us-gaap:RentalRevenue", 1.0),
                            ("us-gaap:OperatingLeasesIncomeStatementLeaseRevenue", 1.0),
                            ("ext:ResidentialRentalRevenue", 1.0),
                            ("ext:RentalIncome", 1.0),
                            ("ext:LeaseIncome", 1.0),
                            ("ext:RentalAndOtherIncome", 1.0),
                            ("ext:PropertyAndOtherIncome", 1.0)], 0.91, {"REITs","RealEstate"}, "Revenue"),
        CompositeCandidate("CruiseRevenue_TicketPlusOnboard",
                           [("ext:PassengerTicketRevenue", 1.0),
                            ("ext:OnboardAndOtherRevenue", 1.0)], 0.91, {"Transportation","HotelsRestaurantsLeisure"}, "Revenue"),
        CompositeCandidate("CasinoResortRevenue_CasinoRoomFandB",
                           [("ext:CasinoRevenue", 1.0),
                            ("ext:RoomRevenue",   1.0),
                            ("ext:FoodAndBeverageRevenue", 1.0)], 0.90, {"HotelsRestaurantsLeisure"}, "Revenue"),
        CompositeCandidate("MediaRevenue_AdsAffiliateLicensing",
                           [("ext:AdvertisingRevenue", 1.0),
                            ("ext:AffiliateRevenue",   1.0),
                            ("ext:LicensingAndOtherRevenue", 1.0)], 0.90, {"Media","CommunicationServices"}, "Revenue"),
    ],
    "OperatingIncome": [
        CompositeCandidate("BankOperatingComparable_PPNRminusPLL",
                           [("us-gaap:InterestIncomeExpenseNet", 1.0),
                            ("us-gaap:NoninterestIncome",       1.0),
                            ("us-gaap:NoninterestExpense",     -1.0),
                            ("us-gaap:ProvisionForLoanLeaseAndOtherLosses", -1.0)], 0.93, {"Banking","Financials","BrokerDealer"}, "OperatingIncomeComparable"),
        CompositeCandidate("InsuranceOperatingComparable",
                           [("us-gaap:UnderwritingIncomeLoss", 1.0),
                            ("us-gaap:NetInvestmentIncome",    1.0)], 0.91, {"Insurance"}, "OperatingIncomeComparable"),
        CompositeCandidate("GenericOperating_GrossMinusOpex",
                           [("us-gaap:GrossProfit",        1.0),
                            ("us-gaap:OperatingExpenses", -1.0)], 0.90, None, "OperatingIncome"),
        # REITs specific composites
        CompositeCandidate("REITOperating_RentalRevenueMinusOperatingExpenses",
                           [("us-gaap:RentalRevenue", 1.0),
                            ("us-gaap:OperatingLeasesIncomeStatementLeaseRevenue", 1.0),
                            ("ext:RentalIncome", 1.0),
                            ("ext:RentalAndOtherIncome", 1.0),
                            ("us-gaap:OperatingExpenses", -1.0),
                            ("us-gaap:RealEstateOperatingExpenses", -1.0)], 0.89, {"REITs","RealEstate"}, "OperatingIncome"),
        CompositeCandidate("REITOperating_TotalRevenueMinusOperatingExpenses",
                           [("us-gaap:RealEstateRevenueNet", 1.0),
                            ("us-gaap:RentalRevenue", 1.0),
                            ("ext:RentalAndOtherIncome", 1.0),
                            ("us-gaap:OperatingExpenses", -1.0)], 0.88, {"REITs","RealEstate"}, "OperatingIncome"),
    ],
}

ADDITIVE_QNAMES = {
    "us-gaap:Revenues",
    "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
    "us-gaap:SalesRevenueNet",
    "us-gaap:NetSales",
    "us-gaap:UtilityRevenue",
    "us-gaap:ElectricUtilityRevenue",
    "us-gaap:GasUtilityRevenue",
    "us-gaap:OperatingLeasesIncomeStatementLeaseRevenue",
    "us-gaap:RealEstateRevenueNet",
    "us-gaap:OperatingRevenue",
    "us-gaap:RentalRevenue",
}

# --------------------- Dynamic mining -------------------------
_REV_INCLUDE_PATTERNS = [
    r"(?:^|:)Revenue(?:s)?$",
    r"(?:^|:)NetSales$",
    r"(?:^|:)SalesRevenue(?:Goods|Services)?Net$",
    r"(?:^|:)OperatingRevenue(?:s)?$",
    r"(?:^|:)RealEstate.*Revenue",
    r"(?:^|:)RentalRevenue$",
    r"(?:^|:)RentalIncome$",
    r"(?:^|:)RentalAndOtherIncome$",
    r"(?:^|:)ResidentialRental(?:Revenue|Income)$",
    r"(?:^|:)OperatingLeases.*(LeaseRevenue|LeaseIncome)",
    r"(?:^|:)Property.*(Revenue|Income)",
    r"(?:^|:)UtilityRevenue$",
    r"(?:^|:)ElectricUtilityRevenue$",
    r"(?:^|:)GasUtilityRevenue$",
    r"(?:^|:)Transaction.*Fee.*Revenue",
    r"(?:^|:)Exchange.*Fee.*Revenue",
    r"(?:^|:)MarketData.*Revenue",
    r"(?:^|:)Access.*(Capacity|Connectivity).*(Fee)?Revenue",
    r"(?:^|:)Brokerage.*Commissions.*Revenue",
    r"(?:^|:)SubscriptionRevenue$",
    r"(?:^|:)SoftwareLicensesRevenue$",
    r"(?:^|:)CargoAndFreightRevenue$",
    r"(?:^|:)Transportation.*Revenue",
    r"(?:^|:)OilAndGas.*Revenue",
    r"(?:^|:)CrudeOil.*Revenue",
    r"(?:^|:)NaturalGas.*Revenue",
    r"(?:^|:)NGL.*Revenue",
    r"(?:^|:)Hydrocarbon.*Revenue",
    r"(?:^|:)Marketing.*Revenue",
    r"(?:^|:)Midstream.*Revenue",
    r"(?:^|:)Upstream.*Revenue",
    r"(?:^|:)TotalRevenue(?:s)?$",
    r"(?:^|:)OtherOperatingRevenue(?:s)?$",
    r"(?:^|:)OperatingAndOtherRevenue(?:s)?$",
    r"(?:^|:)SalesAndOtherOperatingRevenue(?:s)?$",

    # 에너지 디테일 보강(APA 대응)
    r"(?:^|:)OilAndGasSalesRevenue$",
    r"(?:^|:)OilAndGas.?Revenue$",
    r"(?:^|:)Hydrocarbon.*Revenue$",
    r"(?:^|:)Marketing.*Revenue$",
    r"(?:^|:)Midstream.*Revenue$",
    r"(?:^|:)Upstream.*Revenue$",
    r"(?:^|:)Total.*Revenue(?:s)?$",
    r"(?:^|:)Sales.*Revenue$",
    r"(?:^|:)Operating.*Revenue$",
    r"(?:^|:)Revenue.*Oil.*Gas$",
    r"(?:^|:)Revenue.*Crude.*Oil$",
    r"(?:^|:)Revenue.*Natural.*Gas$",
]
_REV_EXCLUDE_SUBSTR = ["DeferredRevenue","UnearnedRevenue","Allowance","Receivable","Liability","Tax","ExciseTax","Contra", "Allowance", "ExciseTax", "VAT", "Accrual", "Refund"]

_ASSETS_INCLUDE_PATTERNS = [
    r"(?:^|:)Assets$",
    r"(?:^|:)TotalAssets$",
]
_ASSETS_EXCLUDE_SUBSTR = ["Current", "Noncurrent", "HeldForSale", "FairValue", "NetOf"]

_LIAB_INCLUDE_PATTERNS = [
    r"(?:^|:)Liabilities$",
    r"(?:^|:)TotalLiabilities$",
]
_LIAB_EXCLUDE_SUBSTR = ["Current", "Noncurrent", "andStockholdersEquity", "HeldForSale", "FairValue"]

_EQUITY_INCLUDE_PATTERNS = [
    r"(?:^|:)StockholdersEquity(?:IncludingPortionAttributableToNoncontrollingInterest)?$",
    r"(?:^|:)Equity$",
]
_EQUITY_EXCLUDE_SUBSTR = ["EquityMethod", "EquitySecurities", "EquityClass"]

def mine_by_patterns(facts_json: dict, include_patterns: List[str], exclude_substr: List[str],
                     metric_name: str, dbg: Debugger) -> List[Candidate]:
    facts = facts_json.get("facts") or {}
    out=[]; seen=set()
    for tax, items in facts.items():
        for tag in items.keys():
            if any(bad in tag for bad in exclude_substr): continue
            qn=f"{tax}:{tag}"
            if any(re.search(p, qn) for p in include_patterns):
                origin = "extension" if tax not in STD_PREFIXES else "mined"
                base = 0.90 if origin=="extension" else 0.86
                if qn not in seen:
                    seen.add(qn)
                    out.append(Candidate(qn, base, None, metric_name, origin=origin, notes="pattern-hit"))
    dbg.log(f"[mine:{metric_name}] found={len(out)} (ext={sum(1 for c in out if c.origin=='extension')})")
    return out

def mine_revenue_candidates(facts_json: dict, dbg: Debugger) -> List[Candidate]:
    return mine_by_patterns(facts_json, _REV_INCLUDE_PATTERNS, _REV_EXCLUDE_SUBSTR, "Revenue", dbg)

def mine_cash_candidates(facts_json: dict, dbg: Debugger) -> List[Candidate]:
    facts = facts_json.get("facts") or {}
    out=[]; seen=set()
    for tax, items in facts.items():
        for tag in items.keys():
            qn=f"{tax}:{tag}"
            if qn in seen: continue
            if re.search(r"Cash.*(Cash)?Equivalents", tag, re.IGNORECASE) or "CashAndShortTermInvestments" in tag:
                origin = "extension" if tax not in STD_PREFIXES else "mined"
                base = 0.90 if origin=="extension" else 0.86
                out.append(Candidate(qn, base, None, "CashAndCashEquivalents", origin=origin, notes="pattern-hit"))
                seen.add(qn)
    dbg.log(f"[mine:Cash] found {len(out)} candidates")
    return out

def mine_assets_candidates(facts_json: dict, dbg: Debugger) -> List[Candidate]:
    return mine_by_patterns(facts_json, _ASSETS_INCLUDE_PATTERNS, _ASSETS_EXCLUDE_SUBSTR, "Assets", dbg)

def mine_liabilities_candidates(facts_json: dict, dbg: Debugger) -> List[Candidate]:
    return mine_by_patterns(facts_json, _LIAB_INCLUDE_PATTERNS, _LIAB_EXCLUDE_SUBSTR, "Liabilities", dbg)

def mine_equity_candidates(facts_json: dict, dbg: Debugger) -> List[Candidate]:
    return mine_by_patterns(facts_json, _EQUITY_INCLUDE_PATTERNS, _EQUITY_EXCLUDE_SUBSTR, "Equity", dbg)

# --------------------- Suggestions loader ---------------------
def load_suggestions(path: Optional[str], dbg: Debugger) -> Dict[str, Dict[str, Set[str]]]:
    """Return {cik: {metric: set(qnames)}}"""
    res: Dict[str, Dict[str, Set[str]]] = {}
    if not path: return res
    try:
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                ln=ln.strip()
                if not ln: continue
                try:
                    obj=json.loads(ln)
                except Exception:
                    continue
                cik = str(int(obj.get("cik"))) if obj.get("cik") else None
                metric = obj.get("metric")
                qn = obj.get("qname")
                if cik and metric and qn:
                    res.setdefault(cik, {}).setdefault(metric, set()).add(qn)
        dbg.log(f"[suggestions] loaded for {len(res)} CIKs from {path}")
    except Exception as e:
        dbg.log(f"[suggestions][ERR] {e}")
    return res

def apply_suggestions(cik: str, metric: str, sugg_map: Dict[str, Dict[str, Set[str]]], dbg: Debugger) -> List[Candidate]:
    out=[]
    if not cik: return out
    key=str(int(cik))
    for qn in sugg_map.get(key, {}).get(metric, set()):
        out.append(Candidate(qn, 0.945, None, metric, origin="suggestion", notes="jsonl-suggestion"))
    if out:
        dbg.log(f"[apply_suggestions] CIK={key} metric={metric} -> {len(out)} qnames")
    return out

# --------------------- Extension hints (revenue only) ----------
EXTENSION_HINTS: Dict[str, List[Tuple[str, str]]] = {
    "1513761": [
        (r":Passenger.*Ticket.*Revenue$", "Revenue"),
        (r":Onboard.*Other.*Revenue$", "Revenue"),
        (r":Tour.*Other.*Services.*Revenue$", "Revenue"),
    ],
    "1174922": [
        (r":Casino.*Revenue$", "Revenue"),
        (r":Room.*Revenue$", "Revenue"),
        (r":Food.*Beverage.*Revenue$", "Revenue"),
    ],
    "1374310": [
        (r":(Transaction|Exchange).*Fee.*Revenue$", "Revenue"),
        (r":MarketData.*Revenue$", "Revenue"),
        (r":Access.*(Capacity|Connectivity).*(Fee)?Revenue$", "Revenue"),
    ],
    "2041610": [
        (r":Advertising.*Revenue$", "Revenue"),
        (r":Affiliate.*Revenue$", "Revenue"),
        (r":Licensing.*Other.*Revenue$", "Revenue"),
    ],
    "906107": [
        (r":Residential.*Rental.*(Revenue|Income)$", "Revenue"),
        (r":Rental.*And.*Other.*(Income|Revenue)$", "Revenue"),
        (r":Lease.*(Revenue|Income)$", "Revenue"),
        (r":Property.*(Revenue|Income)$", "Revenue"),
    ],
    "1841666": [
        (r":Oil.*Gas.*(Sales)?Revenue$", "Revenue"),
        (r":Crude.*Oil.*Revenue$", "Revenue"),
        (r":Natural.*Gas.*Revenue$", "Revenue"),
        (r":NGL.*Revenue$", "Revenue"),
        (r":Hydrocarbon.*Revenue$", "Revenue"),
        (r":Marketing.*Revenue$", "Revenue"),
        (r":Midstream.*Revenue$", "Revenue"),
        (r":Upstream.*Revenue$", "Revenue"),
        (r":OilAndGas.*Revenue$", "Revenue"),
        (r":OilAndGasSalesRevenue$", "Revenue"),
        (r":Total.*Revenue$", "Revenue"),
        (r":Sales.*Revenue$", "Revenue"),
        (r":Operating.*Revenue$", "Revenue"),
        (r":Revenue.*Oil.*Gas$", "Revenue"),
        (r":Revenue.*Crude.*Oil$", "Revenue"),
        (r":Revenue.*Natural.*Gas$", "Revenue"),
    ],
}

def apply_extension_hints(cik: str, facts_json: dict, dbg: Debugger) -> List[Candidate]:
    pats = EXTENSION_HINTS.get(str(int(cik)), []) if cik else []
    out=[]
    if not pats: 
        return out
    facts = facts_json.get("facts") or {}
    for tax, items in facts.items():
        for tag in items.keys():
            qn=f"{tax}:{tag}"
            for rx, metric in pats:
                if re.search(rx, qn, re.IGNORECASE):
                    out.append(Candidate(qn, 0.935, None, metric, origin="hint", notes="company-hint"))
    if out: dbg.log(f"[ext-hints] CIK={cik} matched {len(out)} candidates via hints")
    return out

# --------------------- Alignment helpers ----------------------
def align_pair_instant(a: dict, b: dict, anchors: List[date]) -> Tuple[dict, dict]:
    """Choose pair with closest 'end' dates; if one end dominates (closer to anchor), align to that."""
    if not a or not b: return a, b
    ea, eb = parse_date(a.get("end")), parse_date(b.get("end"))
    if not ea or not eb: return a, b
    da, db = end_distance(ea, anchors), end_distance(eb, anchors)
    # choose nearer to anchor as target date
    target = ea if da <= db else eb
    # if ends differ > 45 days, keep as-is; else prefer the nearer one
    if abs((ea - eb).days) <= 45:
        if da <= db: return a, {"u":b["unit"],"end":a["end"],"form":b["form"],"fp":b.get("fp"),"v":b["v"]}
        else:        return {"u":a["unit"],"end":b["end"],"form":a["form"],"fp":a.get("fp"),"v":a["v"]}, b
    return a, b

# --------------------- Annual/Instant pickers ------------------
def pick_best_annual(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger, prefer_unit="USD", tol_days=90, accept_missing_fp=True):
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

    # Pass 1: FY/CY/FYR
    pass1=[(u,r) for (u,r) in pool if (r.get("fp") or "").upper() in ("FY","CY","FYR")]
    chosen = smart_pick([r for (_,r) in pass1], anchors, tol_days, dbg)
    if chosen:
        chosen_unit = [u for (u,r) in pass1 if r is chosen][0]
        return ("annual", {"unit":chosen_unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":chosen.get("fp"),
                           "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")})

    # Pass 2: YTD Q4
    pass2=[(u,r) for (u,r) in pool if r.get("qtrs")==4]
    chosen = smart_pick([r for (_,r) in pass2], anchors, tol_days, dbg)
    if chosen:
        chosen_unit = [u for (u,r) in pass2 if r is chosen][0]
        return ("ytd-q4", {"unit":chosen_unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":"FY",
                           "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")})

    # Pass 3: any fp
    if accept_missing_fp:
        chosen = smart_pick([r for (_,r) in pool], anchors, tol_days, dbg)
        if chosen:
            chosen_unit = [u for (u,r) in pool if r is chosen][0]
            return ("lenient", {"unit":chosen_unit, "end":chosen.get("end"), "form":chosen.get("form"), "fp":chosen.get("fp") or "",
                                "val":float(chosen.get("val")), "accn":chosen.get("accn"), "segment":chosen.get("segment")})
    return None

def pick_best_instant(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger, prefer_unit="USD", tol_days=120):
    unit_map = get_unit_records(facts_json, qname)
    if not unit_map: 
        dbg.log(f"[instant] no units for %s" % qname); return None
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

# --------------------- Segment/Quarter helpers -----------------
def sum_segments_if_allowed(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger, prefer_unit="USD", tol_days=90):
    if qname not in ADDITIVE_QNAMES: return None
    unit_map = get_unit_records(facts_json, qname)
    if not unit_map: return None
    anchors = anchors_for_fy(fy, submissions)
    best=None
    for unit, arr in unit_map.items():
        agg={}
        for rec in arr:
            if not isinstance(rec.get("val"), (int,float)): continue
            end = parse_date(rec.get("end"))
            if not end or not within_tolerance(end, anchors, tol_days): continue
            key=(rec.get("end"), rec.get("form"))
            agg.setdefault(key, 0.0)
            agg[key]+=float(rec.get("val"))
        for (end, form), total in agg.items():
            cand={"unit":unit,"end":end,"form":form,"fp":"FY","val":total,"accn":None,"segment":"seg-sum"}
            if (best is None) or (end>(best["end"] or "")): best=cand
    if best:
        dbg.log(f"[segment-sum] {qname} -> end={best['end']} unit={best['unit']} total={best['val']:.2f}")
    return ("sum-of-segments", best) if best else None

def sum_quarter_increments(facts_json: dict, qname: str, fy: int, submissions: dict, dbg: Debugger, prefer_unit="USD", tol_days=120):
    unit_map = get_unit_records(facts_json, qname)
    if not unit_map: return None
    anchors = anchors_for_fy(fy, submissions)
    for unit, arr in unit_map.items():
        q={}
        for rec in arr:
            if not isinstance(rec.get("val"), (int,float)): continue
            end=parse_date(rec.get("end"))
            if not end or not within_tolerance(end, anchors, tol_days): continue
            if rec.get("qtrs") != 1: continue
            fp=(rec.get("fp") or "").upper()
            if fp in ("Q1","Q2","Q3","Q4"):
                q[fp]=float(rec.get("val"))
        if len(q) >= 4:
            total = q["Q1"]+q["Q2"]+q["Q3"]+q["Q4"]
            ends=[rec.get("end") for rec in arr if (rec.get("qtrs")==1 and (rec.get("fp") or "").upper()=="Q4")]
            end_choice = sorted(ends)[-1] if ends else f"{fy}-12-31"
            return ("sum-of-quarters", {"unit":unit,"end":end_choice,"form":"10-Q/10-K","fp":"FY","val":total,"accn":None,"segment":None})
    return None
    
def try_sum_of_segments_generic(facts, qname, fy, submissions, dbg, prefer_unit="USD", tol_days=90):
    """
    us-gaap 네임스페이스의 Revenue성 qname이라면, 사전 화이트리스트에 없어도 세그먼트 합산을 시도.
    """
    try: tax, tag = qname.split(":")
    except ValueError: 
        return None
    if tax != "us-gaap":
        return None
    # 'Revenue'가 이름에 들어가고, 명백한 제외어가 없을 때만
    if ("Revenue" not in tag) and ("Revenues" not in tag):
        return None
    if any(bad in tag for bad in ["DeferredRevenue","UnearnedRevenue","Allowance","Receivable","Liability","Tax","ExciseTax"]):
        return None
    return sum_segments_if_allowed(facts, qname, fy, submissions, dbg, prefer_unit, tol_days)

def replace_cecl(components):
    """
    컴포지트 정의에 있는 일부 축약 태그를 실제 선택에 유리하게 확장합니다.
    예: PPNR 구성에서 Net/Provision 계정을 세분화하여 매칭 기회를 늘림.
    """
    out = []
    for qname, weight in components:
        if qname == "us-gaap:ProvisionForLoanLeaseAndOtherLosses":
            out.append(("us-gaap:ProvisionForCreditLosses", weight))
            out.append((qname, weight))
        elif qname == "us-gaap:InterestIncomeExpenseNet":
            out.append(("us-gaap:InterestIncome", +1.0))
            out.append(("us-gaap:InterestExpense", -1.0))
            out.append((qname, +1.0))
        else:
            out.append((qname, weight))
    return out

def align_and_sum_components(facts_json: dict,
                             comp_list,
                             fy: int,
                             submissions: dict,
                             dbg,
                             prefer_unit: str = "USD",
                             tol_days: int = 120):
    """
    여러 구성요소(qname, weight)를 같은 회계기간 end와 같은 통화 단위로 정렬해 가중합을 계산.
    - ext:Foo 같은 placeholder는 회사 확장 네임스페이스 또는 us-gaap에서 실제 태그로 해석 시도
    - 같은 end(지배적인 end)에 맞춰 단위를 결정(다수결/선호 통화 우선)
    반환값:
      { value, unit, end, form, fp, rows:[(qname, w, picked_val)], adj }
      또는 None (정렬 실패)
    """
    # 안전 가드
    if not facts_json or not isinstance(facts_json, dict):
        return None

    facts_map = (facts_json.get("facts") or {})
    std_prefixes = {"us-gaap","ifrs-full","dei","srt"}
    nonstd_prefixes = [p for p in facts_map.keys() if p not in std_prefixes]

    # 1) ext: 자리표시자 실제 qname으로 확장
    expanded = []
    for qn, w in comp_list:
        if isinstance(qn, tuple) or isinstance(qn, list):
            qname = qn[0]; wt = qn[1] if len(qn) > 1 else w
        else:
            qname = qn; wt = w

        if isinstance(qname, str) and qname.startswith("ext:"):
            local = qname.split("ext:", 1)[1]
            matched = False
            # (a) 회사 확장 네임스페이스에서 먼저 찾기
            for pfx in nonstd_prefixes:
                if local in (facts_map.get(pfx) or {}):
                    expanded.append((f"{pfx}:{local}", wt))
                    matched = True
            # (b) 정확한 대소문자 불일치 보정
            if not matched:
                for pfx, items in facts_map.items():
                    for tag in items.keys():
                        if tag.lower() == local.lower():
                            expanded.append((f"{pfx}:{tag}", wt))
                            matched = True
                            break
                    if matched:
                        break
            # (c) 실패 시 원본 유지(후속 단계에서 스킵됨)
            if not matched:
                expanded.append((qname, wt))
        else:
            expanded.append((qname, wt))

    # 2) FY 기준 앵커 계산
    def _parse_date(s):
        if not s: return None
        for fmt in ("%Y-%m-%d","%Y/%m/%d","%m/%d/%Y"):
            try: 
                from datetime import datetime
                return datetime.strptime(s, fmt).date()
            except Exception:
                pass
        return None

    def _anchors_for_fy(fy, submissions):
        fye = str(submissions.get("fiscalYearEnd") or "1231").strip()
        if not re.fullmatch(r"\d{4}", fye): fye = "1231"
        mm, dd = int(fye[:2]), int(fye[2:])
        from datetime import date
        return [date(fy, mm, dd), date(fy+1, mm, dd)]

    def _within_tolerance(d, anchors, tol):
        return any(abs((d - a).days) <= tol for a in anchors)

    anchors = _anchors_for_fy(fy, submissions)

    # 3) 각 구성요소별로 (end, unit) 키의 최적 레코드 선택(절대값 최대·최근호감)
    comp_maps = []
    for qname, w in expanded:
        per = {}
        # 존재하지 않는 qname은 패스
        try:
            tax, tag = qname.split(":")
        except Exception:
            continue
        unit_map = ((facts_map.get(tax) or {}).get(tag) or {}).get("units", {}) or {}
        for unit, arr in unit_map.items():
            for rec in arr:
                val = rec.get("val")
                if not isinstance(val, (int, float)): 
                    continue
                end = _parse_date(rec.get("end"))
                if not end or not _within_tolerance(end, anchors, tol_days):
                    continue
                key = (rec.get("end"), unit)
                # 동일 (end, unit)이 여러 값이면 절대값 큰 값 유지
                cur = per.get(key)
                if (cur is None) or (abs(val) > abs(cur["val"])):
                    per[key] = {
                        "val": float(val),
                        "unit": unit,
                        "end": rec.get("end"),
                        "form": rec.get("form"),
                        "fp": rec.get("fp"),
                        "segment": rec.get("segment"),
                        "qname": qname,
                        "w": w
                    }
        if per:
            comp_maps.append(per)

    if not comp_maps:
        if dbg: dbg.log("[composite] no component maps after expansion")
        return None

    # 4) 지배적 end 선택(가장 많이 교집합 되는 end)
    end_counts = {}
    for per in comp_maps:
        for (end, unit) in per.keys():
            end_counts[end] = end_counts.get(end, 0) + 1
    if not end_counts:
        if dbg: dbg.log("[composite] no candidate ends found")
        return None
    dominant_end = max(end_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]

    # 5) 단위 결정(선호 통화 우선, 아니면 빈도수 우선)
    units_at_end = []
    for per in comp_maps:
        if (dominant_end, prefer_unit) in per:
            units_at_end.append(prefer_unit)
        else:
            any_unit = [u for (e, u) in per.keys() if e == dominant_end]
            units_at_end.append(any_unit[0] if any_unit else None)

    if all(u == prefer_unit for u in units_at_end if u):
        chosen_unit = prefer_unit
    else:
        freq = {}
        for u in units_at_end:
            if u: freq[u] = freq.get(u, 0) + 1
        chosen_unit = max(freq, key=freq.get) if freq else (prefer_unit if units_at_end and units_at_end[0] else None)

    # 6) 지배 end & 선택 unit에서 각 구성 요소의 대표값 모으기(근사치 보정 포함)
    picked = []
    for per in comp_maps:
        item = per.get((dominant_end, chosen_unit))
        if not item:
            # 동일 end 내 다른 단위가 있으면 그중 |val| 큰 것
            cand = [v for (e, u), v in per.items() if e == dominant_end]
            if cand:
                item = sorted(cand, key=lambda x: abs(x["val"]))[-1]
            else:
                # 가장 가까운 end 대체
                nearest, bestd = None, None
                for (e, u), v in per.items():
                    d = abs((_parse_date(e) - _parse_date(dominant_end)).days)
                    if bestd is None or d < bestd:
                        bestd = d; nearest = v
                item = nearest
        if item:
            picked.append(item)

    if not picked:
        if dbg: dbg.log("[composite] no aligned rows")
        return None

    # 7) 가중합
    value = sum(r["w"] * r["val"] for r in picked)
    unit  = chosen_unit or picked[0]["unit"]
    form  = picked[0].get("form")
    fp    = picked[0].get("fp")

    # 8) 스코어 보정(간단)
    def _score_adj(form, unit, fp, has_seg, industry_hit=True):
        s = 0.0
        if form in ("10-K","20-F","10-K/A","20-F/A"): s += 0.06
        elif form: s -= 0.01
        if unit == "USD": s += 0.03
        elif unit: s -= 0.02
        if (fp or "").upper() in ("FY","CY","FYR"): s += 0.03
        if has_seg: s -= 0.01
        if industry_hit: s += 0.02
        return s

    adj = sum(_score_adj(r.get("form"), unit, r.get("fp"), bool(r.get("segment")), True) for r in picked) / max(1, len(picked))

    if dbg:
        dbg.log(f"[composite] dominant_end={dominant_end} unit={unit} rows={[(r['qname'], r['val']) for r in picked]} -> {value:.2f}")

    return {
        "value": value,
        "unit": unit,
        "end": dominant_end,
        "form": form,
        "fp": fp,
        "rows": [(r["qname"], r["w"], r["val"]) for r in picked],
        "adj": adj
    }

# --------------------- Selectors -------------------------------
def select_revenue(facts, fy, inds, submissions, dbg: Debugger, prefer_unit="USD", tol_days=90, lenient=True, suggestions_map=None, cik_for_hint=None, dump_ext_only=False):
    # Candidate pool
    mined = mine_revenue_candidates(facts, dbg)
    hints = apply_extension_hints(cik_for_hint, facts, dbg)
    pool = list(CANDIDATES["Revenue"]) + mined + hints
    if suggestions_map:
        pool += apply_suggestions(cik_for_hint, "Revenue", suggestions_map, dbg)
    dbg.log(f"[select_revenue] pool={len(pool)}")

    # record suggestions (mined/hints/ext only if requested)
    for c in mined + hints:
        record_suggestion(cik_for_hint, "Revenue", c.qname, c.origin, c.notes, ext_only=dump_ext_only)

    # Direct passes (two tolerance levels: tol_days, tol_days+60)
    for widen in (0, 60):
        best=None
        for cand in pool:
            unit_map=get_unit_records(facts, cand.qname)
            if not unit_map: 
                dbg.log(f"[revenue] no units for {cand.qname}")
                continue
            res = pick_best_annual(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen, accept_missing_fp=True)
            if res and res[1]:
                p=res[1]; typ=res[0]
                industry_hit = True if not cand.industry_only else bool(cand.industry_only & inds)
                score=cand.base_score + (0.012 if typ=="annual" else (-0.004 if typ=="ytd-q4" else -0.01)) \
                      + score_adj(p["form"], p["unit"], p["fp"], bool(p["segment"]), industry_hit)
                payload={"source_type":typ,"qname":cand.qname,"normalized_as":"Revenue","value":p["val"],"unit":p["unit"],
                         "end":p["end"],"form":p["form"],"accn":p["accn"],"confidence":max(0,min(1,score)),
                         "reason":f"{typ} {cand.qname} [{cand.origin}] (tol+{widen})"}
                if (best is None) or (score>best[0]) or (math.isclose(score,best[0]) and payload["end"]>(best[1]["end"] or "")):
                    best=(score,payload)
            if (best is None) and (cand.qname in ADDITIVE_QNAMES):
                seg=sum_segments_if_allowed(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen)
                if seg:
                    p=seg[1]; score=(cand.base_score-0.01)+score_adj(p["form"], p["unit"], p["fp"], True, True)
                    best=(score,{"source_type":"sum-of-segments","qname":cand.qname,"normalized_as":"Revenue","value":p["val"],"unit":p["unit"],
                                 "end":p["end"],"form":p["form"],"accn":None,"confidence":max(0,min(1,score)),
                                 "reason":f"sum-of-segments {cand.qname} (tol+{widen})"})
            # Generic segment-sum fallback for mined us-gaap:*Revenue* (moved inside loop)
            if best is None:
                seg2 = try_sum_of_segments_generic(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen)
                if seg2:
                    p = seg2[1]
                    score = (cand.base_score - 0.012) + score_adj(p["form"], p["unit"], p["fp"], True, True)
                    best = (score, {
                        "source_type": "sum-of-segments",
                        "qname": cand.qname,
                        "normalized_as": "Revenue",
                        "value": p["val"],
                        "unit":  p["unit"],
                        "end":   p["end"],
                        "form":  p["form"],
                        "accn":  None,
                        "confidence": max(0, min(1, score)),
                        "reason": f"generic sum-of-segments {cand.qname} (tol+{widen})"
                    })
        if best: return best[1]

    # Composite (with ext resolution)
    for comp in COMPOSITES.get("Revenue", []):
        if comp.industry_only and not (comp.industry_only & inds):
            pass
        comp_list = comp.components
        # suggestion record for ext placeholders
        for q,_ in comp_list:
            record_suggestion(cik_for_hint, "Revenue", q, "composite", "component", ext_only=dump_ext_only)
        from_components = []
        # expand & align
        facts_map=facts.get("facts") or {}
        nonstd_prefixes=[p for p in facts_map.keys() if p not in STD_PREFIXES]
        expanded=[]
        for (qn,w) in comp_list:
            if qn.startswith("ext:"):
                local = qn.split("ext:",1)[1]
                matched=False
                for pfx in nonstd_prefixes + ["us-gaap"]:
                    if local in (facts_map.get(pfx) or {}):
                        expanded.append((f"{pfx}:{local}", w)); matched=True
                        from_components.append(f"{pfx}:{local}")
                if not matched:
                    for pfx, items in facts_map.items():
                        for tag in items.keys():
                            if tag.lower()==local.lower():
                                expanded.append((f"{pfx}:{tag}", w)); matched=True
                                from_components.append(f"{pfx}:{tag}")
                if not matched: expanded.append((qn,w))
            else:
                expanded.append((qn,w)); from_components.append(qn)
        aligned = align_and_sum_components(facts, expanded, fy, submissions, dbg, prefer_unit, tol_days+30)
        if aligned:
            # record concrete component qnames used
            for (qname, w, v) in aligned["rows"]:
                record_suggestion(cik_for_hint, "Revenue", qname, "composite-used", f"w={w}", ext_only=dump_ext_only)
            score=0.90 + aligned["adj"]
            payload={"source_type":"composite","name":comp.name,"normalized_as":comp.normalized_as,
                     "value":aligned["value"],"unit":aligned["unit"],"end":aligned["end"],"form":aligned["form"],
                     "accn":None,"components":aligned["rows"],"confidence":max(0,min(1,score)),
                     "reason":f"composite {comp.name} (aligned dominant end)"}
            return payload

    # Quarter sum fallback
    for qn in ["us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax","us-gaap:Revenues","us-gaap:SalesRevenueNet","us-gaap:OperatingRevenue"]:
        res = sum_quarter_increments(facts, qn, fy, submissions, dbg, prefer_unit, tol_days+60)
        if res:
            p=res[1]; score=0.88 + score_adj(p["form"], p["unit"], p["fp"], False, True)
            return {"source_type":"sum-of-quarters","qname":qn,"normalized_as":"Revenue","value":p["val"],"unit":p["unit"],"end":p["end"],
                    "form":p["form"],"accn":None,"confidence":max(0,min(1,score)),"reason":f"sum-of-quarters {qn}"}

    # Last-resort lenient scan (with expanded tolerance for date matching failures)
    if lenient:
        mined = mine_revenue_candidates(facts, dbg)
        anchors=anchors_for_fy(fy, submissions)
        bestR=None
        # Try with progressively wider tolerance: +150, +240, +365 days
        for tol_expand in [150, 240, 365]:
            for cand in mined:
                record_suggestion(cik_for_hint, "Revenue", cand.qname, cand.origin, f"lenient-scan-tol+{tol_expand}", ext_only=dump_ext_only)
                for unit, rec in iter_all_facts(facts, cand.qname):
                    end=parse_date(rec.get("end"))
                    if not end or not within_tolerance(end, anchors, tol_days+tol_expand): continue
                    val=float(rec.get("val"))
                    # Penalize score based on tolerance expansion
                    penalty = 0.0 if tol_expand == 150 else (0.02 if tol_expand == 240 else 0.04)
                    s=0.80 - penalty + score_adj(rec.get("form"), unit, rec.get("fp"), bool(rec.get("segment")), True)
                    payload={"source_type":"lenient-scan","qname":cand.qname,"normalized_as":"Revenue",
                             "value":val,"unit":unit,"end":rec.get("end"),"form":rec.get("form"),"accn":rec.get("accn"),
                             "confidence":max(0,min(1,s)),"reason":f"lenient nearest {cand.qname} (tol+{tol_expand})"}
                    if (bestR is None) or (abs(val)>abs(bestR[1]["value"])):
                        bestR=(s,payload)
            if bestR: break
        if bestR: return bestR[1]

    # Ultimate fallback: try to find ANY revenue-like tag with ANY date (very lenient)
    if lenient:
        anchors=anchors_for_fy(fy, submissions)
        bestR=None
        # First try mined candidates
        mined = mine_revenue_candidates(facts, dbg)
        for cand in mined:
            for unit, rec in iter_all_facts(facts, cand.qname):
                end=parse_date(rec.get("end"))
                if not end: continue
                val=float(rec.get("val"))
                dist = end_distance(end, anchors)
                s=0.70 - (dist/365.0)*0.1 + score_adj(rec.get("form"), unit, rec.get("fp"), bool(rec.get("segment")), True)
                payload={"source_type":"ultimate-fallback","qname":cand.qname,"normalized_as":"Revenue",
                         "value":val,"unit":unit,"end":rec.get("end"),"form":rec.get("form"),"accn":rec.get("accn"),
                         "confidence":max(0,min(1,s)),"reason":f"ultimate fallback {cand.qname} (dist={dist} days)"}
                if (bestR is None) or (dist < end_distance(parse_date(bestR[1]["end"]), anchors) if bestR[1].get("end") else True):
                    bestR=(s,payload)
        # If no mined candidates, try all standard revenue tags directly
        if bestR is None:
            rev_tags = [
                "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                "us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
                "us-gaap:Revenues",
                "us-gaap:SalesRevenueNet",
                "us-gaap:NetSales",
                "us-gaap:OperatingRevenue",
            ]
            for qn in rev_tags:
                unit_map = get_unit_records(facts, qn)
                if not unit_map: continue
                for unit, arr in unit_map.items():
                    for rec in arr:
                        if not isinstance(rec.get("val"), (int,float)): continue
                        end=parse_date(rec.get("end"))
                        if not end: continue
                        val=float(rec.get("val"))
                        dist = end_distance(end, anchors)
                        s=0.65 - (dist/365.0)*0.1 + score_adj(rec.get("form"), unit, rec.get("fp"), bool(rec.get("segment")), True)
                        payload={"source_type":"ultimate-fallback","qname":qn,"normalized_as":"Revenue",
                                 "value":val,"unit":unit,"end":rec.get("end"),"form":rec.get("form"),"accn":rec.get("accn"),
                                 "confidence":max(0,min(1,s)),"reason":f"ultimate fallback {qn} (dist={dist} days)"}
                        if (bestR is None) or (dist < end_distance(parse_date(bestR[1]["end"]), anchors) if bestR[1].get("end") else True):
                            bestR=(s,payload)
        if bestR: return bestR[1]

    return {"source_type":"none","reason":"no candidate matched"}

def select_instant_direct_generic(facts, fy, submissions, dbg, candidates: List[Candidate], metric_name: str,
                                  prefer_unit="USD", tol_days=120, cik_for_hint=None, suggestions_map=None, dump_ext_only=False):
    pool = list(candidates)
    # mined
    if metric_name=="Assets":
        mined = mine_assets_candidates(facts, dbg)
    elif metric_name=="Liabilities":
        mined = mine_liabilities_candidates(facts, dbg)
    elif metric_name=="Equity":
        mined = mine_equity_candidates(facts, dbg)
    else:
        mined = []
    pool += mined
    # suggestions
    if suggestions_map:
        pool += apply_suggestions(cik_for_hint, metric_name, suggestions_map, dbg)
    # suggestions record
    for c in mined:
        record_suggestion(cik_for_hint, metric_name, c.qname, c.origin, c.notes, ext_only=dump_ext_only)

    best=None
    for widen in (0, 60):
        for cand in pool:
            res = pick_best_instant(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen)
            if not res: continue
            p=res; industry_hit=True
            score=cand.base_score + score_adj(p.get("form"), p.get("unit"), p.get("fp"), bool(p.get("segment")), industry_hit) - (0.02 if widen else 0.0)
            out={"source_type":"direct","qname":cand.qname,"normalized_as":metric_name,"value":p["val"],"unit":p["unit"],
                 "end":p["end"],"form":p["form"],"accn":p["accn"],"confidence":max(0,min(1,score)),
                 "reason":f"instant {cand.qname} [{cand.origin}] (tol+{widen})"}
            if (best is None) or (score>best[0]) or (math.isclose(score,best[0]) and out["end"]>(best[1]["end"] or "")):
                best=(score,out)
        if best: break
    return best[1] if best else None

def grab_instant_best(facts, fy, submissions, dbg, qnames: List[str], prefer_unit="USD", tol_days=120):
    """Try a small set of qnames and return best instant record dict or None."""
    for widen in (0, 60):
        anchors = anchors_for_fy(fy, submissions)
        best=None
        for qn in qnames:
            rec = pick_best_instant(facts, qn, fy, submissions, dbg, prefer_unit, tol_days+widen)
            if rec:
                s = 0.90 + score_adj(rec.get("form"), rec.get("unit"), rec.get("fp"), bool(rec.get("segment")), True) - (0.01 if widen else 0.0)
                cand = {"qn": qn, "u": rec["unit"], "end": rec["end"], "form": rec["form"], "fp": rec.get("fp"), "v": rec["val"], "score": s}
                if (best is None) or (cand["score"] > best["score"]):
                    best = cand
        if best: return best
    return None

def select_assets(facts, fy, inds, submissions, dbg, prefer_unit="USD", tol_days=120, suggestions_map=None, cik_for_hint=None, dump_ext_only=False):
    direct = select_instant_direct_generic(facts, fy, submissions, dbg, CANDIDATES["Assets"], "Assets",
                                           prefer_unit, tol_days, cik_for_hint, suggestions_map, dump_ext_only)
    if direct: return direct
    # Derive: Liabilities + Equity  OR  LAS (already direct tried) fallback again via derivation with pair alignment
    liab = grab_instant_best(facts, fy, submissions, dbg, ["us-gaap:Liabilities","ifrs-full:Liabilities"], prefer_unit, tol_days)
    eqty = grab_instant_best(facts, fy, submissions, dbg, [
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "us-gaap:StockholdersEquity","ifrs-full:Equity"
    ], prefer_unit, tol_days)
    if liab and eqty:
        anchors = anchors_for_fy(fy, submissions)
        # Align end dates loosely
        # (We won't force change of end date values; just compute and use nearer end)
        # Choose target end as the one closer to anchors
        da, db = end_distance(parse_date(liab["end"]), anchors), end_distance(parse_date(eqty["end"]), anchors)
        if da <= db:
            end = liab["end"]; unit=liab["u"]; form=liab["form"]; fp=liab.get("fp")
        else:
            end = eqty["end"]; unit=eqty["u"]; form=eqty["form"]; fp=eqty.get("fp")
        val = float(liab["v"]) + float(eqty["v"])
        score = 0.89 + score_adj(form, unit, fp, False, True)
        return {"source_type":"derived","name":"LiabilitiesPlusEquity","normalized_as":"Assets","value":val,"unit":unit,"end":end,"form":form,
                "accn":None,"confidence":max(0,min(1,score)),"reason":"derived Assets = Liabilities + Equity"}
    return {"source_type":"none","reason":"no candidate matched"}

def select_liabilities(facts, fy, inds, submissions, dbg, prefer_unit="USD", tol_days=120, suggestions_map=None, cik_for_hint=None, dump_ext_only=False):
    direct = select_instant_direct_generic(facts, fy, submissions, dbg, CANDIDATES["Liabilities"], "Liabilities",
                                           prefer_unit, tol_days, cik_for_hint, suggestions_map, dump_ext_only)
    if direct: return direct
    # Derive: Assets - Equity  OR  LAS - Equity
    assets = grab_instant_best(facts, fy, submissions, dbg, ["us-gaap:Assets","ifrs-full:Assets","us-gaap:LiabilitiesAndStockholdersEquity","ifrs-full:EquityAndLiabilities"], prefer_unit, tol_days)
    eqty   = grab_instant_best(facts, fy, submissions, dbg, [
        "us-gaap:StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest","us-gaap:StockholdersEquity","ifrs-full:Equity"
    ], prefer_unit, tol_days)
    if assets and eqty:
        anchors = anchors_for_fy(fy, submissions)
        da, db = end_distance(parse_date(assets["end"]), anchors), end_distance(parse_date(eqty["end"]), anchors)
        if da <= db:
            end = assets["end"]; unit=assets["u"]; form=assets["form"]; fp=assets.get("fp")
        else:
            end = eqty["end"]; unit=eqty["u"]; form=eqty["form"]; fp=eqty.get("fp")
        val = float(assets["v"]) - float(eqty["v"])
        score = 0.88 + score_adj(form, unit, fp, False, True)
        return {"source_type":"derived","name":"AssetsMinusEquity","normalized_as":"Liabilities","value":val,"unit":unit,"end":end,"form":form,
                "accn":None,"confidence":max(0,min(1,score)),"reason":"derived Liabilities = Assets − Equity"}
    return {"source_type":"none","reason":"no candidate matched"}

def select_equity(facts, fy, inds, submissions, dbg, prefer_unit="USD", tol_days=120, suggestions_map=None, cik_for_hint=None, dump_ext_only=False):
    direct = select_instant_direct_generic(facts, fy, submissions, dbg, CANDIDATES["Equity"], "Equity",
                                           prefer_unit, tol_days, cik_for_hint, suggestions_map, dump_ext_only)
    if direct: return direct
    # Derive: Assets - Liabilities  OR  LAS - Liabilities
    assets = grab_instant_best(facts, fy, submissions, dbg, ["us-gaap:Assets","ifrs-full:Assets","us-gaap:LiabilitiesAndStockholdersEquity","ifrs-full:EquityAndLiabilities"], prefer_unit, tol_days)
    liab   = grab_instant_best(facts, fy, submissions, dbg, ["us-gaap:Liabilities","ifrs-full:Liabilities"], prefer_unit, tol_days)
    if assets and liab:
        anchors = anchors_for_fy(fy, submissions)
        da, db = end_distance(parse_date(assets["end"]), anchors), end_distance(parse_date(liab["end"]), anchors)
        if da <= db:
            end = assets["end"]; unit=assets["u"]; form=assets["form"]; fp=assets.get("fp")
        else:
            end = liab["end"]; unit=liab["u"]; form=liab["form"]; fp=liab.get("fp")
        val = float(assets["v"]) - float(liab["v"])
        score = 0.88 + score_adj(form, unit, fp, False, True)
        return {"source_type":"derived","name":"AssetsMinusLiabilities","normalized_as":"Equity","value":val,"unit":unit,"end":end,"form":form,
                "accn":None,"confidence":max(0,min(1,score)),"reason":"derived Equity = Assets − Liabilities"}
    return {"source_type":"none","reason":"no candidate matched"}

def select_cash_instant(facts, fy, inds, submissions, dbg: Debugger, prefer_unit="USD", tol_days=120):
    # Direct passes (two tolerance levels: tol_days, tol_days+60)
    for widen in (0, 60):
        for cand in CANDIDATES["CashAndCashEquivalents"] + mine_cash_candidates(facts, dbg):
            record_suggestion(None, "CashAndCashEquivalents", cand.qname, cand.origin, "mined-cash")  # cik not known here
            unit_map=get_unit_records(facts, cand.qname)
            if not unit_map: continue
            anchors=anchors_for_fy(fy, submissions)
            best=None
            for unit, arr in unit_map.items():
                for rec in arr:
                    if not isinstance(rec.get("val"), (int,float)): continue
                    end=parse_date(rec.get("end"))
                    if not end or not within_tolerance(end, anchors, tol_days+widen): continue
                    payload={"unit":unit,"end":rec.get("end"),"form":rec.get("form"),"fp":rec.get("fp"),"val":float(rec.get("val")),"accn":rec.get("accn")}
                    if (best is None) or (payload["end"]>(best["end"] or "")): best=payload
            if best:
                score=cand.base_score + score_adj(best["form"], best["unit"], best["fp"], False, True) - (0.02 if widen else 0.0)
                return {"source_type":"direct","qname":cand.qname,"normalized_as":"CashAndCashEquivalents","value":best["val"],"unit":best["unit"],
                        "end":best["end"],"form":best["form"],"accn":best["accn"],"confidence":max(0,min(1,score)),
                        "reason":f"hit {cand.qname} ({cand.origin}) (tol+{widen})"}
    return {"source_type":"none","reason":"no candidate matched"}

def select_net_income(facts, fy, inds, submissions, dbg: Debugger, prefer_unit="USD", tol_days=90):
    # Direct passes (two tolerance levels: tol_days, tol_days+60)
    for widen in (0, 60):
        best=None
        for cand in CANDIDATES["NetIncome"]:
            res = pick_best_annual(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen, accept_missing_fp=True)
            if res and res[1]:
                p=res[1]; typ=res[0]
                score=cand.base_score + (0.012 if typ=="annual" else (-0.004 if typ=="ytd-q4" else -0.01)) \
                      + score_adj(p["form"], p["unit"], p["fp"], False, True) - (0.02 if widen else 0.0)
                out={"source_type":typ,"qname":cand.qname,"normalized_as":"NetIncome","value":p["val"],"unit":p["unit"],
                     "end":p["end"],"form":p["form"],"accn":p["accn"],"confidence":max(0,min(1,score)),
                     "reason":f"{typ} {cand.qname} (tol+{widen})"}
                if (best is None) or (score>best[0]): best=(score,out)
        if best: return best[1]

    def grab(qn):
        chosen = pick_best_annual(facts, qn, fy, submissions, dbg, prefer_unit, tol_days+30, accept_missing_fp=True)
        if not chosen: return None
        p=chosen[1]; return {"u":p["unit"],"end":p["end"],"form":p["form"],"fp":p["fp"],"v":p["val"]}
    pre  = grab("us-gaap:IncomeBeforeIncomeTaxes")
    tax  = grab("us-gaap:IncomeTaxExpenseBenefit")
    disc = grab("us-gaap:IncomeLossFromDiscontinuedOperationsNetOfTax")
    nci  = grab("us-gaap:NetIncomeLossAttributableToNoncontrollingInterest")
    if pre and tax:
        val = pre["v"] - tax["v"] + (disc["v"] if disc else 0.0) - (nci["v"] if nci else 0.0)
        unit=pre["u"]; end=pre["end"]; form=pre["form"]; fp=pre["fp"]
        score=0.90 + score_adj(form, unit, fp, False, True)
        return {"source_type":"derived","name":"PreTaxMinusTax(±Disc)−NCI","normalized_as":"NetIncome","value":val,"unit":unit,"end":end,"form":form,
                "accn":None,"confidence":max(0,min(1,score)),"reason":"derived NetIncome = PreTax - Tax (±Disc) - NCI"}
    cont = grab("us-gaap:IncomeLossFromContinuingOperationsAfterTax")
    if cont:
        val = cont["v"] + (disc["v"] if disc else 0.0) - (nci["v"] if nci else 0.0)
        unit=cont["u"]; end=cont["end"]; form=cont["form"]; fp=cont["fp"]
        score=0.88 + score_adj(form, unit, fp, False, True)
        return {"source_type":"derived","name":"ContOps±Disc−NCI","normalized_as":"NetIncome","value":val,"unit":unit,"end":end,"form":form,
                "accn":None,"confidence":max(0,min(1,score)),"reason":"derived NetIncome = ContOps ± Disc − NCI"}
    return {"source_type":"none","reason":"no candidate matched"}

def select_operating_income(facts, fy, inds, submissions, dbg: Debugger, prefer_unit="USD", tol_days=90):
    # Direct passes (three tolerance levels: tol_days, tol_days+60, tol_days+120)
    for widen in (0, 60, 120):
        direct=None
        for cand in CANDIDATES["OperatingIncome"]:
            res = pick_best_annual(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen, accept_missing_fp=True)
            if res and res[1]:
                p=res[1]; typ=res[0]
                industry_hit = True if not cand.industry_only else bool(cand.industry_only & inds)
                penalty = 0.0 if widen == 0 else (0.02 if widen == 60 else 0.04)
                score=cand.base_score + (0.012 if typ=="annual" else (-0.004 if typ=="ytd-q4" else -0.01)) \
                      + score_adj(p["form"], p["unit"], p["fp"], bool(p["segment"]), industry_hit) - penalty
                out={"source_type":typ,"qname":cand.qname,"normalized_as":cand.normalized_as if cand.normalized_as!="AUTO" else "OperatingIncome",
                     "value":p["val"],"unit":p["unit"],"end":p["end"],"form":p["form"],"accn":p["accn"],"confidence":max(0,min(1,score)),
                     "reason":f"{typ} {cand.qname} (tol+{widen})"}
                if (direct is None) or (score>direct[0]): direct=(score,out)
        if direct: return direct[1]

    # Composite with progressively wider tolerance
    for tol_expand in [30, 60, 120]:
        for comp in COMPOSITES["OperatingIncome"]:
            comp_list = comp.components
            aligned = align_and_sum_components(facts, comp_list, fy, submissions, dbg, prefer_unit, tol_days+tol_expand)
            if aligned:
                penalty = 0.0 if tol_expand == 30 else (0.01 if tol_expand == 60 else 0.02)
                score=comp.base_score + aligned["adj"] + (0.0 if (comp.industry_only and (comp.industry_only & inds)) else -0.02) - penalty
                payload={"source_type":"composite","name":comp.name,"normalized_as":comp.normalized_as,
                         "value":aligned["value"],"unit":aligned["unit"],"end":aligned["end"],"form":aligned["form"],
                         "accn":None,"components":aligned["rows"],"confidence":max(0,min(1,score)),
                         "reason":f"composite {comp.name} (aligned dominant end, tol+{tol_expand})"}
                return payload

    def grab_best(qn, tol_expand=30):
        chosen = pick_best_annual(facts, qn, fy, submissions, dbg, prefer_unit, tol_days+tol_expand, accept_missing_fp=True)
        if not chosen: return None
        p=chosen[1]; return {"u":p["unit"],"end":p["end"],"form":p["form"],"fp":p["fp"],"v":p["val"]}
    # Try derived methods with progressively wider tolerance
    for tol_expand in [30, 60, 120]:
        gp   = grab_best("us-gaap:GrossProfit", tol_expand); opex = grab_best("us-gaap:OperatingExpenses", tol_expand)
        if gp and opex:
            val=gp["v"]-opex["v"]; unit=gp["u"]; end=gp["end"]; form=gp["form"]; fp=gp["fp"]
            penalty = 0.0 if tol_expand == 30 else (0.01 if tol_expand == 60 else 0.02)
            score=0.90 - penalty + score_adj(form, unit, fp, False, True)
            return {"source_type":"derived","name":"GrossProfitMinusOperatingExpenses","normalized_as":"OperatingIncome","value":val,"unit":unit,"end":end,"form":form,
                    "accn":None,"confidence":max(0,min(1,score)),"reason":f"derived Operating = GrossProfit - OperatingExpenses (tol+{tol_expand})"}
    def fh(lst, tol_expand=30): 
        for q in lst:
            r=grab_best(q, tol_expand)
            if r: return q,r
        return None, None
    # Try Revenue-based derived methods with progressively wider tolerance
    for tol_expand in [30, 60, 120]:
        rev_q, rev = None, None
        for q in ["us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax","us-gaap:Revenues","us-gaap:SalesRevenueNet","us-gaap:OperatingRevenue",
                  "us-gaap:OperatingLeasesIncomeStatementLeaseRevenue","us-gaap:UtilityRevenue","us-gaap:ElectricUtilityRevenue"]:
            r=grab_best(q, tol_expand)
            if r: rev_q, rev = q, r; break
        if not rev: continue
        
        penalty = 0.0 if tol_expand == 30 else (0.01 if tol_expand == 60 else 0.02)
        _, cor = fh(["us-gaap:CostOfRevenue","us-gaap:CostOfGoodsAndServicesSold","us-gaap:CostOfSales"], tol_expand)
        _, sga = fh(["us-gaap:SellingGeneralAndAdministrativeExpense","us-gaap:GeneralAndAdministrativeExpense","us-gaap:SellingAndMarketingExpense"], tol_expand)
        _, rd  = fh(["us-gaap:ResearchAndDevelopmentExpense"], tol_expand)
        _, rst = fh(["us-gaap:RestructuringCharges"], tol_expand)
        _, imp = fh(["us-gaap:AssetImpairmentCharges","us-gaap:GoodwillImpairmentLoss"], tol_expand)
        minus = (cor["v"] if cor else 0.0)+(sga["v"] if sga else 0.0)+(rd["v"] if rd else 0.0)+(rst["v"] if rst else 0.0)+(imp["v"] if imp else 0.0)
        # Only use full calculation if we have at least CostOfRevenue
        if cor or sga or rd or rst or imp:
            val = rev["v"] - minus
            unit=rev["u"]; end=rev["end"]; form=rev["form"]; fp=rev["fp"]
            score=0.87 - penalty + score_adj(form, unit, fp, False, True)
            return {"source_type":"derived","name":"RevenueMinusCostsAndOpex","normalized_as":"OperatingIncome","value":val,"unit":unit,"end":end,"form":form,
                    "accn":None,"confidence":max(0,min(1,score)),"reason":f"derived Operating = Revenue - (Cost + OpEx family) (tol+{tol_expand})"}
        # Enhanced fallback: try Revenue - CostOfRevenue only (simpler calculation)
        _, cor_simple = fh(["us-gaap:CostOfRevenue","us-gaap:CostOfGoodsAndServicesSold","us-gaap:CostOfSales"], tol_expand)
        if cor_simple:
            val_simple = rev["v"] - cor_simple["v"]
            unit=rev["u"]; end=rev["end"]; form=rev["form"]; fp=rev["fp"]
            score=0.85 - penalty + score_adj(form, unit, fp, False, True)
            return {"source_type":"derived","name":"RevenueMinusCostOfRevenue","normalized_as":"OperatingIncome","value":val_simple,"unit":unit,"end":end,"form":form,
                    "accn":None,"confidence":max(0,min(1,score)),"reason":f"derived Operating = Revenue - CostOfRevenue (simplified, tol+{tol_expand})"}
    
    # REITs-specific fallback: Revenue - OperatingExpenses (REITs often don't have CostOfRevenue)
    if {"REITs","RealEstate"} & inds:
        for tol_expand in [30, 60, 120]:
            # Try REITs-specific revenue tags
            rev_q, rev = None, None
            for q in ["us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax",
                      "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                      "us-gaap:RentalRevenue",
                      "us-gaap:RealEstateRevenueNet",
                      "us-gaap:OperatingLeasesIncomeStatementLeaseRevenue",
                      "us-gaap:Revenues"]:
                r=grab_best(q, tol_expand)
                if r: rev_q, rev = q, r; break
            if not rev: continue
            
            # Try REITs-specific operating expenses
            _, opex = fh(["us-gaap:RealEstateOperatingExpenses",
                         "us-gaap:OperatingExpenses",
                         "us-gaap:CostsAndExpenses",
                         "us-gaap:OperatingCostsAndExpenses"], tol_expand)
            if opex:
                penalty = 0.0 if tol_expand == 30 else (0.01 if tol_expand == 60 else 0.02)
                val = rev["v"] - opex["v"]
                unit=rev["u"]; end=rev["end"]; form=rev["form"]; fp=rev["fp"]
                score=0.82 - penalty + score_adj(form, unit, fp, False, True)
                return {"source_type":"derived","name":"REITRevenueMinusOperatingExpenses","normalized_as":"OperatingIncome","value":val,"unit":unit,"end":end,"form":form,
                        "accn":None,"confidence":max(0,min(1,score)),"reason":f"REITs derived Operating = Revenue - OperatingExpenses (tol+{tol_expand})"}
    
    # Ultimate fallback: try to find ANY operating income-like tag with ANY date (very lenient)
    anchors=anchors_for_fy(fy, submissions)
    bestOI=None
    # Try all possible OperatingIncome-related tags
    oi_candidates = [
        "us-gaap:OperatingIncomeLoss",
        "us-gaap:EarningsBeforeInterestAndTaxes",
        "us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "us-gaap:IncomeFromOperations",
        "us-gaap:RealEstateOperatingIncomeLoss",
        "us-gaap:IncomeFromOperationsBeforeTax",
        "us-gaap:OperatingEarnings",
    ]
    # Add REITs-specific tags if applicable
    if {"REITs","RealEstate"} & inds:
        oi_candidates.extend([
            "ext:RealEstateOperatingIncome",
            "ext:OperatingIncome",
            "ext:IncomeFromOperations",
        ])
    for qn in oi_candidates:
        unit_map = get_unit_records(facts, qn)
        if not unit_map: continue
        for unit, arr in unit_map.items():
            for rec in arr:
                if not isinstance(rec.get("val"), (int,float)): continue
                end=parse_date(rec.get("end"))
                if not end: continue
                dist = end_distance(end, anchors)
                val=float(rec.get("val"))
                s=0.70 - (dist/365.0)*0.1 + score_adj(rec.get("form"), unit, rec.get("fp"), bool(rec.get("segment")), True)
                payload={"source_type":"ultimate-fallback","qname":qn,"normalized_as":"OperatingIncome",
                         "value":val,"unit":unit,"end":rec.get("end"),"form":rec.get("form"),"accn":rec.get("accn"),
                         "confidence":max(0,min(1,s)),"reason":f"ultimate fallback {qn} (dist={dist} days)"}
                if (bestOI is None) or (dist < end_distance(parse_date(bestOI[1]["end"]), anchors) if bestOI[1].get("end") else True):
                    bestOI=(s,payload)
    if bestOI: return bestOI[1]
    
    # Last resort: try mining OperatingIncome patterns
    if {"REITs","RealEstate"} & inds:
        oi_patterns = [
            r"(?:^|:)RealEstate.*Operating.*Income",
            r"(?:^|:)Operating.*Income.*RealEstate",
            r"(?:^|:)Income.*Operations",
            r"(?:^|:)Operating.*Income",
        ]
        facts_dict = facts.get("facts") or {}
        for tax, items in facts_dict.items():
            for tag in items.keys():
                qn = f"{tax}:{tag}"
                if any(re.search(p, qn, re.IGNORECASE) for p in oi_patterns):
                    unit_map = get_unit_records(facts, qn)
                    if not unit_map: continue
                    for unit, arr in unit_map.items():
                        for rec in arr:
                            if not isinstance(rec.get("val"), (int,float)): continue
                            end=parse_date(rec.get("end"))
                            if not end: continue
                            dist = end_distance(end, anchors)
                            val=float(rec.get("val"))
                            s=0.65 - (dist/365.0)*0.1 + score_adj(rec.get("form"), unit, rec.get("fp"), bool(rec.get("segment")), True)
                            payload={"source_type":"ultimate-fallback-mined","qname":qn,"normalized_as":"OperatingIncome",
                                     "value":val,"unit":unit,"end":rec.get("end"),"form":rec.get("form"),"accn":rec.get("accn"),
                                     "confidence":max(0,min(1,s)),"reason":f"ultimate fallback mined {qn} (dist={dist} days)"}
                            if (bestOI is None) or (dist < end_distance(parse_date(bestOI[1]["end"]), anchors) if bestOI[1].get("end") else True):
                                bestOI=(s,payload)
        if bestOI: return bestOI[1]
    
    return {"source_type":"none","reason":"no candidate matched"}

def select_cfo(facts, fy, inds, submissions, dbg: Debugger, prefer_unit="USD", tol_days=90):
    # Direct passes (two tolerance levels: tol_days, tol_days+60)
    for widen in (0, 60):
        for cand in CANDIDATES["CFO"]:
            res = pick_best_annual(facts, cand.qname, fy, submissions, dbg, prefer_unit, tol_days+widen, accept_missing_fp=True)
            if res and res[1]:
                p=res[1]; typ=res[0]
                score=cand.base_score + (0.012 if typ=="annual" else (-0.004 if typ=="ytd-q4" else -0.01)) \
                      + score_adj(p["form"], p["unit"], p["fp"], False, True) - (0.02 if widen else 0.0)
                return {"source_type":typ,"qname":cand.qname,"normalized_as":"CFO","value":p["val"],"unit":p["unit"],"end":p["end"],"form":p["form"],"accn":p["accn"],
                        "confidence":max(0,min(1,score)),"reason":f"{typ} {cand.qname} (tol+{widen})"}
    return {"source_type":"none","reason":"no candidate matched"}

def select_metric(facts, fy, metric, inds, submissions, dbg: Debugger, prefer_unit="USD", tol_days=90, cik_for_hint=None, suggestions_map=None, dump_ext_only=False):
    if metric=="Revenue": return select_revenue(facts, fy, inds, submissions, dbg, prefer_unit, tol_days, lenient=True, suggestions_map=suggestions_map, cik_for_hint=cik_for_hint, dump_ext_only=dump_ext_only)
    if metric=="OperatingIncome": return select_operating_income(facts, fy, inds, submissions, dbg, prefer_unit, tol_days)
    if metric=="NetIncome": return select_net_income(facts, fy, inds, submissions, dbg, prefer_unit, tol_days)
    if metric=="CashAndCashEquivalents": return select_cash_instant(facts, fy, inds, submissions, dbg, prefer_unit, tol_days+30)
    if metric=="CFO": return select_cfo(facts, fy, inds, submissions, dbg, prefer_unit, tol_days)
    if metric=="Assets": return select_assets(facts, fy, inds, submissions, dbg, prefer_unit, tol_days+30, suggestions_map, cik_for_hint, dump_ext_only)
    if metric=="Liabilities": return select_liabilities(facts, fy, inds, submissions, dbg, prefer_unit, tol_days+30, suggestions_map, cik_for_hint, dump_ext_only)
    if metric=="Equity": return select_equity(facts, fy, inds, submissions, dbg, prefer_unit, tol_days+30, suggestions_map, cik_for_hint, dump_ext_only)
    return {"source_type":"none","reason":"unknown metric"}

# ----------------------- S&P500 Auto Collection ----------------
def fetch_sp500_constituents(ua: Optional[str], dbg: Optional[Debugger] = None) -> List[dict]:
    """Wikipedia에서 S&P500 구성종목 수집"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    r = http_get(url, ua=ua, timeout=60, dbg=dbg)
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("BeautifulSoup4가 필요합니다. pip install beautifulsoup4")
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"id":"constituents"}) or soup.select_one("table.wikitable")
    if not table:
        raise RuntimeError("S&P500 표를 찾지 못했습니다.")
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
            "sub_industry": tds[isub].get_text(strip=True) if isub is not None else ""
        })
    return rows

def normalize_ticker_key(t: str) -> str:
    return re.sub(r"[.\-\s]", "", t.upper().strip())

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
        raise RuntimeError("SEC ticker→CIK 매핑 실패")
    return out

def map_sp500_to_cik(rows: List[dict], sec_map: Dict[str, dict]) -> List[dict]:
    mapped = []
    for r in rows:
        sym = r["symbol"].upper()
        rec = sec_map.get(normalize_ticker_key(sym)) \
           or sec_map.get(normalize_ticker_key(sym.replace(".", "-"))) \
           or sec_map.get(normalize_ticker_key(sym.replace("-", ".")))
        if not rec: continue
        mapped.append({
            "symbol": sym,
            "name": r.get("name") or rec.get("title") or "",
            "industry": f"{r.get('sector', '')} {r.get('sub_industry', '')}".strip(),
            "cik": rec["cik"]
        })
    return mapped

def collect_companies_auto(ua: Optional[str], tickers: Optional[List[str]] = None, limit: Optional[int] = None, dbg: Optional[Debugger] = None) -> List[dict]:
    rows = fetch_sp500_constituents(ua=ua, dbg=dbg)
    if tickers:
        want = {t.strip().upper() for t in tickers if t.strip()}
        rows = [r for r in rows if r["symbol"].upper() in want]
    sec_map = fetch_sec_ticker_cik_map(ua=ua, dbg=dbg)
    mapped = map_sp500_to_cik(rows, sec_map)
    if limit: mapped = mapped[:int(limit)]
    if not mapped: raise RuntimeError("S&P500→CIK 매핑 결과가 비었습니다.")
    return mapped

def load_companyfacts_from_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# --------------------------- CLI -------------------------------
def process_cik_with_cache(cik_padded, idx, total, ua, cache_dir, dbg, args):
    """단일 CIK 처리 함수 (캐시 확인 포함)"""
    try:
        if not args.force:
            cached = find_existing_cache(cache_dir, cik_padded)
            if cached:
                msg = f"[INFO] {idx}/{total}: CIK{cik_padded} - using cache {cached.name}"
                print(msg, file=sys.stderr)
                dbg.log(msg)
                try:
                    facts = json.load(open(cached, "r", encoding="utf-8"))
                    subs = fetch_sec_submissions(cik_padded, ua, dbg, cache_dir=cache_dir)
                    symbol = facts.get("entityTicker") or ""
                    if not symbol and subs:
                        tickers = subs.get("tickers", [])
                        symbol = tickers[0] if tickers else ""
                    meta = {"cik": cik_padded, "symbol": symbol, "name": facts.get("entityName") or "", "industry": ""}
                    return (meta, facts, subs)
                except Exception as e:
                    msg = f"[WARN] cache load failed CIK{cik_padded}: {e}"
                    print(msg, file=sys.stderr)
                    dbg.log(msg)
        
        msg = f"[INFO] Fetching Company Facts {idx}/{total}: CIK{cik_padded}"
        print(msg, file=sys.stderr)
        dbg.log(msg)
        facts = fetch_company_facts(cik_padded, ua, dbg)
        save_to_cache(cache_dir, cik_padded, facts)
        subs = fetch_sec_submissions(cik_padded, ua, dbg, cache_dir=cache_dir)
        symbol = facts.get("entityTicker") or ""
        if not symbol and subs:
            tickers = subs.get("tickers", [])
            symbol = tickers[0] if tickers else ""
        meta = {"cik": cik_padded, "symbol": symbol, "name": facts.get("entityName") or "", "industry": ""}
        return (meta, facts, subs)
    except Exception as e:
        msg = f"[ERROR] CIK{cik_padded} fetch failed: {e}"
        print(msg, file=sys.stderr)
        dbg.log(msg)
        return None

def process_company_with_cache(co, idx, total, ua, cache_dir, dbg, args):
    """단일 기업 처리 함수 (S&P500 경로용)"""
    cik = co["cik"]; symbol = co["symbol"]; name = co["name"]
    try:
        if not args.force:
            cached = find_existing_cache(cache_dir, cik)
            if cached:
                msg = f"[INFO] {idx}/{total}: {symbol} - using cache {cached.name}"
                print(msg, file=sys.stderr)
                dbg.log(msg)
                try:
                    facts = load_companyfacts_from_file(str(cached))
                    subs = fetch_sec_submissions(cik, ua, dbg, cache_dir=cache_dir)
                    meta = {"cik": cik, "symbol": symbol, "name": name, "industry": co["industry"]}
                    return (meta, facts, subs)
                except Exception as e:
                    msg = f"[WARN] cache load failed {symbol}: {e}"
                    print(msg, file=sys.stderr)
                    dbg.log(msg)
        
        msg = f"[INFO] Fetching Company Facts {idx}/{total}: {symbol}"
        print(msg, file=sys.stderr)
        dbg.log(msg)
        facts = fetch_company_facts(cik, ua, dbg)
        save_to_cache(cache_dir, cik, facts)
        subs = fetch_sec_submissions(cik, ua, dbg, cache_dir=cache_dir)
        meta = {"cik": cik, "symbol": symbol, "name": name, "industry": co["industry"]}
        return (meta, facts, subs)
    except Exception as e:
        msg = f"[ERROR] {symbol} ({cik}) fetch failed: {e}"
        print(msg, file=sys.stderr)
        dbg.log(msg)
        return None

def process_company_metrics(meta, facts, subs, metrics, args, suggestions_map, dbg):
    """단일 기업의 모든 메트릭 처리 함수"""
    cik = meta.get("cik", "")
    symbol = meta.get("symbol", "")
    company_name = f"{symbol} ({cik})" if symbol else f"CIK{cik}"
    
    try:
        inds = infer_industry_set(meta, facts, subs, dbg)
        fye = str(subs.get("fiscalYearEnd") or "")
        rows = []
        
        for m in metrics:
            try:
                sel = select_metric(facts, args.fy, m, inds, subs, dbg, 
                                   prefer_unit=args.prefer_unit, tol_days=args.fy_tol_days,
                                   cik_for_hint=meta.get("cik"), suggestions_map=suggestions_map, 
                                   dump_ext_only=args.dump_ext_only)
                comps = sel.get("components")
                comp_json = ""
                if isinstance(comps, list):
                    try:
                        comp_json=json.dumps([{"qname":q,"weight":wt,"value":val} for (q,wt,val) in comps])
                        # record component qnames as suggestions (ext-only flag honored)
                        for (q,wt,val) in comps:
                            record_suggestion(meta.get("cik"), m, q, "component", f"w={wt}", ext_only=args.dump_ext_only)
                    except Exception: comp_json=""
                # record selected tag into suggestions output too
                if sel.get("qname"):
                    record_suggestion(meta.get("cik"), m, sel.get("qname"), "selected", sel.get("reason",""), ext_only=args.dump_ext_only)
                
                rows.append({
                    "cik": meta.get("cik",""),
                    "symbol": meta.get("symbol",""),
                    "name": meta.get("name",""),
                    "industry_inferred": ";".join(sorted(inds)),
                    "fye": fye,
                    "metric": m,
                    "selected_type": sel.get("source_type",""),
                    "selected_tag": sel.get("qname") or "",
                    "composite_name": sel.get("name") or "",
                    "normalized_as": sel.get("normalized_as") or "",
                    "value": f"{sel.get('value'):.6f}" if isinstance(sel.get('value'), (int,float)) else "",
                    "unit": sel.get("unit") or "",
                    "form": sel.get("form") or "",
                    "end": sel.get("end") or "",
                    "accn": sel.get("accn") or "",
                    "confidence": f"{sel.get('confidence',0.0):.3f}",
                    "reason": sel.get("reason",""),
                    "components": comp_json,
                })
            except Exception as e:
                msg = f"[ERROR] {company_name} metric {m} processing failed: {e}"
                print(msg, file=sys.stderr)
                dbg.log(msg)
                # 에러가 발생해도 다른 메트릭은 계속 처리
                continue
        
        return rows
    except Exception as e:
        msg = f"[ERROR] {company_name} metrics processing failed: {e}"
        print(msg, file=sys.stderr)
        dbg.log(msg)
        return []

def main():
    ap = argparse.ArgumentParser(description="Selector with extension mining + hints + JSONL suggestions + adaptive FY tolerance + balance metrics")
    ap.add_argument("--fy", type=int, required=False, default=2024, help="Fiscal year (default: 2024)")
    ap.add_argument("--metrics", nargs="+", choices=METRICS+["all"], default=["all"])
    ap.add_argument("--ciks", help="Comma separated CIKs (with --use-api)")
    ap.add_argument("--use-api", action="store_true", help="Fetch SEC submissions & facts by CIKs (requires user-agent)")
    ap.add_argument("--facts", nargs="+", help="Local Company Facts JSON paths")
    ap.add_argument("--facts-dir", help="Directory of local Company Facts JSON files")
    ap.add_argument("--user-agent", help="SEC user-agent or env SEC_USER_AGENT")
    ap.add_argument("--prefer-unit", default="USD")
    ap.add_argument("--fy-tol-days", type=int, default=90, help="Tolerance days around fiscal year end anchors")
    ap.add_argument("--suggestions", help="JSONL file to load as curated suggestions; fields: cik,metric,qname")
    ap.add_argument("--dump-suggestions", help="Path to dump mined/hinted/used qnames as JSONL")
    ap.add_argument("--dump-suggestions-append", action="store_true", help="Append to JSONL if exists")
    ap.add_argument("--dump-ext-only", action="store_true", help="Dump only non-standard (extension) qnames")
    ap.add_argument("--debug", action="store_true", help="Enable debug traces")
    ap.add_argument("--debug-file", help="Path to debug log file (stderr if omitted)")
    ap.add_argument("--cache-dir", default=_CACHE_DIR, help="Cache directory for company facts")
    ap.add_argument("--force", action="store_true", help="Force API fetch even if cache exists")
    ap.add_argument("--tickers", nargs="+", help="Filter S&P500 by tickers (with --use-api, no --ciks)")
    ap.add_argument("--limit", type=int, help="Limit number of companies to process (with --use-api, no --ciks)")
    ap.add_argument("--out", default="data/tags.csv", help="Output CSV path (default: data/tags.csv)")
    args = ap.parse_args()

    dbg = Debugger(enabled=args.debug, path=args.debug_file)
    suggestions_map = load_suggestions(args.suggestions, dbg) if args.suggestions else {}

    metrics = METRICS if "all" in args.metrics else args.metrics
    ua = get_user_agent(args)

    pairs = []
    if args.facts:
        for f in args.facts:
            j=json.load(open(f,"r",encoding="utf-8"))
            cik=str(j.get("cik") or "").zfill(10)
            subs = fetch_sec_submissions(cik, ua, dbg, cache_dir=args.cache_dir if args.use_api else None) if args.use_api else {}
            # Get symbol from facts first, then from submissions
            symbol = j.get("entityTicker") or ""
            if not symbol and subs:
                tickers = subs.get("tickers", [])
                symbol = tickers[0] if tickers else ""
            meta={"cik":cik,"symbol":symbol,"name":j.get("entityName") or "","industry":""}
            pairs.append((meta, j, subs))
    elif args.facts_dir:
        for fp in pathlib.Path(args.facts_dir).glob("*.json"):
            j=json.load(open(fp,"r",encoding="utf-8"))
            cik=str(j.get("cik") or "").zfill(10)
            subs = fetch_sec_submissions(cik, ua, dbg, cache_dir=args.cache_dir if args.use_api else None) if args.use_api else {}
            # Get symbol from facts first, then from submissions
            symbol = j.get("entityTicker") or ""
            if not symbol and subs:
                tickers = subs.get("tickers", [])
                symbol = tickers[0] if tickers else ""
            meta={"cik":cik,"symbol":symbol,"name":j.get("entityName") or "","industry":""}
            pairs.append((meta, j, subs))
    elif args.use_api:
        if not ua:
            msg = "[WARN] --use-api needs --user-agent or SEC_USER_AGENT"
            print(msg, file=sys.stderr)
            dbg.log(msg)
        cache_dir = args.cache_dir
        
        if args.ciks:
            cik_list = [c.strip() for c in args.ciks.split(",") if c.strip()]
            total = len(cik_list)
            
            # 병렬 처리 (max_workers는 rate limit 고려해서 최대 10)
            max_workers = min(10, total)
            pairs = []
            
            msg = f"[INFO] Processing {total} CIKs with {max_workers} workers..."
            print(msg, file=sys.stderr)
            dbg.log(msg)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 모든 작업 제출
                future_to_cik = {
                    executor.submit(process_cik_with_cache, str(cik).zfill(10), idx+1, total, ua, cache_dir, dbg, args): cik
                    for idx, cik in enumerate(cik_list)
                }
                
                # 완료된 작업부터 결과 수집
                for future in as_completed(future_to_cik):
                    result = future.result()
                    if result:
                        pairs.append(result)
        else:
            msg = "[INFO] Auto-collect S&P500..."
            print(msg, file=sys.stderr)
            dbg.log(msg)
            comps = collect_companies_auto(ua=ua, tickers=args.tickers, limit=args.limit, dbg=dbg)
            total = len(comps)
            msg = f"[INFO] collected {total} companies"
            print(msg, file=sys.stderr)
            dbg.log(msg)
            
            # 병렬 처리 (max_workers는 rate limit 고려해서 최대 10)
            max_workers = min(10, total)
            pairs = []
            
            msg = f"[INFO] Processing {total} companies with {max_workers} workers..."
            print(msg, file=sys.stderr)
            dbg.log(msg)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 모든 작업 제출
                future_to_co = {
                    executor.submit(process_company_with_cache, co, idx+1, total, ua, cache_dir, dbg, args): co
                    for idx, co in enumerate(comps)
                }
                
                # 완료된 작업부터 결과 수집
                for future in as_completed(future_to_co):
                    result = future.result()
                    if result:
                        pairs.append(result)
    else:
        raise SystemExit("Provide --facts/--facts-dir or --use-api")

    outp = pathlib.Path(args.out); outp.parent.mkdir(parents=True, exist_ok=True)

    # 병렬 처리로 각 기업의 메트릭 처리
    max_workers = min(10, len(pairs))
    total_companies = len(pairs)

    msg = f"[INFO] Processing metrics for {total_companies} companies with {max_workers} workers..."
    print(msg, file=sys.stderr)
    dbg.log(msg)

    # 진행 상황 추적을 위한 카운터
    processed_count = 0
    processed_lock = threading.Lock()

    def update_progress():
        nonlocal processed_count
        with processed_lock:
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == total_companies:
                msg = f"[INFO] Metrics processed: {processed_count}/{total_companies} companies"
                print(msg, file=sys.stderr)
                dbg.log(msg)

    # 임시 디렉토리 생성
    temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="metrics_"))
    temp_files = []

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 모든 작업 제출
            future_to_pair = {
                executor.submit(process_company_metrics, meta, facts, subs, metrics, args, suggestions_map, dbg): (meta, facts, subs)
                for meta, facts, subs in pairs
            }
            
            # 완료된 작업부터 임시 파일에 쓰기 (lock 불필요)
            for future in as_completed(future_to_pair):
                try:
                    rows = future.result()
                    if rows and len(rows) > 0:
                        # 각 기업별로 독립적인 임시 파일에 쓰기
                        cik = rows[0].get('cik', 'unknown')
                        thread_id = threading.current_thread().ident
                        temp_file = temp_dir / f"company_{cik}_{thread_id}_{processed_count}.csv"
                        try:
                            with open(temp_file, "w", newline="", encoding="utf-8") as f:
                                w = csv.DictWriter(f, fieldnames=[
                                    "cik","symbol","name","industry_inferred","fye","metric","selected_type","selected_tag","composite_name",
                                    "normalized_as","value","unit","form","end","accn","confidence","reason","components"
                                ])
                                w.writeheader()  # 헤더 작성 추가
                                for row in rows:
                                    w.writerow(row)
                            temp_files.append(temp_file)
                        except Exception as e:
                            msg = f"[WARN] Failed to write temp file for {cik}: {e}"
                            print(msg, file=sys.stderr)
                            dbg.log(msg)
                except Exception as e:
                    msg = f"[WARN] Failed to process company metrics: {e}"
                    print(msg, file=sys.stderr)
                    dbg.log(msg)
                finally:
                    update_progress()
        
        # 모든 임시 파일을 최종 파일로 합치기
        msg = f"[INFO] Merging {len(temp_files)} temporary files..."
        print(msg, file=sys.stderr)
        dbg.log(msg)
        with open(outp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[
                "cik","symbol","name","industry_inferred","fye","metric","selected_type","selected_tag","composite_name",
                "normalized_as","value","unit","form","end","accn","confidence","reason","components"
            ])
            w.writeheader()
            
            for temp_file in sorted(temp_files):
                try:
                    with open(temp_file, "r", newline="", encoding="utf-8") as tf:
                        reader = csv.DictReader(tf)
                        for row in reader:
                            w.writerow(row)
                except Exception as e:
                    msg = f"[WARN] Failed to read temp file {temp_file}: {e}"
                    print(msg, file=sys.stderr)
                    dbg.log(msg)

    finally:
        # 임시 파일 및 디렉토리 삭제
        msg = "[INFO] Cleaning up temporary files..."
        print(msg, file=sys.stderr)
        dbg.log(msg)
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                msg = f"[WARN] Failed to cleanup temp directory {temp_dir}: {e}"
                print(msg, file=sys.stderr)
                dbg.log(msg)

    if args.dump_suggestions:
        dump_suggestions(args.dump_suggestions, append=args.dump_suggestions_append)
        msg = f"[OK] dumped suggestions → {args.dump_suggestions}"
        print(msg, file=sys.stderr)
        dbg.log(msg)

    msg = f"[OK] wrote: {outp}"
    print(msg, file=sys.stderr)
    dbg.log(msg)
    dbg.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_instance_ttl.py
--------------------------
Generate RDF instances for the EDGAR-FIN 2024 ontology from tag-selection CSV
(e.g., output of select_tags_gapfill_plus_v3.py / v4.py).

Input CSV columns (expected):
  cik,symbol,name,industry_inferred,fye,metric,selected_type,selected_tag,composite_name,
  normalized_as,value,unit,form,end,accn,confidence,reason,components

Key mapping to ontology (https://w3id.org/edgar-fin/2024#):
  - One efin:FinancialObservation per CSV row with a numeric value.
  - forEntity -> efin:LegalEntity for the CIK
  - forMetric -> Canonical metric individual (Revenue, OperatingIncome, NetIncome, CFO, CashAndCashEquivalents)
  - normalizedAs -> Canonical metric (if provided and different)
  - hasPeriod -> DurationPeriod or InstantPeriod
  - hasCurrency -> Currency individual (e.g., efin:USD)
  - usesAccountingStandard -> efin:USGAAP or efin:IFRS (derived from industry_inferred)
  - basedOnConcept -> efin:XbrlConcept individual for selected_tag (if any) and also each component qname (if composite)
  - TagMapping instances (mapsFrom XBRL concept -> mapsTo Canonical metric) are also created per observation.

Usage:
  pip install rdflib python-dateutil
  python create_instance_ttl.py --csv result_v4.csv --out instances.ttl --base https://w3id.org/edgar-fin/2024# \
      --min-confidence 0.0 --import-schema https://w3id.org/edgar-fin/2024

Notes:
  - Period start is approximated from fiscalYearEnd (CSV column 'fye' MMDD) and 'end' date:
        end  = anchor(fy, fye)
        start= anchor(fy-1, fye) + 1 day
    where fy is inferred from 'end' closest to anchor windows.
  - For Instant metrics (CashAndCashEquivalents, Assets, Liabilities, Equity) we only assert periodEnd.
  - Components in composite selections are attached via 'basedOnConcept' (multiple) and
    emitted as comments; if you want separate component observations, set --materialize-components.
"""

from __future__ import annotations
import csv, json, re, argparse, math, os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Tuple, List

from rdflib import Graph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

# ---------------- CLI -----------------
def parse_args():
    ap = argparse.ArgumentParser(description="Build EDGAR-FIN instances from tag-selection CSV")
    ap.add_argument("--csv", default="data/tags.csv", help="Extracted CSV file from extract_tags.py (default: data/tags.csv)")
    ap.add_argument("--out", required=False, default="ontology/efin_instances.ttl", help="Output TTL path")
    ap.add_argument("--base", default="https://w3id.org/edgar-fin/2024#", help="Base IRI (efin:)")
    ap.add_argument("--import-schema", default=None, help="Optional owl:imports IRI (e.g., https://w3id.org/edgar-fin/2024)")
    ap.add_argument("--min-confidence", type=float, default=0.0, help="Skip rows with confidence lower than this")
    ap.add_argument("--materialize-components", action="store_true", help="Create component FinancialObservation individuals for composite rows")
    ap.add_argument("--debug", action="store_true")
    return ap.parse_args()

# ------------- Helpers / model -------------
INSTANT_METRICS = {"CashAndCashEquivalents", "Assets", "Liabilities", "Equity"}
CANONICALS = ["Revenue","OperatingIncome","OperatingIncomeComparable","NetIncome","CFO","Assets","Liabilities","Equity","CashAndCashEquivalents"]

def slug(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("/", "-")
    s = re.sub(r"[^A-Za-z0-9\-\._]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-") or "na"

def parse_date(s: Optional[str]) -> Optional[date]:
    if not s: return None
    for fmt in ("%Y-%m-%d","%Y/%m/%d","%m/%d/%Y"):
        try: return datetime.strptime(s, fmt).date()
        except Exception: pass
    return None

def fye_mmdd_to_tuple(fye: str) -> Tuple[int,int]:
    fye = (fye or "").strip()
    if re.fullmatch(r"\d{4}", fye):
        return int(fye[:2]), int(fye[2:])
    # default 1231
    return 12, 31

def anchors_for_year(y: int, mm: int, dd: int) -> date:
    # robust against Feb-29 mismatch
    try:
        return date(y, mm, dd)
    except ValueError:
        # If Feb-29 invalid, fallback to Feb-28
        if mm == 2 and dd == 29:
            return date(y, 2, 28)
        # last day of month fallback
        d = date(y, mm, 1)
        if mm == 12:
            nxt = date(y+1, 1, 1)
        else:
            nxt = date(y, mm+1, 1)
        return nxt - timedelta(days=1)

def infer_fy_from_end(end: date, fye: str) -> int:
    mm, dd = fye_mmdd_to_tuple(fye)
    candidates = [anchors_for_year(end.year-1, mm, dd),
                  anchors_for_year(end.year,   mm, dd),
                  anchors_for_year(end.year+1, mm, dd)]
    dists = [abs((end - c).days) for c in candidates]
    idx = min(range(len(dists)), key=lambda i: dists[i])
    # candidate years correspond to FY labels equal to anchors' year
    return candidates[idx].year

def compute_period_bounds(end: date, fye: str) -> Tuple[date, date]:
    fy = infer_fy_from_end(end, fye)
    mm, dd = fye_mmdd_to_tuple(fye)
    endd = anchors_for_year(fy, mm, dd)
    start = anchors_for_year(fy-1, mm, dd) + timedelta(days=1)
    return start, endd

def pick_accounting_standard(industry_inferred: str) -> str:
    s = (industry_inferred or "").upper()
    if "IFRS" in s:
        return "IFRS"
    return "USGAAP"

# ------------- RDF builders -------------
@dataclass
class Context:
    g: Graph
    efin: Namespace
    base: str
    created: Dict[str, URIRef]

def canonical_iri(efin: Namespace, name: str) -> URIRef:
    return URIRef(str(efin) + name)

def concept_iri(efin: Namespace, qname: str) -> URIRef:
    # Turn "us-gaap:Revenues" into efin:xbrl-us-gaap-Revenues
    return URIRef(str(efin) + "xbrl-" + slug(qname.replace(":", "-")))

def entity_iri(efin: Namespace, cik: str) -> URIRef:
    return URIRef(str(efin) + "entity-" + slug(cik))

def industry_iri(efin: Namespace, label: str) -> URIRef:
    return URIRef(str(efin) + "ind-" + slug(label))

def currency_iri(efin: Namespace, code: str) -> URIRef:
    return URIRef(str(efin) + slug(code.upper()))

def accounting_std_iri(efin: Namespace, code: str) -> URIRef:
    return URIRef(str(efin) + code.upper())

def filing_iri(efin: Namespace, accn: str) -> URIRef:
    return URIRef(str(efin) + "filing-" + slug(accn))

def period_iri(efin: Namespace, cik: str, fy: int, kind: str, end_str: str) -> URIRef:
    return URIRef(str(efin) + f"per-{slug(cik)}-{fy}-{kind}-{slug(end_str)}")

def observation_iri(efin: Namespace, cik: str, fy: int, metric: str, end_str: str) -> URIRef:
    return URIRef(str(efin) + f"obs-{slug(cik)}-{fy}-{slug(metric)}-{slug(end_str)}")

def tagmap_iri(efin: Namespace, cik: str, metric: str, qname: str) -> URIRef:
    return URIRef(str(efin) + f"tagmap-{slug(cik)}-{slug(metric)}-{slug(qname)}")

def ensure_entity(ctx: Context, cik: str, symbol: str, name: str, industry_inferred: str) -> URIRef:
    g, efin = ctx.g, ctx.efin
    ent = entity_iri(efin, cik)
    if ent not in ctx.created:
        g.add((ent, RDF.type, efin.LegalEntity))
        label = f"{symbol} ({name}) [CIK {cik}]".strip()
        g.add((ent, RDFS.label, Literal(label)))
        # industries
        inds = [i for i in (industry_inferred or "").split(";") if i and i not in ("USGAAP","IFRS")]
        for ind in inds:
            ind_node = industry_iri(efin, ind)
            g.add((ind_node, RDF.type, efin.Industry))
            g.add((ind_node, RDFS.label, Literal(ind)))
            g.add((ent, efin.hasIndustry, ind_node))
        ctx.created[ent] = ent
    return ent

def ensure_currency(ctx: Context, code: str) -> URIRef:
    g, efin = ctx.g, ctx.efin
    cur = currency_iri(efin, code or "USD")
    if cur not in ctx.created:
        g.add((cur, RDF.type, efin.Currency))
        g.add((cur, RDFS.label, Literal((code or "USD").upper())))
        ctx.created[cur] = cur
    return cur

def ensure_accounting(ctx: Context, std_code: str) -> URIRef:
    g, efin = ctx.g, ctx.efin
    node = accounting_std_iri(efin, std_code or "USGAAP")
    if node not in ctx.created:
        g.add((node, RDF.type, efin.AccountingStandard))
        g.add((node, RDFS.label, Literal((std_code or "USGAAP").upper())))
        ctx.created[node] = node
    return node

def ensure_concept(ctx: Context, qname: str) -> URIRef:
    g, efin = ctx.g, ctx.efin
    node = concept_iri(efin, qname)
    if node not in ctx.created:
        g.add((node, RDF.type, efin.XbrlConcept))
        g.add((node, RDFS.label, Literal(qname)))
        ctx.created[node] = node
    return node

def ensure_tagmap(ctx: Context, cik: str, qname: str, canonical: str) -> URIRef:
    g, efin = ctx.g, ctx.efin
    node = tagmap_iri(efin, cik, canonical, qname)
    if node not in ctx.created:
        g.add((node, RDF.type, efin.TagMapping))
        g.add((node, efin.mapsFrom, ensure_concept(ctx, qname)))
        g.add((node, efin.mapsTo, canonical_iri(efin, canonical)))
        g.add((node, RDFS.label, Literal(f"Map {qname} -> {canonical} (CIK {cik})")))
        ctx.created[node] = node
    return node

def ensure_period(ctx: Context, cik: str, end_str: str, fye: str, metric: str) -> Tuple[URIRef, int]:
    """Return (period_node, fiscalYear)."""
    g, efin = ctx.g, ctx.efin
    endd = parse_date(end_str) or date(1900,1,1)
    fy = infer_fy_from_end(endd, fye or "1231")
    kind = "instant" if metric in INSTANT_METRICS else "duration"
    p = period_iri(efin, cik, fy, kind, end_str or str(endd))
    if p not in ctx.created:
        g.add((p, RDF.type, efin.InstantPeriod if kind == "instant" else efin.DurationPeriod))
        g.add((p, efin.periodEnd, Literal(endd.isoformat(), datatype=XSD.date)))
        g.add((p, efin.fiscalYear, Literal(str(fy), datatype=XSD.gYear)))
        if kind == "duration":
            start, end_anchor = compute_period_bounds(endd, fye or "1231")
            g.add((p, efin.periodStart, Literal(start.isoformat(), datatype=XSD.date)))
        g.add((p, RDFS.label, Literal(f"{kind.title()} period FY{fy} ending {endd}")))
        ctx.created[p] = p
    return p, fy

def build_observation(ctx: Context, row: Dict[str,str], materialize_components: bool = False, debug: bool=False) -> Optional[URIRef]:
    g, efin = ctx.g, ctx.efin
    # basic validations
    try:
        val = float(row.get("value") or "")
    except Exception:
        return None
    if (row.get("selected_type") or "") == "none":
        return None
    if row.get("confidence"):
        try:
            conf = float(row["confidence"])
        except Exception:
            conf = 0.0
    else:
        conf = 0.0

    cik = (row.get("cik") or "").zfill(10)
    symbol = row.get("symbol") or ""
    name   = row.get("name") or ""
    metric = row.get("metric") or ""
    end    = row.get("end") or ""
    fye    = row.get("fye") or "1231"
    unit   = row.get("unit") or "USD"
    normalized_as = row.get("normalized_as") or ""
    selected_tag  = row.get("selected_tag") or ""
    form   = row.get("form") or ""
    accn   = row.get("accn") or ""
    industry_inferred = row.get("industry_inferred") or ""

    canonical = normalized_as if normalized_as else metric
    if canonical not in CANONICALS:
        # map a few known aliases
        alias = {"RevenueComparable":"Revenue","OperatingIncomeLoss":"OperatingIncome"}.get(canonical, None)
        canonical = alias or canonical

    # entity
    ent = ensure_entity(ctx, cik, symbol, name, industry_inferred)
    # currency
    cur = ensure_currency(ctx, unit)
    # accounting standard
    std = ensure_accounting(ctx, pick_accounting_standard(industry_inferred))
    # period
    period_node, fy = ensure_period(ctx, cik, end, fye, metric)
    # observation
    obs = observation_iri(ctx.efin, cik, fy, canonical, end or "na")
    g.add((obs, RDF.type, efin.FinancialObservation))
    g.add((obs, efin.forEntity, ent))
    g.add((obs, efin.forMetric, canonical_iri(ctx.efin, canonical)))
    g.add((obs, efin.hasPeriod, period_node))
    g.add((obs, efin.hasCurrency, cur))
    g.add((obs, efin.usesAccountingStandard, std))
    g.add((obs, efin.hasValue, Literal(val, datatype=XSD.decimal)))
    if normalized_as and normalized_as != metric:
        g.add((obs, efin.normalizedAs, canonical_iri(ctx.efin, normalized_as)))
    # label + comment
    g.add((obs, RDFS.label, Literal(f"{symbol} {canonical} FY{fy} ({unit})")))
    reason = row.get("reason") or ""
    if reason:
        g.add((obs, RDFS.comment, Literal(f"{row.get('selected_type','')} | {reason} | conf={conf:.3f}")))

    # concept(s)
    if selected_tag:
        cpt = ensure_concept(ctx, selected_tag)
        g.add((obs, efin.basedOnConcept, cpt))
        ensure_tagmap(ctx, cik, selected_tag, canonical)

    comps_json = row.get("components") or ""
    if comps_json:
        try:
            comps = json.loads(comps_json)
        except Exception:
            comps = []
        for c in comps:
            qn = c.get("qname")
            if qn:
                cpt = ensure_concept(ctx, qn)
                g.add((obs, efin.basedOnConcept, cpt))
                ensure_tagmap(ctx, cik, qn, canonical)
            if materialize_components and qn and isinstance(c.get("value"), (int,float)):
                # create a component observation with same period/currency/std; forMetric = parent canonical
                comp_val = float(c["value"]) * float(c.get("weight", 1.0))
                comp_obs = observation_iri(ctx.efin, cik, fy, f"{canonical}-component-{slug(qn)}", end or "na")
                g.add((comp_obs, RDF.type, efin.FinancialObservation))
                g.add((comp_obs, efin.forEntity, ent))
                g.add((comp_obs, efin.forMetric, canonical_iri(ctx.efin, canonical)))
                g.add((comp_obs, efin.hasPeriod, period_node))
                g.add((comp_obs, efin.hasCurrency, cur))
                g.add((comp_obs, efin.usesAccountingStandard, std))
                g.add((comp_obs, efin.hasValue, Literal(comp_val, datatype=XSD.decimal)))
                g.add((comp_obs, efin.basedOnConcept, ensure_concept(ctx, qn)))
                g.add((obs, efin.computedFrom, comp_obs))
                g.add((comp_obs, RDFS.label, Literal(f"{symbol} {canonical} component: {qn}")))
                g.add((comp_obs, RDFS.comment, Literal(f"weight={c.get('weight',1.0)}, raw={c.get('value')}")))

    # filing (if accn present) — represented with label only; schema doesn't define a linking prop; we add seeAlso
    if accn:
        filing = filing_iri(ctx.efin, accn)
        g.add((filing, RDF.type, ctx.efin.RegulatoryFiling))
        g.add((filing, RDFS.label, Literal(f"{row.get('form','')} ACCN {accn}")))
        g.add((obs, RDFS.seeAlso, filing))

    return obs

# ------------- Main -------------
def main():
    args = parse_args()
    g = Graph()
    efin = Namespace(args.base)
    g.bind("efin", efin)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)

    # Optional ontology header & imports
    inst_onto = URIRef(str(efin) + "instances")
    g.add((inst_onto, RDF.type, OWL.Ontology))
    if args.import_schema:
        g.add((inst_onto, OWL.imports, URIRef(args.import_schema)))
    else:
        # seed canonical metric individuals (only if schema file wasn't imported)
        for nm in CANONICALS:
            g.add((canonical_iri(efin, nm), RDF.type, efin.CanonicalMetric))
            g.add((canonical_iri(efin, nm), RDFS.label, Literal(nm)))

    ctx = Context(g=g, efin=efin, base=args.base, created={})

    with open(args.csv, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        rows = list(rdr)

    n_total=0; n_kept=0; n_skipped=0
    for row in rows:
        n_total += 1
        try:
            conf = float(row.get("confidence") or "0")
        except Exception:
            conf = 0.0
        if conf < args.min-confidence if hasattr(args, "min-confidence") else False:  # safeguard if attribute name contains hyphen
            pass  # not used
        # manual check
        if conf < args.min_confidence:
            n_skipped += 1
            if args.debug:
                print(f"[SKIP] conf<{args.min_confidence}: {row.get('cik')} {row.get('metric')} {row.get('end')}", flush=True)
            continue
        # require numeric value
        try:
            _ = float(row.get("value") or "")
        except Exception:
            n_skipped += 1
            if args.debug:
                print(f"[SKIP] non-numeric value: {row.get('cik')} {row.get('metric')}", flush=True)
            continue
        # require selected_type not none
        if (row.get("selected_type") or "") == "none":
            n_skipped += 1
            if args.debug:
                print(f"[SKIP] selected_type=none: {row.get('cik')} {row.get('metric')}", flush=True)
            continue

        obs = build_observation(ctx, row, materialize_components=args.materialize_components, debug=args.debug)
        if obs is not None:
            n_kept += 1

    outp = args.out
    # Ensure output directory exists
    output_dir = os.path.dirname(outp)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    g.serialize(destination=outp, format="turtle")
    print(f"[OK] Instances written: {outp} (kept={n_kept}/{n_total}, skipped={n_skipped})")

if __name__ == "__main__":
    main()

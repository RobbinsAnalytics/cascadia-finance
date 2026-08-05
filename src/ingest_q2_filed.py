"""
ingest_q2_filed.py — Q2 FY2026 FILED build (freeze EXTENSION, not a refresh).

Cascadia Semiconductors · Q2 FY2026 filed-vs-announced

WHAT & WHY  (see .claude/skills/q2-filed-build/SKILL.md — this is step 2 + 3)
---------------------------------------------------------------------------
FormFactor's Q2 FY2026 (quarter ended 2026-06-27) 10-Q makes filed XBRL
available for a quarter the site previously carried only as *announced*
press-release figures. This build adds ONE new page (the announced-vs-filed
reconciliation) as the third freeze extension, after ingest_segments.py and
ingest_peers.py.

It NEVER runs src/ingest.py, never re-pulls companyfacts, never touches the
2026-07-21 freeze. It writes only NEW files. Both SEC sources are pulled here
so NO figure is ever hand-typed — the announced and filed numbers alike come
straight from EDGAR:

  * FILED   — the Q2 10-Q XBRL instance (accession 0001039399-26-000033),
              non-dimensional consolidated facts, matching the Phase 1 metric
              set for a like-for-like comparison.
  * ANNOUNCED — the Q2 8-K Item 2.02 EX-99.1 earnings release
              (accession 0001039399-26-000030), the *other half* of the
              comparison. Sourced from the exhibit itself, not scraped from the
              rendered read-through page.

SEC etiquette: declared User-Agent, ~4 req/s, polite backoff (same as
ingest_segments.py).

Outputs (and only these):
  data/raw/q2filed_FORM_CIK0001039399.json   filed facts
  data/raw/q2filed_manifest_FORM.json        manifest (as_of = retrieval date)
  data/raw/announced_q2_fy2026.json          announced figures (8-K EX-99.1)
  governance/tag_mapping.csv                 APPENDED with any new tag (never rewritten)

Usage:
    python src/ingest_q2_filed.py
"""

import csv
import gzip
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
GOV_DIR = REPO_ROOT / "governance"

CIK = "0001039399"
TICKER = "FORM"
TENQ_ACCESSION = "0001039399-26-000033"     # Q2 FY2026 10-Q (period 2026-06-27)
EK_ACCESSION = "0001039399-26-000030"       # Q2 FY2026 8-K Item 2.02 (furnished 2026-07-29)
Q2_END = "2026-06-27"
Q2_START = "2026-03-29"                      # 13-week quarter start
YTD_START = "2025-12-28"                     # 6-month YTD start (for the tie-out)

USER_AGENT = "RobbinsAnalytics cascadia-semiconductors ajayrobbins@hotmail.com"
THROTTLE = 0.25
BACKOFF = [2, 5, 15, 60]
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/"

# Filed GAAP concepts to extract — the Phase 1 metric set, so announced-vs-filed
# is like-for-like. metric_code -> (label, us-gaap tag, unit).
FILED_CONCEPTS = {
    "revenue": ("Revenue (GAAP)", "RevenueFromContractWithCustomerExcludingAssessedTax", "USD"),
    "cost_of_revenue": ("Cost of Revenue (GAAP)", "CostOfGoodsAndServicesSold", "USD"),
    "gross_profit": ("Gross Profit (GAAP)", "GrossProfit", "USD"),
    "rnd_expense": ("R&D Expense (GAAP)", "ResearchAndDevelopmentExpense", "USD"),
    "sgna_expense": ("SG&A Expense (GAAP)", "SellingGeneralAndAdministrativeExpense", "USD"),
    "opex_total": ("Total Operating Expenses (GAAP)", "OperatingExpenses", "USD"),
    "operating_income": ("Operating Income (GAAP)", "OperatingIncomeLoss", "USD"),
    "net_income": ("Net Income (GAAP)", "NetIncomeLoss", "USD"),
    "eps_diluted": ("Diluted EPS (GAAP)", "EarningsPerShareDiluted", "USD/shares"),
}
# Restructuring is disclosed by income-statement location via a TYPED dimension
# (us-gaap:StatementOfIncomeLocationBalanceAxis). We capture the consolidated
# total plus the cost-of-revenue portion, because the read-through page flagged
# an apparent restructuring non-tie for the 10-Q to resolve.
RESTRUCTURING_TAG = "RestructuringCharges"
INCOME_LOCATION_AXIS = "StatementOfIncomeLocationBalanceAxis"
COGS_LOCATION_MEMBER = "CostOfGoodsAndServicesSold"


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def polite_get(url: str) -> bytes:
    last = None
    for attempt, back in enumerate([0] + BACKOFF):
        if back:
            print(f"    retrying in {back}s (attempt {attempt + 1}) ...")
            time.sleep(back)
        time.sleep(THROTTLE)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept-Encoding": "gzip, deflate"})
        try:
            resp = urllib.request.urlopen(req, timeout=90)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 502, 503, 504):
                raise
        except urllib.error.URLError as e:
            last = e
    raise RuntimeError(f"Failed after retries: {url} ({last})")


def local(tag: str) -> str:
    """Bare local-name from Clark notation or a prefixed QName."""
    return tag.split("}")[-1].split(":")[-1]


def filing_dir(accession: str) -> str:
    return ARCHIVE.format(cik_int=int(CIK), acc_nodash=accession.replace("-", ""))


def find_file(accession: str, predicate) -> str:
    idx = json.loads(polite_get(filing_dir(accession) + "index.json"))
    for it in idx["directory"]["item"]:
        if predicate(it["name"]):
            return it["name"]
    raise RuntimeError(f"No matching file in {accession}")


# ---------------------------------------------------------------------------
# FILED — parse the 10-Q XBRL instance
# ---------------------------------------------------------------------------

def parse_instance(instance_bytes: bytes):
    """Return (contexts, root). Context = {start, end, explicit[], typed[]}."""
    root = ET.fromstring(instance_bytes)
    ctx = {}
    for c in root.iter():
        if local(c.tag) != "context":
            continue
        start = end = None
        explicit, typed = [], []
        for e in c.iter():
            le = local(e.tag)
            if le == "startDate":
                start = e.text
            elif le == "endDate":
                end = e.text
            elif le == "explicitMember":
                explicit.append((local(e.get("dimension", "")), local((e.text or "").strip())))
            elif le == "typedMember":
                axis = local(e.get("dimension", ""))
                # the typed value is the text of the child element (a QName)
                val = "".join((ch.text or "").strip() for ch in e)
                typed.append((axis, local(val)))
        ctx[c.get("id")] = {"start": start, "end": end, "explicit": explicit, "typed": typed}
    return ctx, root


def q2_value(root, ctx, tag, *, dimensionless=True, typed_axis=None, typed_member=None,
             start=Q2_START, end=Q2_END):
    """Extract the single Q2 fact for `tag` under a precise context shape.

    dimensionless=True selects the consolidated fact (no explicit/typed dims).
    Otherwise supply typed_axis/typed_member to pick a location-tagged fact.
    Raises if zero or conflicting (>1 distinct value) facts are found — we never
    guess which of several facts is the real one.
    """
    found = set()
    for el in root.iter():
        if local(el.tag) != tag:
            continue
        c = ctx.get(el.get("contextRef"))
        if not c or c["start"] != start or c["end"] != end:
            continue
        if dimensionless:
            if c["explicit"] or c["typed"]:
                continue
        else:
            if c["explicit"] or len(c["typed"]) != 1:
                continue
            axis, member = c["typed"][0]
            if axis != typed_axis or member != typed_member:
                continue
        if el.text not in (None, ""):
            found.add(el.text.strip())
    if len(found) != 1:
        raise RuntimeError(f"{tag}: expected 1 fact ({start}->{end}, "
                           f"{'no dims' if dimensionless else typed_member}), got {sorted(found)}")
    return found.pop()


def ingest_filed() -> dict:
    inst_name = find_file(TENQ_ACCESSION, lambda n: n.endswith("_htm.xml"))
    url = filing_dir(TENQ_ACCESSION) + inst_name
    print(f"[filed] {inst_name}")
    raw = polite_get(url)
    ctx, root = parse_instance(raw)

    facts = {}
    for code, (label, tag, unit) in FILED_CONCEPTS.items():
        v = q2_value(root, ctx, tag)
        facts[code] = {"label": label, "tag": tag, "unit": unit,
                       "value": float(v) if unit != "USD" else int(float(v))}

    # restructuring: consolidated total + cost-of-revenue portion
    facts["restructuring_total"] = {
        "label": "Restructuring charges — total (GAAP)", "tag": RESTRUCTURING_TAG, "unit": "USD",
        "value": int(float(q2_value(root, ctx, RESTRUCTURING_TAG)))}
    facts["restructuring_cogs"] = {
        "label": "Restructuring in cost of revenue (GAAP)",
        "tag": f"{RESTRUCTURING_TAG}@{INCOME_LOCATION_AXIS}={COGS_LOCATION_MEMBER}", "unit": "USD",
        "value": int(float(q2_value(root, ctx, RESTRUCTURING_TAG, dimensionless=False,
                                    typed_axis=INCOME_LOCATION_AXIS, typed_member=COGS_LOCATION_MEMBER)))}

    # YTD (6-month) revenue — used by validate for the Q1+Q2 tie-out
    ytd_rev = int(float(q2_value(root, ctx, FILED_CONCEPTS["revenue"][1], start=YTD_START)))

    return {"instance_url": url, "bytes": len(raw), "facts": facts, "ytd_revenue": ytd_rev}


# ---------------------------------------------------------------------------
# ANNOUNCED — parse the 8-K EX-99.1 earnings release
# ---------------------------------------------------------------------------

def _num(s):
    return float(s.replace(",", "").replace("(", "-").replace(")", ""))


def ingest_announced() -> dict:
    ex_name = find_file(EK_ACCESSION, lambda n: n.lower().startswith("ex99") and n.endswith(".htm"))
    url = filing_dir(EK_ACCESSION) + ex_name
    print(f"[announced] {ex_name}")
    html = polite_get(url).decode("utf-8", "ignore")
    t = re.sub(r"<[^>]+>", " ", html).replace(" ", " ").replace("&#160;", " ").replace("&amp;", "&")
    t = re.sub(r"[ \t\r\n]+", " ", t)

    # GAAP income statement — first numeric column is Q2 FY2026 ($ thousands).
    LINES = {
        "revenue": "Revenues", "cost_of_revenue": "Cost of revenues",
        "gross_profit": "Gross profit", "rnd_expense": "Research and development",
        "sgna_expense": "Selling, general and administrative",
        "opex_total": "Total operating expenses", "operating_income": "Operating income",
        "net_income": "Net income",
    }
    out = {}

    def grab(pattern, what):
        m = re.search(pattern, t)
        if not m:
            raise RuntimeError(f"announced parse: could not find {what} in {ex_name} — "
                               f"refusing to hand-fill; stop and inspect.")
        return m.group(1)

    for code, label in LINES.items():
        out[code] = int(_num(grab(re.escape(label) + r"\s+[$]?\s*\(?([\d,]+)\)?", label)) * 1000)
    out["eps_diluted"] = _num(grab(r"Diluted\s+[$]?\s*([\d.]+)", "diluted EPS"))
    out["gaap_gross_margin_pct"] = _num(grab(
        r"[Gg]ross margin for the second quarter of 2026 was ([\d.]+)%", "GAAP gross margin"))
    out["nongaap_gross_margin_pct"] = _num(grab(
        r"non-GAAP basis, gross margin for the second quarter of 2026 was ([\d.]+)%",
        "non-GAAP gross margin"))
    # restructuring in cost of revenue: first "Restructuring charges N" is the
    # gross-profit (cost-of-revenue) reconciliation column.
    out["restructuring_cogs"] = int(_num(grab(
        r"Restructuring charges\s+([\d,]+)", "restructuring in cost of revenue")) * 1000)
    return {"exhibit_url": url, "figures": out}


# ---------------------------------------------------------------------------
# tag_mapping.csv — APPEND new tags only (never rewrite)
# ---------------------------------------------------------------------------

def append_tag_mapping(as_of: str):
    path = GOV_DIR / "tag_mapping.csv"
    existing = list(csv.reader(open(path, encoding="utf-8")))
    have = {(r[0], r[1], r[3]) for r in existing[1:]}
    new = []
    rows = [("FORM", "restructuring_total", "Restructuring charges — total (GAAP)",
             "RestructuringCharges", "q2_filed",
             "Q2 FY2026 filed build; consolidated restructuring total"),
            ("FORM", "restructuring_cogs", "Restructuring in cost of revenue (GAAP)",
             f"RestructuringCharges@{INCOME_LOCATION_AXIS}={COGS_LOCATION_MEMBER}", "q2_filed",
             "typed income-statement-location dimension (cost of revenue portion)")]
    for tk, code, label, tag, role, note in rows:
        if (tk, code, tag) not in have:
            new.append([tk, code, label, tag, role, note, as_of])
    if new:
        with open(path, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(new)
    return len(new)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    retrieved = date.today().isoformat()       # genuinely-later pull; NOT 2026-07-21
    print(f"Q2 FY2026 filed build · retrieval date {retrieved}")
    print(f"  10-Q accession {TENQ_ACCESSION} · 8-K accession {EK_ACCESSION}")

    filed = ingest_filed()
    announced = ingest_announced()

    # FILED artifact + manifest
    (RAW_DIR / f"q2filed_{TICKER}_CIK{CIK}.json").write_text(json.dumps({
        "ticker": TICKER, "cik": CIK, "fiscal_period": "2026Q2",
        "period_start": Q2_START, "period_end": Q2_END,
        "source": "SEC EDGAR 10-Q XBRL instance", "accession": TENQ_ACCESSION,
        "instance_url": filed["instance_url"], "ytd_revenue": filed["ytd_revenue"],
        "facts": filed["facts"],
    }, indent=1), encoding="utf-8")

    (RAW_DIR / f"q2filed_manifest_{TICKER}.json").write_text(json.dumps({
        "as_of_date": retrieved,               # the ACTUAL retrieval date (not the freeze)
        "note": ("Q2 FY2026 filed build — a freeze EXTENSION. The Phase 1-3 dataset "
                 "(frozen 2026-07-21) was NOT refreshed or re-stamped."),
        "tenq_accession": TENQ_ACCESSION, "tenq_instance": filed["instance_url"],
        "tenq_filed": "2026-08-04", "tenq_bytes": filed["bytes"],
        "eightk_accession": EK_ACCESSION, "eightk_exhibit": announced["exhibit_url"],
        "eightk_furnished": "2026-07-29",
    }, indent=2), encoding="utf-8")

    # ANNOUNCED artifact (sourced to the 8-K, tier-marked)
    (RAW_DIR / "announced_q2_fy2026.json").write_text(json.dumps({
        "tier": "announced",
        "source": "SEC EDGAR 8-K Item 2.02 EX-99.1 earnings release",
        "accession": EK_ACCESSION, "furnished": "2026-07-29",
        "exhibit_url": announced["exhibit_url"],
        "unit_note": "USD (dollars); margins in percent; EPS in USD/share",
        "figures": announced["figures"],
    }, indent=1), encoding="utf-8")

    added = append_tag_mapping(retrieved)

    print(f"\nWrote data/raw/q2filed_{TICKER}_CIK{CIK}.json "
          f"({len(filed['facts'])} filed facts)")
    print(f"Wrote data/raw/q2filed_manifest_{TICKER}.json")
    print(f"Wrote data/raw/announced_q2_fy2026.json ({len(announced['figures'])} announced figures)")
    print(f"tag_mapping.csv: appended {added} new tag row(s)")
    print(f"\nfiled revenue ${filed['facts']['revenue']['value']/1e6:.3f}M · "
          f"announced revenue ${announced['figures']['revenue']/1e6:.3f}M")


if __name__ == "__main__":
    main()

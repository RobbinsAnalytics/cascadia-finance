"""
validate.py — Reconcile and sanity-check the conformed data; write the report.

Cascadia Finance · Phase A

Checks performed (all offline, against the frozen snapshot):

  1. Q4 / full-year reconciliation — for every fiscal year with a filed FY
     fact, Q1+Q2+Q3+Q4 must equal FY within tolerance (USD metrics: $2,000
     absolute — XBRL values are filed as exact integers; EPS: $0.02, since
     per-share amounts are not strictly additive across quarters).
  2. Cross-foot consistency — Gross Profit − Total Opex + Gain on Sale of
     Business must equal Operating Income each quarter (same tolerances).
     The gain term matters: FormFactor's GAAP operating income includes
     divestiture gains (FRT Metrology, FY2023 Q4: +$72.9M; China business,
     FY2024 Q1: +$20.3M) that sit outside the OperatingExpenses tag. When no
     gain fact is filed for a quarter the term is zero BY ACCOUNTING IDENTITY
     (no such line item on that income statement) — this is not zero-filling
     a missing disclosure. This check catches tag-mapping errors.
  3. Gap audit — every quarter in the FY2018→FY2026Q1 grid must either carry
     a value or be explicitly flagged missing. No silent gaps.
  4. Flag audit — every derived and restated row is enumerated for review.
  5. Spot-check table — recent quarters' GAAP revenue and gross profit are
     listed with their source filings so a human can verify them against
     FormFactor's press releases (GAAP tables, not non-GAAP headlines).

Output: governance/validation_report.md  (regenerated every run)
Exit code is non-zero if any check FAILS, so this can gate a rebuild.

Usage:
    python src/validate.py
"""

import csv
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from datetime import date
from pathlib import Path

# A gate that crashes while printing its own PASS line reports failure to
# anything reading the exit code. The Windows console defaults to cp1252, which
# cannot encode the minus sign in check 2's name, so a clean all-pass run wrote
# a correct report and then died with UnicodeEncodeError and exit 1. Never let
# formatting decide the verdict. Same guard as validate_freeze.py and
# validate_q2_filed.py; this script was the one that never got it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Reuse the conform layer's extraction logic so validation sees the same
# facts the pipeline used — no second, subtly-different parser.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from conform import (FILED_METRICS, NON_ADDITIVE_METRICS, collect_periods,
                     load_companyfacts)

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = REPO_ROOT / "data" / "conformed" / "fact_financials_quarterly.csv"
SEG_CSV_PATH = REPO_ROOT / "data" / "conformed" / "fact_segments_quarterly.csv"
PEERS_CSV_PATH = REPO_ROOT / "data" / "conformed" / "fact_peers_quarterly.csv"
REPORT_PATH = REPO_ROOT / "governance" / "validation_report.md"
MANIFEST = REPO_ROOT / "data" / "raw" / "manifest.json"

USD_TOLERANCE = 2_000     # dollars; filings are exact integers, so this is generous
EPS_TOLERANCE = 0.02      # dollars/share; EPS is not strictly additive


def load_conformed():
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    by_metric = defaultdict(dict)
    for r in rows:
        by_metric[r["metric_code"]][r["fiscal_period"]] = r
    return rows, by_metric


def check_fy_reconciliation(results):
    """Check 1: quarters sum to the filed full-year value."""
    facts = load_companyfacts("FORM")["facts"]["us-gaap"]
    _, by_metric = load_conformed()
    failures, checked = [], 0
    for code, (label, unit, tags) in FILED_METRICS.items():
        tol = EPS_TOLERANCE if code in NON_ADDITIVE_METRICS else USD_TOLERANCE
        _, years = collect_periods(facts, tags, unit)
        for year, fy in sorted(years.items()):
            quarters = [by_metric[code].get(f"{year}Q{q}") for q in (1, 2, 3, 4)]
            if any(q is None or q["missing"] == "True" for q in quarters):
                continue  # outside the analysis window or genuinely missing
            qsum = sum(float(q["value"]) for q in quarters)
            checked += 1
            if abs(qsum - fy["value"]) > tol:
                failures.append(f"{code} FY{year}: quarters sum {qsum:,.2f} "
                                f"vs FY filed {fy['value']:,.2f}")
    results.append(("Q4 / full-year reconciliation",
                    not failures, f"{checked} metric-years reconciled", failures))


def check_crossfoot(results):
    """Check 2: gross_profit − opex_total + gain_on_sale == operating_income.

    GainLossOnSaleOfBusiness is extracted from the same frozen snapshot with
    the same quarter/Q4-derivation logic as every other metric. Quarters with
    no gain fact use zero — an accounting identity (no such income-statement
    line that quarter), not a fill of missing data.
    """
    facts = load_companyfacts("FORM")["facts"]["us-gaap"]
    gains_q, gains_fy = collect_periods(facts, ["GainLossOnSaleOfBusiness"], "USD")
    # Q4 gain = FY − (Q1+Q2+Q3), where quarters with no gain fact contribute
    # zero (the line item didn't exist those quarters — identity, not a fill).
    for year, fy in gains_fy.items():
        if (year, 4) not in gains_q:
            q123 = sum(gains_q.get((year, q), {}).get("value", 0) for q in (1, 2, 3))
            gains_q[(year, 4)] = {"value": fy["value"] - q123}

    _, by_metric = load_conformed()
    failures, checked = [], 0
    for period, gp in by_metric["gross_profit"].items():
        opex = by_metric["opex_total"].get(period)
        oi = by_metric["operating_income"].get(period)
        if any(x is None or x["missing"] == "True" for x in (gp, opex, oi)):
            continue
        checked += 1
        key = (int(period[:4]), int(period[-1]))
        gain = gains_q.get(key, {}).get("value", 0)
        diff = float(gp["value"]) - float(opex["value"]) + gain - float(oi["value"])
        if abs(diff) > USD_TOLERANCE:
            failures.append(f"{period}: GP−Opex+Gain−OI = {diff:,.0f}")
    results.append(("Cross-foot (GP − Opex + Divestiture Gains = Operating Income)",
                    not failures, f"{checked} quarters checked", failures))


def check_gaps(results):
    """Check 3: no silent gaps — every grid cell has a value or a missing flag."""
    rows, _ = load_conformed()
    bad = [f"{r['metric_code']} {r['fiscal_period']}" for r in rows
           if r["value"] == "" and r["missing"] != "True"]
    n_missing = sum(1 for r in rows if r["missing"] == "True")
    results.append(("Gap audit (missing is flagged, never silent)",
                    not bad, f"{len(rows)} rows scanned; {n_missing} flagged missing", bad))


# ---------------------------------------------------------------------------
# Phase B — segment checks (skipped cleanly if the segment CSV is absent)
# ---------------------------------------------------------------------------

def load_segments():
    """Return segment rows indexed by (segment, metric) -> {period: value_float}."""
    rows = list(csv.DictReader(open(SEG_CSV_PATH, encoding="utf-8")))
    by = defaultdict(dict)
    for r in rows:
        if r["value"] != "" and r["missing"] != "True":
            by[(r["segment_code"], r["metric_code"])][r["fiscal_period"]] = float(r["value"])
    return rows, by


def check_segment_revenue(results):
    """Check 6: Probe Cards + Systems revenue == consolidated revenue, every quarter.

    This is the correctness gate for the dimensional segment pull: if a segment
    revenue fact were mis-extracted (wrong axis, double count, unit slip), the
    two would stop tying. USD tolerance ($2,000) applies — filings are exact.
    """
    _, by_metric = load_conformed()
    _, seg = load_segments()
    cons = {p: float(r["value"]) for p, r in by_metric["revenue"].items()
            if r["value"] != "" and r["missing"] != "True"}
    probe, systems = seg[("probe_cards", "seg_revenue")], seg[("systems", "seg_revenue")]
    failures, checked = [], 0
    for period, total in sorted(cons.items()):
        if period not in probe or period not in systems:
            failures.append(f"{period}: missing a segment revenue value")
            continue
        checked += 1
        diff = probe[period] + systems[period] - total
        if abs(diff) > USD_TOLERANCE:
            failures.append(f"{period}: segment revenue sum − consolidated = {diff:,.0f}")
    results.append(("Segment revenue reconciles to consolidated revenue",
                    not failures, f"{checked} quarters reconciled", failures))


def check_segment_gp_bridge(results):
    """Check 7: segment gross-profit bridge closes to consolidated GAAP GP.

    Where FormFactor files the reconciling line (FY2024+, ASU 2023-07):
        ProbeCards GP + Systems GP + Corporate/unallocated GP == consolidated GP.
    We check ONLY periods that carry all three filed segment gross-profit values
    (the reconcilable window); earlier periods have no tagged reconciling item
    and are deliberately not asserted (and not shown on the page).
    """
    _, by_metric = load_conformed()
    _, seg = load_segments()
    cons_gp = {p: float(r["value"]) for p, r in by_metric["gross_profit"].items()
               if r["value"] != "" and r["missing"] != "True"}
    probe = seg[("probe_cards", "seg_gross_profit")]
    systems = seg[("systems", "seg_gross_profit")]
    corp = seg[("corporate_unallocated", "seg_gross_profit")]
    failures, checked = [], 0
    for period in sorted(corp):                    # gated: only reconcilable periods
        if period not in probe or period not in systems or period not in cons_gp:
            failures.append(f"{period}: incomplete gross-profit bridge inputs")
            continue
        checked += 1
        diff = probe[period] + systems[period] + corp[period] - cons_gp[period]
        if abs(diff) > USD_TOLERANCE:
            failures.append(f"{period}: segment GP bridge − consolidated GP = {diff:,.0f}")
    results.append(("Segment gross-profit bridge (Probe+Systems+Corporate = consolidated GP)",
                    not failures, f"{checked} reconcilable quarters checked", failures))


def check_segment_gaps(results):
    """Check 8: no silent gaps in the segment grid (missing is always flagged)."""
    rows, _ = load_segments()
    all_rows = list(csv.DictReader(open(SEG_CSV_PATH, encoding="utf-8")))
    bad = [f"{r['segment_code']}/{r['metric_code']} {r['fiscal_period']}"
           for r in all_rows if r["value"] == "" and r["missing"] != "True"]
    n_missing = sum(1 for r in all_rows if r["missing"] == "True")
    results.append(("Segment gap audit (missing is flagged, never silent)",
                    not bad, f"{len(all_rows)} segment rows scanned; "
                    f"{n_missing} flagged missing", bad))


# ---------------------------------------------------------------------------
# Phase C — peer-benchmark checks (skipped cleanly if the peer CSV is absent)
# ---------------------------------------------------------------------------

# The concepts the benchmark compares; each peer must reconcile these to its own
# filings exactly the way FORM does (that is the correctness gate on the pull).
PEER_BENCHMARK_METRICS = ["revenue", "gross_profit", "operating_income", "rnd_expense"]


def load_peers():
    rows = list(csv.DictReader(open(PEERS_CSV_PATH, encoding="utf-8")))
    by = defaultdict(dict)
    for r in rows:
        by[(r["ticker"], r["metric_code"])][r["fiscal_period"]] = r
    return rows, by


def check_peer_reconciliation(results):
    """Check 9: each peer's quarters sum to its own filed full-year value.

    Same identity as check 1, run per peer against the peer's own companyfacts —
    so a mis-extracted peer quarter (wrong tag, wrong scale, double count) is
    caught. Metrics a peer doesn't file are simply absent and skipped.
    """
    rows, by = load_peers()
    peers = sorted({r["ticker"] for r in rows})
    failures, checked = [], 0
    for tk in peers:
        facts = load_companyfacts(tk)["facts"]["us-gaap"]
        for code in PEER_BENCHMARK_METRICS:
            _, unit, tags = FILED_METRICS[code]
            try:
                _, years = collect_periods(facts, tags, unit)
            except ValueError:
                continue                       # out-of-tolerance calendar — skip, not our metric
            for year, fy in sorted(years.items()):
                quarters = [by[(tk, code)].get(f"{year}Q{q}") for q in (1, 2, 3, 4)]
                if any(q is None or q["missing"] == "True" for q in quarters):
                    continue
                qsum = sum(float(q["value"]) for q in quarters)
                checked += 1
                if abs(qsum - fy["value"]) > USD_TOLERANCE:
                    failures.append(f"{tk} {code} FY{year}: quarters {qsum:,.0f} "
                                    f"vs FY filed {fy['value']:,.0f}")
    results.append(("Peer FY reconciliation (each peer's quarters sum to its filed FY)",
                    not failures, f"{checked} peer metric-years reconciled", failures))


def check_peer_gaps(results):
    """Check 10: no silent gaps — every peer grid cell is a value or flagged."""
    rows, _ = load_peers()
    bad = [f"{r['ticker']}/{r['metric_code']} {r['fiscal_period']}"
           for r in rows if r["value"] == "" and r["missing"] != "True"]
    n_missing = sum(1 for r in rows if r["missing"] == "True")
    results.append(("Peer gap audit (missing / not-comparable is flagged, never silent)",
                    not bad, f"{len(rows)} peer rows scanned; {n_missing} flagged missing", bad))


def enumerate_flags():
    """Check 4 (informational): list every derived / restated row."""
    rows, _ = load_conformed()
    derived = [r for r in rows if r["derived"] == "True" and r["unit"] != "pct"]
    restated = [r for r in rows if r["restated"] == "True" and r["unit"] != "pct"]
    return derived, restated


def spot_check_table():
    """Check 5: recent revenue / gross profit values for human verification."""
    _, by_metric = load_conformed()
    picks = ["2026Q1", "2025Q4", "2025Q3", "2025Q2", "2025Q1"]
    lines = []
    for period in picks:
        rev, gp = by_metric["revenue"].get(period), by_metric["gross_profit"].get(period)
        if not rev or rev["missing"] == "True":
            continue
        note = "derived: FY − (Q1+Q2+Q3)" if rev["derived"] == "True" else \
               f"{rev['source_form']} filed {rev['filed']}"
        lines.append((period, float(rev["value"]), float(gp["value"]),
                      round(100 * float(gp["value"]) / float(rev["value"]), 1), note))
    return lines


# ===========================================================================
# Proving the checks CAN fail
# ===========================================================================
#
# Every check above passes. That on its own is worth very little: a check that
# cannot fail passes for the same reason a deleted check passes, and the report
# reads identically either way. This suite shares an author with the pipeline it
# validates, which is exactly the condition under which a check quietly stops
# testing anything and nobody notices.
#
# So each check is fed deliberately wrong numbers and must reject them. A check
# that does NOT trip here is reported as broken, and the run fails.
#
# THE FROZEN SNAPSHOT IS NEVER TOUCHED. The conformed CSVs are copied to a
# temporary directory, the copy is corrupted, and the module's path constants
# are repointed at the copy for the duration of one check. data/raw/ and
# data/conformed/ are opened read-only and restored paths are asserted after
# every scenario. Corrupting the real files to prove a point would fail the
# freeze gate for a reason that has nothing to do with the data.


@contextmanager
def _corrupted(target: str, mutate):
    """Repoint one conformed CSV at a corrupted copy, for one check only.

    `target` is the module-global name of the path constant to swap. `mutate`
    receives the parsed rows as a list of dicts and edits them in place.
    """
    globals_ = globals()
    original = globals_[target]
    tmpdir = Path(tempfile.mkdtemp(prefix="cascadia-prove-failable-"))
    try:
        rows = list(csv.DictReader(open(original, encoding="utf-8")))
        mutate(rows)
        copy = tmpdir / original.name
        with open(copy, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        globals_[target] = copy
        yield
    finally:
        globals_[target] = original
        shutil.rmtree(tmpdir, ignore_errors=True)
        assert globals_[target] == original, "path constant not restored"


def _first(rows, **match):
    """The first row matching every key=value, with a non-empty value."""
    for r in rows:
        if r["value"] != "" and all(r.get(k) == v for k, v in match.items()):
            return r
    raise RuntimeError("no row matched %r — the fixture moved" % (match,))


def _scale(**match):
    """Multiply the first matching row's value by 1.5 — a tag/scale slip."""
    def mutate(rows):
        row = _first(rows, **match)
        row["value"] = str(float(row["value"]) * 1.5)
    return mutate


def _blank_unflagged(**match):
    """Empty a value WITHOUT setting missing — the silent gap the audits exist for."""
    def mutate(rows):
        row = _first(rows, **match)
        row["value"] = ""
        row["missing"] = "False"
    return mutate


def _failable_scenarios(has_segments, has_peers):
    """(check function, path constant, mutation, what the corruption represents)."""
    scenarios = [
        (check_fy_reconciliation, "CSV_PATH", _scale(metric_code="revenue"),
         "a revenue quarter inflated 1.5x — quarters no longer sum to the filed FY"),
        (check_crossfoot, "CSV_PATH", _scale(metric_code="operating_income"),
         "operating income inflated 1.5x — GP - Opex + Gain no longer closes"),
        (check_gaps, "CSV_PATH", _blank_unflagged(metric_code="revenue"),
         "a revenue cell emptied with no missing flag — a silent gap"),
    ]
    if has_segments:
        scenarios += [
            (check_segment_revenue, "SEG_CSV_PATH",
             _scale(segment_code="probe_cards", metric_code="seg_revenue"),
             "probe-card revenue inflated 1.5x — segments no longer tie to consolidated"),
            (check_segment_gp_bridge, "SEG_CSV_PATH",
             _scale(segment_code="probe_cards", metric_code="seg_gross_profit"),
             "probe-card gross profit inflated 1.5x — the bridge no longer closes"),
            (check_segment_gaps, "SEG_CSV_PATH",
             _blank_unflagged(segment_code="probe_cards"),
             "a segment cell emptied with no missing flag — a silent gap"),
        ]
    if has_peers:
        scenarios += [
            (check_peer_reconciliation, "PEERS_CSV_PATH", _scale(metric_code="revenue"),
             "a peer revenue quarter inflated 1.5x — that peer no longer reconciles"),
            (check_peer_gaps, "PEERS_CSV_PATH", _blank_unflagged(metric_code="revenue"),
             "a peer cell emptied with no missing flag — a silent gap"),
        ]
    return scenarios


def prove_failable(has_segments, has_peers):
    print("\nProving each check CAN fail, by feeding it wrong numbers:\n")
    proofs = []
    for check, target, mutate, scenario in _failable_scenarios(has_segments, has_peers):
        probe = []
        try:
            with _corrupted(target, mutate):
                check(probe)
            name, passed = probe[0][0], probe[0][1]
            tripped = not passed
        except Exception as exc:                   # noqa: BLE001
            # A check that raises on bad input has still rejected it, but say so
            # rather than scoring it as a clean trip.
            name, tripped = getattr(check, "__name__", str(check)), True
            scenario += f"  [raised {type(exc).__name__}]"
        proofs.append((name, scenario, tripped))

    all_tripped = all(t for _, _, t in proofs)
    for name, scenario, tripped in proofs:
        print(f"  [{'TRIPPED' if tripped else 'DID NOT TRIP'}] {name}")
        print(f"              {scenario}")
    print()
    return proofs, all_tripped


# ===========================================================================

def main() -> None:
    as_of = json.loads(MANIFEST.read_text())["as_of_date"]
    results = []
    check_fy_reconciliation(results)
    check_crossfoot(results)
    check_gaps(results)
    # Phase B segment checks — only if the segment CSV has been built.
    has_segments = SEG_CSV_PATH.exists()
    if has_segments:
        check_segment_revenue(results)
        check_segment_gp_bridge(results)
        check_segment_gaps(results)
    # Phase C peer checks — only if the peer CSV has been built.
    has_peers = PEERS_CSV_PATH.exists()
    if has_peers:
        check_peer_reconciliation(results)
        check_peer_gaps(results)
    derived, restated = enumerate_flags()
    spots = spot_check_table()
    proofs, all_tripped = prove_failable(has_segments, has_peers)

    # A check that cannot fail is not a passing check. Both conditions gate the
    # exit code: every check passes on the real data, AND every check rejects
    # deliberately wrong data.
    all_pass = all(ok for _, ok, _, _ in results) and all_tripped

    md = [
        "# Validation Report — Cascadia Finance",
        "",
        f"*Auto-generated by `src/validate.py` on {date.today().isoformat()}. "
        f"Data snapshot as-of **{as_of}** (SEC EDGAR XBRL, frozen in `data/raw/`).*",
        "",
        f"**Overall: {'ALL CHECKS PASS' if all_pass else 'FAILURES DETECTED'}**",
        "",
        "## Automated checks",
        "",
        "| # | Check | Result | Coverage |",
        "|---|-------|--------|----------|",
    ]
    for i, (name, ok, coverage, failures) in enumerate(results, 1):
        md.append(f"| {i} | {name} | {'PASS' if ok else 'FAIL'} | {coverage} |")
    for name, ok, _, failures in results:
        if failures:
            md += ["", f"### Failures — {name}", ""] + [f"- {f}" for f in failures]

    md += [
        "",
        "## Proof the checks can fail",
        "",
        "*Each check above is re-run against a deliberately corrupted copy of the",
        "conformed data and must reject it. A check that passes corrupted input is",
        "not testing anything, and reads identically in this report to one that",
        "works. The frozen snapshot is never modified — the corruption is applied",
        "to a temporary copy and the path is restored after every scenario.*",
        "",
        f"**{sum(1 for _, _, t in proofs if t)} of {len(proofs)} checks rejected "
        f"deliberately wrong data.**",
        "",
        "| Check | Corruption fed to it | Rejected? |",
        "|-------|----------------------|-----------|",
    ]
    for name, scenario, tripped in proofs:
        md.append(f"| {name} | {scenario} | {'yes' if tripped else '**NO**'} |")

    md += [
        "",
        "## Spot-check table (verify against FormFactor GAAP press-release figures)",
        "",
        "These are the GAAP values this pipeline extracted. Compare them to the",
        "*GAAP* income-statement tables in FormFactor's earnings press releases",
        "(investors.formfactor.com) — **not** the non-GAAP headline numbers.",
        "",
        "| Quarter | Revenue (GAAP) | Gross Profit (GAAP) | GM% (GAAP) | Source |",
        "|---------|----------------|---------------------|------------|--------|",
    ]
    for period, rev, gp, gm, note in spots:
        md.append(f"| {period} | ${rev/1e6:,.1f}M | ${gp/1e6:,.1f}M | {gm}% | {note} |")

    md += [
        "",
        "## Governance flags",
        "",
        f"**Derived values ({len(derived)} rows):** Q4 income-statement values are",
        "not filed discretely (the 10-K files the full year), so Q4 = FY − (Q1+Q2+Q3).",
        "Diluted EPS derived this way is approximate — per-share amounts are not",
        "strictly additive when share counts move between quarters.",
        "",
        "| Metric | Periods derived |",
        "|--------|-----------------|",
    ]
    by_code = defaultdict(list)
    for r in derived:
        by_code[r["metric_code"]].append(r["fiscal_period"])
    for code, periods in sorted(by_code.items()):
        md.append(f"| {code} | {', '.join(sorted(periods))} |")

    md += ["", f"**Restated values ({len(restated)} rows):** latest filed value wins.", ""]
    if restated:
        md += ["| Metric | Period | Value kept | Filed |", "|--------|--------|-----------|-------|"]
        md += [f"| {r['metric_code']} | {r['fiscal_period']} | {float(r['value']):,.0f} | "
               f"{r['filed']} ({r['source_form']}) |" for r in restated]
    else:
        md.append("None detected.")

    if has_segments:
        _, seg = load_segments()
        rev_periods = sorted(seg[("probe_cards", "seg_revenue")])
        gp_periods = sorted(seg[("corporate_unallocated", "seg_gross_profit")])
        md += [
            "",
            "## Segment data (Phase B — Probe Cards vs Systems)",
            "",
            "Segment facts are DIMENSIONAL XBRL, absent from the `companyfacts`",
            "snapshot; they were pulled once from the filing XBRL instances by",
            "`src/ingest_segments.py` (a freeze extension at the same as-of date) and",
            "conformed by `src/conform_segments.py`.",
            "",
            f"- **Segment revenue** is available and reconciles to consolidated revenue "
            f"for **all {len(rev_periods)} quarters** ({rev_periods[0]}–{rev_periods[-1]}).",
            f"- **Segment gross profit / margin** is emitted only where FormFactor files "
            f"the CorporateNonSegment reconciling line so the bridge closes exactly to "
            f"consolidated GAAP gross profit — **{len(gp_periods)} quarters** "
            f"({gp_periods[0]}–{gp_periods[-1]}, FASB ASU 2023-07 onward). Earlier "
            f"periods carry no tagged reconciling item and are flagged missing "
            f"(\"not reconcilable from tagged XBRL\"), never estimated.",
            "- **Segment operating income** is not disclosed (operating expenses are "
            "largely unallocated) and is not produced.",
        ]

    if has_peers:
        peers_manifest = json.loads((REPO_ROOT / "data" / "raw" / "peers_manifest.json").read_text())
        retrieved = peers_manifest.get("retrieval_date", "?")
        _, by_metric = load_conformed()
        prows, pby = load_peers()
        # snapshot = FORM's frozen latest quarter (the benchmark anchor/cap)
        snap = max(p for p, r in by_metric["revenue"].items()
                   if r["value"] != "" and r["missing"] != "True")
        companies = ["FORM"] + sorted({r["ticker"] for r in prows})

        def cell(tk, metric, period):
            row = (by_metric.get(metric, {}) if tk == "FORM"
                   else pby.get((tk, metric), {})).get(period)
            return row if row and row["value"] != "" and row["missing"] != "True" else None

        def has(tk, metric, period):
            return cell(tk, metric, period) is not None

        def growth(tk, period):
            row = cell(tk, "revenue", period)
            return bool(row) and row["yoy_pct"] != ""

        md += [
            "",
            "## Peer benchmark (Phase 3 — US-listed T&M peers)",
            "",
            f"Peer `companyfacts` bundles were pulled by `src/ingest_peers.py` as an ADDITIVE",
            f"extension of the {as_of} freeze; **actual retrieval date {retrieved}**. The",
            f"benchmark never shows a peer quarter later than FORM's frozen latest "
            f"(**{snap}**), so the later pull cannot leak newer data. Peers are conformed",
            "with the same rules as FORM (`src/conform_peers.py`).",
            "",
            f"**Snapshot quarter for the ranked comparison: {snap}.** Availability of each",
            "comparison metric at the snapshot (Y = filed & comparably tagged, — = not):",
            "",
            "| Company | Revenue | Gross margin | Op. margin | R&D % | Rev. growth |",
            "|---------|:-------:|:------------:|:----------:|:-----:|:-----------:|",
        ]
        yn = lambda b: "Y" if b else "—"
        for tk in companies:
            md.append(f"| {tk} | {yn(has(tk,'revenue',snap))} | {yn(has(tk,'gross_margin_pct',snap))} "
                      f"| {yn(has(tk,'operating_margin_pct',snap))} | {yn(has(tk,'rnd_expense',snap))} "
                      f"| {yn(growth(tk,snap))} |")
        md += [
            "",
            "**Not comparable at the snapshot (flagged, never estimated):**",
            "- **CAMT (Camtek)** — foreign private issuer; files Form 20-F/6-K, not 10-Q/10-K. "
            "No recent quarterly GAAP XBRL, so it is excluded from every quarterly ranking.",
            "- **KLAC (KLA)** — tagged `GrossProfit` only through FY2021 Q2 and does not tag "
            "`OperatingIncomeLoss` in-window (latest 2015), so gross and operating margin are not "
            "comparable at the snapshot; shown on revenue scale, R&D %, and growth (it is a "
            "process-control margin *reference*, not a direct comp).",
            "- **COHU (Cohu)** — does not tag `GrossProfit` in-window; gross margin not comparable.",
        ]

    md += [
        "",
        "---",
        "*GAAP per XBRL filings; company headline figures may be non-GAAP.",
        "Missing data is flagged, never filled. Built from public SEC filings",
        f"(EDGAR XBRL APIs), as-of {as_of}. Not investment advice.*",
        "",
    ]

    REPORT_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    for name, ok, coverage, _ in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {coverage}")
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()

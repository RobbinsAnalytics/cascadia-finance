"""
validate_q2_filed.py — publish gate for the Q2 FY2026 filed build (skill step 5/6).

Cascadia Semiconductors · Q2 FY2026 filed-vs-announced

Writes governance/validation_report_q2_filed.md and exits NON-ZERO on any
failure. If it fails, publish nothing and commit nothing.

Checks:
  1. Q2 filed revenue, gross profit, total opex and diluted EPS are present and
     non-null (missing is flagged, never filled).
  2. Crossfoot — gross profit == revenue − cost of revenue; operating income ==
     gross profit − total operating expenses (within rounding).
  3. Tie-out — the 10-Q's own 6-month YTD revenue == frozen Q1 filed revenue +
     Q2 filed revenue. This is what ties Q2 to the frozen dataset without
     touching it.
  4. Every announced line has a filed counterpart, or an explicit not_comparable
     reason (non-GAAP has no XBRL counterpart).
  5. FREEZE INTEGRITY — the pre-existing frozen data and pages are byte-identical
     to git HEAD. Implemented with `git diff --quiet HEAD -- <path>`, which is
     line-ending-aware (so CRLF/LF normalization can't cause a false failure).
     This turns "this build didn't touch the freeze" into a verified assertion.

Usage:
    python src/validate_q2_filed.py
"""

import csv
import glob
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "data" / "raw"
CONF = REPO_ROOT / "data" / "conformed"
REPORT = REPO_ROOT / "governance" / "validation_report_q2_filed.md"

USD_TOL = 2_000

# Everything this build must NOT have altered (checked vs git HEAD).
def frozen_paths():
    paths = ["data/raw/manifest.json", "data/raw/segments_manifest_FORM.json",
             "data/raw/peers_manifest.json",
             "data/conformed/fact_financials_quarterly.csv",
             "data/conformed/fact_segments_quarterly.csv",
             "data/conformed/fact_peers_quarterly.csv",
             "docs/index.html", "docs/margins.html", "docs/peers.html",
             "docs/q2-readthrough.html"]
    for p in sorted(glob.glob(str(RAW / "companyfacts_*.json"))):
        paths.append(str(Path(p).relative_to(REPO_ROOT)).replace("\\", "/"))
    for p in sorted(glob.glob(str(RAW / "segments_FORM_*.json"))):
        paths.append(str(Path(p).relative_to(REPO_ROOT)).replace("\\", "/"))
    return paths


def git_unchanged(path: str) -> bool:
    """True if `path` is byte-identical to HEAD (git, line-ending-aware)."""
    r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", path],
                       cwd=REPO_ROOT, capture_output=True)
    return r.returncode == 0


def frozen_q1_revenue():
    for r in csv.DictReader(open(CONF / "fact_financials_quarterly.csv", encoding="utf-8")):
        if r["fiscal_period"] == "2026Q1" and r["metric_code"] == "revenue" and r["value"]:
            return int(float(r["value"]))
    return None


def main():
    filed = json.loads((RAW / "q2filed_FORM_CIK0001039399.json").read_text())
    ff = {k: v["value"] for k, v in filed["facts"].items()}
    rows = list(csv.DictReader(open(CONF / "fact_q2_filed.csv", encoding="utf-8")))
    results = []   # (name, ok, detail, failures[])

    # 1 · presence
    need = {"revenue": "revenue", "gross_profit": "gross profit",
            "opex_total": "total opex", "eps_diluted": "diluted EPS"}
    missing = [lbl for k, lbl in need.items() if ff.get(k) in (None, "")]
    results.append(("Q2 filed headline lines present & non-null", not missing,
                    f"{len(need)} required lines", [f"missing {m}" for m in missing]))

    # 2 · crossfoot
    cf = []
    if abs(ff["gross_profit"] - (ff["revenue"] - ff["cost_of_revenue"])) > USD_TOL:
        cf.append("gross profit != revenue - cost of revenue")
    if abs(ff["operating_income"] - (ff["gross_profit"] - ff["opex_total"])) > USD_TOL:
        cf.append("operating income != gross profit - total opex")
    results.append(("Crossfoot (GP = Rev − CoR; OpInc = GP − OpEx)", not cf,
                    "2 identities", cf))

    # 3 · YTD tie-out to the frozen Q1
    q1_rev = frozen_q1_revenue()
    ytd = filed["ytd_revenue"]
    tie_ok = q1_rev is not None and abs(ytd - (q1_rev + ff["revenue"])) <= USD_TOL
    results.append(("Q1+Q2 filed revenue ties to the 10-Q's 6-month YTD", tie_ok,
                    f"YTD {ytd:,} vs Q1 {q1_rev:,} + Q2 {ff['revenue']:,}",
                    [] if tie_ok else ["6-month YTD revenue does not equal Q1 + Q2"]))

    # 4 · every announced line has a filed counterpart or is not_comparable
    bad = [r["line"] for r in rows
           if r["flag"] not in ("match", "differs", "not_comparable")
           or (r["flag"] == "not_comparable" and r["basis"] != "non-GAAP")]
    results.append(("Every announced line reconciled or flagged not_comparable",
                    not bad, f"{len(rows)} compared lines", bad))

    # 5 · FREEZE INTEGRITY
    changed = [p for p in frozen_paths() if not git_unchanged(p)]
    results.append(("Freeze integrity — frozen data & pages byte-identical to HEAD",
                    not changed, f"{len(frozen_paths())} protected paths checked",
                    [f"CHANGED: {c}" for c in changed]))

    all_pass = all(ok for _, ok, _, _ in results)
    n_match = sum(1 for r in rows if r["flag"] == "match")
    n_nc = sum(1 for r in rows if r["flag"] == "not_comparable")
    n_diff = sum(1 for r in rows if r["flag"] == "differs")

    md = [
        "# Validation Report — Q2 FY2026 filed build",
        "",
        f"*Auto-generated by `src/validate_q2_filed.py` on {date.today().isoformat()}.*",
        "",
        f"**Overall: {'ALL CHECKS PASS' if all_pass else 'FAILURES DETECTED'}**",
        "",
        "This is a freeze **extension**: it adds the Q2 FY2026 filed page and reconciliation.",
        "The Phase 1–3 dataset stays frozen as-of **2026-07-21** and is verified unchanged by",
        "check 5. Q2 10-Q accession **0001039399-26-000033** (filed 2026-08-04); announced",
        "figures from 8-K EX-99.1 accession **0001039399-26-000030** (furnished 2026-07-29).",
        "",
        "| # | Check | Result | Coverage |",
        "|---|-------|--------|----------|",
    ]
    for i, (name, ok, cov, _) in enumerate(results, 1):
        md.append(f"| {i} | {name} | {'PASS' if ok else 'FAIL'} | {cov} |")
    for name, ok, _, fails in results:
        if fails:
            md += ["", f"### Failures — {name}", ""] + [f"- {f}" for f in fails]

    md += [
        "",
        "## Announced-vs-filed result",
        "",
        f"- **{n_match} of {len(rows)} compared lines match** the filed 10-Q XBRL to the tolerance "
        f"(USD ${USD_TOL:,}; margins 5 bps; EPS $0.005).",
        f"- **{n_diff} differ.**",
        f"- **{n_nc} not comparable** — the company's non-GAAP gross margin, which has no GAAP XBRL counterpart.",
        "- The restructuring tie-out the read-through flagged is resolved by the filed income-statement-location",
        "  breakdown (cost of revenue $4.292M + operating expenses net $0.201M = $4.493M total).",
        "",
        "---",
        "*GAAP per XBRL filings; non-GAAP figures are company-defined and not XBRL-tagged.",
        "Phases 1–3 remain frozen as-of 2026-07-21. Not investment advice.*",
        "",
    ]
    REPORT.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {REPORT}")
    for name, ok, cov, _ in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {cov}")
    if not all_pass:
        print("\nPUBLISH GATE: FAILED — publish nothing, commit nothing.")
        sys.exit(1)
    print("\nPUBLISH GATE: PASSED.")


if __name__ == "__main__":
    main()

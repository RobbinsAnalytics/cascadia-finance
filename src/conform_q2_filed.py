"""
conform_q2_filed.py — Q2 FY2026 announced-vs-filed reconciliation.

Cascadia Semiconductors · Q2 FY2026 filed-vs-announced  (skill step 4)

Input : data/raw/q2filed_FORM_CIK0001039399.json   (filed 10-Q XBRL facts)
        data/raw/announced_q2_fy2026.json           (announced 8-K EX-99.1 figures)
        data/conformed/fact_financials_quarterly.csv (frozen Q1 FY2026 — READ ONLY)
Output: data/conformed/fact_q2_filed.csv            (NEW file — the comparison)
        docs/q2-filed.html                          (data injected between markers)

Per compared line we emit announced value, filed value, absolute variance,
percent variance, and for margin lines the variance in basis points, plus a
flag: match / differs / not_comparable. Non-GAAP lines are not_comparable by
construction — XBRL carries GAAP only.

This never appends to fact_financials_quarterly.csv and never runs
build_pages.py. It reads the frozen Q1 series but does not modify it.

Usage:
    python src/conform_q2_filed.py
"""

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
CONFORMED_DIR = REPO_ROOT / "data" / "conformed"
FROZEN_CSV = CONFORMED_DIR / "fact_financials_quarterly.csv"
OUT_CSV = CONFORMED_DIR / "fact_q2_filed.csv"
PAGE = REPO_ROOT / "docs" / "q2-filed.html"
MARK_START = "<!--CASCADIA_Q2_START-->"
MARK_END = "<!--CASCADIA_Q2_END-->"

USD_TOL = 2_000        # dollars — filings are exact integers
EPS_TOL = 0.005        # dollars/share
BPS_TOL = 5            # basis points on a computed margin

M = 1e-6               # USD -> $millions


def frozen_q1():
    """Read Q1 FY2026 filed values from the frozen series (read-only)."""
    want = {"revenue", "gross_profit", "gross_margin_pct", "operating_income",
            "net_income", "eps_diluted"}
    out = {}
    for r in csv.DictReader(open(FROZEN_CSV, encoding="utf-8")):
        if r["fiscal_period"] == "2026Q1" and r["metric_code"] in want and r["value"] != "":
            out[r["metric_code"]] = float(r["value"])
    return out


def flag_for(unit, announced, filed):
    if filed is None or announced is None:
        return "not_comparable"
    if unit == "pct":
        return "match" if abs((filed - announced) * 100) <= BPS_TOL else "differs"
    if unit == "USD/shares":
        return "match" if abs(filed - announced) <= EPS_TOL else "differs"
    return "match" if abs(filed - announced) <= USD_TOL else "differs"


def build():
    filed = json.loads((RAW_DIR / "q2filed_FORM_CIK0001039399.json").read_text())["facts"]
    ff = {k: v["value"] for k, v in filed.items()}
    ann = json.loads((RAW_DIR / "announced_q2_fy2026.json").read_text())["figures"]
    q1 = frozen_q1()

    # computed GAAP gross margin from FILED line items
    filed_gm = round(100.0 * ff["gross_profit"] / ff["revenue"], 2)

    # ---- comparison lines: (label, basis, unit, announced, filed) ----
    LINES = [
        ("Revenue", "GAAP", "USD", ann["revenue"], ff["revenue"]),
        ("Cost of revenue", "GAAP", "USD", ann["cost_of_revenue"], ff["cost_of_revenue"]),
        ("Gross profit", "GAAP", "USD", ann["gross_profit"], ff["gross_profit"]),
        ("Gross margin", "GAAP", "pct", ann["gaap_gross_margin_pct"], filed_gm),
        ("R&D expense", "GAAP", "USD", ann["rnd_expense"], ff["rnd_expense"]),
        ("SG&A expense", "GAAP", "USD", ann["sgna_expense"], ff["sgna_expense"]),
        ("Total operating expenses", "GAAP", "USD", ann["opex_total"], ff["opex_total"]),
        ("Operating income", "GAAP", "USD", ann["operating_income"], ff["operating_income"]),
        ("Net income", "GAAP", "USD", ann["net_income"], ff["net_income"]),
        ("Diluted EPS", "GAAP", "USD/shares", ann["eps_diluted"], ff["eps_diluted"]),
        ("Restructuring in cost of revenue", "GAAP", "USD",
         ann["restructuring_cogs"], ff["restructuring_cogs"]),
        ("Gross margin", "non-GAAP", "pct", ann["nongaap_gross_margin_pct"], None),
    ]

    rows = []
    for label, basis, unit, a, f in LINES:
        flag = flag_for(unit, a, f)
        abs_var = None if f is None else round(f - a, 6)
        pct_var = None if (f is None or not a) else round(100.0 * (f - a) / abs(a), 4)
        bps_var = None if (unit != "pct" or f is None) else round((f - a) * 100, 2)
        rows.append({
            "line": label, "basis": basis, "unit": unit,
            "announced": a, "filed": "" if f is None else f,
            "abs_variance": "" if abs_var is None else abs_var,
            "pct_variance": "" if pct_var is None else pct_var,
            "bps_variance": "" if bps_var is None else bps_var,
            "flag": flag,
        })

    # ---- restructuring resolution (the read-through flagged an apparent non-tie) ----
    restr = {"cogs": ff["restructuring_cogs"], "total": ff["restructuring_total"],
             "opex_net": ff["restructuring_total"] - ff["restructuring_cogs"]}

    # ---- gross-profit walk on FILED figures (Phase 2 method) ----
    d_rev = ff["revenue"] * M - q1["revenue"] * M
    rev_effect = round(d_rev * (q1["gross_margin_pct"] / 100.0), 2)
    margin_effect = round((filed_gm - q1["gross_margin_pct"]) / 100.0 * ff["revenue"] * M, 2)
    walk = {"revenue_effect": rev_effect, "margin_effect": margin_effect,
            "total": round(ff["gross_profit"] * M - q1["gross_profit"] * M, 2)}

    gaap_differs = [r for r in rows if r["basis"] == "GAAP" and r["flag"] == "differs"]
    headline = "differs" if gaap_differs else "match"

    payload = {
        "as_of_frozen": "2026-07-21",
        "as_of_filed": json.loads((RAW_DIR / "q2filed_manifest_FORM.json").read_text())["as_of_date"],
        "tenq_accession": "0001039399-26-000033", "tenq_filed": "2026-08-04",
        "eightk_accession": "0001039399-26-000030", "eightk_furnished": "2026-07-29",
        "headline_result": headline,
        "q1": {"revenue": round(q1["revenue"] * M, 3), "gross_profit": round(q1["gross_profit"] * M, 3),
               "gm": q1["gross_margin_pct"], "operating_income": round(q1["operating_income"] * M, 3),
               "net_income": round(q1["net_income"] * M, 3), "eps": q1["eps_diluted"]},
        "q2": {"revenue": round(ff["revenue"] * M, 3), "cost_of_revenue": round(ff["cost_of_revenue"] * M, 3),
               "gross_profit": round(ff["gross_profit"] * M, 3), "gm": filed_gm,
               "rnd": round(ff["rnd_expense"] * M, 3), "sgna": round(ff["sgna_expense"] * M, 3),
               "opex": round(ff["opex_total"] * M, 3), "operating_income": round(ff["operating_income"] * M, 3),
               "net_income": round(ff["net_income"] * M, 3), "eps": ff["eps_diluted"],
               "restr_cogs": round(restr["cogs"] * M, 3), "restr_total": round(restr["total"] * M, 3),
               "restr_opex_net": round(restr["opex_net"] * M, 3),
               "nongaap_gm": ann["nongaap_gross_margin_pct"]},
        "compare": [{"line": r["line"], "basis": r["basis"], "unit": r["unit"],
                     "announced": (r["announced"] * M if r["unit"] == "USD" else r["announced"]),
                     "filed": ("" if r["filed"] == "" else (r["filed"] * M if r["unit"] == "USD" else r["filed"])),
                     "flag": r["flag"],
                     "bps": r["bps_variance"], "absM": ("" if r["abs_variance"] == "" else
                            (round(r["abs_variance"] * M, 4) if r["unit"] == "USD" else r["abs_variance"]))}
                    for r in rows],
        "walk": walk,
        "restructuring": {"cogs": round(restr["cogs"] * M, 3), "total": round(restr["total"] * M, 3),
                          "opex_net": round(restr["opex_net"] * M, 3)},
    }
    return rows, payload


def inject(payload):
    if not PAGE.exists():
        print(f"(page {PAGE.name} not present yet — skipping injection)")
        return
    html = PAGE.read_text(encoding="utf-8")
    s, e = html.index(MARK_START), html.index(MARK_END)
    block = (f"{MARK_START}\n<script id=\"cascadia-q2\" type=\"application/json\">\n"
             f"{json.dumps(payload, separators=(',', ':'))}\n</script>\n")
    PAGE.write_text(html[:s] + block + html[e:], encoding="utf-8")


def main():
    rows, payload = build()
    CONFORMED_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {OUT_CSV} ({len(rows)} compared lines)")

    n_match = sum(1 for r in rows if r["flag"] == "match")
    n_diff = sum(1 for r in rows if r["flag"] == "differs")
    n_nc = sum(1 for r in rows if r["flag"] == "not_comparable")
    print(f"  match={n_match}  differs={n_diff}  not_comparable={n_nc}  "
          f"-> headline: {payload['headline_result']}")
    inject(payload)
    print(f"Injected CASCADIA_Q2 into {PAGE.name}" if PAGE.exists() else "")


if __name__ == "__main__":
    main()

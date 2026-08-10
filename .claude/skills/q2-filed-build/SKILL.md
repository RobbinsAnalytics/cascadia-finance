---
name: q2-filed-build
description: Build the Q2 FY2026 FILED page from FormFactor's 10-Q XBRL as an additive freeze extension. Run when the Q2 FY2026 10-Q appears on EDGAR. Adds a new page; never refreshes, rebuilds or amends the existing frozen builds.
---

# Q2 FY2026 filed build — a freeze EXTENSION, not a refresh

FormFactor's Q2 FY2026 (quarter ended **2026-06-27**) 10-Q makes filed XBRL
available for a quarter the site currently carries only as *announced* press-
release figures. This build adds **one new page** carrying the filed numbers
and the announced-vs-filed comparison.

It does not refresh anything. Phase 1/2/3 stay exactly as frozen at
**2026-07-21**, and the claim on the module page — that refreshing is a
deliberate act and never a side effect — stays literally true, because no
existing series is re-pulled or re-stamped.

This is the third freeze extension, after `ingest_segments.py` (Phase B) and
`ingest_peers.py` (Phase C). Follow their shape: new files, new manifest, own
as-of date, nothing existing touched.

---

## Hard guardrails — violating any of these invalidates the build

1. **Never run `src/ingest.py`.** It re-pulls `companyfacts` and *overwrites
   the freeze*. Running it destroys the 2026-07-21 snapshot, which is the only
   thing that makes the announced-vs-filed comparison computable.
2. **Never modify** `data/raw/companyfacts_*.json`, `data/raw/manifest.json`,
   `data/raw/segments_*`, `data/raw/peers_*`, or any existing file in
   `data/conformed/`.
3. **Never rebuild** `docs/index.html`, `docs/margins.html`, `docs/peers.html`.
   `src/build_pages.py` rewrites all three — do not invoke it unscoped.
4. **Do not restate `docs/q2-readthrough.html`.** Its announced figures are the
   *other half* of the comparison and must stay as published. The single
   permitted edit is adding a link to the new filed page. Nothing numeric.
5. **Publish nothing if validation fails.** See step 6.

---

## 1 · Confirm the filing actually exists

```bash
curl -s -H "User-Agent: RobbinsAnalytics cascadia-semiconductors ajayrobbins@hotmail.com" \
  https://data.sec.gov/submissions/CIK0001039399.json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); r=d['filings']['recent']; \
[print(r['form'][i], r['filingDate'][i], r['reportDate'][i], r['accessionNumber'][i]) \
 for i in range(40) if r['form'][i]=='10-Q']"
```

Proceed **only** if a `10-Q` row shows `reportDate == 2026-06-27`. Record its
`accessionNumber` and `filingDate` — both go in the manifest.

If no such row exists, stop and report. A 10-Q for a different period, an 8-K,
or an NT 10-Q (late-filing notification) is not this build's trigger.

## 2 · Record the announced figures as a sourced artifact

Before pulling anything, write `data/raw/announced_q2_fy2026.json` capturing
the 2026-07-29 8-K EX-99.1 figures already published on the read-through page —
revenue, GAAP gross profit and margin, non-GAAP gross margin, operating
expenses, GAAP diluted EPS — each with the source accession and a
`tier: "announced"` marker.

Do not scrape these from the rendered HTML. They are an input to a governance
comparison and need their own dated, citable artifact.

## 3 · Ingest — `src/ingest_q2_filed.py`

Model on `src/ingest_segments.py` (same User-Agent, ~4 req/s, backoff on
429/5xx). Pull the Q2 FY2026 XBRL **from the 10-Q filing instance** for that
accession, not from `companyfacts`.

Writes, and only these:

- `data/raw/q2filed_FORM_CIK0001039399.json` — extracted facts
- `data/raw/q2filed_manifest_FORM.json` — `as_of_date` = actual retrieval date
  (**not** 2026-07-21 — this is a genuinely later pull and must say so),
  accession, filing URL, filed date, byte counts

Concepts to extract, matching the Phase 1 metric set so the comparison is
like-for-like: revenue, cost of revenue, gross profit, R&D, SG&A, total
operating expenses, operating income, diluted EPS. Reuse
`governance/tag_mapping.csv`; append any new tag encountered rather than
silently mapping it.

## 4 · Conform — `src/conform_q2_filed.py`

Writes `data/conformed/fact_q2_filed.csv` — a **new** file. Never append to
`fact_financials_quarterly.csv`.

Produce, per compared line: announced value, filed value, absolute variance,
percent variance, and for margin lines the variance in basis points. Flag every
line `match` / `differs` / `not_comparable`. Non-GAAP lines are
`not_comparable` by construction — XBRL carries GAAP only, and that asymmetry
is itself part of the story the page tells.

## 5 · Validate — `src/validate_q2_filed.py`

Writes `governance/validation_report_q2_filed.md`. Exits **1** on any failure.
Checks:

- Q2 filed revenue, gross profit, opex and diluted EPS are all present and
  non-null. Missing is flagged, never filled.
- Crossfoot: gross profit == revenue - cost of revenue; operating income ==
  gross profit - total opex, within rounding.
- Filed revenue ties to the consolidated revenue the 10-Q itself reports.
- Every announced line has a filed counterpart or an explicit
  `not_comparable` reason.
- **Freeze integrity.** Hash `data/raw/companyfacts_FORM_*.json`,
  `data/raw/manifest.json`, and every pre-existing file in `data/conformed/`,
  and compare against `git show HEAD:<path>`. Any difference fails the build.

That last check is the important one. It turns "this build didn't touch the
freeze" from a promise into a verified assertion — the same reasoning as the
whitespace hook in the website repo: make the control structural rather than
remembered.

## 6 · The publish gate

If `validate_q2_filed.py` exits non-zero: **stop. Publish nothing. Commit
nothing.** Report which checks failed and what the values were. A failed
financial dataset must never reach the live site.

## 7 · Build the page — `docs/q2-filed.html`

A new page. Structure:

- **Tier labelling on every figure.** `FILED (10-Q XBRL)` vs
  `ANNOUNCED (8-K EX-99.1)`, in the same visual language the read-through page
  already uses.
- **Headline Q2 FY2026 filed GAAP figures**, with QoQ against Q1 FY2026 drawn
  from the existing frozen series (read-only).
- **The announced-vs-filed table** — the centrepiece. Every compared line with
  its variance, and the `not_comparable` lines shown rather than dropped.
- **The margin walk applied to filed figures**, same method as Phase 2.
- **A "what moved and why" note.** If filed matches announced, say so plainly —
  a null result is a real result, and the page pre-committed to publishing it
  either way.
- **Data & method footnotes**: both as-of dates, both accessions, the GAAP vs
  non-GAAP asymmetry, and an explicit statement that the Phase 1-3 dataset was
  not refreshed.

Inline the data at build time as the existing pages do. Do not add a CDN call.

## 8 · Publish

GitHub Pages serves `docs/` from `main` in this repo, reached at
`www.robbinsanalytics.com/cascadia-finance/`. Pushing `main` publishes.

Stage by name — never `git add -A`:

```bash
git add data/raw/q2filed_* data/raw/announced_q2_fy2026.json \
        data/conformed/fact_q2_filed.csv \
        src/ingest_q2_filed.py src/conform_q2_filed.py src/validate_q2_filed.py \
        governance/validation_report_q2_filed.md governance/tag_mapping.csv \
        docs/q2-filed.html
git commit && git push origin main
```

## 9 · Surface it on the website

In `RobbinsAnalytics.github.io`, add a button for the new page to
`projects/cascadia-finance.qmd` alongside the existing four, and update
the read-through bullet to note the filed page now exists. Publish that repo
with its own `/publish` skill — do not improvise a shorter version.

## 10 · Report

State: the accession and filed date, which lines differed and by how much,
whether validation passed, what was published, and — explicitly — that the
frozen dataset was not modified, citing the freeze-integrity check result.

---

## Failure modes seen or anticipated

**NT 10-Q filed instead.** FormFactor requested an extension. Not a trigger;
stop and report the new expected date.

**Filing present but XBRL instance not yet indexed.** Financial report exhibits
occasionally lag the filing index by minutes. Retry once after a short wait,
then stop and report rather than partially ingesting.

**A tag changed since Q1.** Append to `governance/tag_mapping.csv` and surface
the addition in the report. Never silently coerce an unrecognized tag.

**Filed equals announced exactly.** Expected, and fine. Publish it as a null
result. The page's value is the discipline of checking, not the size of the gap.

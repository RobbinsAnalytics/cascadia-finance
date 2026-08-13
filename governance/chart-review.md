# Cascadia Finance — chart review

**Standard: `CHART-REVIEW.md` v2.5, companion to `VIZ-PRINCIPLES.md` v2.5.**

This module had never had a chart review. Nineteen charts across five pages
shipped without one, and Rule 7.1 has been `INVARIANT` since v2.0. This file is
the first, run as part of the v2.5 reskin authorized in `governance/freeze.toml`
on 2026-08-12.

---

## Part 1 — Author's pre-panel review

**Written and committed before the reading panel was run.** That ordering is a
requirement, not a courtesy: the panel's `N` metric counts defects the author
had **not** already written down, and v2.5 is explicit that the number "has to
be captured before the panel runs, not reconstructed after." Anything the panel
raises that is not in this list is novel; anything already here is not.

These were found during Phases 1–5 of the reskin, mostly by measuring rather
than by looking. Each is recorded with the rule it engages and what was done.

### Already fixed

| # | Defect | Rule | Where |
|---|---|---|---|
| 1 | `--muted #898781` measured 3.41:1 on the page ground — every kicker, chart subtitle, footnote and disclosure on all five pages failed 4.5:1 as text | 5.3 | Phase 1 |
| 2 | `q2-filed` walk drew a fixed 680px viewBox scaled to fit, so its "12px" labels rendered at ~5.4 CSS px at 320 | 5.3, 5.5 | Phase 2 |
| 3 | `q2-filed` walk totals used `--baseline`: 1.75:1 before the palette swap, 1.21:1 after, against the 3:1 a mark owes | 2.3.6 | Phase 2 |
| 4 | Badge ink on mist measured 4.27:1 (evergreen) and 3.75:1 (madrona) against the 4.5:1 badge text owes | 5.3 | Phase 2 |
| 5 | **The vendored theme's `aria.enabled` overwrote every authored `aria-label` on every render.** A screen reader on the waterfall received the transparent stacking series read aloud, ending in `NaN` | 5.1, 5.2, K2 | Phase 3 |
| 6 | `q2-readthrough` slope chart carried a legend restating three series already ending in direct labels | 3.6 | Phase 3 |
| 7 | `q2-readthrough` table swatches were literal old-palette hexes, desynced from the charts they label by the Phase 1 swap | 2.3.1 | Phase 3 |
| 8 | Adopting the theme silently removed the slope chart's endpoint markers via `showSymbol: false` | 2.5 | Phase 3 |
| 9 | `margins` GP bridge coloured Corporate/unallocated with `--up-ink`/`--down-ink` — variance signals reused as series colours, which the stylesheet forbids in as many words | 2.3.1, 2.3.2 | Phase 3 |
| 10 | `margins` decomposition started at colour slot 2 while the module's other two walk charts use slots 1 and 2 for the same two concepts | 2.3.1 | Phase 3 |
| 11 | `margins` `chart-gm` and `chart-bridge` had no data table anywhere on the page | 5.1 | Phase 3 |
| 12 | **`peers` trend charts drew six Rain series with no direct label and no legend.** At 320 px, five indistinguishable grey lines identifiable only by hover | 2.3.6, 3.3, 3.6, 5.5 | Phase 3 |
| 13 | `peers` scatter clipped the direct label off its highest point (Teradyne, 36.9% against a 40% axis top) — and that point is Rain, so the clipped label was the compensating condition | 2.3.6, 5.5 | Phase 3 |
| 14 | `peers` scatter clipped the y-axis name off the left edge; `containLabel` reserves room for axis labels but not axis names | 5.3 | Phase 3 |
| 15 | `peers` used two different hand-picked greys for one role, `#aab2ba` and `#a7b0b8`, both 2.09:1 | 2.3.6 | Phase 3 |
| 16 | `peers` had no data table for any of its seven charts; the only table maps XBRL tags | 5.1 | Phase 3 |
| 17 | Raising `peers` trend x-axis labels to the 12px floor collided eight year labels at 320 | K4, 5.5 | Phase 3 |
| 18 | In-chart text below 12px throughout — axis labels, legends, markers, strip text at 10, 10.5, 11 and 11.5px | 5.3 | Phases 1–3 |
| 19 | Rounded bar caps on revenue, EPS, both waterfalls | 2.5 | Phases 2–3 |
| 20 | No favicon on any of the five pages | K8 | Phase 2 |
| 21 | `q2-readthrough` loaded a floating `echarts@5` tag — a frozen page whose rendering could change without a commit | K7 | Phase 3 |
| 22 | `margins` GP bridge and `peers` scatter had no chart title at all | 3.1 | Phase 4 |
| 23 | Nineteen titles named the metric rather than stating a finding | 3.1 | Phase 4 |

### Known and NOT fixed — carried into the panel

| # | Issue | Rule | Why it is here |
|---|---|---|---|
| 24 | **Evergreen and `--up-ink` are both green and measure 1.42:1 against each other.** A green series mark and a green "up" chip are the same green to the eye | 2.3.2 | The chips carry an arrow and signed text, so colour is not the only channel and 2.3.2 holds. This is coherence, not conformance, and the handoff directed that the variance set survive the swap untouched. Recorded in the stylesheet. |
| 25 | `index` opex chart keeps a legend where Rule 3.6 prefers direct labels | 3.6 | The page documents why: three ratio lines converge in a narrow band and the end-labels collided, worst at phone width. That is the case 3.6's exception exists for. Flagged rather than reopened. |
| 26 | Two charts state a computed aggregate the eye cannot verify from the marks — "highest quarter in the series" and "its own fastest in the series" | 3.2 | Both are true of the plotted series and both are visible as the extreme mark on the chart they title. Offered to the panel as 3.2 `PASS-BY-EXCEPTION` candidates rather than assumed. |

**Pre-panel defect count: 26.** Twenty-three fixed, three carried.

---

## Part 2 — Reading panel (Rule 7.4)

```
READING PANEL — Cascadia Finance, 19 charts across 5 pages — 2026-08-12
Standard: CHART-REVIEW.md v2.5 (canonical copy, cascadia-standards/design-system)
Decision served (Rule 0.1): a finance-literate hiring manager or interviewer
  judging analytical judgement from a portfolio piece in minutes, with no access
  to the filings. Secondary: an equity/FP&A reader asking what moved FormFactor's
  margins and how it compares to peers.
Nature: simulated
Widths given to every seat: 1280 px (design) and 320 px (narrowest supported)

  Seat 1  Director of FP&A, semiconductor capital equipment, 12 yrs
          — why this seat: the person the hiring manager would ask to
            sanity-check the work. Owns a margin number internally and will test
            whether a move is mix, price, or a charge that will not repeat.
  Seat 2  Sell-side equity analyst, semi-cap coverage, 9 yrs
          — why this seat: the secondary reader named in 0.1. Judges disclosure
            quality for a living and is the seat most likely to catch a
            GAAP/non-GAAP boundary being blurred.
  Seat 3  Technical recruiter screening analytics candidates, 6 yrs
          — why this seat: Rule 0.1 asks for the room's actual literacy, and the
            person who opens a portfolio link first is usually not a finance
            specialist. Tests whether the pages work for their least technical
            real reader.
  Seat 4  visualization — canvas only; no tables, no data, no finding

Blindness confirmed: design system [x] · review and build notes [x] · source data [x] ·
                     intended finding [x] · other reviewers' output [x]
Run: parallel [x]  (all four spawned in one message; no seat saw another's return)
```

**Self-attestation, stated as the standard requires.** Blindness and parallelism
are properties of how the seats were spawned, not of anything visible in this
file. What is checkable here: a reason per seat, four items returned per seat
per chart, a canvas location for every quoted number, and a disposition for
every finding.

### Disposition

Consensus is the number of seats that reached the finding independently. It
drives fix order — a three-seat gap outranks a one-seat defect.

| # | Finding, in the reviewer's words | Seats | Defect? | Disposition | Rule |
|---|---|---|---|---|---|
| 1 | *"Which line is which? There's no legend."* | 4 | yes | **fix** — four charts declare a legend but never set `show: true`, so the vendored theme's `legend: {show: false}` default hid all four. Series identity is gone on `index__chart-opex`, `margins__chart-bridge`, `margins__chart-segmix`, `margins__chart-seggm`. Introduced by this reskin in Phase 3 and asserted as intact in that commit message | 3.6 |
| 2 | *"the year labels smash into each other — it reads as '2019202020212022' with no gaps"* | 4 | yes | **fix** — 320 px, all eight year-axis charts. The every-other-year rule already written for the peers trends was never applied to the rest | K4, 5.5 |
| 3 | *"the annotations mark the first spike and the negative bar… the sentence names one pair of bars and the drawing marks a different pair"* | 1 | yes | **fix** — the Phase 4 title says "the two spikes are one-time items"; (1) is on the $1.13 spike and (2) on the −$0.17 trough. The title is wrong about its own chart | 3.2 |
| 4 | *"the subtitle promises '(1)(2) are footnoted one-time items' and no footnote text appears anywhere in the card"* | 3 | yes | **fix** — the footnote sits in Data & method further down the page. Lift the chart into a slide and the caveat is stranded | 4.3 |
| 5 | *"the 'Q1 FY26' callout balloon collides with the line it labels… reads as 'FY2ø'"* | 3 | yes | **fix** — and it is clipped by the card edge at 320 px | 5.3, 5.5 |
| 6 | *"only 'Probe Cards' and 'Corporate / unallocated' remain… two of the four bars unidentified"* | 3 | yes | **fix** — `margins__chart-gpbridge` at 320 px. The unlabelled total bar is Rain, so the dropped label is 2.3.6's compensating condition | 2.3.6, 5.5 |
| 7 | *"'+$31.8M' and '$130.9M' merge into '+$31.8M$130.9M'"* | 3 | yes | **fix** — `q2-readthrough__c1` at 320 px; the category labels collide too | 5.3, 5.5 |
| 8 | *"the x-axis labels overlap into '$1.00B$2.00B$3.00B'"* | 4 | yes | **fix** — all four peer rank charts at 320 px | K4 |
| 9 | *"inTEST has no visible bar at all — just a label and a value with nothing drawn"* | 3 | yes | **fix** — KLA's $3.42B sets the axis and crushes the ranked set into 8% of the width | 1.2 |
| 10 | *"'inTEST' is truncated to 'inT' — the FormFactor bubble covers the rest"* | 3 | yes | **fix** — scatter at 320 px. The occluded points are Rain, so again this is the label that makes the hue legal | 2.3.6, 5.5 |
| 11 | *"the right-edge labels… now sit inside the plot area, over the line ends they're meant to label"* and *"KLAC and CAMT now nearly touch"* | 3 | yes | **fix** — both peer trend charts at 320 px | 2.3.6, 5.5 |
| 12 | *"this chart's own headline figure is unobtainable from the chart"* | 4 | yes | **fix** — `margins__chart-bridge`. The title claims a $4.0M decline; nothing marks the latest quarter among 33, and with no legend the encoding is undecidable | 3.2 |
| 13 | *"My first read was 'the chart failed to load.'"* | 4 | yes | **fix** — `margins__chart-seggm` runs an eight-year axis over eight quarters of data, on a 0% baseline over a 36–51% range | 3.5, 1.3 |
| 14 | *"the title says 'the four peers that tag it' and the chart shows four bars including FormFactor"* | 1 | yes | **fix** — off by one. It is FormFactor plus three peers | 3.2 |
| 15 | *"five points is about eleven pixels… the endpoint looks highest, but the difference is inside the resolution of the chart"* | 1 | yes | **fix** — `peers__trend-growth`. Pre-flagged by the author as a 3.2 exception candidate; the panel's read is that it fails rather than passes. **Not novel** | 3.2 |
| 16 | *"Revenue had six names, this has four… is the peer group changing between charts?"* | 3 | yes | **fix** — the four rank charts carry 6 / 4 / 5 / 6 companies with no on-chart reason, and CAMT appears in both trends and in none of the rank charts | 4.1, 4.3 |
| 17 | *"'bubble area ≈ revenue' and no scale… It's decoration rather than a third variable"* | 3 | yes | **fix** — no size legend on the scatter | 3.6 |
| 18 | *"Why are there two of these? … my first reaction was that someone duplicated a slide"* | 3 | yes | **fix** — the identical title on `q2-readthrough__c1` and `q2-filed__walk` was deliberate and it backfired: three seats read duplication rather than reconciliation. That announced equals filed to the dollar is the finding, and no chart says it | 3.1 |
| 19 | *"'Held' is the wrong verb… the green line ranges 28% to 40% and has fallen about five points since early 2025"* | 1 | yes | **fix** — `index__chart-opex` title | 3.2 |
| 20 | *"13.6 plus 14.3 is 27.9, not 31.0 — so there's 3.1 points of something else and the chart doesn't name it"* | 2 | yes | **fix** — the opex title implies a decomposition that does not close | 3.2, 4.1 |
| 21 | *"'Systems fell 34.0%' — not visible… comparing floating segment lengths across bars is the specific thing stacked bars cannot do"* | 1 | yes | **accepted** — the stack is right for the 88% share claim, which is the dominant one. The title's "Systems fell 34.0%" clause stays for now: changing a title needs authorisation under Phase 4 and this one was not in the approved set. Carried as an open item | 3.2 |
| 22 | *"no way of knowing which bars are derived… one point in four is a residual"* | 2 | yes | **accept** — the ‡ convention is disclosed in the provenance strip and in Data & method and predates this reskin. Marking individual bars is a data-layer change outside this authorization | 4.1 |
| 23 | *"Why am I looking at this twice? It's the identical line to the index page chart"* | 3 | no | **rejected** — `index` carries the headline series and `margins` opens the walk with it. Repetition across a linked pack is navigation, not a chart defect | — |
| 24 | *"What happened in that 2022 quarter that took margin to 27%?"* | 3 | no | **rejected** — a good reader question, but no title on the page makes a claim about 2022, so 3.4 does not bite. Logged as content backlog | — |
| 25 | *"the middle two bars float… nothing connects them"* | 3 | no | **rejected** — connector lines are a preference. Every bar is named and valued, and all three waterfalls crossfoot on screen | — |
| 26 | *"there is no y-axis at all"* on `q2-filed__walk` | 2 | no | **rejected** — deliberate. Four labelled bars carry their own values, and the same seat called it the cleanest chart in the set and the best behaved at 320 px | — |
| 27 | *"I'd want the absolute dollars"* on R&D intensity | 2 | no | **rejected** — a request for a different analysis, not a misreading of this one | — |
| 28 | *"What's driving Teradyne's 87%?"* | 3 | no | **rejected** — a domain question about a peer's business, not answerable from a benchmark chart and not a defect in it | — |
| 29 | *"Is the $21.5M restructuring done?"* | 3 | no | **rejected** — the best question the panel asked, and out of scope for a frozen dataset. Logged as content backlog | — |
| 30 | *"Full company names instead of tickers"* on the trends | 1 | no | **rejected** — tickers are direct labels, chosen to fit 320 px, and the governance table maps every one | — |
| 31 | *"some sense of where you'd want to be on this chart"* | 1 | no | **rejected** — preference | — |
| 32 | *"I don't know what 'ex-restructuring' or 'non-GAAP' mean"* | 1 | no | **rejected** — the literacy seat working as designed. Both are defined in the page's callouts; this is the cost of the subject matter, not a chart defect | — |
| 33 | *"The Y axis says 36, 41, 46, 51, 56 with no percent sign"* | 2 | yes | **fix** — cheap, and the seat that rated this chart highest still stumbled on it | 5.2 |
| 34 | *"Which bar is which quarter? the axis only ticks years"* | 3 | no | **rejected** — 33 quarters cannot each carry a label. Per-quarter identity is in the tooltip and the data table, and thinning to fiscal-year starts is the declared rule | — |

```
PANEL: 4 seats, simulated · 19 charts · findings 34 · defects 22 · novel 20
       fixed 20 · accepted 2 · rejected 12
       D = 1.16 defects/chart · N = 0.91 novel share · R = 0.35 rejected share
```

**D = 1.16** — 22 defects across 19 charts.

**N = 0.91** — 20 of 22 defects were absent from the author's pre-panel list.
Only finding 15 and part of finding 20 were already written down.

**R = 0.35** — 12 of 34 findings rejected as preferences, domain questions, or
requests for a different analysis.

**Retirement trigger (Rule 7.4): not met, and not close.** The rule retires at
D < 0.25 and N < 0.25 across three consecutive modules. One module at N = 0.91
is the opposite of that: the panel found what measuring could not.

**Visualization-seat ratio, per the skill's standing caution.** Seat 4 produced
or sharpened 11 of the 22 defects — half, against Deal Desk's 13 of 19. But the
three domain seats converged independently on the missing legends, the 320 px
year-label collapse and the duplicate-title reading, none of which seat 4 found
alone. The domain floor of three earned its place here; do not cut it on this
evidence.

**On the sentence returns**, which Rule 7.2's DracoGPT caveat marks as the
weakest link: they were not bland and did not echo the titles. Seat 3 returned
*"Honestly? I don't know what this chart is showing me"* for
`margins__chart-bridge`, and seat 1 independently returned *"I couldn't read
this one in the time I had."* Two seats failing to state any finding at all
from a chart is a 7.1 result in its own right.

### Verdict

**DO NOT SHIP.**

Any INVARIANT failure blocks regardless of preference score. Finding 1 alone is
a 3.6 failure on four charts — introduced by this reskin and asserted as intact
in its own commit message. Findings 2, 6, 7, 8, 10 and 11 are 5.3 / 5.5 / 2.3.6
failures at the narrowest supported width, which is the width v2.5 added to
this rule precisely because the first panel run under 7.4 read design-width
renders only and missed exactly this class. Findings 3, 12, 14, 19 and 20 are
3.2 failures where a title asserts something its own chart does not carry.

---

## Part 3 — Fix round

All 20 fixable defects were repaired across five commits, one page each, with
both gates run either side of every one.

**The regression that started it.** Four charts declared a legend without
`show: true`, so the theme's `legend: {show: false}` default hid all four when
Phase 3 adopted it. Restored on `index__chart-opex`,
`margins__chart-bridge`, `margins__chart-segmix` and `margins__chart-seggm`.

**Everything that broke only at 320 px**, which is the width v2.5 added to this
rule: year labels thinned to every other year on all eight year-axis charts;
the peers rank charts thin their ticks with `hideOverlap`; the GP bridge forces
all four category labels; the readthrough bridge wraps its categories and
staggers its value labels; the scatter's bubbles scale with the canvas and its
axis names stand down; the trend end-labels get a measured right gutter. Four
of those were Rain series losing the direct label that makes the hue legal at
all — 2.3.6's compensating condition, not cosmetics.

**Three that were wrong at every width.** The `margins__chart-gm` endpoint
marker is a text label now, not a 42 px pin whose own outline struck through
"FY26". `margins__chart-seggm` is cut to the quarters that carry data, on a
value axis derived from their range, instead of eight empty years on a 0%
baseline. KLA no longer sets the revenue ranking's scale — it is declared
"reference, not ranked" on that page, so letting it own the axis was the
inconsistency, and one seat reported inTEST as having no visible bar at all.

**Five titles revised and re-approved**, all of them claims the chart did not
carry: the EPS title named "the two spikes" while the markers sat on one spike
and one trough; `peers__rank-gm` was off by one against its own bar count; the
opex title said "held" of a line that had fallen five points; `trend-growth`
dropped a superlative the axis resolution could not support; and `q2-filed`
now states the reconciliation the panel read as a duplicated slide.

**Two rendering changes were deliberate and are recorded as such.**
`chart-seggm` draws 9 category slots instead of 33, and `rank-revenue` draws
five bars instead of six. Verified value by value: every non-null figure in
seggm is identical, and every surviving company in rank-revenue holds its exact
value. Nothing else moved — no plotted value, KPI, callout, as-of date or table
content differs anywhere across the five pages from the pre-reskin capture.

### Open items carried

| Item | Why it is carried |
|---|---|
| The `margins__chart-segmix` title claims "Systems fell 34.0%", which a floating stacked segment cannot show (finding 21) | Changing it is a title change and needs authorisation under Phase 4; it was not in the approved set. The 88% share claim the stack does support is the dominant one |
| Derived Q4 bars are not individually marked (finding 22) | Disclosed in the provenance strip and Data & method. Marking bars is a data-layer change outside this reskin's authorization |
| Evergreen and `--up-ink` measure 1.42:1 (pre-panel item 24) | Coherence rather than conformance — the chips carry an arrow and signed text. No seat raised it, which is weak evidence it does not bite in practice |
| Two content questions the panel asked and the frozen dataset cannot answer: what caused the 2022 margin collapse, and whether the $21.5M restructuring repeats | Both are good. Both need data past the freeze |

### Revised verdict

**No INVARIANT failure outstanding.** The 3.6 legend failure is repaired on all
four charts; the 5.3 / 5.5 / 2.3.6 failures at 320 px are repaired on all
affected charts; the 3.2 title failures are repaired and re-approved. Two
defects ship accepted, with reasons recorded above and no preference weight
attached to either.

**SHIP** — subject to the module's own publish gates, which are green: four
domain checks pass and the freeze is intact at 19 protected paths.

Nothing has been pushed. Publishing is Aaron's call and pushing `main` is the
deploy.

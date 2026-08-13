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

*Run after this file was committed. Roster, returns, disposition and the
D / N / R block follow.*

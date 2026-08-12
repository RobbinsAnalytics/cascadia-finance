#!/usr/bin/env python3
"""capture_charts.py — render every chart and capture every rendered number.

Phase 0 of the VIZ-PRINCIPLES v2.5 reskin. Two artifacts, one run:

    1. A PNG of each of the 19 charts, at the design width and at 320 px.
       The visual comparison set for the Phase 6 reading panel.

    2. A numeric fixture — series values, axis extents, rendered axis labels,
       every table cell, every KPI, every callout, every <text> node in an SVG
       chart. The artifact that proves "nothing numeric changed."

The fixture matters more than the pictures, and the reason is in R1 of the
reskin handoff. governance/freeze.toml sets baseline = "HEAD", so
validate_freeze.py compares each protected path against the *last commit*. An
authorized edit fails the gate until it is committed and passes ever after.
That makes it a change-detector, not a verification of the as-of claim. It will
report PASS across the entire reskin. So the freeze gate is what makes a change
visible; THIS is what proves the figures are intact.

Which means the extractor has to be committed and re-run unchanged. A Phase 6
re-capture from a differently-written script diffs the two scripts, not the two
renders. Do not "improve" the extraction between the before and after runs.

Usage:
    python src/capture_charts.py --label pre-reskin
    python src/capture_charts.py --label post-reskin
    python src/capture_charts.py --label post-reskin --diff pre-reskin

Writes to governance/reskin-baseline/<label>/. Exit 0 on a clean capture; with
--diff, exit 1 if any number moved.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import re
import socket
import socketserver
import sys
import threading
from pathlib import Path

# Same reason as validate_freeze.py: the Windows console defaults to cp1252 and
# these pages are full of en dashes and minus signs. Never let formatting
# decide the verdict.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PAGES = [
    "index.html",
    "margins.html",
    "peers.html",
    "q2-readthrough.html",
    "q2-filed.html",
]

# 1080px .wrap + 20px padding either side; the .chart-grid breakpoint is 760px,
# so 1280 renders the two-column design layout. 320 is MIN_CANVAS in the
# Cascadia ECharts theme and the width WCAG 1.4.10 (adopted by Rule 5.3) tests.
WIDTHS = [1280, 320]

# ECharts' default entry animation is 1000ms. Screenshot before it lands and the
# "comparison set" is a set of half-drawn charts that never compare equal.
SETTLE_MS = 1800

# Everything the page renders that carries a number, pulled from the live chart
# instances rather than from the source JSON — the point is to capture what a
# reader actually sees, including axis extents ECharts computed rather than the
# page declared.
EXTRACT_JS = r"""
() => {
  const out = { charts: [], tables: [], kpis: [], callouts: [], asof: null };
  const txt = (el) => (el ? el.textContent.replace(/\s+/g, " ").trim() : null);

  const asof = document.querySelector(".asof");
  if (asof) out.asof = txt(asof);

  document.querySelectorAll(".callouts li").forEach((li) => {
    out.callouts.push(txt(li));
  });

  document.querySelectorAll(".kpi").forEach((k) => {
    out.kpis.push({
      label: txt(k.querySelector(".label")),
      value: txt(k.querySelector(".value")),
      chips: Array.from(k.querySelectorAll(".chip")).map(txt),
      foot: txt(k.querySelector(".foot")),
    });
  });

  document.querySelectorAll("table").forEach((t) => {
    out.tables.push({
      id: t.id || null,
      rows: Array.from(t.rows).map((r) => Array.from(r.cells).map(txt)),
    });
  });

  // Axis labels as ECharts actually laid them out. This is the "axis extents"
  // half of the fixture: a canvas chart has no text in the DOM, so the option
  // alone would not catch a y-axis that silently rescaled.
  const axisInfo = (chart, dim) => {
    const res = [];
    for (let i = 0; ; i++) {
      let comp;
      try { comp = chart.getModel().getComponent(dim, i); } catch (e) { break; }
      if (!comp) break;
      const axis = comp.axis;
      const entry = { index: i, type: axis.type };
      try { entry.extent = axis.scale.getExtent(); } catch (e) {}
      try {
        entry.labels = axis.getViewLabels().map((l) => l.formattedLabel);
      } catch (e) {}
      res.push(entry);
    }
    return res;
  };

  const seriesInfo = (s) => ({
    name: s.name ?? null,
    type: s.type ?? null,
    data: s.data ?? null,
    markLine: s.markLine ? s.markLine.data : null,
    markPoint: s.markPoint ? s.markPoint.data : null,
  });

  const haveECharts = typeof echarts !== "undefined";
  document.querySelectorAll("div").forEach((el) => {
    const chart = haveECharts ? echarts.getInstanceByDom(el) : null;
    const svg = el.querySelector(":scope > svg");
    // A chart container is either an ECharts instance or, on q2-filed.html, a
    // div holding hand-rolled SVG. Skip plain layout divs.
    if (!chart && !(svg && el.id)) return;

    const entry = { id: el.id || null, echarts: !!chart };

    if (chart) {
      const opt = chart.getOption();
      entry.series = (opt.series || []).map(seriesInfo);
      entry.xAxis = axisInfo(chart, "xAxis");
      entry.yAxis = axisInfo(chart, "yAxis");
      entry.title = (opt.title || []).map((t) => ({
        text: t.text ?? null, subtext: t.subtext ?? null,
      }));
    }

    // Every rendered glyph, in document order. Covers the SVG-renderer page and
    // the hand-rolled SVG, and is the most direct possible reading of "the
    // number on the page did not move."
    const svgText = Array.from(el.querySelectorAll("text"))
      .map((t) => t.textContent.replace(/\s+/g, " ").trim())
      .filter((s) => s.length);
    if (svgText.length) entry.svgText = svgText;

    out.charts.push(entry);
  });

  out.charts.sort((a, b) => String(a.id).localeCompare(String(b.id)));
  return out;
}
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(docs: Path, port: int) -> socketserver.TCPServer:
    """A static server over docs/.

    file:// would mostly work — the pages inline their data and make no SEC
    calls at runtime — but http keeps the ECharts CDN tag and any relative
    fetch behaving exactly as they do on GitHub Pages.
    """
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):  # one request line per page is noise
            pass

    handler = functools.partial(Quiet, directory=str(docs))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def capture(root: Path, out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    port = free_port()
    httpd = serve(root / "docs", port)
    fixture: dict = {}
    shots = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in WIDTHS:
                shot_dir = out / f"w{width}"
                shot_dir.mkdir(parents=True, exist_ok=True)
                ctx = browser.new_context(
                    viewport={"width": width, "height": 2400},
                    device_scale_factor=2,
                )
                page = ctx.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                for name in PAGES:
                    page.goto(f"http://127.0.0.1:{port}/{name}",
                              wait_until="networkidle")
                    page.wait_for_timeout(SETTLE_MS)
                    data = page.evaluate(EXTRACT_JS)
                    fixture.setdefault(name, {})[f"w{width}"] = data

                    for chart in data["charts"]:
                        cid = chart["id"]
                        if not cid:
                            continue
                        el = page.query_selector(f"#{cid}")
                        if el is None:
                            continue
                        stem = name.replace(".html", "")
                        el.screenshot(path=str(shot_dir / f"{stem}__{cid}.png"))
                        shots += 1

                    print(f"  w{width:<5} {name:<22} "
                          f"{len(data['charts'])} charts, "
                          f"{len(data['tables'])} tables, "
                          f"{len(data['kpis'])} KPIs")
                if errors:
                    # A page that threw is a page whose charts may be missing
                    # from the fixture entirely — which would then "match" on a
                    # re-capture that also fails. Never let that pass quietly.
                    raise SystemExit(
                        f"page errors at w{width}: {errors}"
                    )
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()

    print(f"\n  {shots} chart renders written under {out}")
    return fixture


# A fixture line reads `path = json-value`. A delta counts as a colour change
# only if the path ends in a key that carries a colour AND the value is a hex
# or rgb string. Both halves are required: `label.color = "#5b6660"` is a
# restyle, but a `color` key holding anything else is not something to wave
# through, and no other key is.
_COLOUR_KEY = re.compile(r"\.(color|borderColor|backgroundColor|textBorderColor"
                         r"|shadowColor|areaColor)$")
_COLOUR_VALUE = re.compile(r'^"(#[0-9a-fA-F]{3,8}|rgba?\([^"]*\))"$')


def is_colour_change(line: str) -> bool:
    path, sep, value = line.partition(" = ")
    if not sep:
        return False
    return bool(_COLOUR_KEY.search(path) and _COLOUR_VALUE.match(value.strip()))


def flatten(fixture: dict) -> list[str]:
    """The fixture as sorted `path = value` lines.

    A JSON diff of nested option objects is unreadable at 3am. This is the form
    a human can scan and a reviewer can paste into a report.
    """
    lines: list[str] = []

    def walk(prefix: str, node) -> None:
        if isinstance(node, dict):
            for k in sorted(node, key=str):
                walk(f"{prefix}.{k}", node[k])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(f"{prefix}[{i}]", v)
        else:
            lines.append(f"{prefix} = {json.dumps(node, ensure_ascii=False)}")

    for page in sorted(fixture):
        walk(page, fixture[page])
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Render charts and capture numbers.")
    ap.add_argument("--label", default="pre-reskin", help="capture directory name")
    ap.add_argument("--diff", default=None, help="compare against an earlier label")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    base = root / "governance" / "reskin-baseline"
    out = base / args.label
    out.mkdir(parents=True, exist_ok=True)

    print(f"Capturing {len(PAGES)} pages at widths {WIDTHS} -> {args.label}\n")
    fixture = capture(root, out)

    lines = flatten(fixture)
    (out / "numeric-fixture.json").write_text(
        json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    (out / "numeric-fixture.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n",
    )
    n_charts = sum(len(w["charts"])
                   for p in fixture.values() for w in p.values()) // len(WIDTHS)
    print(f"  {len(lines)} numeric facts across {n_charts} charts\n")

    if args.diff:
        prior = base / args.diff / "numeric-fixture.txt"
        if not prior.exists():
            sys.exit(f"no fixture to diff against at {prior}")
        before = set(prior.read_text(encoding="utf-8").splitlines())
        after = set(lines)
        delta = sorted(before ^ after)

        # A reskin changes colours by definition, and peers.html carries
        # itemStyle.color INSIDE series.data — so a palette swap shows up as a
        # data delta. Reporting that as a numeric defect makes the gate cry
        # wolf on every phase, and a gate nobody believes is worse than none.
        #
        # This classifies; it does not suppress. Both counts are always
        # printed, and the test is deliberately narrow — a known colour key
        # AND a hex or rgb() value. Anything else, including a colour key
        # holding something that is not a colour, counts as a numeric defect.
        # Widen this only with a reason.
        #
        # Note this is the REPORTING half of the tool. EXTRACT_JS and flatten()
        # are untouched, so a fixture captured before this change still
        # compares against one captured after it.
        colour_delta = [d for d in delta if is_colour_change(d)]
        numeric_delta = [d for d in delta if not is_colour_change(d)]

        print(f"DIFF vs {args.diff}: {len(after)} facts, "
              f"{len(colour_delta)} colour deltas, "
              f"{len(numeric_delta)} numeric deltas")

        if numeric_delta:
            print(f"\nNUMERIC DELTA — {len(numeric_delta)} lines:")
            for line in numeric_delta[:60]:
                print(f"  {'-' if line in before else '+'} {line}")
            print("\nAny delta here is a defect, not a finding.")
            return 1
        print("\nNo number moved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

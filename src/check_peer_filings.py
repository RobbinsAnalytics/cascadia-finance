#!/usr/bin/env python3
"""check_peer_filings.py — has the T&M peer set filed calendar-Q2 2026 yet?

Read-only. Touches nothing, writes nothing, ingests nothing. Its whole job is
to answer one question so a build is started on the right day rather than
attempted repeatedly and abandoned.

Why it exists: `peers.html` deliberately holds at the last quarter **every**
peer has filed. Same-quarter comparability is a hard module rule — showing one
peer's newer quarter beside another's older one because it filed first is a
defect, not freshness. So the Q2 peer panel is not buildable until the whole
set has filed, and "have they?" is a question worth asking on a schedule
instead of by hand.

Peers are resolved from the COMMITTED ticker map, the same as ingest_peers.py,
so this cannot drift from the peer set the module actually uses. SEC etiquette
is unchanged: declared User-Agent, throttled well under the published limits.

    python src/check_peer_filings.py            # calendar Q2 2026
    python src/check_peer_filings.py --after 2026-06-01 --before 2026-07-15

Exit 0 when the full core set has filed (the panel is buildable), 1 when it has
not. The exit code is the signal; the printed table is the explanation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
TICKER_MAP = REPO_ROOT / "data" / "raw" / "company_tickers.json"

# The comparison set. KLAC is carried as a process-control margin reference,
# not a probe-card peer, so it does not gate the build — reported, not required.
CORE_PEERS = ["TER", "ONTO", "CAMT", "COHU", "INTT"]
REFERENCE = ["KLAC"]
SUBJECT = "FORM"

USER_AGENT = "RobbinsAnalytics cascadia-semiconductors ajayrobbins@hotmail.com"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:0>10}.json"
THROTTLE_SECONDS = 0.25


def fetch(url: str, tries: int = 3) -> dict:
    for attempt in range(tries):
        if attempt:
            time.sleep(2 ** attempt)
        time.sleep(THROTTLE_SECONDS)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:                      # noqa: BLE001
            if attempt == tries - 1:
                raise RuntimeError(f"{url}: {exc}") from exc
    raise RuntimeError("unreachable")


def ciks() -> dict[str, int]:
    """Resolve tickers to CIKs from the committed map — never a live lookup."""
    raw = json.loads(TICKER_MAP.read_text(encoding="utf-8"))
    rows = raw.values() if isinstance(raw, dict) else raw
    by_ticker = {r["ticker"].upper(): int(r["cik_str"]) for r in rows}
    wanted = CORE_PEERS + REFERENCE + [SUBJECT]
    missing = [t for t in wanted if t not in by_ticker]
    if missing:
        sys.exit(f"ticker(s) absent from the committed map: {', '.join(missing)}")
    return {t: by_ticker[t] for t in wanted}


def latest_10q(cik: int, after: str, before: str) -> tuple[str, str, str] | None:
    """The most recent 10-Q whose PERIOD (not filing date) falls in the window.

    Matching on reportDate is what makes this a comparability check rather than
    a recency check: a 10-Q filed last week for a quarter ending in March is
    not the quarter being asked about.
    """
    recent = fetch(SUBMISSIONS_URL.format(cik=cik))["filings"]["recent"]
    hits = [
        (recent["reportDate"][i], recent["filingDate"][i], recent["accessionNumber"][i])
        for i in range(len(recent["form"]))
        if recent["form"][i] == "10-Q" and after <= recent["reportDate"][i] <= before
    ]
    return max(hits) if hits else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Has the T&M peer set filed the quarter?")
    ap.add_argument("--after", default="2026-05-15", help="earliest period end (inclusive)")
    ap.add_argument("--before", default="2026-07-31", help="latest period end (inclusive)")
    args = ap.parse_args()

    resolved = ciks()
    print(f"Calendar-Q2 2026 10-Q check — periods ending {args.after} .. {args.before}")
    print(f"Run {date.today().isoformat()}\n")

    filed, waiting = [], []
    for ticker, cik in resolved.items():
        role = "subject" if ticker == SUBJECT else ("reference" if ticker in REFERENCE else "peer")
        try:
            hit = latest_10q(cik, args.after, args.before)
        except RuntimeError as exc:
            print(f"  {ticker:5} {role:9} ERROR — {exc}")
            if ticker in CORE_PEERS:
                waiting.append(ticker)
            continue
        if hit:
            period, filed_on, accession = hit
            print(f"  {ticker:5} {role:9} FILED    period {period}  filed {filed_on}  {accession}")
            filed.append(ticker)
        else:
            print(f"  {ticker:5} {role:9} waiting  no 10-Q for a period in range")
            if ticker in CORE_PEERS:
                waiting.append(ticker)

    core_done = [t for t in CORE_PEERS if t in filed]
    print(f"\nCore peer set: {len(core_done)}/{len(CORE_PEERS)} filed "
          f"({', '.join(core_done) or 'none'})")

    if waiting:
        print(f"Still waiting on: {', '.join(waiting)}")
        print("\nNOT BUILDABLE — peers.html holds at the last quarter every peer has filed.")
        return 1

    print("\nBUILDABLE — the full core peer set has filed this quarter.")
    print("Next: the additive freeze-extension pattern (cascadia-module-build skill).")
    print("Phases 1-3 stay frozen at 2026-07-21; the panel is new files only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

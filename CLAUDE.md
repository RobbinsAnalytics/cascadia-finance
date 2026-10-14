# Cascadia Finance — what an agent needs to know

FormFactor (NASDAQ: FORM) GAAP financials built from committed SEC EDGAR XBRL,
published as static HTML from `docs/` to
`www.robbinsanalytics.com/cascadia-finance/`.

Facts that are not inferable from the code, each of which has already cost
something. Everything else, read `README.md`.

## The freeze

**The data is frozen as-of 2026-07-21, and that date is a claim Aaron makes out
loud in interviews.** Treat it as sacred. Advancing it is his decision, never a
side effect of a build.

**`python src/ingest.py` re-pulls `companyfacts` and overwrites the freeze.**
Running it destroys the snapshot that makes every announced-vs-filed comparison
computable — the earlier figures have to still exist, exactly as published, to
be compared against. Only run it to deliberately refresh the dataset.

**`src/build_pages.py` rewrites `index.html`, `margins.html` and `peers.html`
together.** Never invoke it unscoped during an extension; it will rebuild
frozen pages as a side effect of touching one.

**`governance/freeze.toml` is the authoritative protected-path list.** It is
read by `src/validate_freeze.py` *and* by check 5 of `src/validate_q2_filed.py`,
so there is exactly one answer to "what is frozen?" Two copies of that list is
how they drift apart unnoticed; that is why the hardcoded `frozen_paths()` was
removed. **Do not restate the count here** — this line said "18 paths" while the
file resolved to 19, because the patterns glob and a Q2 `companyfacts_*.json`
landed inside one of them without touching this sentence. Both gates print the
number they actually checked; read it there.

**`src/validate.py` is itself a protected path.** Freezing only the data left
the obvious hole: a build that weakens a check reports PASS against a check that
has stopped testing anything. Changing a check is a declared `permitted_edit`,
not an ordinary commit.

**Edits to frozen pages are authorized one at a time, and only non-numeric
ones.** Two have been authorized so far: the `q2-readthrough.html` cross-link
(commit `4127468`) and the 2026-08-05 back-navigation kicker across all five
reports. Both are recorded with their reasoning at the bottom of
`governance/freeze.toml`. The announced figures on `q2-readthrough.html` are
the other half of the reconciliation — nothing numeric on any frozen page
changes without Aaron deciding to advance the freeze itself.

## Publishing

**Both gates must pass, and both exit non-zero on failure:**

```bash
python src/validate_q2_filed.py    # domain: presence, crossfoot, tie-out, coverage
python src/validate_freeze.py      # freeze integrity
```

If either fails: **publish nothing, commit nothing.** Report which checks
failed and what the values were. A failed financial dataset must never reach a
live page.

**GitHub Pages serves `docs/` from `main`. Pushing `main` is the deploy.**
There is no build step and no Action here — what is committed is what is
served.

**Surface new pages on the website repo too** (`RobbinsAnalytics.github.io`):
the case study at `projects/cascadia-finance.qmd` and the Finance card
on `index.qmd`. Publish that repo with its own `/publish` skill, from a session
rooted in it.

## Committing

**Stage by name — never blanket-stage the tree.** What enforces this is the
`PreToolUse` hook `.claude/hooks/no_blanket_add_or_force_push.py`, not the
`deny` block in `.claude/settings.json`. **The deny block does not bind here:**
this surface runs in `bypassPermissions` deliberately, and that skips the
permission layer entirely — measured against `cascadia-curiosities`, where a
blanket stage *and* a force push both ran to completion with the deny block in
place. A `PreToolUse` hook is run by Claude Code itself, so it binds regardless
of mode. The deny block stays where it is: it costs nothing and binds again if
the mode ever changes. The same hook refuses force pushes, `--force-with-lease`
included.

**That hook inspects the command string, so it is deliberately coarse.** A
command that merely *quotes* one of the refused patterns is refused too —
writing documentation about them from a heredoc, for one. Use the Write or Edit
tool for such content rather than a shell heredoc.

**Line-ending churn on frozen data is not cosmetic.** CRLF rewrites once showed
30 files as modified including `data/raw/` and `data/conformed/` — which *are*
the freeze. It makes "the snapshot is untouched" impossible to assert.
`.gitattributes` (`* text=auto eol=lf`) prevents it; `.githooks/` catches what
gets through and refuses the commit.

**The whitespace check is a git `pre-commit` hook, not a `PreToolUse` one, and
the move was the point.** A `PreToolUse` hook is handed the index as it stood
*before* the tool call runs, so staging and committing inside a single call
passed a check that had already inspected the index. It was not wrong; it was
early. A git hook runs after the index is final and no command shape outruns it.

**A fresh clone has no gate until it is activated.** The scripts are tracked and
arrive with the repo; the config line does not. Run once per clone:

```bash
git config core.hooksPath .githooks
```

**`.githooks/pre-commit` runs two gates** — `no_whitespace_commits.py` and
`secret_scan.py`. Do not reach for `--no-verify`; that is how a gate stops
working.

**Run each repo's commits from a session rooted in that repo.** Hooks and this
file load only from the primary working directory — `/add-dir` shares files and
skills but never hooks.

## Extending

The pattern is the shared `cascadia-module-build` skill; the concrete runbook
for the last extension is `.claude/skills/q2-filed-build/SKILL.md`. New periods
are **additive**: new ingest, new conformed file, new page, own manifest with
its own actual retrieval date. Nothing existing is re-pulled or re-stamped.

`src/validate_freeze.py` is copied verbatim from
`cascadia-standards/templates/validate_freeze.py` and prints its template
version on every run; read it there rather than here. Never edit it here —
module-specific behaviour belongs in `governance/freeze.toml`. Since template
v1.1.0 (2026-10-14) it resolves protected patterns against git — the baseline
tree, the index and untracked paths — not the filesystem, so an untracked file
under a protected pattern fails the gate.

## Content

**Canonical domain is `https://www.robbinsanalytics.com`.** The `github.io`
address still resolves and redirects but must not appear in new source.

**Pages inline their data at build time.** No SEC calls at runtime — the site
works offline and forever. Do not add a CDN dependency for a chart library.

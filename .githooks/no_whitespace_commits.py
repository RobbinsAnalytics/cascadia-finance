#!/usr/bin/env python3
"""Git pre-commit hook — refuse commits that stage line-ending-only changes.

    cascadia-standards template v2.0.0
    Copied verbatim into each repo's .githooks/. Do not edit per repo.

Windows tooling rewrites files with CRLF, and they then show as modified when
nothing about them changed. In the website repo five files did this chronically
and one session nearly committed 440 lines of pure noise. In a data module it
is worse than noise: line-ending churn on the frozen snapshot makes "the freeze
is untouched" impossible to assert, and fails the freeze gate for a reason that
has nothing to do with the data.

This makes the check structural instead of remembered.

WHAT CHANGED IN v2.0.0, AND WHY IT IS A MOVE RATHER THAN A REWRITE

v1.0.0 was a Claude Code `PreToolUse` hook in `.claude/hooks/`. The logic below
is unchanged from it. What changed is *when* it runs, and that was the whole
defect: a PreToolUse hook is handed the index as it stood **before** the tool
call executes, so

    git add noisy.md && git commit -m "..."

staged and committed inside a single call the hook had already inspected, and
passed. The check was not wrong; it was early.

Teaching the old hook to read the command string was the rejected alternative.
It keeps the check fail-open by construction — `;`, `&&`, a heredoc, `bash -c`
or a shell function each defeat the next version of the parser, and every one
of those defeats is silent. A pre-commit hook runs after the index is final.
There is no command shape that outruns it.

The cost, stated: **the activation does not travel with a clone.** The script
is tracked and arrives with the repo; `core.hooksPath = .githooks` does not,
so a fresh clone has no gate until it is set. That is the same trade
`job-search`'s secret scan already makes in this estate, and it is why the
config line belongs in the starter kit's setup step rather than in a comment.

FAILURE POSTURE

Fails CLOSED. No interpreter, an unreadable index, or any internal exception
blocks the commit rather than waving it through. A gate that opens when it
breaks is not a gate. The v1.0.0 hook returned 0 on a JSON parse error, which
was the right posture for an advisory layer and the wrong one for this.

A staged file is noise when it has a diff normally and no diff under
--ignore-all-space. Binary files report "-" for both counts and are never
flagged. New files are never flagged: their content is all addition.

The companion control is `.gitattributes` declaring `* text=auto eol=lf`, which
prevents the churn rather than catching it. Ship both.
"""

import subprocess
import sys


def git(*args):
    """Run a git command. Raises on failure — this hook fails closed."""
    r = subprocess.run(("git",) + args, capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(
            "git %s failed (exit %d): %s" % (" ".join(args), r.returncode, r.stderr.strip())
        )
    return r.stdout.strip()


def find_noise():
    staged = [f for f in git("diff", "--cached", "--name-only").splitlines() if f]
    noise = []
    for f in staged:
        # Added files have no HEAD version to compare against — never noise.
        status = git("diff", "--cached", "--name-status", "--", f)
        if status.startswith("A"):
            continue
        raw = git("diff", "--cached", "--numstat", "--", f)
        if not raw:
            continue
        # Binary: numstat reports "-\t-\tpath". Always a real change.
        if raw.split("\t")[0] == "-":
            continue
        if not git("diff", "--cached", "--ignore-all-space", "--numstat", "--", f):
            noise.append(f)
    return noise


def main():
    try:
        noise = find_noise()
    except Exception as exc:                      # noqa: BLE001 — fail closed
        sys.stderr.write(
            "\nCOMMIT BLOCKED — the whitespace check could not complete.\n\n"
            "    %s\n\n"
            "This blocks rather than passes, by design. Fix the cause, or use\n"
            "`git commit --no-verify` deliberately and say why in the message.\n\n" % exc
        )
        return 1

    if not noise:
        return 0

    listing = "\n".join("    %s" % f for f in noise)
    sys.stderr.write(
        "\nCOMMIT BLOCKED — these staged files have line-ending-only diffs and\n"
        "no real changes.\n\n"
        "%s\n\n"
        "Committing them adds hundreds of lines of noise that bury the actual\n"
        "change and make every future diff harder to read.\n\n"
        "Unstage them and commit again:\n"
        "    git restore --staged %s\n\n"
        "If one of these genuinely changed, the check is wrong — verify with\n"
        "`git diff --cached --ignore-all-space -- <file>` before overriding.\n\n"
        % (listing, " ".join(noise))
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())

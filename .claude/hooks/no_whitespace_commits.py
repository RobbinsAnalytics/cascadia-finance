#!/usr/bin/env python3
"""PreToolUse hook — refuse commits that stage line-ending-only changes.

    cascadia-standards template v1.0.0
    Copied verbatim into each repo's .claude/hooks/. Do not edit per repo.

Windows tooling rewrites files with CRLF, and they then show as modified when
nothing about them changed. In the website repo five files did this chronically
and one session nearly committed 440 lines of pure noise. In a data module it
is worse than noise: line-ending churn on the frozen snapshot makes "the freeze
is untouched" impossible to assert, and fails the freeze gate for a reason that
has nothing to do with the data.

This makes the check structural instead of remembered.

A staged file is noise when it has a diff normally and no diff under
--ignore-all-space. Binary files report "-" for both counts and are never
flagged. New files are never flagged: their content is all addition.

Python rather than bash so it runs the same on Windows without needing jq or a
POSIX shell, which is where the ThinkCentre actually lives.

Wire it up in .claude/settings.json as a PreToolUse hook with matcher "Bash".
To bypass deliberately: `git commit --no-verify` is NOT enough — this runs
before git does. Unstage the file instead.

The companion control is `.gitattributes` declaring `* text=auto eol=lf`, which
prevents the churn rather than catching it. Ship both.
"""

import json
import subprocess
import sys


def git(*args):
    """Run a git command, returning stdout or '' on failure."""
    try:
        r = subprocess.run(("git",) + args, capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def deny(reason):
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)
    sys.stdout.write("\n")
    sys.exit(2)


def main():
    # The matcher should already scope this to git commit, but a hook that only
    # works when the matcher is right is a hook with two failure modes.
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    if "git commit" not in cmd:
        return 0

    staged = [f for f in git("diff", "--cached", "--name-only").splitlines() if f]
    if not staged:
        return 0

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

    if noise:
        listing = "\n".join(f"    {f}" for f in noise)
        deny(
            "Commit refused: these staged files have line-ending-only diffs and "
            "no real changes.\n\n"
            f"{listing}\n\n"
            "Committing them adds hundreds of lines of noise that bury the "
            "actual change and make every future diff harder to read.\n\n"
            "Unstage them and commit again:\n"
            f"    git restore --staged {' '.join(noise)}\n\n"
            "If one of these genuinely changed, the check is wrong — verify with "
            "`git diff --cached --ignore-all-space -- <file>` before overriding."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

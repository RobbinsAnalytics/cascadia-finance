#!/usr/bin/env python3
"""PreToolUse hook — refuse blanket staging and force pushes.

    cascadia-standards template v1.0.0
    Copied verbatim into each repo's .claude/hooks/. Do not edit per repo.

These five rules already exist in .claude/settings.json as a permissions
"deny" block. That block is not load-bearing here: the desktop Code surface
runs in bypassPermissions deliberately, so an unattended run does not stall
waiting on a human, and bypassPermissions skips the permission layer
entirely. The rules the repo defines were therefore unenforced in the repo
that defines them.

PreToolUse hooks are run by Claude Code itself rather than by the permission
layer, so they bind regardless of mode. That was verified on this machine
before this file was written, not assumed: a minimal version of this hook
refused a blanket stage under bypassPermissions, and git never ran.

The settings.json deny block stays where it is. It costs nothing and binds
again if the mode ever changes. Two independent controls, one of which is
active at any given time.

WHY THESE FIVE

Blanket staging stages whatever happens to be in the tree. In this estate
that is never what is wanted: work sits half-finished in the working tree
for days at a time by design — the open item 20 disposition alone specifies
two commits in a particular order across three files — and a blanket stage
silently folds unrelated work into someone else's commit. Staging by name is
the house rule. This makes it structural rather than remembered.

Force pushing rewrites published history. The module repos are consumed by
other repos and by the site; a rewritten main is not recoverable from a
clone that already fetched it.

--force-with-lease is refused too. It is safer than a bare --force but it is
still a force push, and the reason to refuse is the rewrite, not the race.

Python rather than bash so it runs the same on Windows without needing jq or
a POSIX shell, which is where the ThinkCentre actually lives.

Wire it up in .claude/settings.json as a PreToolUse hook with matcher "Bash",
alongside no_whitespace_commits.py.

KNOWN COARSENESS: the command string is inspected, so a command that merely
quotes one of these patterns — writing this file from a heredoc, for one —
is refused too. That happened while building this hook. It is the safe
direction to be wrong in, and it is the same tradeoff
no_whitespace_commits.py makes. Use the Write tool for such content.
"""

import json
import re
import sys

# A leading `git` may carry its own options (-C <path>, -c k=v) before the
# subcommand, which is how these get invoked from a session rooted elsewhere.
_GIT = r"\bgit\s+(?:-[cC]\s+\S+\s+|--\S+\s+)*"

# Each rule: (name, compiled pattern, what to do instead).
RULES = (
    (
        "git add -A",
        re.compile(_GIT + r"add\b[^\n]*?\s(?:-A|--all)\b"),
        "Stage the files you mean, by name:\n    git add path/to/file.md",
    ),
    (
        "git add .",
        # `.` as a whole pathspec only. `git add ./docs/x.md` names a file
        # and is fine — the lookahead requires the dot to end the token.
        re.compile(_GIT + r"add\b(?:\s+-{1,2}\S+)*\s+(?:--\s+)?\.(?=\s|$)"),
        "Stage the files you mean, by name:\n    git add path/to/file.md",
    ),
    (
        "git push --force",
        re.compile(_GIT + r"push\b[^\n]*?\s--force(?:-with-lease|-if-includes)?\b"),
        "Do not rewrite published history. If a bad commit is already pushed,\n"
        "add a commit that corrects it, or ask Aaron before rewriting.",
    ),
    (
        "git push -f",
        re.compile(_GIT + r"push\b[^\n]*?\s-f\b"),
        "Do not rewrite published history. If a bad commit is already pushed,\n"
        "add a commit that corrects it, or ask Aaron before rewriting.",
    ),
)

# Shell separators. Splitting on these keeps each command independent, so a
# `git push` in one segment cannot combine with a `-f` in the next.
SEGMENT = re.compile(r"&&|\|\||;|\||\n")


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
    # The matcher should already scope this to Bash, but a hook that only
    # works when the matcher is right is a hook with two failure modes.
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    if "git" not in cmd:
        return 0

    for segment in SEGMENT.split(cmd):
        for name, pattern, remedy in RULES:
            if pattern.search(segment):
                deny(
                    f"Refused by rule: {name}\n\n"
                    f"    {segment.strip()}\n\n"
                    f"{remedy}\n\n"
                    "This is a PreToolUse hook, not a permission rule, so it "
                    "binds under bypassPermissions. `--no-verify` does not "
                    "reach it — this runs before git does."
                )
    return 0


if __name__ == "__main__":
    sys.exit(main())

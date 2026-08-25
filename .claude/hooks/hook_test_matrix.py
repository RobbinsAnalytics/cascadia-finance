#!/usr/bin/env python3
"""Runnable test matrix for this repo's two commit guards.

    cascadia-standards template v2.0.0
    Copied verbatim into each repo. Do not edit per repo.

Run it:

    python .claude/hooks/hook_test_matrix.py

Exit 0 if every case behaves as declared, 1 otherwise, with the failures
listed. It mutates nothing outside a temporary directory it creates and
deletes, and it never touches the repo it is run from.

WHY THIS EXISTS

The guards were verified once, by hand, in the session that wrote them. That
verification survived only in a session report, which is not a thing anyone can
re-run after editing a regex. Behaviour asserted in prose rots the first time
its pattern is touched.

The declared behaviour is the point. Each row states a command and whether it
must be allowed or refused, so the file reads as a specification and executes
as a check. **The negative controls matter as much as the refusals** — a guard
that refused `git add docs/README.md` would be worse than no guard, because the
house rule it enforces is "stage by name" and that is staging by name.

TWO GUARDS, TWO SURFACES, AND THE SPLIT IS DELIBERATE

  .claude/hooks/no_blanket_add_or_force_push.py   PreToolUse hook
      Inspects the command string. That is the right surface for it: the thing
      being judged IS the command, and it must be judged before git runs.

  .githooks/no_whitespace_commits.py              git pre-commit hook
      Inspects the index. A PreToolUse hook cannot do this correctly, because
      it reads the index as it stood BEFORE the call, so `git add x && git
      commit` outran it. Moved 2026-08-24. The last section below proves the
      move end to end by driving a real commit.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BLANKET = os.path.join(HERE, "no_blanket_add_or_force_push.py")
GITHOOKS = os.path.join(REPO, ".githooks")
WHITESPACE = os.path.join(GITHOOKS, "no_whitespace_commits.py")

ALLOW, DENY = "allow", "refuse"


def run_pretooluse(script, command, cwd=None):
    """Feed a PreToolUse hook the same JSON payload Claude Code sends."""
    payload = json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    })
    r = subprocess.run([sys.executable, script], input=payload,
                       capture_output=True, text=True, timeout=30, cwd=cwd)
    return DENY if r.returncode == 2 else ALLOW


def run_githook(cwd):
    """Run the pre-commit script the way git runs it: no stdin, exit != 0 blocks."""
    r = subprocess.run([sys.executable, WHITESPACE],
                       capture_output=True, text=True, timeout=30, cwd=cwd)
    return DENY if r.returncode != 0 else ALLOW


# ---------------------------------------------------------------------------
# no_blanket_add_or_force_push.py — pure string inspection, no repo state.
#
# Provenance: the ten refusals and seven negative controls below are the cases
# the 2026-08-18 pilot (6da609f) and the 2026-08-19 propagation (b1c2f52, in
# cascadia-curiosities) actually recorded. Everything after them is derived
# from the hook's own rules rather than from the record, because the record
# describes a "21-case payload matrix" and names only seventeen of its cases.
# ---------------------------------------------------------------------------

BLANKET_CASES = [
    # --- refused live in the pilot, five of five ---
    (DENY,  "git add -A",                          "pilot: blanket stage, short flag"),
    (DENY,  "git add .",                           "pilot: blanket stage, dot pathspec"),
    (DENY,  "git add . --verbose",                 "pilot: dot pathspec with a trailing flag"),
    (DENY,  "git push --force",                    "pilot: force push"),
    (DENY,  "git push -f",                         "pilot: force push, short flag"),

    # --- additionally caught by the pilot's payload matrix, five of five ---
    (DENY,  "git add --all",                       "pilot matrix: long form of -A"),
    (DENY,  "git add -A .",                        "pilot matrix: both blanket forms at once"),
    (DENY,  "git push --force-with-lease",         "pilot matrix: still a rewrite, still refused"),
    (DENY,  "git -C /c/Projects/other add -A",     "pilot matrix: git's own option before the subcommand"),
    (DENY,  "cd /tmp && git add -A",               "pilot matrix: blanket stage after a separator"),

    # --- the seven negative controls, verbatim from the pilot ---
    (ALLOW, "git add docs/README.md",              "control: staging by name is the house rule"),
    (ALLOW, "git add ./docs/standard/x.md",        "control: leading ./ is a path, not a blanket stage"),
    (ALLOW, "git add docs/v2.5.md",                "control: a dot inside a filename"),
    (ALLOW, "git push origin main",                "control: ordinary push"),
    (ALLOW, "git push -u origin main",             "control: ordinary push, upstream flag"),
    (ALLOW, "git diff -- .",                       "control: a dot pathspec on a read-only command"),
    (ALLOW, "git push origin main && ls -f",       "control: -f belongs to ls, in its own segment"),

    # --- derived from the hook's rules; not in the recorded set ---
    (DENY,  "git -c core.pager=cat add --all",     "derived: -c k=v before the subcommand"),
    (DENY,  "git push --force-if-includes",        "derived: third force spelling in the pattern"),
    (DENY,  "git add -- .",                        "derived: dot pathspec after the -- separator"),
    (DENY,  "git status; git add .",               "derived: semicolon separator"),
    (DENY,  "git status | grep x; git push -f",    "derived: pipe and semicolon in one command"),
    (DENY,  "git commit -m 'never git add -A'",    "derived: documented coarseness, a quoted pattern refuses"),
    (ALLOW, "ls -A",                               "derived: no 'git' in the command, hook returns early"),
    (ALLOW, "git add 'file with . in name.md'",    "derived: dot inside a quoted filename"),
    (ALLOW, "git restore --staged .",              "derived: restore is not add; blanket unstage is safe"),
]


# ---------------------------------------------------------------------------
# no_whitespace_commits.py — needs an index, so it runs against a throwaway
# repo. Aimed at a temporary directory rather than at this one, because the
# failure mode of a staging test is destructive.
# ---------------------------------------------------------------------------

def git(cwd, *args):
    return subprocess.run(("git",) + args, cwd=cwd, capture_output=True, text=True)


def build_scratch_repo(root):
    git(root, "init", "-q")
    git(root, "config", "user.email", "matrix@example.invalid")
    git(root, "config", "user.name", "Hook Matrix")
    git(root, "config", "core.autocrlf", "false")
    git(root, "config", "commit.gpgsign", "false")
    for name in ("noise.md", "real.md"):
        with open(os.path.join(root, name), "wb") as f:
            f.write(b"alpha\nbeta\ngamma\n")
    with open(os.path.join(root, "blob.bin"), "wb") as f:
        f.write(bytes(range(256)))
    git(root, "add", "noise.md", "real.md", "blob.bin")
    git(root, "commit", "-q", "-m", "baseline")


def whitespace_cases(root):
    def clean():
        git(root, "reset", "-q")
        git(root, "checkout", "-q", "--", ".")

    def crlf_only():
        clean()
        open(os.path.join(root, "noise.md"), "wb").write(b"alpha\r\nbeta\r\ngamma\r\n")
        git(root, "add", "noise.md")

    def real_change():
        clean()
        open(os.path.join(root, "real.md"), "wb").write(b"alpha\nbeta\ndelta\n")
        git(root, "add", "real.md")

    def new_file():
        clean()
        open(os.path.join(root, "added.md"), "wb").write(b"brand\r\nnew\r\n")
        git(root, "add", "added.md")

    def binary():
        clean()
        open(os.path.join(root, "blob.bin"), "wb").write(bytes(range(255, -1, -1)))
        git(root, "add", "blob.bin")

    def mixed():
        clean()
        open(os.path.join(root, "noise.md"), "wb").write(b"alpha\r\nbeta\r\ngamma\r\n")
        open(os.path.join(root, "real.md"), "wb").write(b"alpha\nbeta\ndelta\n")
        git(root, "add", "noise.md", "real.md")

    return [
        (DENY,  crlf_only,   "line-ending-only diff on a tracked file"),
        (ALLOW, real_change, "control: a real one-line change"),
        (ALLOW, new_file,    "control: a new file is all addition, never noise"),
        (ALLOW, binary,      "control: binary reports '-' for both counts"),
        (DENY,  mixed,       "one noisy file alongside a real one still refuses"),
        (ALLOW, clean,       "control: nothing staged, nothing to judge"),
    ]


def main():
    failures, rows = [], 0

    print("no_blanket_add_or_force_push.py   (PreToolUse, inspects the command)")
    print("-" * 82)
    for expected, cmd, note in BLANKET_CASES:
        rows += 1
        actual = run_pretooluse(BLANKET, cmd)
        ok = actual == expected
        print("  %s  %-6s  %-46s  %s" % ("ok  " if ok else "FAIL", expected, cmd, note))
        if not ok:
            failures.append("%r: expected %s, got %s" % (cmd, expected, actual))

    root = tempfile.mkdtemp(prefix="cascadia-hook-matrix-")
    try:
        build_scratch_repo(root)

        print()
        print("no_whitespace_commits.py   (git pre-commit, inspects the index)")
        print("-" * 82)
        for expected, setup, note in whitespace_cases(root):
            rows += 1
            setup()
            actual = run_githook(root)
            ok = actual == expected
            print("  %s  %-6s  %-46s  %s" % ("ok  " if ok else "FAIL", expected, "<staged index>", note))
            if not ok:
                failures.append("[%s]: expected %s, got %s" % (note, expected, actual))

        # --- fail-closed posture: no index to read at all ---
        rows += 1
        outside = tempfile.mkdtemp(prefix="cascadia-not-a-repo-")
        try:
            actual = run_githook(outside)
        finally:
            shutil.rmtree(outside, ignore_errors=True)
        ok = actual == DENY
        print("  %s  %-6s  %-46s  %s" % ("ok  " if ok else "FAIL", DENY, "<run outside any repo>",
                                         "fails CLOSED when it cannot read an index"))
        if not ok:
            failures.append("fail-closed posture: expected refuse, got %s" % actual)

        # --- end to end: the case the PreToolUse version could not catch ---
        print()
        print("end to end   (real commit, core.hooksPath active)")
        print("-" * 82)
        # Copy the guard into the scratch repo and activate it there, exactly
        # as a real clone would. Pointing core.hooksPath at this repo's
        # .githooks would not work and would not be the thing under test: the
        # pre-commit script resolves its python file against the toplevel of
        # the repo being committed to, so it must live inside that repo.
        shutil.copytree(GITHOOKS, os.path.join(root, ".githooks"))
        git(root, "config", "core.hooksPath", ".githooks")

        rows += 1
        git(root, "reset", "-q"); git(root, "checkout", "-q", "--", ".")
        open(os.path.join(root, "noise.md"), "wb").write(b"alpha\r\nbeta\r\ngamma\r\n")
        r = git(root, "add", "noise.md")
        r = git(root, "commit", "-m", "stage and commit in one breath")
        ok = r.returncode != 0
        print("  %s  %-6s  %-46s  %s" % ("ok  " if ok else "FAIL", DENY,
                                         "git add noise.md && git commit",
                                         "THE FIX: outran the PreToolUse hook, not this one"))
        if not ok:
            failures.append("end-to-end: a noisy stage-and-commit was NOT blocked")

        rows += 1
        git(root, "reset", "-q"); git(root, "checkout", "-q", "--", ".")
        open(os.path.join(root, "real.md"), "wb").write(b"alpha\nbeta\nepsilon\n")
        git(root, "add", "real.md")
        r = git(root, "commit", "-m", "a real change still commits")
        ok = r.returncode == 0
        print("  %s  %-6s  %-46s  %s" % ("ok  " if ok else "FAIL", ALLOW,
                                         "git add real.md && git commit",
                                         "control: the guard does not block real work"))
        if not ok:
            failures.append("end-to-end: a real change was blocked (%s)" % r.stderr.strip()[:120])
    finally:
        git(root, "reset", "-q", "--hard")
        shutil.rmtree(root, ignore_errors=True)

    print()
    print("-" * 82)
    if failures:
        print("%d of %d cases did not behave as declared:" % (len(failures), rows))
        for f in failures:
            print("  - %s" % f)
        return 1
    print("%d of %d cases behaved as declared." % (rows, rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())

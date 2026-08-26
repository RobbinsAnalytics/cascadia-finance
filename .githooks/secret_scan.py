#!/usr/bin/env python3
"""
Pre-commit secret scan -- the credential gate.

    cascadia-standards template v1.0.0
    THIS IS THE CANONICAL COPY. Copied verbatim into each repo's .githooks/.
    Do not edit per repo -- fix it here and re-sync outward.

WHAT THIS IS FOR
    This finds CREDENTIALS in staged content: API keys, tokens, private keys,
    connection strings. It blocks the commit if it finds one.

WHAT THIS IS NOT FOR
    It is NOT a PII scanner. It does not look for salary figures, employer
    contacts or application history. Where such content exists it is protected
    by the repository being private, not by this script. Do not extend it into
    a PII matcher --
    a scan that fires on ordinary content in this repo is a scan that gets
    bypassed, and then it protects nothing at all.

DESIGN
    Two tiers of rule, because a bare keyword matcher is useless here. This
    tree's resume theme talks about design "tokens" in prose, and a matcher
    that fires on the word alone cries wolf on day one.

      Tier 1 -- SHAPE rules. Provider-specific credential formats (AWS,
                GitHub, Slack, Stripe, ...). These are unambiguous, so they
                always fire and are not suppressed by the placeholder
                allowlist.
      Tier 2 -- ASSIGNMENT + ENTROPY. A credential-ish name assigned a quoted
                literal that is long and high-entropy. Prose never has this
                shape. Obvious placeholders are allowed through.

    Only ADDED lines in the staged diff are scanned. Existing history is not
    re-litigated on every commit.

ESCAPE HATCH
    Put the marker  pragma: allowlist secret  in a line's comment to exempt
    that line. Deliberate, greppable and reviewable -- unlike --no-verify.

FAILURE POSTURE
    Fails CLOSED. Any internal error blocks the commit rather than waving it
    through, because a gate that opens when it breaks is not a gate.
"""

import math
import re
import subprocess
import sys

ENTROPY_MIN = 3.2
PRAGMA = re.compile(r"pragma:\s*allowlist\s+secret", re.I)

# ---------------------------------------------------------------------------
# Tier 1 -- shape rules. Always fire. Not subject to the allowlist.
# ---------------------------------------------------------------------------
SHAPE_RULES = [
    (r"(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[0-9A-Z]{16}", "AWS access key ID"),
    (r"(?i)aws.{0,20}?(?:secret|private).{0,24}?[:=]\s*[\"'][0-9a-zA-Z/+]{40}[\"']",
     "AWS secret access key"),
    (r"gh[pousr]_[A-Za-z0-9]{36,}", "GitHub token"),
    (r"github_pat_[A-Za-z0-9_]{40,}", "GitHub fine-grained PAT"),
    (r"glpat-[A-Za-z0-9_\-]{20,}", "GitLab personal access token"),
    (r"xox[abprs]-[A-Za-z0-9-]{10,}", "Slack token"),
    (r"https://hooks\.slack\.com/services/T[A-Za-z0-9_/]{20,}", "Slack webhook URL"),
    (r"AIza[0-9A-Za-z_\-]{35}", "Google API key"),
    (r"ya29\.[0-9A-Za-z_\-]{20,}", "Google OAuth access token"),
    (r"sk-ant-[A-Za-z0-9_\-]{20,}", "Anthropic API key"),
    (r"sk-proj-[A-Za-z0-9_\-]{20,}", "OpenAI project key"),
    (r"(?<![A-Za-z0-9])sk-[A-Za-z0-9]{32,}", "OpenAI-style secret key"),
    (r"(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}", "Stripe key"),
    (r"SG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}", "SendGrid API key"),
    (r"(?i)\bAC[0-9a-f]{32}\b", "Twilio account SID"),
    (r"npm_[A-Za-z0-9]{36}", "npm access token"),
    (r"pypi-AgEIcHlwaS5vcmc[A-Za-z0-9_\-]{20,}", "PyPI upload token"),
    (r"dop_v1_[a-f0-9]{64}", "DigitalOcean personal access token"),
    (r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----",
     "private key block"),
    (r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
     "JSON Web Token"),
    (r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:@/]+:[^\s:@/]+@",
     "database URI with inline password"),
    (r"(?i)AccountName=[^;\s]+;AccountKey=[A-Za-z0-9+/=]{60,}",
     "Azure storage connection string"),
]

# ---------------------------------------------------------------------------
# Tier 2 -- assignment + entropy. Suppressed by the placeholder allowlist.
# ---------------------------------------------------------------------------
ASSIGNMENT = re.compile(
    r"(?i)\b("
    r"api[_-]?key|apikey|secret[_-]?key|secret|client[_-]?secret|"
    r"passwd|password|pwd|"
    r"auth[_-]?token|access[_-]?token|refresh[_-]?token|bearer[_-]?token|token|"
    r"private[_-]?key|credentials?|session[_-]?key|encryption[_-]?key"
    r")\b\s*[:=]{1,2}\s*[\"'`]([^\"'`\n]{16,})[\"'`]"
)

# Substrings that mark a value as an obvious non-secret. Tier 2 only.
PLACEHOLDER_MARKERS = (
    "example", "changeme", "change_me", "placeholder", "redacted", "dummy",
    "sample", "yourkey", "your_", "your-", "insert_", "todo", "fixme",
    "xxxx", "aaaa", "0000", "1234567890", "notreal", "fake", "test_value",
    "os.environ", "getenv", "process.env", "vault:", "secretsmanager",
)
PLACEHOLDER_SHAPES = (
    re.compile(r"[<>{}$]"),                 # <TOKEN>, {{token}}, ${TOKEN}
    re.compile(r"^%[sd]"),                  # %s / %d format slot
    re.compile(r"^[a-z][a-z0-9 _.\-]*$"),   # plain lowercase words / dotted path
    re.compile(r"^[A-Z][A-Z0-9_]*$"),       # SHOUTY_CONSTANT_NAME
    re.compile(r"^(.)\1+$"),                # a single repeated character
)


def shannon(s):
    """Shannon entropy in bits per character."""
    if not s:
        return 0.0
    total = len(s)
    return -sum(
        (n / total) * math.log2(n / total)
        for n in (s.count(c) for c in set(s))
    )


def is_placeholder(value):
    low = value.lower()
    if any(marker in low for marker in PLACEHOLDER_MARKERS):
        return True
    return any(shape.search(value) for shape in PLACEHOLDER_SHAPES)


def scan_line(text):
    """Return a list of (rule_name, evidence) for one added line."""
    if PRAGMA.search(text):
        return []
    hits = []
    for pattern, name in SHAPE_RULES:
        match = re.search(pattern, text)
        if match:
            hits.append((name, match.group(0)))
    for match in ASSIGNMENT.finditer(text):
        name, value = match.group(1), match.group(2)
        if is_placeholder(value) or shannon(value) < ENTROPY_MIN:
            continue
        hits.append(("high-entropy value assigned to '%s'" % name.lower(), value))
    return hits


def redact(evidence):
    """Never echo a full credential into a terminal or a log."""
    if len(evidence) <= 12:
        return evidence[:4] + "*" * (len(evidence) - 4)
    return "%s...%s  (%d chars)" % (evidence[:6], evidence[-4:], len(evidence))


def staged_added_lines():
    """Yield (path, lineno, text) for every added line in the staged diff."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--unified=0", "--no-color",
         "--diff-filter=ACMR"],
        capture_output=True, text=True, errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError("git diff --cached failed: %s" % result.stderr.strip())

    path, lineno = None, 0
    for raw in result.stdout.splitlines():
        if raw.startswith("+++ b/"):
            path, lineno = raw[6:], 0
        elif raw.startswith("+++ "):
            path, lineno = None, 0
        elif raw.startswith("Binary files"):
            path = None
        elif raw.startswith("@@"):
            match = re.match(r"@@ -\S+ \+(\d+)", raw)
            lineno = int(match.group(1)) if match else 0
        elif raw.startswith("+") and path is not None:
            yield path, lineno, raw[1:]
            lineno += 1


def main():
    findings = []
    for path, lineno, text in staged_added_lines():
        for name, evidence in scan_line(text):
            findings.append((path, lineno, name, evidence))

    if not findings:
        return 0

    write = sys.stderr.write
    write("\n")
    write("=" * 72 + "\n")
    write("  COMMIT BLOCKED -- pre-commit secret scan\n")
    write("=" * 72 + "\n")
    write("\n")
    write("  %d possible credential(s) found in staged content.\n" % len(findings))
    write("  A credential committed here can reach the remote, and anything\n")
    write("  that reaches a remote does not stay on this machine.\n")
    write("\n")
    for path, lineno, name, evidence in findings:
        write("  %s:%d\n" % (path, lineno))
        write("      rule     : %s\n" % name)
        write("      evidence : %s\n" % redact(evidence))
        write("\n")
    write("  WHAT TO DO\n")
    write("    1. Remove the credential from the file. Read it from the\n")
    write("       environment or a secret store instead.\n")
    write("    2. Unstage it:   git restore --staged <file>\n")
    write("    3. If this is a FALSE POSITIVE and you are certain, add the\n")
    write("       marker  pragma: allowlist secret  to that line's comment.\n")
    write("\n")
    write("  Do not reach for --no-verify. That is how the gate stops working.\n")
    write("=" * 72 + "\n")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail closed, deliberately
        sys.stderr.write(
            "\nCOMMIT BLOCKED -- the secret scan could not run: %s\n"
            "It blocks rather than passes, by design. Fix the scan.\n" % exc
        )
        sys.exit(1)

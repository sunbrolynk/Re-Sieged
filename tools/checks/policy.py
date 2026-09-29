#!/usr/bin/env python3
"""Re-Sieged repository policy checks.

One script, three callers, so the rules live in one place:

    Claude Code hooks  (.claude/settings.json)  -> claude-pretool, session-start
    Git hooks          (.githooks/)             -> staged, commit-msg, pre-push
    CI                 (.github/workflows/)     -> ci

Rules are described in docs/process/workflow.md. Rule IDs (H1, H2, ...) match
that document. Standard library only, so it runs unchanged on Linux, WSL,
Windows (Git for Windows) and GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Policy configuration
# --------------------------------------------------------------------------

# H1: file types that are proprietary game content (ADR-0002). Keep in sync
# with .gitignore; this list is the enforcement, .gitignore is the convenience.
FORBIDDEN_EXTENSIONS = {
    ".ds2res", ".ds2map", ".ds2world", ".ds2party", ".ds2save",
    ".dsres", ".dsmap", ".tank",
    ".exe", ".dll", ".asi", ".m3d", ".bik", ".iso",
    ".asp", ".prs", ".raw", ".sno", ".dds",
}

# H2: maximum size of any single committed file.
MAX_FILE_BYTES = 1_000_000

# H3: bulk-pasted game script/data heuristics. A few quoted lines in a
# research note are fine; many in one file suggests a pasted GAS/Skrit file.
GAS_BLOCK = re.compile(r"^\s*\[t:[A-Za-z_]+,\s*n:")
SKRIT_IDENT = re.compile(r"[A-Za-z0-9_]\$")
BULK_LINE_THRESHOLD = 15

# H4: directories whose files may be added but never changed afterwards.
IMMUTABLE_DIRS = ("docs/handoff/",)

# H5: commit subject format.
AREAS = ("Docs", "Research", "Decision", "Tools", "Repo", "Planning", "Process")
SUBJECT = re.compile(r"^(%s): \S.{0,70}$" % "|".join(AREAS))
SUBJECT_EXEMPT = re.compile(r"^(Merge |Revert \"|fixup! |squash! )")

# H6: branches nobody pushes to directly.
PROTECTED_BRANCHES = ("main",)

# H10: secrets. Patterns for common credential formats, plus file names that
# conventionally hold secrets. This file is exempt from content scanning
# because it necessarily contains the patterns themselves.
SECRET_PATTERNS = [
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[0-9a-zA-Z]{20,}")),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("credentials in URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s:@]+@")),
]
# key = "value" style assignments; the value must look random (has a digit and
# a lowercase letter) so identifiers like WE_MCP_SECTION_COMPLETED don't trip it.
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|passw(?:or)?d|token|access[_-]?key|auth)\b\s*[:=]\s*[\"']?([A-Za-z0-9/+_.=-]{16,})"
)
SECRET_FILENAMES = re.compile(
    r"(?i)(^|/)(\.env(\.(?!example$|sample$|template$)[^/]+)?|id_(rsa|dsa|ecdsa|ed25519)|"
    r"credentials\.json|\.netrc|\.pypirc|\.npmrc)$|\.(pem|key|pfx|p12|keystore|jks)$"
)

# H11: private terms (your real name, personal email, etc.). The list itself
# must never be committed, so it is read from outside the working tree:
#   local:  .git/info/resieged-private-terms   (one term per line)
#   CI:     the RESIEGED_PRIVATE_TERMS repository secret (newline/comma separated)
PRIVATE_TERMS_FILE = "info/resieged-private-terms"

# H12: personal filesystem paths, which leak OS user names.
PERSONAL_PATH = re.compile(
    r"(?i)\b[A-Z]:\\{1,2}Users\\{1,2}([^\\\s\"'`<>|]+)|/home/([^/\s\"'`<>]+)|/Users/([^/\s\"'`<>]+)"
)
# Generic placeholders, CI/cloud accounts, and the repository owner's already
# public GitHub handle.
ALLOWED_PATH_USERS = {
    "user", "users", "runner", "root", "public", "default", "username", "name",
    "you", "<you>", "<user>", "<username>", "$user", "%username%", "*", "...", "…",
    "sunbrolynk",
}

# H13: commit identities must not expose personal email addresses.
SAFE_EMAIL = re.compile(r"(?i)noreply|no-reply")

# Paths exempt from content scans (they define the patterns).
SCAN_EXEMPT = ("tools/checks/",)

ZERO_SHA = "0" * 40

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


class Report:
    """Collects errors (block) and warnings (inform) for one run."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, rule: str, msg: str) -> None:
        self.errors.append(f"[{rule}] {msg}")

    def warn(self, rule: str, msg: str) -> None:
        self.warnings.append(f"[{rule}] {msg}")

    def emit(self, stream=sys.stderr) -> int:
        for w in self.warnings:
            print(f"policy warning {w}", file=stream)
        for e in self.errors:
            print(f"policy BLOCKED {e}", file=stream)
        if self.errors:
            print(
                "See docs/process/workflow.md. If you believe a rule is wrong, "
                "raise it with the project lead rather than bypassing it.",
                file=stream,
            )
        return 1 if self.errors else 0


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel").strip())


def ext_of(path: str) -> str:
    return os.path.splitext(path.lower())[1]


def check_forbidden_type(path: str, report: Report) -> None:
    if ext_of(path) in FORBIDDEN_EXTENSIONS:
        report.error("H1", f"{path}: proprietary game file type is never committed (ADR-0002)")


def check_size(path: str, size: int, report: Report) -> None:
    if size > MAX_FILE_BYTES:
        report.error("H2", f"{path}: {size:,} bytes exceeds {MAX_FILE_BYTES:,}-byte limit")


def check_bulk_content(path: str, added_lines: list[str], report: Report) -> None:
    if path.startswith("tools/checks/"):
        return
    gas = sum(1 for line in added_lines if GAS_BLOCK.search(line))
    skrit = sum(1 for line in added_lines if SKRIT_IDENT.search(line))
    if gas >= BULK_LINE_THRESHOLD or skrit >= BULK_LINE_THRESHOLD:
        report.error(
            "H3",
            f"{path}: looks like bulk GAS/Skrit content ({gas} template headers, "
            f"{skrit} Skrit-style lines added). Quote minimally; summarize instead.",
        )


def load_private_terms() -> list[str]:
    """H11 terms from the per-clone file and/or the CI secret. Never printed."""
    terms: list[str] = []
    location = git("rev-parse", "--git-path", PRIVATE_TERMS_FILE, check=False).strip()
    if location and Path(location).is_file():
        terms += Path(location).read_text(encoding="utf-8", errors="replace").splitlines()
    terms += re.split(r"[\n,]", os.environ.get("RESIEGED_PRIVATE_TERMS", ""))
    cleaned = {t.strip().lower() for t in terms if t.strip() and not t.strip().startswith("#")}
    return sorted(t for t in cleaned if len(t) >= 3)


def scan_text(where: str, lines: list[str], report: Report, terms: list[str]) -> None:
    """H10 secrets, H11 private terms, H12 personal paths in some text lines."""
    exempt = where.startswith(SCAN_EXEMPT)
    location = where  # no line numbers: diff-added lines don't map to file lines
    for line in lines:
        if not exempt:
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    report.error("H10", f"{location}: possible {label}. Remove it and rotate the credential if it was real")
            m = SECRET_ASSIGNMENT.search(line)
            if m and re.search(r"\d", m.group(1)) and re.search(r"[a-z]", m.group(1)):
                report.error("H10", f"{location}: looks like a hard-coded secret value")
        lowered = line.lower()
        for index, term in enumerate(terms, 1):
            if term in lowered:
                # Never echo the term itself: CI logs are public.
                report.error("H11", f"{location}: contains private term #{index} from your private-terms list")
        if not exempt:
            for m in PERSONAL_PATH.finditer(line):
                name = next(g for g in m.groups() if g is not None)
                if name.lower() not in ALLOWED_PATH_USERS:
                    report.error("H12", f"{location}: personal path exposes an OS user name ({m.group(0)[:40]}); use a placeholder like C:\\Users\\<you>")


def check_secret_filename(path: str, report: Report) -> None:
    if SECRET_FILENAMES.search(path):
        report.error("H10", f"{path}: file type conventionally holds secrets and is never committed")


def check_identity(where: str, name: str, email: str, report: Report, terms: list[str]) -> None:
    """H13: author/committer identity must not expose a personal address."""
    if not SAFE_EMAIL.search(email):
        report.error(
            "H13",
            f"{where}: commit email is not a noreply address. Set "
            "`git config user.email <id>+<user>@users.noreply.github.com` (see docs/process/workflow.md)",
        )
    scan_text(f"{where} identity", [f"{name} <{email}>"], report, terms)


def scan_commit(sha: str, report: Report, terms: list[str]) -> None:
    """H10–H13 on one commit: identity, message, and every added line."""
    short = sha[:8]
    meta = git("log", "-1", "--format=%an%x00%ae%x00%cn%x00%ce", sha).strip().split("\x00")
    check_identity(f"commit {short} author", meta[0], meta[1], report, terms)
    if (meta[2], meta[3]) != (meta[0], meta[1]):
        check_identity(f"commit {short} committer", meta[2], meta[3], report, terms)
    scan_text(f"commit {short} message", git("log", "-1", "--format=%B", sha).splitlines(), report, terms)
    for path, lines in parse_added_lines(git("show", "--format=", "-U0", "--no-renames", sha)).items():
        check_secret_filename(path, report)
        scan_text(f"{path} (commit {short})", lines, report, terms)


def parse_added_lines(diff: str) -> dict[str, list[str]]:
    """Map path -> added lines from a unified diff."""
    added: dict[str, list[str]] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = target[2:] if target.startswith("b/") else None
            if current is not None:
                added.setdefault(current, [])
        elif line.startswith("+") and current is not None:
            added[current].append(line[1:])
    return added


def check_name_status(name_status: str, base_rev: str | None, report: Report) -> list[str]:
    """Apply H4/H7 to `git diff --name-status` output; return added/modified paths."""
    changed: list[str] = []
    for row in name_status.splitlines():
        if not row.strip():
            continue
        parts = row.split("\t")
        status, paths = parts[0], parts[1:]
        old_path, new_path = paths[0], paths[-1]
        if status[0] in "AMRC":
            changed.append(new_path)
        for immutable in IMMUTABLE_DIRS:
            if status[0] != "A" and old_path.startswith(immutable):
                report.error("H4", f"{old_path}: files in {immutable} are historical and must not change")
        if status[0] == "M" and re.match(r"docs/decisions/\d{4}-", old_path) and base_rev:
            previous = git("show", f"{base_rev}:{old_path}", check=False)
            if re.search(r"\*\*Status:\*\*\s*Accepted", previous):
                report.warn("H7", f"{old_path}: accepted ADRs should be superseded, not edited")
    return changed


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_staged(_: argparse.Namespace) -> int:
    """pre-commit: check what is about to be committed."""
    report = Report()
    head_exists = git("rev-parse", "--verify", "-q", "HEAD", check=False).strip() != ""
    changed = check_name_status(
        git("diff", "--cached", "--name-status", "-M"),
        "HEAD" if head_exists else None,
        report,
    )
    terms = load_private_terms()
    for path in changed:
        check_forbidden_type(path, report)
        check_secret_filename(path, report)
        size = git("cat-file", "-s", f":{path}", check=False).strip()
        if size.isdigit():
            check_size(path, int(size), report)
    for path, lines in parse_added_lines(git("diff", "--cached", "-U0", "--no-renames")).items():
        check_bulk_content(path, lines, report)
        scan_text(path, lines, report, terms)
    # H13: catch a personal email *before* it is baked into a commit.
    for var, role in (("GIT_AUTHOR_IDENT", "author"), ("GIT_COMMITTER_IDENT", "committer")):
        ident = re.match(r"(.*) <(.*)>", git("var", var, check=False).strip())
        if ident:
            check_identity(f"your git {role} identity", ident.group(1), ident.group(2), report, terms)
    return report.emit()


def check_message(message: str, report: Report, require_agent: str | None) -> None:
    lines = [l for l in message.splitlines() if not l.startswith("#")]
    subject = lines[0].strip() if lines else ""
    if SUBJECT_EXEMPT.match(subject):
        return
    if not SUBJECT.match(subject):
        report.error(
            "H5",
            f"subject {subject!r} must look like '<Area>: <summary>' "
            f"(Area one of {', '.join(AREAS)}; max ~72 chars)",
        )
    if require_agent:
        trailer = re.compile(r"^Co-Authored-By: .*%s" % re.escape(require_agent), re.I | re.M)
        if not trailer.search(message):
            report.error("H5", f"AI-assisted commit needs a 'Co-Authored-By: {require_agent} ...' trailer (AI-DISCLOSURE.md)")


def cmd_commit_msg(args: argparse.Namespace) -> int:
    """commit-msg: subject format, plus AI trailer when an agent is committing."""
    report = Report()
    message = Path(args.file).read_text(encoding="utf-8", errors="replace")
    check_message(message, report, os.environ.get("RESIEGED_AGENT") or None)
    body = [l for l in message.splitlines() if not l.startswith("#")]
    scan_text("commit message", body, report, load_private_terms())
    return report.emit()


def cmd_pre_push(args: argparse.Namespace) -> int:
    """pre-push: no pushes to protected branches, no history rewrites."""
    report = Report()
    terms = load_private_terms()
    for line in sys.stdin:
        parts = line.split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, remote_ref, remote_sha = parts
        branch = remote_ref.removeprefix("refs/heads/")
        if branch in PROTECTED_BRANCHES:
            report.error("H6", f"direct push to '{branch}' is not allowed; open a pull request")
            continue
        if local_sha == ZERO_SHA:
            continue  # branch deletion
        # H10–H13 on every commit this push would publish.
        if remote_sha == ZERO_SHA:
            outgoing = git("rev-list", "--no-merges", local_sha, "--not", "--remotes").split()
        else:
            outgoing = git("rev-list", "--no-merges", f"{remote_sha}..{local_sha}", check=False).split()
        for sha in outgoing:
            scan_commit(sha, report, terms)
        if remote_sha == ZERO_SHA:
            continue  # new branch: nothing to fast-forward from
        known = subprocess.run(["git", "cat-file", "-e", f"{remote_sha}^{{commit}}"], capture_output=True)
        if known.returncode != 0:
            report.error("H6", f"remote '{branch}' has commits you have not fetched; fetch and merge first")
            continue
        ff = subprocess.run(["git", "merge-base", "--is-ancestor", remote_sha, local_sha], capture_output=True)
        if ff.returncode != 0:
            report.error("H6", f"push to '{branch}' rewrites history (force push); not allowed")
    return report.emit()


def check_links(root: Path, report: Report) -> None:
    link = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
    for md in git("ls-files", "*.md").splitlines():
        if md.startswith("docs/handoff/"):
            continue
        text = (root / md).read_text(encoding="utf-8", errors="replace")
        for target in link.findall(text):
            if re.match(r"^[a-z]+:", target):
                continue
            if not (root / md).parent.joinpath(target).exists():
                report.warn("H9", f"{md}: broken link -> {target}")


def cmd_ci(args: argparse.Namespace) -> int:
    """CI: whole-tree checks plus checks on everything since the base branch."""
    report = Report()
    root = repo_root()
    terms = load_private_terms()
    if not terms:
        report.warn("H11", "no private terms configured (RESIEGED_PRIVATE_TERMS secret); name/email leak check skipped")
    for path in git("ls-files").splitlines():
        check_forbidden_type(path, report)
        check_secret_filename(path, report)
        full = root / path
        if full.is_file():
            check_size(path, full.stat().st_size, report)

    base = git("merge-base", args.base, "HEAD", check=False).strip()
    if base:
        changed = check_name_status(git("diff", "--name-status", "-M", base, "HEAD"), base, report)
        for path, lines in parse_added_lines(git("diff", "-U0", base, "HEAD")).items():
            check_bulk_content(path, lines, report)
        # Per commit, not just the net diff: a secret added then deleted is
        # still in history. Merges only combine already-scanned parents.
        for sha in git("rev-list", "--no-merges", f"{base}..HEAD").split():
            scan_commit(sha, report, terms)
        for sha in git("rev-list", "--no-merges", f"{base}..HEAD").split():
            sub = Report()
            check_message(git("log", "-1", "--format=%B", sha), sub, None)
            report.errors += [f"{e} (commit {sha[:8]})" for e in sub.errors]
        if any(p.startswith(("docs/", "tools/")) for p in changed) and "CHANGELOG.md" not in changed:
            report.warn("H8", "docs/ or tools/ changed without a CHANGELOG.md entry")
    else:
        report.warn("CI", f"could not find merge base with {args.base}; history checks skipped")

    check_links(root, report)
    return report.emit(sys.stdout)


# ---- Claude Code hook entry points ----------------------------------------

GIT_COMMIT = re.compile(r"\bgit\b[^;&|]*\bcommit\b")
GIT_PUSH = re.compile(r"\bgit\b[^;&|]*\bpush\b")
# `git commit -n` is short for --no-verify; only match it on an actual `git commit`
# invocation on the same line (a looser pattern flagged `grep -n`).
NO_VERIFY = re.compile(r"--no-verify\b|\bgit\s+commit\b[^;&|\n]*\s-[a-zA-Z]*n\b")
FORCE = re.compile(r"--force\b|--force-with-lease|\s-f\b|\s\+[\w/.-]+")


def cmd_claude_pretool(_: argparse.Namespace) -> int:
    """Claude PreToolUse hook. Exit 2 blocks the tool call and shows stderr to Claude."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input", {}) or {}
    root = repo_root()
    report = Report()

    if tool == "Bash":
        command = tool_input.get("command", "")
        if (GIT_COMMIT.search(command) or GIT_PUSH.search(command)) and NO_VERIFY.search(command):
            report.error("H6", "bypassing git hooks with --no-verify is not allowed for agents")
        if GIT_PUSH.search(command):
            if FORCE.search(command):
                report.error("H6", "force-push is not allowed for agents")
            for branch in PROTECTED_BRANCHES:
                if re.search(r"(\s|:|refs/heads/)%s(\s|$)" % branch, command):
                    report.error("H6", f"agents never push to '{branch}'; push a branch and open a PR")
            current = git("branch", "--show-current", check=False).strip()
            if current in PROTECTED_BRANCHES:
                report.error("H6", f"currently on '{current}'; switch to a work branch before pushing")
        if GIT_COMMIT.search(command):
            current = git("branch", "--show-current", check=False).strip()
            if current in PROTECTED_BRANCHES:
                report.error("H6", f"agents do not commit on '{current}'; create a work branch first")
        if report.errors:
            report.emit()
            return 2
        return 0

    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        path = Path(raw)
        try:
            rel = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return 0
        for immutable in IMMUTABLE_DIRS:
            if rel.startswith(immutable) and path.exists():
                report.error("H4", f"{rel}: handoff documents are historical; record corrections in docs/research/claims-register.md")
        if ext_of(rel) in FORBIDDEN_EXTENSIONS:
            report.error("H1", f"{rel}: agents do not write proprietary game file types inside the repository")
        if not rel.startswith(".git/"):
            check_secret_filename(rel, report)
            texts = [tool_input.get("content") or "", tool_input.get("new_string") or ""]
            texts += [e.get("new_string") or "" for e in tool_input.get("edits") or []]
            texts += [tool_input.get("new_source") or ""]
            scan_text(rel, "\n".join(texts).splitlines(), report, load_private_terms())
        if report.errors:
            report.emit()
            return 2
    return 0


def cmd_session_start(_: argparse.Namespace) -> int:
    """Claude SessionStart hook. Stdout becomes context for the session."""
    if git("config", "--get", "core.hooksPath", check=False).strip() != ".githooks":
        git("config", "core.hooksPath", ".githooks", check=False)
    branch = git("branch", "--show-current", check=False).strip() or "(detached)"
    print(f"Re-Sieged session start. Branch: {branch}. Git hooks: .githooks (enabled).")
    print("Phase: see ROADMAP.md. Rules: AGENTS.md. Workflow: docs/process/workflow.md.")
    if branch in PROTECTED_BRANCHES:
        print(f"WARNING: on protected branch '{branch}'. Create a work branch before committing.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("staged").set_defaults(func=cmd_staged)
    p = sub.add_parser("commit-msg")
    p.add_argument("file")
    p.set_defaults(func=cmd_commit_msg)
    sub.add_parser("pre-push").set_defaults(func=cmd_pre_push)
    p = sub.add_parser("ci")
    p.add_argument("--base", default="origin/main")
    p.set_defaults(func=cmd_ci)
    sub.add_parser("claude-pretool").set_defaults(func=cmd_claude_pretool)
    sub.add_parser("session-start").set_defaults(func=cmd_session_start)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

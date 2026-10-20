"""Delete the local AI's branches that Noy2's audit has finished with, so the runner stops pushing them back.

    python local-ai/branch_cleanup.py           delete them (locally, and on GitHub when they are still there)
    python local-ai/branch_cleanup.py --dry     only list what it would delete

ai-queue.ps1 runs this before every GitHub sync. Noy2's audit (scripts/audit_local_ai.py finish --delete-remote)
deletes a local-ai/* branch on GitHub once it is handled, but the runner used to push every local branch that
GitHub did not have, so each sync spent ~10 minutes putting about 190 handled branches back (2026-10-20).

A branch counts as handled by the same rule the audit uses: it has no commits that main lacks, or every TODO
item its commits name ("local-ai: <ITEM>: ...") is ticked in planning/TODO.md or planning/TODO-NEXT.md.
A branch checked out in a working copy (the task running now) is never touched.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBJECT = re.compile(r"^local-ai: (?:chain:)?([A-Z0-9][A-Z0-9-]*[A-Z0-9])(?::\d+)?:")


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def ticked():
    ids = set()
    for name in ("TODO.md", "TODO-NEXT.md"):
        path = ROOT / "planning" / name
        if path.exists():
            ids |= set(re.findall(r"(?m)^\s*- \[x\] ([A-Z0-9][A-Z0-9-]*[A-Z0-9])", path.read_text(encoding="utf-8")))
    return ids


def main(argv):
    done = ticked()
    in_use = set(re.findall(r"(?m)^branch refs/heads/(\S+)", git("worktree", "list", "--porcelain")))
    remote = {line.split("refs/heads/", 1)[1] for line in git("ls-remote", "--heads", "origin", "local-ai/*").splitlines() if "refs/heads/" in line}
    handled = []
    for branch in git("for-each-ref", "--format=%(refname:short)", "refs/heads/local-ai/").split():
        if branch in in_use:
            continue
        subjects = git("log", "--no-merges", "--format=%s", "main.." + branch).splitlines()
        ids = {m.group(1) for m in map(SUBJECT.match, subjects) if m}
        # a chain step's commit names the step (R4-AFPC-6-1); the TODO item is the chain name before the step number
        ids = {re.sub(r"-\d+$", "", i) if i not in done and re.sub(r"-\d+$", "", i) in done else i for i in ids}
        if not subjects or (ids and ids <= done):
            handled.append(branch)
    on_github = [b for b in handled if b in remote]
    print("branch_cleanup: %d handled branches (%d still on GitHub) of %d local-ai branches"
          % (len(handled), len(on_github), len(git("for-each-ref", "--format=%(refname:short)", "refs/heads/local-ai/").split())))
    if "--dry" in argv:
        for b in handled[:15]:
            print("  " + b)
        return 0
    for i in range(0, len(on_github), 25):
        subprocess.run(["git", "-C", str(ROOT), "push", "-q", "origin", "--delete", *on_github[i:i + 25]], capture_output=True)
    for i in range(0, len(handled), 50):
        subprocess.run(["git", "-C", str(ROOT), "branch", "-q", "-D", *handled[i:i + 50]], capture_output=True)
    print("branch_cleanup: deleted %d local branches and %d on GitHub" % (len(handled), len(on_github)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

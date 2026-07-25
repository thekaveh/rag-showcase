from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.docs import push_wiki


def test_run_helper_applies_default_local_timeout(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kwargs: calls.append((cmd, kwargs)),
    )
    push_wiki.run(["git", "status"])
    assert calls[0][1]["timeout"] == push_wiki._LOCAL_GIT_TIMEOUT
    assert calls[0][1]["check"] is True


def test_run_helper_honors_explicit_timeout_override(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kwargs: calls.append((cmd, kwargs)),
    )
    push_wiki.run(["git", "clone", "x", "y"], timeout=push_wiki._NETWORK_GIT_TIMEOUT)
    assert calls[0][1]["timeout"] == push_wiki._NETWORK_GIT_TIMEOUT


def test_main_push_uses_network_timeout_for_clone_and_push_only(tmp_path, monkeypatch) -> None:
    # clone/push cross the network (SSH to GitHub) and get the longer budget;
    # add/status/commit are local and stay on the short default — an SSH stall in
    # unattended CI (docs.yml's wiki job) must fail fast with a diagnosable error
    # instead of hanging until the job's own outer timeout kills it.
    wiki_src = tmp_path / "generated-wiki"
    wiki_src.mkdir()
    (wiki_src / "Home.md").write_text("hello\n", encoding="utf-8")
    monkeypatch.setattr(push_wiki, "WIKI_SRC", wiki_src)
    monkeypatch.setattr(push_wiki, "build", lambda **kwargs: None)

    calls = []

    def fake_run(cmd, cwd=None, check=None, text=None, capture_output=None, timeout=None):
        calls.append((cmd, timeout))
        if cmd[:2] == ["git", "clone"]:
            work = Path(cmd[-1])
            (work / ".git").mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(cmd, 0)
        if cmd[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=" M Home.md\n")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["push_wiki.py", "--push"])

    push_wiki.main()

    by_cmd = {tuple(cmd[:2]): timeout for cmd, timeout in calls}
    assert by_cmd[("git", "clone")] == push_wiki._NETWORK_GIT_TIMEOUT
    assert by_cmd[("git", "push")] == push_wiki._NETWORK_GIT_TIMEOUT
    assert by_cmd[("git", "add")] == push_wiki._LOCAL_GIT_TIMEOUT
    assert by_cmd[("git", "status")] == push_wiki._LOCAL_GIT_TIMEOUT
    assert by_cmd[("git", "commit")] == push_wiki._LOCAL_GIT_TIMEOUT

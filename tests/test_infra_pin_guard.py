"""Functional coverage for scripts/restore-infra-pin.sh — the atlas#797 pin guard.

Builds a throwaway super-repo with `infra` recorded as a gitlink, simulates the
Atlas launcher advancing + staging that submodule, and asserts the guard restores
the working tree and unstages so the repo is byte-clean at the pinned SHA.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "restore-infra-pin.sh"


def _git(cwd, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=check
    )


def _make_super_with_infra_pin(tmp_path):
    """A super-repo with `infra` recorded as a gitlink at a committed SHA."""
    infra = tmp_path / "infra"
    infra.mkdir()
    _git(infra, "init", "-q", "-b", "main")
    _git(infra, "config", "user.email", "t@example.com")
    _git(infra, "config", "user.name", "t")
    (infra / "f").write_text("v1", encoding="utf-8")
    _git(infra, "add", "-A")
    _git(infra, "commit", "-qm", "v1")
    pin = _git(infra, "rev-parse", "HEAD").stdout.strip()

    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{pin},infra")
    _git(tmp_path, "commit", "-qm", "pin infra")
    return infra, pin


def _drift_and_stage(super_path, infra, pin):
    (infra / "f").write_text("v2", encoding="utf-8")
    _git(infra, "add", "-A")
    _git(infra, "commit", "-qm", "v2")
    drifted = _git(infra, "rev-parse", "HEAD").stdout.strip()
    assert drifted != pin
    _git(super_path, "add", "infra")  # stage the drifted gitlink, as the launcher does
    return drifted


def test_guard_restores_drifted_and_staged_pin(tmp_path):
    infra, pin = _make_super_with_infra_pin(tmp_path)
    _drift_and_stage(tmp_path, infra, pin)
    assert _git(tmp_path, "status", "--porcelain", "--", "infra").stdout.strip() != ""

    res = subprocess.run(["bash", str(GUARD), str(tmp_path), pin], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "WARNING" in res.stderr  # acted, and loudly

    assert _git(infra, "rev-parse", "HEAD").stdout.strip() == pin
    assert _git(tmp_path, "status", "--porcelain", "--", "infra").stdout.strip() == ""


def test_guard_is_noop_when_clean(tmp_path):
    infra, pin = _make_super_with_infra_pin(tmp_path)
    assert _git(tmp_path, "status", "--porcelain", "--", "infra").stdout.strip() == ""

    res = subprocess.run(["bash", str(GUARD), str(tmp_path), pin], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert "WARNING" not in res.stderr  # nothing to restore
    assert _git(infra, "rev-parse", "HEAD").stdout.strip() == pin
    assert _git(tmp_path, "status", "--porcelain", "--", "infra").stdout.strip() == ""


def test_guard_noop_outside_git_repo(tmp_path):
    # No git repo at the root → guard exits 0 without touching anything.
    res = subprocess.run(
        ["bash", str(GUARD), str(tmp_path), "0" * 40], capture_output=True, text=True
    )
    assert res.returncode == 0

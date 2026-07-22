#!/usr/bin/env bash
# Guard for thekaveh/atlas#797: the Atlas launcher can advance the vendored `infra`
# submodule to a newer commit AND `git add`-stage that drift into the consumer's
# index during a run — so a later `git commit -am` would silently bump the pin.
#
# Given the repo root and the pinned submodule SHA, restore `infra` to that SHA and
# unstage it, so a run always leaves the repo byte-clean at the pinned commit. A
# no-op when nothing drifted. Emits a loud warning to stderr when it has to act.
# Remove this guard (and its call site) once atlas#797 ships.
#
# Usage: restore-infra-pin.sh <repo-root> <pinned-sha>
set -uo pipefail

ROOT="${1:?repo root required}"
PIN="${2:?pinned sha required}"

# Nothing to guard if this isn't a git checkout or we captured no pin.
git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || exit 0
[ -n "$PIN" ] || exit 0

now="$(git -C "$ROOT/infra" rev-parse HEAD 2>/dev/null || echo "")"
staged="$(git -C "$ROOT" ls-files -s -- infra 2>/dev/null | awk '{print $2}')"

drifted=0
[ -n "$now" ] && [ "$now" != "$PIN" ] && drifted=1
[ -n "$staged" ] && [ "$staged" != "$PIN" ] && drifted=1

if [ "$drifted" = 1 ]; then
  echo "WARNING: the stack run advanced/staged the infra submodule off its pin (thekaveh/atlas#797)." >&2
  echo "         Restoring infra to ${PIN} and unstaging so the repo stays byte-clean at the pinned SHA." >&2
  # Unstage first (index back to HEAD's recorded gitlink), then move the working
  # tree back to the pin. `restore --staged` on older git → fall back to `reset`.
  git -C "$ROOT" restore --staged -- infra 2>/dev/null \
    || git -C "$ROOT" reset -q -- infra 2>/dev/null || true
  git -C "$ROOT/infra" checkout -q "$PIN" 2>/dev/null || true
fi

exit 0

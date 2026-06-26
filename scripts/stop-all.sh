#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
( cd "$ROOT/infra" && ./stop.sh )
echo "Stopped. (Use 'cd infra && ./stop.sh --cold' to also wipe data.)"

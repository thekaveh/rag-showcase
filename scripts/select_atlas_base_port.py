#!/usr/bin/env python3
"""Select a wholly free Atlas host-port block."""
from __future__ import annotations

import argparse
import socket
import sys
from collections.abc import Iterable


BLOCK_SIZE = 110
DEFAULT_CANDIDATES = tuple(range(64500, 65341, 120))


def _validate(base: int, block_size: int) -> None:
    if block_size < 1:
        raise ValueError("block size must be positive")
    if base < 1024 or base + block_size - 1 > 65535:
        raise ValueError(
            f"port block {base}-{base + block_size - 1} is outside 1024-65535"
        )


def block_is_free(base: int, *, block_size: int = BLOCK_SIZE) -> bool:
    """Bind every IPv4 port at once so a partial block cannot be selected."""
    _validate(base, block_size)
    sockets: list[socket.socket] = []
    try:
        for port in range(base, base + block_size):
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockets.append(listener)
            listener.bind(("0.0.0.0", port))
            listener.listen(1)
        return True
    except OSError:
        return False
    finally:
        for listener in sockets:
            listener.close()


def choose_base_port(
    *,
    preferred: int | None = None,
    candidates: Iterable[int] = DEFAULT_CANDIDATES,
    block_size: int = BLOCK_SIZE,
) -> int:
    if preferred is not None:
        _validate(preferred, block_size)
        if not block_is_free(preferred, block_size=block_size):
            raise RuntimeError(
                f"requested Atlas port block {preferred}-{preferred + block_size - 1} "
                "is not wholly free"
            )
        return preferred
    for base in candidates:
        _validate(base, block_size)
        if block_is_free(base, block_size=block_size):
            return base
    raise RuntimeError("no wholly free Atlas port block was found")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=int, help="Require this exact base port")
    args = parser.parse_args()
    try:
        selected = choose_base_port(preferred=args.base)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    print(selected)


if __name__ == "__main__":
    main()

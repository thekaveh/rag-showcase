#!/usr/bin/env python3
"""Select a wholly free Atlas host-port block."""
from __future__ import annotations

import argparse
import errno
import socket
import sys
from collections.abc import Iterable


BLOCK_SIZE = 110
# Keep automatic allocations below the IANA dynamic/private range. Host runtimes
# such as Ollama can create ephemeral child listeners after Atlas starts, so a
# block that was free during preflight can otherwise collide between datasets.
DEFAULT_CANDIDATES = tuple(range(22000, 32101, 120))


def _validate(base: int, block_size: int) -> None:
    if block_size < 1:
        raise ValueError("block size must be positive")
    if base < 1024 or base + block_size - 1 > 65535:
        raise ValueError(
            f"port block {base}-{base + block_size - 1} is outside 1024-65535"
        )


def block_is_free(base: int, *, block_size: int = BLOCK_SIZE) -> bool:
    """Bind every IPv4 and available IPv6 port so the whole block is free."""
    _validate(base, block_size)
    sockets: list[socket.socket] = []
    ipv6_unavailable = {
        errno.EAFNOSUPPORT,
        errno.EPROTONOSUPPORT,
        errno.EADDRNOTAVAIL,
    }
    try:
        for port in range(base, base + block_size):
            for family, address in (
                (socket.AF_INET, "0.0.0.0"),
                (socket.AF_INET6, "::"),
            ):
                listener: socket.socket | None = None
                try:
                    listener = socket.socket(family, socket.SOCK_STREAM)
                    if family == socket.AF_INET6:
                        listener.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                    listener.bind((address, port))
                    listener.listen(1)
                    sockets.append(listener)
                except OSError as exc:
                    if listener is not None:
                        listener.close()
                    if family == socket.AF_INET6 and exc.errno in ipv6_unavailable:
                        continue
                    raise
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

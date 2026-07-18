from __future__ import annotations

import socket

import pytest

from scripts.select_atlas_base_port import (
    DEFAULT_CANDIDATES,
    block_is_free,
    choose_base_port,
)


def test_default_candidates_avoid_dynamic_private_port_range() -> None:
    assert DEFAULT_CANDIDATES
    assert max(DEFAULT_CANDIDATES) + 109 < 49152


def test_block_check_rejects_any_port_collision() -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    occupied = listener.getsockname()[1]
    try:
        assert not block_is_free(occupied, block_size=1)
    finally:
        listener.close()


def test_block_check_rejects_ipv6_only_collision() -> None:
    listener = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        listener.bind(("::1", 0))
        listener.listen(1)
    except OSError as exc:
        listener.close()
        pytest.skip(f"IPv6 loopback is unavailable: {exc}")
    occupied = listener.getsockname()[1]
    try:
        assert not block_is_free(occupied, block_size=1)
    finally:
        listener.close()


def test_selector_skips_colliding_block_and_returns_wholly_free_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.select_atlas_base_port.block_is_free",
        lambda base, *, block_size: base == 22010 and block_size == 1,
    )

    assert choose_base_port(candidates=[22000, 22010], block_size=1) == 22010


@pytest.mark.parametrize("base", [0, 1023, 65535])
def test_selector_rejects_invalid_full_block(base: int) -> None:
    with pytest.raises(ValueError):
        choose_base_port(preferred=base, block_size=110)

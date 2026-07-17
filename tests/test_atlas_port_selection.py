from __future__ import annotations

import socket

import pytest

from scripts.select_atlas_base_port import block_is_free, choose_base_port


def test_block_check_rejects_any_port_collision() -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    occupied = listener.getsockname()[1]
    try:
        assert not block_is_free(occupied, block_size=1)
    finally:
        listener.close()


def test_selector_skips_colliding_block_and_returns_wholly_free_block() -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    occupied = listener.getsockname()[1]
    free = occupied + 10 if occupied < 65000 else occupied - 10
    try:
        selected = choose_base_port(candidates=[occupied, free], block_size=1)
    finally:
        listener.close()
    assert selected == free


@pytest.mark.parametrize("base", [0, 1023, 65535])
def test_selector_rejects_invalid_full_block(base: int) -> None:
    with pytest.raises(ValueError):
        choose_base_port(preferred=base, block_size=110)

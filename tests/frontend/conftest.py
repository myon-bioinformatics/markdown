from __future__ import annotations

import socket

import pytest


@pytest.fixture()
def free_port() -> int:
    """A free TCP port on localhost for a demo server to bind to."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

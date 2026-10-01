"""Offline playback must never fall back to network inference."""

import socket
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def deny_network() -> Iterator[list[str]]:
    attempts: list[str] = []

    def denied(*args: object, **kwargs: object) -> None:
        attempts.append("socket connection attempted during offline reproduction")
        raise OSError("OFFLINE: network connections prohibited")

    with (
        patch.object(socket.socket, "connect", denied),
        patch.object(socket.socket, "connect_ex", denied),
        patch.object(socket, "create_connection", denied),
    ):
        yield attempts

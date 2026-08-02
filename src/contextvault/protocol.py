from __future__ import annotations

from dataclasses import dataclass

from contextvault import __version__


PROTOCOL_VERSION = 2
MIN_PROTOCOL_VERSION = 1


@dataclass(frozen=True)
class Compatibility:
    compatible: bool
    server_version: str
    server_protocol: int
    minimum_protocol: int
    message: str


def check_protocol(client_protocol: int) -> Compatibility:
    compatible = MIN_PROTOCOL_VERSION <= client_protocol <= PROTOCOL_VERSION
    if compatible:
        message = "compatible"
    elif client_protocol < MIN_PROTOCOL_VERSION:
        message = "client_upgrade_required"
    else:
        message = "server_upgrade_required"
    return Compatibility(
        compatible,
        __version__,
        PROTOCOL_VERSION,
        MIN_PROTOCOL_VERSION,
        message,
    )

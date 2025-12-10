from enum import Enum
from typing import Optional


class MqttTransportType(Enum):
    """Defines ways to connect to an MQTT broker."""

    TCP = "tcp"
    WEBSOCKET = "websockets"
    UNIX = "unix"


class MqttTransport:
    """Defines the transport parameters for connecting to an MQTT broker."""

    def __init__(
        self,
        transport_type: MqttTransportType,
        host: Optional[str] = None,
        port: Optional[int] = None,
        socket_path: Optional[str] = None,
    ):
        self.transport = transport_type
        self.host_or_path = (
            socket_path if transport_type == MqttTransportType.UNIX else host
        )
        self.port = 0 if transport_type == MqttTransportType.UNIX else (port or 1883)

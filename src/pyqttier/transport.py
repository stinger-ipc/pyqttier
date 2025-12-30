from enum import Enum
from typing import Optional
import ssl


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
        self.tls_enabled = False
        self.ca_certs: Optional[str] = None
        self.certfile: Optional[str] = None
        self.keyfile: Optional[str] = None
        self.cert_reqs: int = ssl.CERT_REQUIRED
        self.tls_version: int = ssl.PROTOCOL_TLS
        self.ciphers: Optional[str] = None

    def enable_tls(
        self,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        cert_reqs: int = ssl.CERT_REQUIRED,
        tls_version: int = ssl.PROTOCOL_TLS,
        ciphers: Optional[str] = None,
    ):
        """
        Configure TLS/SSL for the MQTT connection.

        Args:
            ca_certs: Path to the Certificate Authority certificate files that are to be
                     treated as trusted by this client. Required for certificate validation.
            certfile: Path to the PEM encoded client certificate. Used for client authentication.
            keyfile: Path to the PEM encoded client private key. Used with certfile for client authentication.
            cert_reqs: Defines the certificate requirements that the client imposes on the broker.
                      Defaults to ssl.CERT_REQUIRED (certificate is required and will be validated).
                      Use ssl.CERT_NONE to disable verification (not recommended for production).
            tls_version: Specifies the version of the SSL/TLS protocol to use.
                        Defaults to ssl.PROTOCOL_TLS (automatic negotiation).
            ciphers: String specifying which encryption ciphers are allowable for this connection.
        """
        self.tls_enabled = True
        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
        self.cert_reqs = cert_reqs
        self.tls_version = tls_version
        self.ciphers = ciphers


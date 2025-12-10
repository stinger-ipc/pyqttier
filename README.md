# PyQTTier

A Python MQTT client library providing a clean, type-safe wrapper around paho-mqtt with support for MQTT 5.0 features.

## Features

- **MQTT 5.0 Support** - Full support for MQTT 5.0 protocol features including message properties, correlation data, and response topics
- **Type Safety** - Strongly typed with mypy-checked type hints for reliability
- **Multiple Transports** - Supports TCP, WebSocket, and Unix socket connections
- **Mock Implementation** - Built-in `MockConnection` for easy testing without a broker
- **Python 3.7+** - Compatible with Python 3.7 through 3.12 [![Python 3.7 Tests](https://github.com/stinger-ipc/pyqttier/actions/workflows/python37.yml/badge.svg)](https://github.com/stinger-ipc/pyqttier/actions/workflows/python37.yml)

## Installation

```bash
pip install pyqttier
```

## Quick Start

### Basic Usage

```python
from pyqttier.connection import Mqtt5Connection
from pyqttier.transport import MqttTransport, MqttTransportType
from pyqttier.message import Message

# Connect to broker
transport = MqttTransport(MqttTransportType.TCP, host="localhost", port=1883)
conn = Mqtt5Connection(transport=transport, client_id="my-client")

# Subscribe to a topic
def on_message(msg: Message):
    print(f"Received: {msg.payload.decode()}")

conn.subscribe("sensors/temperature", callback=on_message)

# Publish a message
msg = Message(topic="sensors/temperature", payload=b"23.5", qos=1)
conn.publish(msg)
```

### Testing with MockConnection

```python
from pyqttier.mock import MockConnection
from pyqttier.message import Message

# Create mock connection for testing
conn = MockConnection()

# Publish and verify
conn.publish(Message(topic="test", payload=b"data", qos=1))
assert len(conn.published_messages) == 1
assert conn.published_messages[0].topic == "test"
```

## Examples

See the [examples/](examples/) directory for more detailed usage examples:

- `usage_example.py` - Real broker connections, wildcards, request-response patterns
- `mock_example.py` - Testing with MockConnection

## Development

```bash
# Install project
uv pip install -e .

# Type checking
uv run mypy --check-untyped-defs ./src/

# Unit tests
uv run pytest
```

## License

MIT License.

See [LICENSE](LICENSE) file for details.

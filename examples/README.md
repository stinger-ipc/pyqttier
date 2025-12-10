# PyQTTier Examples

This directory contains concise examples for using PyQTTier.

## Usage Example (`usage_example.py`)

Demonstrates connecting to an MQTT broker, publishing/subscribing, retained messages, wildcards, and request-response. Requires a broker on `localhost:1883`:

```bash
docker run -p 1883:1883 eclipse-mosquitto
```

Run the examples:
```bash
uv run examples/usage_example.py
```

## Mock Connection Example (`mock_example.py`)

Shows how to use `MockConnection` for testing without a real broker. Run with:

```bash
uv run examples/mock_example.py
```

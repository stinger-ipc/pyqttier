#!/usr/bin/env python3
"""
Example demonstrating connection checking and automatic reconnection with PyQTTier.

This example shows:
1. Connecting to an MQTT broker using environment variables for configuration
2. Publishing to 'test/ping' every minute when connected
3. Subscribing to 'test/pong' and printing any messages received
4. Automatic reconnection handling by the underlying MQTT client
"""
import os
import ssl
import time
import signal
import sys

from pyqttier.connection import Mqtt5Connection
from pyqttier.transport import MqttTransport, MqttTransportType


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n🛑 Received interrupt signal, shutting down...")
    sys.exit(0)


def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Get broker configuration from environment variables with defaults
    hostname = os.getenv("MQTT_HOSTNAME", "smokecloud.vivint.com")
    port = int(os.getenv("MQTT_PORT", "8883"))
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")
    credentials = None
    if username is not None and password is not None:
        print(
            f"🔑 Using credentials for {username} (password provided but not displayed)"
        )
        credentials = (username, password)

    print(f"🔧 Connecting to MQTT broker at {hostname}:{port}")

    # Create transport configuration
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP, host=hostname, port=port
    )
    transport.enable_tls(cert_reqs=ssl.CERT_NONE)

    # Create connection
    conn = Mqtt5Connection(
        transport=transport,
        client_id="connection-check-example",
        credentials=credentials,
        lwt=False,
    )

    # Wait for initial connection
    print("⏳ Waiting for initial connection...")
    timeout = 100
    elapsed = 0.0
    while not conn.is_connected() and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5
        print(f"   Still waiting... ({elapsed}s/{timeout}s)")

    if not conn.is_connected():
        print("❌ Failed to establish initial connection. Exiting.")
        return

    print("✅ Connected to MQTT broker!")
    print(f"   Client ID: {conn.client_id}")

    # Main loop: publish to 'test/ping' every minute
    print("🔄 Starting main loop")
    print("   Press Ctrl+C to stop")

    try:
        while True:
            if conn.is_connected():
                print("✅ Still connected (probably)")

            # Wait 60 seconds before next check
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n🛑 Received keyboard interrupt")
    finally:
        print("🧹 Cleaning up...")
        # The connection will be cleaned up automatically when the object is deleted
        # or we could add an explicit disconnect method if needed


if __name__ == "__main__":
    main()

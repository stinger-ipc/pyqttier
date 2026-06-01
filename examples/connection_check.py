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
import time
import signal
import sys

from pyqttier.connection import Mqtt5Connection
from pyqttier.transport import MqttTransport, MqttTransportType
from pyqttier.message import Message


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print('\n🛑 Received interrupt signal, shutting down...')
    sys.exit(0)


def main():
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Get broker configuration from environment variables with defaults
    hostname = os.getenv('MQTT_HOSTNAME', 'localhost')
    port = int(os.getenv('MQTT_PORT', '1883'))
    
    print(f"🔧 Connecting to MQTT broker at {hostname}:{port}")
    
    # Create transport configuration
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host=hostname,
        port=port
    )
    
    # Create connection
    conn = Mqtt5Connection(transport=transport, client_id="connection-check-example")
    
    # Wait for initial connection
    print("⏳ Waiting for initial connection...")
    timeout = 100
    elapsed = 0
    while not conn.is_connected() and elapsed < timeout:
        time.sleep(0.5)
        elapsed += 0.5
        print(f"   Still waiting... ({elapsed}s/{timeout}s)")
    
    if not conn.is_connected():
        print("❌ Failed to establish initial connection. Exiting.")
        return
    
    print("✅ Connected to MQTT broker!")
    print(f"   Client ID: {conn.client_id}")
    print(f"   Online topic: {conn.online_topic}")
    
    # Subscribe to 'test/pong' topic
    def on_pong_message(message):
        print(f"📨 Received on 'test/pong': {message.payload.decode()}")
    
    subscription_id = conn.subscribe('test/pong', callback=on_pong_message)
    print(f"📡 Subscribed to 'test/pong' with subscription ID: {subscription_id}")
    
    # Main loop: publish to 'test/ping' every minute
    print("🔄 Starting main loop - will publish to 'test/ping' every minute")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            if conn.is_connected():
                # Create and publish ping message
                ping_msg = Message(
                    topic='test/ping',
                    payload=f"ping from {conn.client_id} at {time.time()}".encode(),
                    qos=1,
                )
                future = conn.publish(ping_msg)
                # Wait for publish to complete (with timeout)
                try:
                    future.result(timeout=5.0)
                    print(f"📤 Published to 'test/ping': {ping_msg.payload.decode()}")
                except TimeoutError:
                    print("⚠️  Publish timeout", future)
            else:
                print("⚠️  Not connected - waiting for reconnection...")
            
            # Wait 60 seconds before next publish
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n🛑 Received keyboard interrupt")
    finally:
        print("🧹 Cleaning up...")
        # The connection will be cleaned up automatically when the object is deleted
        # or we could add an explicit disconnect method if needed


if __name__ == "__main__":
    main()
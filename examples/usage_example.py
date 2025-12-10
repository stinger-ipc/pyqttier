#!/usr/bin/env python3
"""
Example demonstrating real-world usage of PyQTTier with Mqtt5Connection.

This example shows:
1. Connecting to an MQTT broker
2. Publishing status messages
3. Subscribing to topics
4. Handling retained messages
5. Request-response pattern
6. Clean disconnection
"""
import sys
import time

from pyqttier.connection import Mqtt5Connection
from pyqttier.transport import MqttTransport, MqttTransportType
from pyqttier.message import Message


def example_basic_connection():
    """Example 1: Basic connection to MQTT broker."""
    print("=" * 60)
    print("Example 1: Connecting to MQTT Broker")
    print("=" * 60)
    
    # Create transport configuration (TCP connection to local broker)
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    # Create connection with a custom client ID
    conn = Mqtt5Connection(transport=transport, client_id="pyqttier-example-1")
    
    # Wait for connection
    timeout = 5
    elapsed = 0
    while not conn.is_connected() and elapsed < timeout:
        print(f"⏳ Waiting for connection... ({elapsed}s/{timeout}s)")
        time.sleep(0.5)
        elapsed += 0.5
    
    if conn.is_connected():
        print("✅ Connected to MQTT broker!")
        print(f"   Client ID: {conn.client_id}")
        print(f"   Online topic: {conn.online_topic}")
    else:
        print("❌ Failed to connect to broker")
        return
    
    # Clean disconnect
    print("\n🔌 Disconnecting...")
    del conn
    print("✓ Disconnected\n")

def example_publish():
    """Example 2: Publishing messages to a topic.
    
    We're going to publish to a topic with a retain flag so that we can receive it in example 3
    """
    print("=" * 60)
    print("Example 2: Publishing Messages")
    print("=" * 60)
    
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    conn = Mqtt5Connection(transport=transport, client_id="pyqttier-example-2-publisher")
    
    # Wait for connection
    while not conn.is_connected():
        time.sleep(0.1)
    
    print("✅ Connected!")
    
    msg = Message(
        topic="example/topic",
        payload=b"Example message",
        qos=1,
        retain=True
    )
    future = conn.publish(msg)
    future.result()  # Wait for publish to complete

    print(f"📤 Published: {msg.payload.decode()}")
    time.sleep(0.2)
    
    # Cleanup
    del conn
    print("✓ Disconnected\n")

def example_publish_subscribe():
    """Example 2: Publishing and subscribing to messages."""
    print("=" * 60)
    print("Example 2: Publish and Subscribe")
    print("=" * 60)
    
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    conn = Mqtt5Connection(transport=transport, client_id="pyqttier-example-2")
    
    # Wait for connection
    while not conn.is_connected():
        time.sleep(0.1)
    
    print("✅ Connected!")
    
    # Subscribe to a topic
    received_messages = []
    
    def on_temperature(msg: Message):
        temp = msg.payload.decode()
        print(f"🌡️  Temperature update: {temp}°C")
        received_messages.append(msg)
    
    sub_id = conn.subscribe("sensors/temperature", callback=on_temperature)
    print(f"📥 Subscribed to 'sensors/temperature' (ID: {sub_id})")
    
    # Give subscription time to complete
    time.sleep(0.5)
    
    # Publish some temperature readings
    for temp in [20.5, 21.0, 21.5, 22.0]:
        msg = Message(
            topic="sensors/temperature",
            payload=str(temp).encode(),
            qos=1
        )
        future = conn.publish(msg)
        print(f"📤 Published: {temp}°C")
        time.sleep(0.2)
    
    # Wait for messages to be received
    time.sleep(1)
    
    print(f"\n✓ Received {len(received_messages)} temperature readings")
    
    # Cleanup
    del conn
    print()


def example_retained_messages():
    """Example 3: Working with retained messages."""
    print("=" * 60)
    print("Example 3: Retained Messages")
    print("=" * 60)
    
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    # First connection - publish retained status
    print("📡 First connection - publishing retained status...")
    conn1 = Mqtt5Connection(transport=transport, client_id="pyqttier-example-3a")
    
    while not conn1.is_connected():
        time.sleep(0.1)
    
    # Publish a retained status message
    status_msg = Message(
        topic="device/status",
        payload=b'{"status":"online","version":"1.0.0"}',
        qos=1,
        retain=True,
        content_type="application/json"
    )
    conn1.publish(status_msg)
    print("✅ Published retained status message")
    
    time.sleep(0.5)
    del conn1
    print("🔌 Disconnected first connection\n")
    
    # Second connection - should receive retained message immediately
    print("📡 Second connection - subscribing to status...")
    conn2 = Mqtt5Connection(transport=transport, client_id="pyqttier-example-3b")
    
    while not conn2.is_connected():
        time.sleep(0.1)
    
    retained_received = []
    
    def on_status(msg: Message):
        print(f"📨 Received status: {msg.payload.decode()}")
        print(f"   Retained: {msg.retain}")
        retained_received.append(msg)
    
    conn2.subscribe("device/status", callback=on_status)
    
    # Wait to receive the retained message
    time.sleep(1)
    
    if retained_received:
        print("✅ Successfully received retained message on new connection!")
    
    # Clear the retained message
    print("\n🧹 Clearing retained message...")
    conn2.unpublish_retained("device/status")
    time.sleep(0.5)
    
    del conn2
    print()


def example_wildcard_subscriptions():
    """Example 4: Using wildcard subscriptions."""
    print("=" * 60)
    print("Example 4: Wildcard Subscriptions")
    print("=" * 60)
    
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    conn = Mqtt5Connection(transport=transport, client_id="pyqttier-example-4")
    
    while not conn.is_connected():
        time.sleep(0.1)
    
    print("✅ Connected!")
    
    # Subscribe to all sensors using single-level wildcard
    sensor_data = {}
    
    def on_sensor(msg: Message):
        sensor_type = msg.topic.split('/')[-1]
        value = msg.payload.decode()
        sensor_data[sensor_type] = value
        print(f"📊 {sensor_type}: {value}")
    
    conn.subscribe("building/floor1/+", callback=on_sensor)
    print("📥 Subscribed to 'building/floor1/+'\n")
    
    time.sleep(0.5)
    
    # Publish to different sensor topics
    sensors = {
        "building/floor1/temperature": "22.0",
        "building/floor1/humidity": "45.5",
        "building/floor1/occupancy": "3",
        "building/floor1/light": "850",
    }
    
    for topic, value in sensors.items():
        msg = Message(topic=topic, payload=value.encode(), qos=1)
        conn.publish(msg)
    
    # Wait for messages
    time.sleep(1)
    
    print(f"\n✓ Collected {len(sensor_data)} sensor readings")
    
    del conn
    print()


def example_request_response():
    """Example 5: Request-response pattern with correlation."""
    print("=" * 60)
    print("Example 5: Request-Response Pattern")
    print("=" * 60)
    
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    # Device that responds to commands
    device_conn = Mqtt5Connection(transport=transport, client_id="pyqttier-device")
    
    while not device_conn.is_connected():
        time.sleep(0.1)
    
    def on_command(msg: Message):
        command = msg.payload.decode()
        print(f"🔧 Device received command: {command}")
        
        if msg.response_topic:
            # Send response
            response_payload = f'{{"result":"ok","command":"{command}"}}'.encode()
            response = Message(
                topic=msg.response_topic,
                payload=response_payload,
                qos=1,
                correlation_data=msg.correlation_data,
                content_type="application/json"
            )
            device_conn.publish(response)
            print(f"↩️  Sent response to {msg.response_topic}")
    
    device_conn.subscribe("device/commands", callback=on_command)
    print("📥 Device subscribed to 'device/commands'")
    
    time.sleep(0.5)
    
    # Client that sends commands
    client_conn = Mqtt5Connection(transport=transport, client_id="pyqttier-client")
    
    while not client_conn.is_connected():
        time.sleep(0.1)
    
    responses = []
    
    def on_response(msg: Message):
        print(f"✅ Client received response: {msg.payload.decode()}")
        print(f"   Correlation: {msg.correlation_data.decode() if msg.correlation_data else 'None'}")
        responses.append(msg)
    
    client_conn.subscribe("client/responses", callback=on_response)
    print("📥 Client subscribed to 'client/responses'\n")
    
    time.sleep(0.5)
    
    # Send a command with response topic
    command = Message(
        topic="device/commands",
        payload=b"reboot",
        qos=1,
        response_topic="client/responses",
        correlation_data=b"cmd-12345"
    )
    
    print("📤 Client sending command: reboot")
    client_conn.publish(command)
    
    # Wait for response
    time.sleep(1)
    
    if responses:
        print(f"\n✓ Request-response completed successfully!")
    
    del device_conn
    del client_conn
    print()


def example_multiple_callbacks():
    """Example 6: Using both specific and global callbacks."""
    print("=" * 60)
    print("Example 6: Multiple Message Callbacks")
    print("=" * 60)
    
    transport = MqttTransport(
        transport_type=MqttTransportType.TCP,
        host="localhost",
        port=1883
    )
    
    conn = Mqtt5Connection(transport=transport, client_id="pyqttier-example-6")
    
    while not conn.is_connected():
        time.sleep(0.1)
    
    print("✅ Connected!")
    
    # Specific callback for alerts
    def on_alert(msg: Message):
        print(f"🚨 ALERT: {msg.payload.decode()}")
    
    # Global callback for everything else
    def on_any_message(msg: Message):
        print(f"📬 General message on '{msg.topic}': {msg.payload.decode()}")
    
    conn.subscribe("system/alerts", callback=on_alert)
    conn.add_message_callback(on_any_message)
    print("📥 Set up specific and global callbacks\n")
    
    time.sleep(0.5)
    
    # Publish various messages
    messages = [
        ("system/alerts", b"High CPU usage detected!"),
        ("system/info", b"System running normally"),
        ("application/logs", b"Application started"),
    ]
    
    for topic, payload in messages:
        msg = Message(topic=topic, payload=payload, qos=1)
        conn.publish(msg)
        time.sleep(0.3)
    
    time.sleep(1)
    
    print("\n✓ Demonstrated callback routing")
    
    del conn
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("PyQTTier Real MQTT Connection Examples")
    print("=" * 60)
    print("\nNOTE: These examples require a running MQTT broker on localhost:1883")
    print("You can start one with: docker run -p 1883:1883 eclipse-mosquitto")
    print("=" * 60 + "\n")
    
    try:
        example_basic_connection()
        example_publish_subscribe()
        example_retained_messages()
        example_wildcard_subscriptions()
        example_request_response()
        example_multiple_callbacks()
        
        print("=" * 60)
        print("All examples completed successfully! ✨")
        print("=" * 60 + "\n")
    
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("\nMake sure you have an MQTT broker running on localhost:1883")
        print("Start one with: docker run -p 1883:1883 eclipse-mosquitto")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

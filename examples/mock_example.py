#!/usr/bin/env python3
"""
Example demonstrating how to use MockConnection for testing MQTT-based applications.

This example shows:
1. Publishing messages
2. Subscribing to topics with callbacks
3. Using global message callbacks
4. Topic wildcard matching
5. Simulating received messages
6. Verifying published messages
"""

import sys
from pathlib import Path

# Add src to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from pyqttier.mock import MockConnection
from pyqttier.message import Message


def example_basic_publish_subscribe():
    """Example 1: Basic publish and subscribe with callbacks."""
    print("=" * 60)
    print("Example 1: Basic Publish and Subscribe")
    print("=" * 60)
    
    # Create a mock connection
    conn = MockConnection().set_connected(True)

    # Publish a message
    msg = Message(
        topic="sensors/temperature",
        payload=b"23.5",
        qos=1,
        retain=False
    )
    fut = conn.publish(msg)
    print(f"📤 Published temperature reading: {msg.payload.decode()}°C")
    
    assert len(conn.published_messages) == 1, "Should have one published message"

    # Verify the message was received
    print(f"✓ Published {len(conn.published_messages)} message.\n")

def example_basic_subscribe():
    """Example 2: Basic subscribe with topic filter and callback."""
    print("=" * 60)
    print("Example 2: Basic Subscribe with Callback")
    print("=" * 60)
    
    # Create a mock connection
    conn = MockConnection().set_connected(True)

    received_count = 0

    # Define a callback for received messages
    def message_callback(msg: Message):
        nonlocal received_count
        print(f"📥 Received message on topic '{msg.topic}': {msg.payload.decode()}")
        received_count += 1

    # Subscribe to a topic
    sub_id = conn.subscribe("sensors/+", message_callback)
    print(f"🔔 Subscribed to 'sensors/+' with subscription ID {sub_id}")

    # Simulate receiving a message
    incoming_msg = Message(
        topic="sensors/humidity",
        payload=b"45%",
        qos=1,
        retain=False
    )
    conn.simulate_message(incoming_msg)

    assert received_count == 1, "Should have received one message"
    print(f"✓ Received {received_count} message(s) via subscription.\n")

def example_request_response():
    """Example 3: Request-Response pattern using response topics."""
    print("=" * 60)
    print("Example 3: Request-Response Pattern")
    print("=" * 60)
    
    # Create a mock connection
    conn = MockConnection().set_connected(True)

    responses_received = 0

    # Define a callback for responses
    def response_callback(msg: Message):
        nonlocal responses_received
        responses_received += 1
        print(f"📥 Received response on topic '{msg.topic}': {msg.payload.decode()}")

    # Subscribe to the response topic
    response_topic = "responses/device123"
    conn.subscribe(response_topic, response_callback)
    print(f"🔔 Subscribed to response topic '{response_topic}'")

    # Simulate sending a request
    request_msg = Message(
        topic="requests/device123",
        payload=b"GetStatus",
        qos=1,
        retain=False,
        response_topic=response_topic
    )
    conn.publish(request_msg)
    print(f"📤 Sent request: {request_msg.payload.decode()}")

    assert len(conn.published_messages) == 1, "Should have one published request message"

    # Simulate receiving a response
    response_msg = Message(
        topic=response_topic,
        payload=b"Status: OK",
        qos=1,
        retain=False
    )
    conn.simulate_message(response_msg)

    assert responses_received == 1, "Should have received one response"

    print("✓ Completed request-response simulation.\n")

if __name__ == "__main__":
    example_basic_publish_subscribe()
    example_basic_subscribe()
    example_request_response()

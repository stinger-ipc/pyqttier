import unittest
from pyqttier.message import Message
from pyqttier.mock import MockConnection
from pyqttier.transport import MqttTransport, MqttTransportType
import threading


class TestMockConnection(unittest.TestCase):
    """Test MockConnection implementation."""

    def setUp(self):
        """Create a fresh mock connection for each test."""
        self.conn = MockConnection()

    def test_initial_state(self):
        """Test initial connection state."""
        self.assertTrue(self.conn.is_connected())
        self.assertEqual(len(self.conn.published_messages), 0)
        self.assertEqual(self.conn.get_subscription_count(), 0)

    def test_publish_message(self):
        """Test publishing a message."""
        msg = Message(topic="test/topic", payload=b"hello", qos=1)
        future = self.conn.publish(msg)

        # Future should be immediately resolved
        self.assertTrue(future.done())
        self.assertIsNone(future.result())

        # Message should be recorded
        published = self.conn.published_messages
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].topic, "test/topic")
        self.assertEqual(published[0].payload, b"hello")

    def test_publish_multiple_messages(self):
        """Test publishing multiple messages."""
        for i in range(5):
            msg = Message(topic=f"test/{i}", payload=f"msg{i}".encode(), qos=0)
            self.conn.publish(msg)

        published = self.conn.published_messages
        self.assertEqual(len(published), 5)
        self.assertEqual(published[2].topic, "test/2")

    def test_clear_published_messages(self):
        """Test clearing published messages."""
        msg = Message(topic="test", payload=b"test", qos=0)
        self.conn.publish(msg)
        self.assertEqual(len(self.conn.published_messages), 1)

        self.conn.clear_published_messages()
        self.assertEqual(len(self.conn.published_messages), 0)

    def test_subscribe_basic(self):
        """Test basic subscription."""
        sub_id = self.conn.subscribe("test/topic")
        self.assertIsInstance(sub_id, int)
        self.assertEqual(self.conn.get_subscription_count(), 1)

    def test_subscribe_with_callback(self):
        """Test subscription with callback."""
        received_messages = []

        def callback(msg: Message):
            received_messages.append(msg)

        sub_id = self.conn.subscribe("test/topic", callback)

        # Simulate receiving a message
        msg = Message(topic="test/topic", payload=b"hello", qos=0)
        self.conn.simulate_message(msg)

        # Callback should have been called
        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].topic, "test/topic")
        self.assertEqual(received_messages[0].payload, b"hello")
        self.assertEqual(received_messages[0].subscription_ids, [sub_id])

    def test_multiple_subscriptions(self):
        """Test multiple subscriptions with different callbacks."""
        topic1_messages = []
        topic2_messages = []

        self.conn.subscribe("topic/1", lambda msg: topic1_messages.append(msg))
        self.conn.subscribe("topic/2", lambda msg: topic2_messages.append(msg))

        self.conn.simulate_message(Message(topic="topic/1", payload=b"msg1", qos=0))
        self.conn.simulate_message(Message(topic="topic/2", payload=b"msg2", qos=0))

        self.assertEqual(len(topic1_messages), 1)
        self.assertEqual(len(topic2_messages), 1)
        self.assertEqual(topic1_messages[0].payload, b"msg1")
        self.assertEqual(topic2_messages[0].payload, b"msg2")

    def test_add_message_callback(self):
        """Test adding a global message callback."""
        received_messages = []

        def callback(msg: Message):
            received_messages.append(msg)

        self.conn.add_message_callback(callback)

        # Subscribe without a callback
        self.conn.subscribe("test/topic")

        # Simulate a message - should go to global callback
        msg = Message(topic="test/topic", payload=b"global", qos=0)
        self.conn.simulate_message(msg)

        self.assertEqual(len(received_messages), 1)
        self.assertEqual(received_messages[0].payload, b"global")

    def test_subscription_callback_priority(self):
        """Test that subscription callbacks take priority over global callbacks."""
        subscription_messages = []
        global_messages = []

        self.conn.subscribe(
            "specific/topic", lambda msg: subscription_messages.append(msg)
        )
        self.conn.add_message_callback(lambda msg: global_messages.append(msg))

        # Message matching subscription should only go to subscription callback
        self.conn.simulate_message(
            Message(topic="specific/topic", payload=b"test", qos=0)
        )

        self.assertEqual(len(subscription_messages), 1)
        self.assertEqual(len(global_messages), 0)

    def test_is_topic_sub_exact_match(self):
        """Test exact topic matching."""
        self.assertTrue(self.conn.is_topic_sub("test/topic", "test/topic"))
        self.assertFalse(self.conn.is_topic_sub("test/topic", "test/other"))

    def test_is_topic_sub_single_level_wildcard(self):
        """Test single-level wildcard (+) matching."""
        self.assertTrue(self.conn.is_topic_sub("test/topic", "test/+"))
        self.assertTrue(self.conn.is_topic_sub("test/anything", "test/+"))
        self.assertTrue(self.conn.is_topic_sub("a/b/c", "a/+/c"))
        self.assertFalse(self.conn.is_topic_sub("test/topic/extra", "test/+"))

    def test_is_topic_sub_multi_level_wildcard(self):
        """Test multi-level wildcard (#) matching."""
        self.assertTrue(self.conn.is_topic_sub("test/topic", "test/#"))
        self.assertTrue(self.conn.is_topic_sub("test/topic/subtopic", "test/#"))
        self.assertTrue(self.conn.is_topic_sub("test/a/b/c", "test/#"))
        self.assertFalse(self.conn.is_topic_sub("other/topic", "test/#"))

    def test_set_connected(self):
        """Test changing connection status."""
        self.assertTrue(self.conn.is_connected())

        self.conn.set_connected(False)
        self.assertFalse(self.conn.is_connected())

        self.conn.set_connected(True)
        self.assertTrue(self.conn.is_connected())

    def test_unsubscribe(self):
        """Test unsubscribing."""
        sub_id = self.conn.subscribe("test/topic")
        self.assertEqual(self.conn.get_subscription_count(), 1)

        self.conn.unsubscribe(sub_id)
        self.assertEqual(self.conn.get_subscription_count(), 0)

    def test_thread_safety(self):
        """Test thread safety of mock connection."""

        def publish_worker():
            for i in range(10):
                msg = Message(topic=f"thread/test/{i}", payload=b"test", qos=0)
                self.conn.publish(msg)

        threads = [threading.Thread(target=publish_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 50 messages total
        self.assertEqual(len(self.conn.published_messages), 50)


class TestMqttTransport(unittest.TestCase):
    """Test MqttTransport class."""

    def test_tcp_transport(self):
        """Test TCP transport configuration."""
        transport = MqttTransport(
            transport_type=MqttTransportType.TCP, host="localhost", port=1883
        )
        self.assertEqual(transport.transport, MqttTransportType.TCP)
        self.assertEqual(transport.host_or_path, "localhost")
        self.assertEqual(transport.port, 1883)

    def test_tcp_transport_default_port(self):
        """Test TCP transport with default port."""
        transport = MqttTransport(
            transport_type=MqttTransportType.TCP, host="broker.example.com"
        )
        self.assertEqual(transport.host_or_path, "broker.example.com")
        self.assertEqual(transport.port, 1883)

    def test_websocket_transport(self):
        """Test WebSocket transport configuration."""
        transport = MqttTransport(
            transport_type=MqttTransportType.WEBSOCKET, host="ws.example.com", port=8080
        )
        self.assertEqual(transport.transport, MqttTransportType.WEBSOCKET)
        self.assertEqual(transport.host_or_path, "ws.example.com")
        self.assertEqual(transport.port, 8080)

    def test_unix_socket_transport(self):
        """Test Unix socket transport configuration."""
        transport = MqttTransport(
            transport_type=MqttTransportType.UNIX, socket_path="/var/run/mqtt.sock"
        )
        self.assertEqual(transport.transport, MqttTransportType.UNIX)
        self.assertEqual(transport.host_or_path, "/var/run/mqtt.sock")
        self.assertEqual(transport.port, 0)


class TestInterface(unittest.TestCase):
    """Test interface compliance."""

    def test_mock_implements_interface(self):
        """Test that MockConnection implements all interface methods."""
        from pyqttier.interface import IBrokerConnection

        conn = MockConnection()
        self.assertIsInstance(conn, IBrokerConnection)

        # Verify all abstract methods are implemented
        self.assertTrue(callable(getattr(conn, "publish", None)))
        self.assertTrue(callable(getattr(conn, "subscribe", None)))
        self.assertTrue(callable(getattr(conn, "add_message_callback", None)))
        self.assertTrue(callable(getattr(conn, "is_topic_sub", None)))
        self.assertTrue(callable(getattr(conn, "is_connected", None)))

    def test_unpublish_retained(self):
        """Test the unpublish_retained helper method."""
        conn = MockConnection()
        conn.unpublish_retained("test/topic")

        published = conn.published_messages
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].topic, "test/topic")
        self.assertEqual(published[0].payload, b"")
        self.assertTrue(published[0].retain)
        self.assertEqual(published[0].qos, 1)


class TestMockConnectionMultipleCallbacks(unittest.TestCase):
    """Test MockConnection multi-callback subscription behaviour."""

    def setUp(self):
        self.conn = MockConnection()

    def test_same_topic_returns_same_sub_id(self):
        """Re-subscribing to the same topic returns the same subscription ID."""
        sub_id1 = self.conn.subscribe("test/topic")
        sub_id2 = self.conn.subscribe("test/topic")
        self.assertEqual(sub_id1, sub_id2)

    def test_same_topic_does_not_create_extra_subscription(self):
        """Re-subscribing to the same topic keeps the subscription count at 1."""
        self.conn.subscribe("test/topic")
        self.conn.subscribe("test/topic")
        self.assertEqual(self.conn.get_subscription_count(), 1)

    def test_multiple_callbacks_all_invoked(self):
        """All callbacks registered for a topic are called when a message arrives."""
        received_a = []
        received_b = []

        sub_id1 = self.conn.subscribe("test/topic", lambda msg: received_a.append(msg))
        sub_id2 = self.conn.subscribe("test/topic", lambda msg: received_b.append(msg))

        self.assertEqual(sub_id1, sub_id2)

        self.conn.simulate_message(Message(topic="test/topic", payload=b"hello", qos=0))

        self.assertEqual(len(received_a), 1)
        self.assertEqual(len(received_b), 1)
        self.assertEqual(received_a[0].payload, b"hello")
        self.assertEqual(received_b[0].payload, b"hello")

    def test_multiple_callbacks_correct_subscription_id(self):
        """Messages delivered to multi-callback subscriptions carry the correct sub ID."""
        received = []
        sub_id = self.conn.subscribe("test/topic", lambda msg: received.append(msg))
        self.conn.subscribe("test/topic", lambda msg: received.append(msg))

        self.conn.simulate_message(Message(topic="test/topic", payload=b"x", qos=0))

        for msg in received:
            self.assertEqual(msg.subscription_ids, [sub_id])

    def test_three_callbacks_all_invoked(self):
        """Three callbacks on the same topic are all invoked once per message."""
        counts = [0, 0, 0]
        self.conn.subscribe("a/b", lambda msg: counts.__setitem__(0, counts[0] + 1))
        self.conn.subscribe("a/b", lambda msg: counts.__setitem__(1, counts[1] + 1))
        self.conn.subscribe("a/b", lambda msg: counts.__setitem__(2, counts[2] + 1))

        self.conn.simulate_message(Message(topic="a/b", payload=b"", qos=0))

        self.assertEqual(counts, [1, 1, 1])

    def test_callback_added_without_prior_callback(self):
        """A callback added to a subscription that was created without one is called."""
        received = []
        self.conn.subscribe("test/topic")  # no callback
        self.conn.subscribe("test/topic", lambda msg: received.append(msg))

        self.conn.simulate_message(Message(topic="test/topic", payload=b"hi", qos=0))

        self.assertEqual(len(received), 1)

    def test_independent_topics_unaffected(self):
        """Adding callbacks to one topic does not affect delivery to another topic."""
        topic1_msgs = []
        topic2_msgs = []

        self.conn.subscribe("t/1", lambda msg: topic1_msgs.append(msg))
        self.conn.subscribe("t/1", lambda msg: topic1_msgs.append(msg))
        self.conn.subscribe("t/2", lambda msg: topic2_msgs.append(msg))

        self.conn.simulate_message(Message(topic="t/1", payload=b"one", qos=0))
        self.conn.simulate_message(Message(topic="t/2", payload=b"two", qos=0))

        self.assertEqual(len(topic1_msgs), 2)  # two callbacks on t/1
        self.assertEqual(len(topic2_msgs), 1)


if __name__ == "__main__":
    unittest.main()

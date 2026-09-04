import unittest
from pyqttier.message import Message
from paho.mqtt.client import MQTTMessage
from paho.mqtt.properties import Properties as MqttProperties
from paho.mqtt.packettypes import PacketTypes


class TestMessage(unittest.TestCase):
    """Test Message class."""

    def test_set_user_property_initializes_dict(self):
        """Test that set_user_property initializes user_properties when None."""
        msg = Message(topic="test", payload=b"data", qos=0)
        # user_properties should be initialized to empty dict in __post_init__
        self.assertIsNotNone(msg.user_properties)

        msg.set_user_property("key1", "value1")
        self.assertEqual(msg.user_properties["key1"], "value1")

    def test_set_user_property_single_property(self):
        """Test setting a single user property."""
        msg = Message(topic="test", payload=b"data", qos=0)
        msg.set_user_property("color", "red")

        self.assertEqual(len(msg.user_properties), 1)
        self.assertEqual(msg.user_properties["color"], "red")

    def test_set_user_property_multiple_properties(self):
        """Test setting multiple user properties."""
        msg = Message(topic="test", payload=b"data", qos=0)
        msg.set_user_property("color", "red")
        msg.set_user_property("size", "large")
        msg.set_user_property("quantity", "10")

        self.assertEqual(len(msg.user_properties), 3)
        self.assertEqual(msg.user_properties["color"], "red")
        self.assertEqual(msg.user_properties["size"], "large")
        self.assertEqual(msg.user_properties["quantity"], "10")

    def test_set_user_property_overwrites_existing(self):
        """Test that set_user_property overwrites existing values."""
        msg = Message(topic="test", payload=b"data", qos=0)
        msg.set_user_property("key", "value1")
        self.assertEqual(msg.user_properties["key"], "value1")

        msg.set_user_property("key", "value2")
        self.assertEqual(msg.user_properties["key"], "value2")
        self.assertEqual(len(msg.user_properties), 1)

    def test_set_user_property_empty_string_value(self):
        """Test setting a user property with an empty string value."""
        msg = Message(topic="test", payload=b"data", qos=0)
        msg.set_user_property("empty", "")

        self.assertEqual(msg.user_properties["empty"], "")

    def test_set_user_property_special_characters(self):
        """Test setting user properties with special characters."""
        msg = Message(topic="test", payload=b"data", qos=0)
        msg.set_user_property("special-key_123", "value-with-special_chars!@#")

        self.assertEqual(
            msg.user_properties["special-key_123"], "value-with-special_chars!@#"
        )

    def test_set_user_property_with_initial_properties(self):
        """Test set_user_property when initialized with existing properties."""
        initial_props = {"existing": "value"}
        msg = Message(
            topic="test", payload=b"data", qos=0, user_properties=initial_props
        )

        msg.set_user_property("new_key", "new_value")

        self.assertEqual(len(msg.user_properties), 2)
        self.assertEqual(msg.user_properties["existing"], "value")
        self.assertEqual(msg.user_properties["new_key"], "new_value")

    def test_default_values(self):
        """Test that a minimal Message has the expected default field values."""
        msg = Message(topic="test/topic", payload=b"data", qos=1)

        self.assertEqual(msg.topic, "test/topic")
        self.assertEqual(msg.payload, b"data")
        self.assertEqual(msg.qos, 1)
        self.assertFalse(msg.retain)
        self.assertIsNone(msg.content_type)
        self.assertIsNone(msg.correlation_data)
        self.assertIsNone(msg.response_topic)
        self.assertEqual(msg.subscription_ids, [])
        self.assertIsNone(msg.message_expiry_interval)
        self.assertEqual(msg.user_properties, {})

    def test_post_init_with_explicit_none_user_properties(self):
        """Test that passing user_properties=None explicitly is normalized to {}."""
        msg = Message(topic="test", payload=b"", qos=0, user_properties=None)
        self.assertEqual(msg.user_properties, {})

    def test_paho_kwargs_minimal_fields(self):
        """Test paho_kwargs with only required fields set."""
        msg = Message(topic="test/topic", payload=b"hello", qos=1)
        kwargs = msg.paho_kwargs()

        self.assertEqual(kwargs["topic"], "test/topic")
        self.assertEqual(kwargs["payload"], b"hello")
        self.assertEqual(kwargs["qos"], 1)
        self.assertFalse(kwargs["retain"])

        props = kwargs["properties"]
        self.assertNotIn("ContentType", props.__dict__)
        self.assertNotIn("CorrelationData", props.__dict__)
        self.assertNotIn("ResponseTopic", props.__dict__)
        self.assertNotIn("MessageExpiryInterval", props.__dict__)
        self.assertNotIn("UserProperty", props.__dict__)

    def test_paho_kwargs_retain_flag(self):
        """Test that the retain flag is passed through to paho_kwargs."""
        msg = Message(topic="test", payload=b"", qos=2, retain=True)
        kwargs = msg.paho_kwargs()
        self.assertTrue(kwargs["retain"])
        self.assertEqual(kwargs["qos"], 2)

    def test_paho_kwargs_with_optional_properties(self):
        """Test that optional properties are set on the paho Properties object."""
        msg = Message(
            topic="test",
            payload=b"data",
            qos=1,
            content_type="application/json",
            correlation_data=b"corr-id",
            response_topic="resp/topic",
            message_expiry_interval=60,
        )
        props = msg.paho_kwargs()["properties"]

        self.assertEqual(props.ContentType, "application/json")
        self.assertEqual(props.CorrelationData, b"corr-id")
        self.assertEqual(props.ResponseTopic, "resp/topic")
        self.assertEqual(props.MessageExpiryInterval, 60)

    def test_paho_kwargs_with_user_properties(self):
        """Test that non-empty user_properties are converted to UserProperty pairs."""
        msg = Message(topic="test", payload=b"", qos=0)
        msg.set_user_property("k1", "v1")
        msg.set_user_property("k2", "v2")

        props = msg.paho_kwargs()["properties"]
        self.assertEqual(
            sorted(props.UserProperty), sorted([("k1", "v1"), ("k2", "v2")])
        )

    def test_paho_kwargs_empty_user_properties_omitted(self):
        """Test that empty user_properties do not set UserProperty on the properties object."""
        msg = Message(topic="test", payload=b"", qos=0)
        props = msg.paho_kwargs()["properties"]
        self.assertNotIn("UserProperty", props.__dict__)

    @staticmethod
    def _make_paho_message(topic, payload, qos=0, retain=False, properties=None):
        """Helper to build a real paho MQTTMessage for from_paho_message tests."""
        paho_msg = MQTTMessage(topic=topic.encode())
        paho_msg.payload = payload
        paho_msg.qos = qos
        paho_msg.retain = retain
        if properties is not None:
            paho_msg.properties = properties
        return paho_msg

    def test_from_paho_message_basic_fields(self):
        """Test conversion of core fields with no MQTT v5 properties set."""
        props = MqttProperties(PacketTypes.PUBLISH)
        paho_msg = self._make_paho_message(
            "test/topic", b"hello", qos=1, retain=True, properties=props
        )

        msg = Message.from_paho_message(paho_msg)

        self.assertEqual(msg.topic, "test/topic")
        self.assertEqual(msg.payload, b"hello")
        self.assertEqual(msg.qos, 1)
        self.assertTrue(msg.retain)
        self.assertIsNone(msg.content_type)
        self.assertEqual(msg.user_properties, {})
        self.assertEqual(msg.subscription_ids, [])

    def test_from_paho_message_with_all_properties(self):
        """Test conversion of all optional MQTT v5 properties."""
        props = MqttProperties(PacketTypes.PUBLISH)
        props.ContentType = "text/plain"
        props.CorrelationData = b"abc123"
        props.ResponseTopic = "reply/topic"
        props.MessageExpiryInterval = 3600
        props.UserProperty = [("a", "1"), ("b", "2")]
        paho_msg = self._make_paho_message("test", b"data", properties=props)

        msg = Message.from_paho_message(paho_msg)

        self.assertEqual(msg.content_type, "text/plain")
        self.assertEqual(msg.correlation_data, b"abc123")
        self.assertEqual(msg.response_topic, "reply/topic")
        self.assertEqual(msg.message_expiry_interval, 3600)
        self.assertEqual(msg.user_properties, {"a": "1", "b": "2"})

    def test_from_paho_message_subscription_id_single_int(self):
        """Test that a single SubscriptionIdentifier is wrapped into a list."""
        props = MqttProperties(PacketTypes.PUBLISH)
        props.SubscriptionIdentifier = 5
        paho_msg = self._make_paho_message("test", b"", properties=props)

        msg = Message.from_paho_message(paho_msg)
        self.assertEqual(msg.subscription_ids, [5])

    def test_from_paho_message_subscription_id_list(self):
        """Test that a list of SubscriptionIdentifiers is preserved as-is."""
        props = MqttProperties(PacketTypes.PUBLISH)
        props.SubscriptionIdentifier = [1, 2, 3]
        paho_msg = self._make_paho_message("test", b"", properties=props)

        msg = Message.from_paho_message(paho_msg)
        self.assertEqual(msg.subscription_ids, [1, 2, 3])

    def test_from_paho_message_missing_properties_raises(self):
        """Test current behavior when paho_msg.properties is left as None (default).

        MQTTMessage initializes `properties` to None, and from_paho_message
        unconditionally accesses `.properties.__dict__`, so this raises
        AttributeError rather than falling back to an empty dict.
        """
        paho_msg = MQTTMessage(topic=b"test/topic")
        paho_msg.payload = b"data"
        with self.assertRaises(AttributeError):
            Message.from_paho_message(paho_msg)

    def test_round_trip_paho_kwargs_and_from_paho_message(self):
        """Test that paho_kwargs -> MQTTMessage -> from_paho_message round-trips."""
        original = Message(
            topic="round/trip",
            payload=b"payload-data",
            qos=2,
            retain=True,
            content_type="application/json",
            correlation_data=b"corr",
            response_topic="resp",
            message_expiry_interval=120,
        )
        original.set_user_property("x", "y")

        kwargs = original.paho_kwargs()
        paho_msg = MQTTMessage(topic=kwargs["topic"].encode())
        paho_msg.payload = kwargs["payload"]
        paho_msg.qos = kwargs["qos"]
        paho_msg.retain = kwargs["retain"]
        paho_msg.properties = kwargs["properties"]

        reconstructed = Message.from_paho_message(paho_msg)

        self.assertEqual(reconstructed.topic, original.topic)
        self.assertEqual(reconstructed.payload, original.payload)
        self.assertEqual(reconstructed.qos, original.qos)
        self.assertEqual(reconstructed.retain, original.retain)
        self.assertEqual(reconstructed.content_type, original.content_type)
        self.assertEqual(reconstructed.correlation_data, original.correlation_data)
        self.assertEqual(reconstructed.response_topic, original.response_topic)
        self.assertEqual(
            reconstructed.message_expiry_interval, original.message_expiry_interval
        )
        self.assertEqual(reconstructed.user_properties, original.user_properties)


if __name__ == "__main__":
    unittest.main()

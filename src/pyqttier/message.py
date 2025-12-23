from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from paho.mqtt.client import MQTTMessage
from paho.mqtt.properties import Properties as MqttProperties
from paho.mqtt.packettypes import PacketTypes

@dataclass
class Message:
    topic: str
    payload: bytes
    qos: int
    retain: bool = False
    content_type: Optional[str] = None
    correlation_data: Optional[bytes] = None
    response_topic: Optional[str] = None
    subscription_id: Optional[int] = None  # Ignored on publish
    message_expiry_interval: Optional[int] = None
    user_properties: Optional[Dict[str, str]] = field(default_factory=dict)

    def __post_init__(self):
        if self.user_properties is None:
            self.user_properties = dict()

    def paho_kwargs(self) -> Dict[str, Any]:
        props = MqttProperties(PacketTypes.PUBLISH)
        if self.content_type is not None:
            props.ContentType = self.content_type
        if self.correlation_data is not None:
            props.CorrelationData = self.correlation_data
        if self.response_topic is not None:
            props.ResponseTopic = self.response_topic
        if self.message_expiry_interval is not None:
            props.MessageExpiryInterval = self.message_expiry_interval
        if self.user_properties is not None and len(self.user_properties) > 0:
            props.UserProperty = list(self.user_properties.items())
        kwargs = {
            "topic": self.topic,
            "payload": self.payload,
            "qos": self.qos,
            "retain": self.retain,
            "properties": props,
        }
        return kwargs

    @classmethod
    def from_paho_message(cls, paho_msg: MQTTMessage) -> "Message":
        msg_obj = cls(
            topic=paho_msg.topic,
            payload=paho_msg.payload,
            qos=paho_msg.qos,
            retain=paho_msg.retain,
        )
        properties = (
            paho_msg.properties.__dict__ if hasattr(paho_msg, "properties") else {}
        )
        if "UserProperty" in properties:
            msg_obj.user_properties = dict(properties["UserProperty"])
        if "ContentType" in properties:
            msg_obj.content_type = properties["ContentType"]
        if "CorrelationData" in properties:
            msg_obj.correlation_data = properties["CorrelationData"]
        if "ResponseTopic" in properties:
            msg_obj.response_topic = properties["ResponseTopic"]
        if "MessageExpiryInterval" in properties:
            msg_obj.message_expiry_interval = properties["MessageExpiryInterval"]
        if "SubscriptionIdentifier" in properties:
            msg_obj.subscription_id = properties["SubscriptionIdentifier"]
        return msg_obj

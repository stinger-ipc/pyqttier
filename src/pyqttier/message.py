from dataclasses import dataclass, field
from typing import Optional, Dict, Union, Any
from paho.mqtt.client import MQTTMessage
from paho.mqtt.properties import Properties as MqttProperties
from paho.mqtt.packettypes import PacketTypes
from pydantic import BaseModel
from enum import Enum
import uuid


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
        return msg_obj

    @classmethod
    def status_message(
        cls, topic, status_message: BaseModel, expiry_seconds: int
    ) -> "Message":
        return cls(
            topic=topic,
            payload=status_message.model_dump_json(by_alias=True).encode("utf-8"),
            qos=1,
            retain=True,
            message_expiry_interval=expiry_seconds,
        )

    @classmethod
    def error_response_message(
        cls,
        topic: str,
        return_code: int,
        correlation_id: Union[str, bytes],
        debug_info: Optional[str] = None,
    ) -> "Message":
        msg_obj = cls(
            topic=topic,
            payload=b"{}",
            qos=1,
            retain=False,
            correlation_data=(
                correlation_id.encode("utf-8")
                if isinstance(correlation_id, str)
                else correlation_id
            ),
            user_properties={"ReturnCode": str(return_code)},
        )
        if (
            debug_info is not None and msg_obj.user_properties is not None
        ):  # user_properties should never be None here, but checking to satisfy type checker
            msg_obj.user_properties["DebugInfo"] = debug_info
        return msg_obj

    @classmethod
    def response_message(
        cls,
        response_topic: str,
        response_obj: BaseModel,
        return_code: int,
        correlation_id: Union[str, bytes],
    ) -> "Message":
        msg_obj = cls(
            topic=response_topic,
            payload=response_obj.model_dump_json(by_alias=True).encode("utf-8"),
            qos=1,
            retain=False,
            correlation_data=(
                correlation_id.encode("utf-8")
                if isinstance(correlation_id, str)
                else correlation_id
            ),
            user_properties={"ReturnCode": str(return_code)},
        )
        return msg_obj

    @classmethod
    def property_state_message(
        cls, topic: str, state_obj: BaseModel, state_version: Optional[int] = None
    ) -> "Message":
        msg_obj = cls(
            topic=topic,
            payload=state_obj.model_dump_json(by_alias=True).encode("utf-8"),
            qos=1,
            retain=True,
        )
        if state_version is not None:
            msg_obj.user_properties = {"PropertyVersion": str(state_version)}
        return msg_obj

    @classmethod
    def property_update_request_message(
        cls,
        topic: str,
        property_obj: BaseModel,
        version: str,
        response_topic: str,
        correlation_id: Union[str, bytes, None] = None,
    ) -> "Message":
        msg_obj = cls(
            topic=topic,
            payload=property_obj.model_dump_json(by_alias=True).encode("utf-8"),
            qos=1,
            retain=False,
            response_topic=response_topic,
            correlation_data=(
                correlation_id.encode("utf-8")
                if isinstance(correlation_id, str)
                else correlation_id
            ),
            user_properties={"PropertyVersion": str(version)},
        )
        return msg_obj

    @classmethod
    def property_response_message(
        cls,
        response_topic: str,
        property_obj: BaseModel,
        version: str,
        return_code: int,
        correlation_id: Union[str, bytes],
        debug_info: Optional[str] = None,
    ) -> "Message":
        msg_obj = cls(
            topic=response_topic,
            payload=property_obj.model_dump_json(by_alias=True).encode("utf-8"),
            qos=1,
            retain=False,
            correlation_data=(
                correlation_id.encode("utf-8")
                if isinstance(correlation_id, str)
                else correlation_id
            ),
            user_properties={
                "ReturnCode": str(return_code),
                "PropertyVersion": str(version),
            },
        )
        if (
            debug_info is not None and msg_obj.user_properties is not None
        ):  # user_properties should never be None here, but checking to satisfy type checker
            msg_obj.user_properties["DebugInfo"] = debug_info
        return msg_obj

    @classmethod
    def publish_request(
        cls,
        topic: str,
        request_obj: BaseModel,
        response_topic: str,
        correlation_id: Union[str, bytes, None] = None,
    ) -> "Message":
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        msg_obj = cls(
            topic=topic,
            payload=request_obj.model_dump_json(by_alias=True).encode("utf-8"),
            qos=1,
            retain=False,
            response_topic=response_topic,
            correlation_data=(
                correlation_id.encode("utf-8")
                if isinstance(correlation_id, str)
                else correlation_id
            ),
        )
        return msg_obj

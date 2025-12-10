from concurrent.futures import Future
import logging
import threading
import uuid
from typing import Callable, Optional, Tuple, Any, Union, List, Dict
from paho.mqtt.client import Client as MqttClient, topic_matches_sub
from paho.mqtt.enums import MQTTProtocolVersion, CallbackAPIVersion
from paho.mqtt.properties import Properties as MqttProperties
from paho.mqtt.packettypes import PacketTypes
from queue import Queue, Empty
from .interface import IBrokerConnection, MessageCallback
from .transport import MqttTransport
from .message import Message
from .lwt import OnlinePresence
from dataclasses import dataclass

logging.basicConfig(level=logging.DEBUG)


class Mqtt5Connection(IBrokerConnection):

    @dataclass
    class PendingSubscription:
        topic: str
        subscription_id: int

    @dataclass
    class PendingPublish:
        msg: Message
        future: Future

    def __init__(
        self,
        transport: MqttTransport,
        client_id: Optional[str] = None,
        lwt: Optional[OnlinePresence] = None,
    ):
        self._logger = logging.getLogger("MqttConnection")
        self._transport = transport
        self._client_id = client_id or str(uuid.uuid4())
        self._queued_messages = Queue()  # type: Queue[Mqtt5Connection.PendingPublish]
        self._queued_subscriptions = (
            Queue()
        )  # type: Queue[Mqtt5Connection.PendingSubscription]
        self._connected: bool = False

        lwt_properties = MqttProperties(PacketTypes.PUBLISH)
        lwt_properties.ContentType = "application/json"
        lwt_properties.MessageExpiryInterval = 60 * 60 * 24  # 1 day
        self._lwt = lwt or OnlinePresence.default(self._client_id)

        self._connect_inner_mqtt_client()

        self._message_handling_lock = threading.Lock()
        with self._message_handling_lock:
            self._subscription_callbacks = dict()  # type: Dict[int, MessageCallback]
            self._message_callbacks = []  # type: List[MessageCallback]

        self._publishing_lock = threading.Lock()
        with self._publishing_lock:
            self._publish_futures = dict()  # type: Dict[int, Future]

        self._client.loop_start()
        self._next_subscription_id = 10

    def _connect_inner_mqtt_client(self):
        """
        Private method to be called from constructor only.
        """
        self._client = MqttClient(
            CallbackAPIVersion.VERSION2,
            protocol=MQTTProtocolVersion.MQTTv5,
            transport=self._transport.transport.value,
            client_id=self._client_id,
            reconnect_on_failure=True,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_publish = self.on_publish_complete
        self._client.will_set(**self._lwt.online.paho_kwargs())
        host = self._transport.host_or_path or "localhost"
        self._client.connect(host, self._transport.port)

    def __del__(self):
        if self._lwt is not None:
            self._client.publish(**self._lwt.offline.paho_kwargs()).wait_for_publish()
        self._client.disconnect()
        self._client.loop_stop()

    @property
    def online_topic(self) -> str:
        return self._lwt.topic

    @property
    def client_id(self) -> str:
        return self._client_id

    def is_connected(self) -> bool:
        return self._connected

    def get_next_subscription_id(self) -> int:
        sub_id = self._next_subscription_id
        self._next_subscription_id += 1
        return sub_id

    def add_message_callback(self, callback: MessageCallback):
        self._message_callbacks.append(callback)

    def _on_message(self, client, userdata, msg):
        self._logger.debug("Got a message to %s : %s", msg.topic, msg.payload.decode())
        message = Message.from_paho_message(msg)
        if message.subscription_id is not None:
            sub_id = message.subscription_id
            with self._message_handling_lock:
                if sub_id in self._subscription_callbacks:
                    self._subscription_callbacks[sub_id](message)
                    return
        with self._message_handling_lock:
            for callback in self._message_callbacks:
                callback(message)

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:  # Connection successful
            self._connected = True
            self._logger.info(
                "Connected to %s:%d", self._transport.host_or_path, self._transport.port
            )
            while not self._queued_subscriptions.empty():
                try:
                    pending_subscr = self._queued_subscriptions.get_nowait()
                except Empty:
                    break
                else:
                    self._logger.debug(
                        "Connected and subscribing to %s", pending_subscr.topic
                    )
                    sub_props = MqttProperties(PacketTypes.SUBSCRIBE)
                    sub_props.SubscriptionIdentifier = pending_subscr.subscription_id
                    self._client.subscribe(
                        pending_subscr.topic, qos=1, properties=sub_props
                    )
            while not self._queued_messages.empty():
                try:
                    msg = self._queued_messages.get_nowait()
                except Empty:
                    break
                else:
                    self._logger.info(f"Publishing queued up message")
                    pub_info = self._client.publish(**msg.msg.paho_kwargs())
                    with self._publishing_lock:
                        self._publish_futures[pub_info.mid] = msg.future

            self._client.publish(**self._lwt.online.paho_kwargs())
        else:
            self._logger.error(
                "Connection failed with reason code %s", str(reason_code)
            )
            self._connected = False

    def on_publish_complete(
        self, client, userdata, mid, reason_code=None, properties=None
    ):
        with self._publishing_lock:
            if mid in self._publish_futures:
                fut = self._publish_futures.pop(mid)
                fut.set_result(None)

    def publish(self, message: Message) -> Future:
        """Publish a message to mqtt, or queue it if not connected yet.  Returns a Future that completes when the message is published."""
        fut = Future()  # type: Future
        if self._connected:
            self._logger.info("Publishing %s", message.topic)
            msg_info = self._client.publish(**message.paho_kwargs())
            with self._publishing_lock:
                self._publish_futures[msg_info.mid] = fut
        else:
            self._logger.info("Queueing %s for publishing later", message.topic)
            pending_pub = self.PendingPublish(msg=message, future=fut)
            self._queued_messages.put(pending_pub)
        return fut

    def subscribe(self, topic: str, callback: Optional[MessageCallback] = None) -> int:
        """Subscribes to a topic. If the connection is not established, the subscription is queued.
        Returns the subscription ID.
        """
        sub_id = self.get_next_subscription_id()
        if self._connected:
            self._logger.debug("Subscribing to %s", topic)
            sub_props = MqttProperties(PacketTypes.SUBSCRIBE)
            sub_props.SubscriptionIdentifier = sub_id
            self._client.subscribe(topic, qos=1, properties=sub_props)
        else:
            self._logger.debug("Pending subscription to %s", topic)
            self._queued_subscriptions.put(self.PendingSubscription(topic, sub_id))
        if callback is not None:
            self._subscription_callbacks[sub_id] = callback
        return sub_id

    def is_topic_sub(self, topic: str, sub: str) -> bool:
        return topic_matches_sub(sub, topic)

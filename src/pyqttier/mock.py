from concurrent.futures import Future
from typing import Optional, Dict, List, Callable, Tuple
from copy import copy
from .interface import IBrokerConnection, MessageCallback
from .message import Message
import threading
import logging

class MockConnection(IBrokerConnection):
    """
    Mock implementation of IBrokerConnection for testing purposes.
    Simulates broker behavior without requiring an actual MQTT broker.
    """

    def __init__(self):
        self._connected = True
        self._subscriptions = (
            {}
        )  # type: Dict[int, Tuple[str, Optional[MessageCallback]]]
        self._message_callbacks = []  # type: List[MessageCallback]
        self._published_messages = []  # type: List[Message]
        self._next_subscription_id = 1  # type: int
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.info("Initialized MockConnection")

    @property
    def client_id(self) -> str:
        return "mock-client"
    
    @property
    def online_topic(self) -> Optional[str]:
        return None

    @property
    def published_messages(self) -> List[Message]:
        """Returns list of all published messages for testing verification."""
        with self._lock:
            return self._published_messages.copy()

    def clear_published_messages(self) -> None:
        """Clears the list of published messages."""
        with self._lock:
            self._published_messages.clear()

    def find_published(self, topic: str) -> List[Message]:
        """
        Find published messages matching the given topic pattern (supports wildcards).
        
        Args:
            topic: Topic pattern to match, supports MQTT wildcards (+ and #)
        
        Returns:
            List of messages that match the topic pattern
        """
        with self._lock:
            return [msg for msg in self._published_messages if self.is_topic_sub(msg.topic, topic)]

    def set_connected(self, connected: bool) -> "MockConnection":
        """Sets the connection status for testing."""
        with self._lock:
            self._connected = connected
        return self

    def simulate_message(self, message: Message) -> None:
        """
        Simulates receiving a message from the broker.
        Triggers appropriate callbacks based on subscriptions.
        """
        self._logger.debug("Simulating incoming message on topic: %s", message.topic)
        with self._lock:
            # Check subscription-specific callbacks
            for sub_id, (topic_filter, callback) in self._subscriptions.items():
                if self.is_topic_sub(message.topic, topic_filter):
                    if callback is not None:
                        receiving_msg = copy(message)
                        receiving_msg.subscription_ids = [sub_id]
                        callback(receiving_msg)
                        return

            # If no specific callback matched, call general message callbacks
            self._logger.debug("No subscription-specific callback matched, calling general callbacks")
            for callback in self._message_callbacks:
                callback(message)

    def publish(self, message: Message) -> Future:
        """
        Records the published message and returns a completed Future.
        """
        self._logger.debug("Publishing message to topic: %s", message.topic)
        with self._lock:
            self._published_messages.append(message)

        future: Future = Future()
        future.set_result(None)
        return future

    def subscribe(self, topic: str, callback: Optional[MessageCallback] = None, qos: int = 1) -> int:
        """
        Registers a subscription and returns a subscription ID.
        """
        self._logger.debug("Subscribe to topic: %s", topic)
        with self._lock:
            sub_id = self._next_subscription_id
            self._next_subscription_id += 1
            self._subscriptions[sub_id] = (topic, callback)
            return sub_id

    def add_message_callback(self, callback: MessageCallback) -> None:
        """
        Adds a callback for messages without specific subscription callbacks.
        """
        with self._lock:
            self._message_callbacks.append(callback)

    def is_topic_sub(self, topic: str, sub: str) -> bool:
        """
        Simple topic matching implementation.
        Supports MQTT wildcards: + (single level) and # (multi level).
        """
        topic_parts = topic.split("/")
        sub_parts = sub.split("/")

        # # must be last and matches everything after
        if "#" in sub_parts:
            hash_idx = sub_parts.index("#")
            if hash_idx != len(sub_parts) - 1:
                return False  # # must be last
            sub_parts = sub_parts[:hash_idx]
            topic_parts = topic_parts[:hash_idx]

        if len(topic_parts) != len(sub_parts):
            return False

        for topic_part, sub_part in zip(topic_parts, sub_parts):
            if sub_part == "+":
                continue  # + matches any single level
            if topic_part != sub_part:
                return False

        return True

    def is_connected(self) -> bool:
        """Returns the connection status."""
        with self._lock:
            return self._connected

    def unsubscribe(self, subscription_id: int) -> None:
        """
        Helper method to unsubscribe by subscription ID.
        Not part of the interface but useful for testing.
        """
        with self._lock:
            if subscription_id in self._subscriptions:
                del self._subscriptions[subscription_id]

    def get_subscription_count(self) -> int:
        """
        Returns the number of active subscriptions.
        Helper method for testing.
        """
        with self._lock:
            return len(self._subscriptions)

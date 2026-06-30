#!/usr/bin/env python3
"""Smoke test for pyqttier against a live MQTT broker.

Requires a broker running on localhost:1883 (configurable via MQTT_HOSTNAME / MQTT_PORT).
Exits with code 1 immediately if the broker is unreachable.

Usage:
    python examples/smoke_test.py
    MQTT_HOSTNAME=mybroker MQTT_PORT=1884 python examples/smoke_test.py

Scenarios:
  1. Two-way pub/sub          — two clients exchange messages in both directions
  2. Per-subscription callback — specific callbacks route correctly; global callback
                                  is NOT invoked for messages with matching MQTT5
                                  subscription IDs (correct MQTT5 behavior)
  3. Wildcard subscriptions   — single-level (+) and multi-level (#) wildcards
  4. Retained messages        — new subscriber receives a message published before it connected
  5. QoS levels               — QoS 0, 1, and 2 messages are delivered
  6. LWT / online presence    — online:true on connect, online:false on disconnect
  7. Request / response       — response_topic + correlation_data round-trip
"""
import os
import sys
import time
import threading
from typing import Callable, Dict, List, Optional

from pyqttier.connection import Mqtt5Connection
from pyqttier.message import Message
from pyqttier.transport import MqttTransport, MqttTransportType

# ── Configuration ──────────────────────────────────────────────────────────────

HOSTNAME = os.getenv("MQTT_HOSTNAME", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))

CONNECT_TIMEOUT = 5.0  # seconds to wait for broker connection
MSG_TIMEOUT = 5.0  # seconds to wait for a message to arrive

# Unique run prefix so consecutive runs never interfere via retained messages.
RUN_ID = str(int(time.time() * 1000))[-8:]


# ── Utilities ──────────────────────────────────────────────────────────────────


class Collector:
    """Thread-safe message collector usable directly as an MQTT callback."""

    def __init__(self) -> None:
        self._messages: List[Message] = []
        self._lock = threading.RLock()
        self._event = threading.Event()

    def __call__(self, msg: Message) -> None:
        with self._lock:
            self._messages.append(msg)
        self._event.set()

    def wait_for(
        self,
        predicate: Callable[[], bool],
        timeout: float = MSG_TIMEOUT,
    ) -> bool:
        """Block until *predicate* returns True or *timeout* expires."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                if predicate():
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._event.wait(timeout=remaining)
            self._event.clear()
        with self._lock:
            return predicate()

    @property
    def messages(self) -> List[Message]:
        with self._lock:
            return list(self._messages)

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()
        self._event.clear()


def _make_transport() -> MqttTransport:
    return MqttTransport(transport_type=MqttTransportType.TCP, host=HOSTNAME, port=PORT)


def connect(client_id: str) -> Mqtt5Connection:
    """Create an Mqtt5Connection and block until connected.

    Exits the process immediately (exit code 1) if the broker cannot be
    reached within CONNECT_TIMEOUT seconds.
    """
    conn = Mqtt5Connection(transport=_make_transport(), client_id=client_id)
    deadline = time.monotonic() + CONNECT_TIMEOUT
    while not conn.is_connected() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not conn.is_connected():
        print(
            f"\nFATAL: broker unreachable at {HOSTNAME}:{PORT} "
            f"(waited {CONNECT_TIMEOUT:.0f}s). Is the broker running?"
        )
        sys.exit(1)
    return conn


def publish_sync(
    conn: Mqtt5Connection,
    msg: Message,
    timeout: float = MSG_TIMEOUT,
) -> None:
    """Publish *msg* and block until the broker acknowledges it."""
    future = conn.publish(msg)
    future.result(timeout=timeout)


# ── Test runner ────────────────────────────────────────────────────────────────

_results: Dict[str, bool] = {}


def run_scenario(name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
        _results[name] = True
        print(f"  ✅ PASS  {name}")
    except AssertionError as exc:
        _results[name] = False
        print(f"  ❌ FAIL  {name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        _results[name] = False
        print(f"  ❌ ERROR {name}: {type(exc).__name__}: {exc}")


# ── Scenario 1: Two-way pub/sub ────────────────────────────────────────────────


def scenario_two_way_pubsub() -> None:
    """Client A and B exchange messages in both directions."""
    a = connect(f"smoke-{RUN_ID}-a-twoway")
    b = connect(f"smoke-{RUN_ID}-b-twoway")
    try:
        prefix = f"smoke/{RUN_ID}/twoway"
        a_inbox = Collector()
        b_inbox = Collector()

        a.subscribe(f"{prefix}/to-a", callback=a_inbox)
        b.subscribe(f"{prefix}/to-b", callback=b_inbox)
        time.sleep(0.3)  # let subscriptions propagate to broker

        publish_sync(a, Message(topic=f"{prefix}/to-b", payload=b"hello-from-a", qos=1))
        publish_sync(b, Message(topic=f"{prefix}/to-a", payload=b"hello-from-b", qos=1))

        assert b_inbox.wait_for(
            lambda: len(b_inbox.messages) >= 1
        ), "B did not receive message from A"
        assert a_inbox.wait_for(
            lambda: len(a_inbox.messages) >= 1
        ), "A did not receive message from B"
        assert b_inbox.messages[0].payload == b"hello-from-a"
        assert a_inbox.messages[0].payload == b"hello-from-b"
    finally:
        del a, b


# ── Scenario 2: Per-subscription vs global callback ───────────────────────────


def scenario_per_subscription_vs_global_callback() -> None:
    """
    Messages on a topic with a registered subscription callback are delivered
    exclusively to that callback.  With MQTT5, the broker includes subscription
    IDs so the global add_message_callback fallback is intentionally NOT invoked.
    """
    a = connect(f"smoke-{RUN_ID}-a-callbacks")
    b = connect(f"smoke-{RUN_ID}-b-callbacks")
    try:
        prefix = f"smoke/{RUN_ID}/callbacks"
        coll_x = Collector()
        coll_y = Collector()
        coll_global = Collector()

        a.subscribe(f"{prefix}/x", callback=coll_x)
        a.subscribe(f"{prefix}/y", callback=coll_y)
        a.add_message_callback(coll_global)
        time.sleep(0.3)

        publish_sync(b, Message(topic=f"{prefix}/x", payload=b"msg-x", qos=1))
        publish_sync(b, Message(topic=f"{prefix}/y", payload=b"msg-y", qos=1))

        assert coll_x.wait_for(
            lambda: len(coll_x.messages) >= 1
        ), "Specific callback for /x was not called"
        assert coll_y.wait_for(
            lambda: len(coll_y.messages) >= 1
        ), "Specific callback for /y was not called"
        assert coll_x.messages[0].payload == b"msg-x"
        assert coll_y.messages[0].payload == b"msg-y"

        # Allow a generous window, then assert the global callback stayed silent.
        time.sleep(0.3)
        assert len(coll_global.messages) == 0, (
            "Global callback should not be invoked when MQTT5 subscription IDs match "
            f"(got {len(coll_global.messages)} message(s))"
        )
    finally:
        del a, b


# ── Scenario 3: Wildcard subscriptions ────────────────────────────────────────


def scenario_wildcard_subscriptions() -> None:
    """Single-level (+) and multi-level (#) wildcard subscriptions work correctly."""
    a = connect(f"smoke-{RUN_ID}-a-wildcards")
    b = connect(f"smoke-{RUN_ID}-b-wildcards")
    try:
        run = f"smoke/{RUN_ID}"
        coll_single = Collector()
        coll_multi = Collector()

        a.subscribe(f"{run}/+/temp", callback=coll_single)
        a.subscribe(f"{run}/logs/#", callback=coll_multi)
        time.sleep(0.3)

        # Should match  smoke/<RUN_ID>/+/temp
        publish_sync(b, Message(topic=f"{run}/sensor1/temp", payload=b"22.5", qos=1))
        publish_sync(b, Message(topic=f"{run}/sensor2/temp", payload=b"23.1", qos=1))
        # Should NOT match  +/temp  (too many levels)
        publish_sync(
            b, Message(topic=f"{run}/sensor1/sub/temp", payload=b"nope", qos=1)
        )

        # Should match  smoke/<RUN_ID>/logs/#
        publish_sync(b, Message(topic=f"{run}/logs/info", payload=b"log1", qos=1))
        publish_sync(
            b, Message(topic=f"{run}/logs/warn/detail", payload=b"log2", qos=1)
        )

        assert coll_single.wait_for(
            lambda: len(coll_single.messages) >= 2
        ), f"Expected 2 single-wildcard messages, got {len(coll_single.messages)}"
        assert coll_multi.wait_for(
            lambda: len(coll_multi.messages) >= 2
        ), f"Expected 2 multi-wildcard messages, got {len(coll_multi.messages)}"

        single_payloads = {m.payload for m in coll_single.messages}
        assert b"22.5" in single_payloads and b"23.1" in single_payloads
        assert (
            b"nope" not in single_payloads
        ), "Message with extra level should not match single-level wildcard"

        multi_payloads = {m.payload for m in coll_multi.messages}
        assert b"log1" in multi_payloads and b"log2" in multi_payloads
    finally:
        del a, b


# ── Scenario 4: Retained messages ─────────────────────────────────────────────


def scenario_retained_messages() -> None:
    """A retained message is delivered to a new subscriber that connects later."""
    retained_topic = f"smoke/{RUN_ID}/retained"
    publisher = connect(f"smoke-{RUN_ID}-retained-pub")
    try:
        publish_sync(
            publisher,
            Message(
                topic=retained_topic,
                payload=b"retained-payload",
                qos=1,
                retain=True,
            ),
        )
    finally:
        del publisher
        time.sleep(0.2)  # ensure broker has processed the retained message

    subscriber = connect(f"smoke-{RUN_ID}-retained-sub")
    try:
        coll = Collector()
        subscriber.subscribe(retained_topic, callback=coll)
        assert coll.wait_for(
            lambda: len(coll.messages) >= 1
        ), "New subscriber did not receive retained message"
        assert coll.messages[0].payload == b"retained-payload"
        assert coll.messages[0].retain, "Message should be flagged as retained"
    finally:
        # Clean up: remove retained message so reruns start fresh.
        cleaner = connect(f"smoke-{RUN_ID}-retained-clean")
        try:
            publish_sync(
                cleaner, Message(topic=retained_topic, payload=b"", qos=1, retain=True)
            )
        finally:
            del cleaner
        del subscriber


# ── Scenario 5: QoS levels ────────────────────────────────────────────────────


def scenario_qos_levels() -> None:
    """Messages published at QoS 0, 1, and 2 are delivered."""
    a = connect(f"smoke-{RUN_ID}-a-qos")
    b = connect(f"smoke-{RUN_ID}-b-qos")
    try:
        prefix = f"smoke/{RUN_ID}/qos"
        colls: Dict[int, Collector] = {0: Collector(), 1: Collector(), 2: Collector()}

        for level in (0, 1, 2):
            a.subscribe(f"{prefix}/{level}", callback=colls[level])
        time.sleep(0.3)

        for level in (0, 1, 2):
            publish_sync(
                b,
                Message(
                    topic=f"{prefix}/{level}",
                    payload=f"qos-{level}".encode(),
                    qos=level,
                ),
            )

        for level in (0, 1, 2):
            coll = colls[level]
            assert coll.wait_for(
                lambda c=coll: len(c.messages) >= 1
            ), f"QoS {level} message was not received"
            assert (
                coll.messages[0].payload == f"qos-{level}".encode()
            ), f"QoS {level} payload mismatch: {coll.messages[0].payload!r}"
    finally:
        del a, b


# ── Scenario 6: LWT / online presence ─────────────────────────────────────────


def scenario_lwt_online_presence() -> None:
    """
    Default LWT publishes online:true (retained) on connect.
    When the connection is torn down via __del__, it publishes online:false.
    """
    monitor = connect(f"smoke-{RUN_ID}-monitor-lwt")
    try:
        lwt_coll = Collector()
        monitor.subscribe("client/+/online", callback=lwt_coll)
        time.sleep(0.3)

        subject = connect(f"smoke-{RUN_ID}-lwt-subject")
        online_topic = subject.online_topic

        assert lwt_coll.wait_for(
            lambda: any(
                m.topic == online_topic and b'"online":true' in m.payload
                for m in lwt_coll.messages
            )
        ), "Did not receive online:true LWT message after connect"

        # Tear down the connection — Mqtt5Connection publishes the offline
        # presence message in its finalizer.  We invoke it explicitly: paho's
        # running network-loop thread keeps the connection reachable, so a plain
        # `del` + gc.collect() would never finalize the object promptly.
        subject.__del__()
        subject._lwt = None  # type: ignore[assignment]  # guard against double offline-publish on GC
        del subject

        assert lwt_coll.wait_for(
            lambda: any(
                m.topic == online_topic and b'"online":false' in m.payload
                for m in lwt_coll.messages
            ),
            timeout=7.0,
        ), "Did not receive online:false LWT message after disconnect"
    finally:
        # Clean up retained LWT message.
        lwt_topic = f"client/smoke-{RUN_ID}-lwt-subject/online"
        cleaner = connect(f"smoke-{RUN_ID}-lwt-clean")
        try:
            publish_sync(
                cleaner, Message(topic=lwt_topic, payload=b"", qos=1, retain=True)
            )
        finally:
            del cleaner
        del monitor


# ── Scenario 7: Request / response ────────────────────────────────────────────


def scenario_request_response() -> None:
    """response_topic and correlation_data round-trip through the broker."""
    server = connect(f"smoke-{RUN_ID}-server-reqresp")
    client = connect(f"smoke-{RUN_ID}-client-reqresp")
    try:
        request_topic = f"smoke/{RUN_ID}/request"
        reply_topic = f"smoke/{RUN_ID}/reply"
        correlation = b"corr-" + RUN_ID.encode()

        reply_coll = Collector()
        client.subscribe(reply_topic, callback=reply_coll)
        time.sleep(0.1)

        def handle_request(msg: Message) -> None:
            if msg.response_topic and msg.correlation_data is not None:
                server.publish(
                    Message(
                        topic=msg.response_topic,
                        payload=b"pong: " + msg.payload,
                        qos=1,
                        correlation_data=msg.correlation_data,
                    )
                )

        server.subscribe(request_topic, callback=handle_request)
        time.sleep(0.2)

        publish_sync(
            client,
            Message(
                topic=request_topic,
                payload=b"ping",
                qos=1,
                response_topic=reply_topic,
                correlation_data=correlation,
            ),
        )

        assert reply_coll.wait_for(
            lambda: len(reply_coll.messages) >= 1
        ), "No response received"
        reply = reply_coll.messages[0]
        assert (
            reply.payload == b"pong: ping"
        ), f"Unexpected response payload: {reply.payload!r}"
        assert (
            reply.correlation_data == correlation
        ), f"correlation_data mismatch: {reply.correlation_data!r} != {correlation!r}"
    finally:
        del server, client


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    print(f"pyqttier smoke test  —  broker: {HOSTNAME}:{PORT}  —  run-id: {RUN_ID}")
    print()

    scenarios = [
        ("two-way pub/sub", scenario_two_way_pubsub),
        (
            "per-subscription vs global callback",
            scenario_per_subscription_vs_global_callback,
        ),
        ("wildcard subscriptions (+/#)", scenario_wildcard_subscriptions),
        ("retained messages", scenario_retained_messages),
        ("QoS levels (0/1/2)", scenario_qos_levels),
        ("LWT / online presence", scenario_lwt_online_presence),
        ("request / response", scenario_request_response),
    ]

    for name, fn in scenarios:
        run_scenario(name, fn)

    print()
    passed = sum(v for v in _results.values())
    total = len(_results)
    emoji = "✅" if passed == total else "❌"
    print(f"{emoji} Results: {passed}/{total} passed")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()

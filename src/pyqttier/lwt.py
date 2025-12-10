from pydantic import BaseModel
from .message import Message


class OnlinePresence(BaseModel):
    topic: str
    online: Message
    offline: Message

    def __post_init__(self):
        self.online.topic = self.topic
        self.offline.topic = self.topic

    @classmethod
    def default(cls, client_id: str) -> "OnlinePresence":
        online_topic = f"client/{client_id}/online"
        online_msg = Message(
            topic=online_topic, payload=b'{"online":true}', qos=1, retain=True
        )
        offline_msg = Message(
            topic=online_topic, payload=b'{"online":false}', qos=1, retain=True
        )
        return cls(topic=online_topic, online=online_msg, offline=offline_msg)

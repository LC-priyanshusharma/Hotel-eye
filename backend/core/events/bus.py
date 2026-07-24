import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import redis

class IEventBus(ABC):
    """
    Abstract interface for publishing and subscribing to cross-process events.
    """
    @abstractmethod
    def publish(self, channel: str, message: Dict[str, Any]) -> None:
        pass
        
    @abstractmethod
    def subscribe(self, channel: str, last_id: str, count: int = 10, block: int = 1000) -> List[Any]:
        pass

class RedisEventBus(IEventBus):
    """
    Redis implementation of the Event Bus using Streams.
    """
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        
    def publish(self, channel: str, message: Dict[str, Any]) -> None:
        # Convert dictionary to JSON string to store in stream payload under 'data' key
        payload = {"data": json.dumps(message)}
        self.client.xadd(channel, payload)
        
    def subscribe(self, channel: str, last_id: str = "$", count: int = 10, block: int = 1000) -> List[Any]:
        # returns format like: [[b'channel_name', [(b'12345-0', {b'data': b'...'}), ...]]]
        # But we use decode_responses=True so strings not bytes
        streams = {channel: last_id}
        messages = self.client.xread(streams, count=count, block=block)
        
        results = []
        if messages:
            # messages[0] = [channel, [(msg_id, payload), ...]]
            for stream_name, stream_msgs in messages:
                for msg_id, payload in stream_msgs:
                    if 'data' in payload:
                        try:
                            parsed_data = json.loads(payload['data'])
                            results.append({"id": msg_id, "data": parsed_data})
                        except Exception:
                            pass
        return results

    def subscribe_group(self, group_name: str, consumer_name: str, channel: str, count: int = 10, block: int = 100) -> List[Any]:
        streams = {channel: ">"}
        messages = self.client.xreadgroup(group_name, consumer_name, streams, count=count, block=block)
        
        results = []
        if messages:
            for stream_name, stream_msgs in messages:
                for msg_id, payload in stream_msgs:
                    if 'data' in payload:
                        try:
                            parsed_data = json.loads(payload['data'])
                            results.append({"id": msg_id, "data": parsed_data})
                        except Exception:
                            pass
        return results
        
    def ack(self, channel: str, group_name: str, msg_id: str) -> None:
        self.client.xack(channel, group_name, msg_id)

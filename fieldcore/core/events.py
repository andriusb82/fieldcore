from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
from threading import RLock
from typing import Any, Callable
from uuid import uuid4


@dataclass
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


EventHandler = Callable[[Event], None]


class LocalEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._lock = RLock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        with self._lock:
            self._subscribers.setdefault(event_name, []).append(handler)

    def publish(self, event: Event) -> None:
        with self._lock:
            handlers = list(self._subscribers.get(event.name, []))

        for handler in handlers:
            handler(event)


class CommandBus:
    def __init__(self) -> None:
        self._queues: dict[str, Queue[Event]] = {}
        self._lock = RLock()

    def register_queue(self, name: str, queue: Queue[Event]) -> None:
        with self._lock:
            self._queues[name] = queue

    def send(self, target: str, command: Event) -> None:
        with self._lock:
            queue = self._queues[target]

        queue.put(command)
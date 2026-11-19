from fieldcore.alarms.alarm_manager import (
    ALARM_CLEAR_REQUESTED,
    ALARM_RAISE_REQUESTED,
    AlarmManagerModule,
)
from fieldcore.core.events import Event, LocalEventBus


class FakeState:
    def update_alarm_state(self, alarm_id, state):
        pass


class FakeStorage:
    def execute(self, sql, params=()):
        pass

    def query(self, sql, params=()):
        return []


class FakeOutbox:
    def enqueue(self, **kwargs):
        pass


class FakeContext:
    def __init__(self):
        self.event_bus = LocalEventBus()
        self.state = FakeState()
        self.storage = FakeStorage()
        self.outbox = FakeOutbox()


def _make_module():
    context = FakeContext()
    module = AlarmManagerModule(AlarmManagerModule.default_config(), context)
    module.register_event_handlers()
    return module, context


def test_raise_requested_event_raises_alarm_by_id():
    module, context = _make_module()

    context.event_bus.publish(Event(
        name=ALARM_RAISE_REQUESTED,
        payload={"alarm_id": "central_system:offline"},
    ))

    assert "central_system:offline" in module.get_active_alarms()


def test_clear_requested_event_clears_alarm_by_id():
    module, context = _make_module()
    module.raise_alarm("central_system:offline")

    context.event_bus.publish(Event(
        name=ALARM_CLEAR_REQUESTED,
        payload={"alarm_id": "central_system:offline"},
    ))

    assert "central_system:offline" not in module.get_active_alarms()


def test_raise_requested_event_passes_through_optional_payload_and_timeout():
    module, context = _make_module()

    context.event_bus.publish(Event(
        name=ALARM_RAISE_REQUESTED,
        payload={
            "alarm_id": "door:open",
            "payload": {"cabinet": "A"},
            "timeout_seconds": 42,
        },
    ))

    active = module.get_active_alarms()
    assert active["door:open"] == {"cabinet": "A"}

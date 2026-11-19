from fieldcore.alarms.alarm_manager import ALARM_CLEAR_REQUESTED, ALARM_RAISE_REQUESTED
from fieldcore.core.events import LocalEventBus
from fieldcore.services.reliability.connectivity import ConnectivityMonitor


def _subscribe_collector(bus, event_name):
    collected = []
    bus.subscribe(event_name, lambda event: collected.append(event.payload))
    return collected


def test_does_not_raise_before_threshold_is_reached():
    bus = LocalEventBus()
    raised = _subscribe_collector(bus, ALARM_RAISE_REQUESTED)
    monitor = ConnectivityMonitor(bus, alarm_id="link:offline", failure_threshold=3)

    def failing(payload, message_type):
        raise RuntimeError("down")

    wrapped = failing
    wrapped = monitor.wrap(wrapped)

    for _ in range(2):
        try:
            wrapped({}, "reading")
        except RuntimeError:
            pass

    assert raised == []
    assert monitor.is_down is False


def test_raises_alarm_once_threshold_is_reached():
    bus = LocalEventBus()
    raised = _subscribe_collector(bus, ALARM_RAISE_REQUESTED)
    monitor = ConnectivityMonitor(bus, alarm_id="link:offline", failure_threshold=3)

    def failing(payload, message_type):
        raise RuntimeError("down")

    wrapped = monitor.wrap(failing)

    for _ in range(3):
        try:
            wrapped({}, "reading")
        except RuntimeError:
            pass

    assert raised == [{"alarm_id": "link:offline"}]
    assert monitor.is_down is True


def test_does_not_re_raise_on_further_consecutive_failures():
    bus = LocalEventBus()
    raised = _subscribe_collector(bus, ALARM_RAISE_REQUESTED)
    monitor = ConnectivityMonitor(bus, alarm_id="link:offline", failure_threshold=1)

    def failing(payload, message_type):
        raise RuntimeError("down")

    wrapped = monitor.wrap(failing)

    for _ in range(3):
        try:
            wrapped({}, "reading")
        except RuntimeError:
            pass

    assert raised == [{"alarm_id": "link:offline"}]


def test_clears_alarm_and_publishes_restored_event_on_recovery():
    bus = LocalEventBus()
    cleared = _subscribe_collector(bus, ALARM_CLEAR_REQUESTED)
    restored = _subscribe_collector(bus, "connectivity.restored")
    monitor = ConnectivityMonitor(bus, alarm_id="link:offline", failure_threshold=1)

    def failing(payload, message_type):
        raise RuntimeError("down")

    try:
        monitor.wrap(failing)({}, "reading")
    except RuntimeError:
        pass
    assert monitor.is_down is True

    def ok(payload, message_type):
        return None

    monitor.wrap(ok)({}, "reading")

    assert monitor.is_down is False
    assert cleared == [{"alarm_id": "link:offline"}]
    assert restored == [{}]


def test_does_not_publish_clear_when_never_down():
    bus = LocalEventBus()
    cleared = _subscribe_collector(bus, ALARM_CLEAR_REQUESTED)
    monitor = ConnectivityMonitor(bus, alarm_id="link:offline", failure_threshold=3)

    def ok(payload, message_type):
        return None

    monitor.wrap(ok)({}, "reading")

    assert cleared == []


def test_successful_send_resets_failure_count():
    bus = LocalEventBus()
    raised = _subscribe_collector(bus, ALARM_RAISE_REQUESTED)
    monitor = ConnectivityMonitor(bus, alarm_id="link:offline", failure_threshold=3)

    def failing(payload, message_type):
        raise RuntimeError("down")

    def ok(payload, message_type):
        return None

    failing_wrapped = monitor.wrap(failing)
    ok_wrapped = monitor.wrap(ok)

    for _ in range(2):
        try:
            failing_wrapped({}, "reading")
        except RuntimeError:
            pass

    ok_wrapped({}, "reading")  # resets the streak

    for _ in range(2):
        try:
            failing_wrapped({}, "reading")
        except RuntimeError:
            pass

    assert raised == []
    assert monitor.is_down is False

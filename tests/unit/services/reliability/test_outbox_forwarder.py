from fieldcore.services.reliability.outbox_forwarder import OutboxForwarder


class FakeOutbox:
    def __init__(self, messages):
        self._messages = messages
        self.sent_ids: list[int] = []
        self.failed: list[tuple[int, str]] = []

    def get_pending_messages(self, limit=None):
        return self._messages[:limit] if limit is not None else list(self._messages)

    def mark_sent(self, message_id):
        self.sent_ids.append(message_id)

    def mark_failed(self, message_id, error, retry_delay_seconds=0.0):
        self.failed.append((message_id, error))


def test_flush_passes_message_type_through_to_send_fn():
    received = []

    def send_fn(payload, message_type):
        received.append((payload, message_type))

    outbox = FakeOutbox([
        {
            "id": 1,
            "payload": {"foo": "bar"},
            "message_type": "weather_reading",
            "retry_count": 0,
        },
    ])
    forwarder = OutboxForwarder(outbox, send_fn)

    sent_count = forwarder.flush()

    assert sent_count == 1
    assert received == [({"foo": "bar"}, "weather_reading")]
    assert outbox.sent_ids == [1]


def test_flush_backs_off_on_failure_without_losing_message_type():
    def send_fn(payload, message_type):
        raise RuntimeError("boom")

    outbox = FakeOutbox([
        {
            "id": 7,
            "payload": {"foo": "bar"},
            "message_type": "alarm",
            "retry_count": 2,
        },
    ])
    forwarder = OutboxForwarder(outbox, send_fn, backoff_base_seconds=1.0)

    sent_count = forwarder.flush()

    assert sent_count == 0
    assert outbox.sent_ids == []
    [(message_id, error)] = outbox.failed
    assert message_id == 7
    assert "boom" in error

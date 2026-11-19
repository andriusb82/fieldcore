from fieldcore.services.reliability.outbox_forwarder_worker import OutboxForwarderWorker
from fieldcore.services.reliability.outbox_service import OutboxService
from fieldcore.services.reliability.reliability_schema import create_reliability_tables
from fieldcore.storage.sqlite_storage import SqliteStorage


class FakeContext:
    def __init__(self, storage, outbox_send_fn):
        self.storage = storage
        self.outbox_send_fn = outbox_send_fn


def _make_storage(tmp_path):
    storage = SqliteStorage(tmp_path / "test.db")
    storage.connect()
    create_reliability_tables(storage)
    return storage


def test_flush_sends_enqueued_messages_through_context_send_fn(tmp_path):
    storage = _make_storage(tmp_path)
    outbox = OutboxService(storage)
    outbox.enqueue(
        owner_module="test",
        message_type="weather_reading",
        target="central_system",
        payload={"foo": "bar"},
    )

    received = []

    def send_fn(payload, message_type):
        received.append((payload, message_type))

    context = FakeContext(storage, send_fn)
    worker = OutboxForwarderWorker(OutboxForwarderWorker.default_config(), context)

    sent_count = worker._forwarder.flush()

    assert sent_count == 1
    assert received == [({"foo": "bar"}, "weather_reading")]
    assert outbox.get_pending_messages() == []


def test_stop_before_start_leaves_running_false(tmp_path):
    storage = _make_storage(tmp_path)
    context = FakeContext(storage, lambda payload, message_type: None)
    worker = OutboxForwarderWorker(OutboxForwarderWorker.default_config(), context)

    worker.stop()

    assert worker.running is False

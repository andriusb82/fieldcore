from __future__ import annotations

from multiprocessing import Queue
from queue import Empty
from typing import Any

from app.core.events import Event
from app.core.module import BaseModule


class StatisticsModule(BaseModule):
    name = "statistics"
    config_section = "statistics"
    runner = "process"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return {
            "enabled": True,
            "runner": "process",
            "interval_minutes": 15,
            "max_parallel_jobs": 1,
        }

    def __init__(self, config: dict[str, Any], context: "AppContext") -> None:
        super().__init__(config, context)
        self.job_queue: Queue = Queue()
        self.context.command_bus.register_queue(self.name, self.job_queue)

    def start(self) -> None:
        self.running = True

        while self.running:
            try:
                job = self.job_queue.get(timeout=1)
                self.calculate_statistics(job)
            except Empty:
                continue

    def stop(self) -> None:
        self.running = False

    def calculate_statistics(self, job: Event) -> None:
        start_time = job.payload["start_time"]
        end_time = job.payload["end_time"]

        # Later: open own DB connection here.
        # Read raw data.
        # Calculate statistics.
        # Write results.

        self.context.event_bus.publish(Event(
            name="statistics.job.finished",
            payload={
                "start_time": start_time,
                "end_time": end_time,
            },
            correlation_id=job.correlation_id,
        ))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def register_event_handlers(self) -> None:
        self.context.event_bus.subscribe(
            "statistics.job.requested",
            self.on_statistics_job_requested,
        )

    def on_statistics_job_requested(self, event: Event) -> None:
        self.job_queue.put(event)
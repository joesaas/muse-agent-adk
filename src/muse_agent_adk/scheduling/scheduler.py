from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from muse_agent_adk.core.events import EventBus


@dataclass(frozen=True)
class CronSpec:
    """Classic 5-field cron: minute hour day-of-month month day-of-week.
    Supports '*', single values, lists (a,b), ranges (a-b), steps (*/n)."""

    expr: str

    def _match_field(self, field: str, value: int) -> bool:
        for part in field.split(","):
            if part == "*":
                return True
            if part.startswith("*/"):
                if value % int(part[2:]) == 0:
                    return True
            elif "-" in part:
                lo, hi = part.split("-", 1)
                if int(lo) <= value <= int(hi):
                    return True
            elif int(part) == value:
                return True
        return False

    def matches(self, dt: datetime) -> bool:
        fields = self.expr.split()
        if len(fields) != 5:
            raise ValueError(f"cron spec needs 5 fields: {self.expr!r}")
        minute, hour, dom, month, dow = fields
        cron_dow = (dt.weekday() + 1) % 7  # cron: 0/7 = Sunday
        return (self._match_field(minute, dt.minute)
                and self._match_field(hour, dt.hour)
                and self._match_field(dom, dt.day)
                and self._match_field(month, dt.month)
                and (self._match_field(dow, cron_dow)
                     or self._match_field(dow, (cron_dow or 7))))


@dataclass
class Job:
    id: str
    spec: CronSpec
    prompt: str                 # the recorded request the run executes
    enabled: bool = True
    last_run_minute: str = ""   # dedupe: at most one run per minute


class Scheduler:
    """Evaluates jobs against a clock supplied by the caller.

    The host process decides how often to tick (every minute is
    typical); the scheduler only decides what is due and emits
    `cron.due` events. It never sleeps and never runs prompts itself.
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.jobs: list[Job] = []

    def add(self, job: Job) -> None:
        self.jobs.append(job)

    def tick(self, now: datetime) -> list[Job]:
        due = []
        stamp = now.strftime("%Y-%m-%dT%H:%M")
        for job in self.jobs:
            if not job.enabled or job.last_run_minute == stamp:
                continue
            if job.spec.matches(now):
                job.last_run_minute = stamp
                due.append(job)
                self.bus.emit("cron.due", job_id=job.id, prompt=job.prompt)
        return due

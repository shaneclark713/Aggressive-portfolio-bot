from dataclasses import dataclass

@dataclass(frozen=True)
class ScheduleSpec:
    hour: int
    minute: int

PREMARKET_SCHEDULE = ScheduleSpec(5, 30)
MIDDAY_SCHEDULE = ScheduleSpec(10, 0)
POSTMARKET_SCHEDULE = ScheduleSpec(21, 0)
SUNDAY_WRAPUP_SCHEDULE = ScheduleSpec(21, 0)

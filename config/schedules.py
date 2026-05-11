from dataclasses import dataclass


@dataclass(frozen=True)
class ScheduleSpec:
    hour: int
    minute: int


# These times are evaluated in APP_TIMEZONE. For Shane's workflow this should be
# America/Los_Angeles so the 10:00 a.m. market scan runs at 7:00 a.m. Pacific.
PREMARKET_SCHEDULE = ScheduleSpec(5, 30)
SPY_0DTE_BREAKDOWN_SCHEDULE = ScheduleSpec(6, 15)
MIDDAY_SCHEDULE = ScheduleSpec(7, 0)
POSTMARKET_SCHEDULE = ScheduleSpec(21, 0)
SUNDAY_WRAPUP_SCHEDULE = ScheduleSpec(21, 0)

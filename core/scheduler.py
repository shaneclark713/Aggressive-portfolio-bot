from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from config.schedules import PREMARKET_SCHEDULE, MIDDAY_SCHEDULE, POSTMARKET_SCHEDULE, SUNDAY_WRAPUP_SCHEDULE

def build_scheduler(timezone_name: str) -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone=ZoneInfo(timezone_name))

def register_jobs(scheduler: AsyncIOScheduler, services: dict, timezone_name: str) -> None:
    tz = ZoneInfo(timezone_name)
    scheduler.add_job(services['premarket'].run, CronTrigger(day_of_week='mon-fri', hour=PREMARKET_SCHEDULE.hour, minute=PREMARKET_SCHEDULE.minute, timezone=tz), id='premarket')
    scheduler.add_job(services['midday'].run, CronTrigger(day_of_week='mon-fri', hour=MIDDAY_SCHEDULE.hour, minute=MIDDAY_SCHEDULE.minute, timezone=tz), id='midday')
    scheduler.add_job(services['postmarket'].run, CronTrigger(day_of_week='mon-fri', hour=POSTMARKET_SCHEDULE.hour, minute=POSTMARKET_SCHEDULE.minute, timezone=tz), id='postmarket')
    scheduler.add_job(services['postmarket'].run_weekly_wrapup, CronTrigger(day_of_week='sun', hour=SUNDAY_WRAPUP_SCHEDULE.hour, minute=SUNDAY_WRAPUP_SCHEDULE.minute, timezone=tz), id='sunday_wrap')

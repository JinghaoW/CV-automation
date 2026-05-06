from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

import config

app = Celery("cv_automation", broker=config.CELERY_BROKER_URL, backend=config.CELERY_RESULT_BACKEND)

# Configure beat schedule for daily workflow
app.conf.timezone = "UTC"
app.conf.beat_schedule = {
    "daily-workflow": {
        "task": "src.tasks.workflow_tasks.run_daily_workflow",
        "schedule": crontab(minute=config.SCHEDULE_MINUTE_UTC, hour=config.SCHEDULE_HOUR_UTC),
        "args": (),
    }
}

# optional worker settings
app.conf.task_annotations = {"src.tasks.workflow_tasks.run_daily_workflow": {"rate_limit": "1/m"}}

__all__ = ["app"]


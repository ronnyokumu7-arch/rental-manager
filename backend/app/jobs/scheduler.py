from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler():
    from app.jobs.subscription_jobs import run_subscription_lifecycle
    from app.jobs.booking_jobs import run_booking_auto_archive

    scheduler.add_job(
        run_subscription_lifecycle,
        trigger=CronTrigger(hour=0, minute=0),
        id="subscription_lifecycle",
        name="Daily subscription lifecycle check",
        replace_existing=True,
    )

    scheduler.add_job(
        run_booking_auto_archive,
        trigger=CronTrigger(hour=1, minute=0),
        id="booking_auto_archive",
        name="Daily booking auto-archive",
        replace_existing=True,
    )

    scheduler.start()


def stop_scheduler():
    scheduler.shutdown()
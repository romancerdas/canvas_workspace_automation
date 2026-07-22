from apscheduler.schedulers.background import BackgroundScheduler


def configure_scheduler(app):
    scheduler = BackgroundScheduler(daemon=True)

    def weekly_sync_job():
        with app.app_context():
            from .routes import perform_configured_sync
            try:
                perform_configured_sync()
            except Exception as exc:  # scheduler must stay alive
                app.logger.exception("Scheduled Canvas sync failed: %s", exc)

    store = app.extensions["json_store"]
    config = store.read("config", {})
    weekday = int(config.get("sync_weekday", 0))
    hour = int(config.get("sync_hour", 8))
    scheduler.add_job(
        weekly_sync_job,
        trigger="cron",
        day_of_week=weekday,
        hour=hour,
        minute=0,
        id="weekly_canvas_sync",
        replace_existing=True,
    )
    scheduler.start()
    app.extensions["scheduler"] = scheduler

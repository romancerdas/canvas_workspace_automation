from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from .canvas_client import CanvasAPIError, CanvasClient
from .sync_service import SyncService

bp = Blueprint("main", __name__)


def _store():
    return current_app.extensions["json_store"]


def _config():
    return _store().read(
        "config",
        {
            "canvas_url": "https://your-school.instructure.com/",
            "token": "",
            "download_dir": current_app.config["DEFAULT_DOWNLOAD_DIR"],
            "selected_course": None,
            "selected_course_name": None,
            "sync_weekday": 0,
            "sync_hour": 8,
        },
    )


def _client(config):
    if not config.get("canvas_url") or not config.get("token"):
        raise CanvasAPIError("Save a Canvas URL and access token first.")
    return CanvasClient(config["canvas_url"], config["token"])


def perform_configured_sync():
    config = _config()
    if not config.get("selected_course"):
        raise CanvasAPIError("Choose a course before synchronizing.")
    course = {"id": config["selected_course"], "name": config.get("selected_course_name")}
    service = SyncService(_client(config), _store(), Path(config["download_dir"]))
    return service.sync_course(course)


@bp.get("/")
def dashboard():
    config = _config()
    summary = _store().read("last_summary", None)
    state = _store().read("sync_state", {})
    return render_template("dashboard.html", config=config, summary=summary, state=state)


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    config = _config()
    if request.method == "POST":
        config.update(
            {
                "canvas_url": request.form.get("canvas_url", "").strip(),
                "token": request.form.get("token", "").strip() or config.get("token", ""),
                "download_dir": request.form.get("download_dir", "").strip() or current_app.config["DEFAULT_DOWNLOAD_DIR"],
                "sync_weekday": int(request.form.get("sync_weekday", 0)),
                "sync_hour": int(request.form.get("sync_hour", 8)),
            }
        )
        _store().write("config", config)
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings"))
    return render_template("settings.html", config=config)


@bp.get("/courses")
def courses():
    config = _config()
    try:
        courses = _client(config).list_courses()
        courses = [c for c in courses if c.get("name")]
        return render_template("courses.html", courses=courses, config=config)
    except CanvasAPIError as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.settings"))


@bp.post("/courses/select")
def select_course():
    config = _config()
    config["selected_course"] = request.form.get("course_id")
    config["selected_course_name"] = request.form.get("course_name")
    _store().write("config", config)
    flash(f"Selected {config['selected_course_name']}.", "success")
    return redirect(url_for("main.dashboard"))


@bp.post("/sync")
def sync_now():
    try:
        summary = perform_configured_sync()
        flash(
            f"Sync finished: {len(summary['new_assignments'])} new assignments and "
            f"{len(summary['downloaded_files'])} downloaded files.",
            "success",
        )
    except (CanvasAPIError, OSError, ValueError) as exc:
        flash(str(exc), "error")
    return redirect(url_for("main.dashboard"))

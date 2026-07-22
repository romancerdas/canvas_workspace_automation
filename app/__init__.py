from pathlib import Path
from flask import Flask

from .routes import bp
from .scheduler import configure_scheduler
from .storage import JsonStore


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY="canvas-workspace-dev-key",
        DATA_DIR=str(Path(__file__).resolve().parent.parent / "data"),
        DEFAULT_DOWNLOAD_DIR=str(Path(__file__).resolve().parent.parent / "workspace"),
        SCHEDULER_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DEFAULT_DOWNLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    app.extensions["json_store"] = JsonStore(Path(app.config["DATA_DIR"]))
    app.register_blueprint(bp)

    if app.config.get("SCHEDULER_ENABLED") and not app.config.get("TESTING"):
        configure_scheduler(app)

    return app

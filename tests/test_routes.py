from app import create_app


def test_dashboard_loads(tmp_path):
    app = create_app({
        "TESTING": True,
        "SCHEDULER_ENABLED": False,
        "DATA_DIR": str(tmp_path / "data"),
        "DEFAULT_DOWNLOAD_DIR": str(tmp_path / "workspace"),
    })
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Canvas Workspace Automation" in response.data

from pathlib import Path

from app.storage import JsonStore
from app.sync_service import SyncService, safe_name


class FakeClient:
    def list_modules(self, course_id):
        return [{"id": 10, "name": "Week 1", "items": [{"type": "File", "content_id": 99}]}]

    def list_folders(self, course_id):
        return [{"id": 1, "name": "course files", "parent_folder_id": None}]

    def list_course_files(self, course_id):
        return [{"id": 100, "folder_id": 1, "display_name": "syllabus.pdf", "updated_at": "v1", "url": "fake"}]

    def list_assignments(self, course_id):
        return [{
            "id": 7,
            "name": "Hello World",
            "due_at": "2026-07-20T23:59:00Z",
            "updated_at": "2026-07-01T12:00:00Z",
            "points_possible": 10,
            "html_url": "https://canvas.example/assignments/7",
            "description": "Build a small program.",
        }]

    def get_file(self, file_id):
        return {"id": file_id, "display_name": "notes.txt", "updated_at": "v1", "url": "fake"}

    def download_file(self, info, destination):
        Path(destination).write_text("course notes", encoding="utf-8")


def test_safe_name_removes_invalid_characters():
    assert safe_name('Week: 1 / Intro?') == "Week_ 1 _ Intro_"


def test_sync_creates_workspace_and_state(tmp_path):
    store = JsonStore(tmp_path / "data")
    service = SyncService(FakeClient(), store, tmp_path / "workspace")
    summary = service.sync_course({"id": 123, "name": "CSE 310"})

    assert len(summary["new_assignments"]) == 1
    assert len(summary["downloaded_files"]) == 2
    assert (tmp_path / "workspace" / "CSE 310" / "Assignments" / "Hello World" / "assignment.md").exists()
    assert (tmp_path / "workspace" / "CSE 310" / "Modules" / "Week 1" / "notes.txt").exists()
    assert (tmp_path / "workspace" / "CSE 310" / "Course Files" / "syllabus.pdf").exists()

    second = service.sync_course({"id": 123, "name": "CSE 310"})
    assert second["new_assignments"] == []
    assert second["downloaded_files"] == []
    assert sorted(second["skipped_files"]) == sorted(["CSE 310/Course Files/syllabus.pdf", "CSE 310/Modules/Week 1/notes.txt"])

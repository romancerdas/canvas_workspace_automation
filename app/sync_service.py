from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .canvas_client import CanvasClient, CanvasAPIError
from .storage import JsonStore


def safe_name(value: str, fallback: str = "untitled") -> str:
    value = (value or fallback).strip()
    value = re.sub(r'[<>:/\\|?*\x00-\x1F]', "_", value).replace(chr(34), "_")
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:120] or fallback


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SyncService:
    def __init__(self, client: CanvasClient, store: JsonStore, download_root: Path):
        self.client = client
        self.store = store
        self.download_root = Path(download_root).expanduser().resolve()
        self.download_root.mkdir(parents=True, exist_ok=True)

    def _write_assignment(self, course_dir: Path, assignment: dict) -> Path:
        folder = course_dir / "Assignments" / safe_name(assignment.get("name"), f"assignment-{assignment.get('id')}")
        folder.mkdir(parents=True, exist_ok=True)
        text = "\n".join(
            [
                f"# {assignment.get('name', 'Untitled Assignment')}",
                "",
                f"Canvas ID: {assignment.get('id', '')}",
                f"Due: {assignment.get('due_at') or 'No due date'}",
                f"Points: {assignment.get('points_possible', 'Not specified')}",
                f"URL: {assignment.get('html_url', '')}",
                "",
                "## Description",
                assignment.get("description") or "No description provided.",
                "",
            ]
        )
        path = folder / "assignment.md"
        path.write_text(text, encoding="utf-8")
        return path

    def _collect_module_file_ids(self, course_id, modules: list[dict]) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []
        for module in modules:
            items = module.get("items") or self.client.list_module_items(course_id, module["id"])
            module_name = module.get("name") or f"Module {module.get('id')}"
            for item in items:
                if item.get("type") == "File" and item.get("content_id"):
                    found.append((int(item["content_id"]), module_name))
        return found

    @staticmethod
    def _extract_file_ids_from_html(html: str | None) -> set[int]:
        """Find Canvas file IDs in assignment/page HTML links."""
        if not html:
            return set()
        decoded = unescape(html)
        patterns = [
            r"/files/(\d+)(?:/download)?",
            r"[?&]file_id=(\d+)",
        ]
        found: set[int] = set()
        for pattern in patterns:
            found.update(int(value) for value in re.findall(pattern, decoded, flags=re.IGNORECASE))
        return found

    def _folder_paths(self, course_id: str) -> dict[str, Path]:
        """Return Canvas folder ID -> relative local path while preserving hierarchy."""
        folders = self.client.list_folders(course_id)
        by_id = {str(f["id"]): f for f in folders if f.get("id") is not None}
        cache: dict[str, Path] = {}

        def resolve(folder_id: str, seen: set[str] | None = None) -> Path:
            if folder_id in cache:
                return cache[folder_id]
            folder = by_id.get(folder_id)
            if not folder:
                return Path()
            seen = set(seen or ())
            if folder_id in seen:
                return Path(safe_name(folder.get("name"), f"folder-{folder_id}"))
            seen.add(folder_id)
            parent_id = folder.get("parent_folder_id")
            parent = resolve(str(parent_id), seen) if parent_id is not None else Path()
            name = safe_name(folder.get("name"), f"folder-{folder_id}")
            # Canvas often has a root folder named "course files"; omit that redundant level.
            if parent_id is None and name.lower() in {"course files", "files"}:
                path = Path()
            else:
                path = parent / name
            cache[folder_id] = path
            return path

        for fid in by_id:
            resolve(fid)
        return cache

    @staticmethod
    def _unique_destination(destination: Path, file_id: int | str, known_path: str | None = None) -> Path:
        """Avoid overwriting a different Canvas file with the same filename."""
        if known_path and Path(known_path) == destination:
            return destination
        if not destination.exists():
            return destination
        return destination.with_name(f"{destination.stem}__{file_id}{destination.suffix}")

    def _download_one(
        self,
        info: dict,
        destination: Path,
        old_files: dict,
        file_state: dict,
        downloaded_files: list[str],
        skipped_files: list[str],
    ) -> None:
        file_id = str(info["id"])
        remote_version = info.get("updated_at") or info.get("modified_at") or info.get("size")
        old = old_files.get(file_id, {})
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = self._unique_destination(destination, file_id, old.get("path"))

        if old.get("version") == remote_version and destination.exists():
            skipped_files.append(str(destination.relative_to(self.download_root)))
        else:
            self.client.download_file(info, destination)
            downloaded_files.append(str(destination.relative_to(self.download_root)))

        file_state[file_id] = {
            "name": destination.name,
            "version": remote_version,
            "path": str(destination),
            "size": info.get("size"),
            "content_type": info.get("content-type") or info.get("content_type"),
        }

    def sync_course(self, course: dict) -> dict[str, Any]:
        course_id = str(course["id"])
        course_name = safe_name(course.get("name") or course.get("course_code"), f"course-{course_id}")
        course_dir = self.download_root / course_name
        course_dir.mkdir(parents=True, exist_ok=True)

        previous = self.store.read("sync_state", {"courses": {}})
        previous_course = previous.get("courses", {}).get(course_id, {})
        old_assignments = previous_course.get("assignments", {})
        old_files = previous_course.get("files", {})

        modules = self.client.list_modules(course_id)
        assignments = self.client.list_assignments(course_id)

        new_assignments, updated_assignments, downloaded_files, skipped_files, errors = [], [], [], [], []
        assignment_state = {}

        assignment_file_ids: dict[int, str] = {}
        for assignment in assignments:
            aid = str(assignment["id"])
            snapshot = {
                "name": assignment.get("name"),
                "due_at": assignment.get("due_at"),
                "updated_at": assignment.get("updated_at"),
            }
            assignment_state[aid] = snapshot
            if aid not in old_assignments:
                new_assignments.append(snapshot)
            elif old_assignments[aid] != snapshot:
                updated_assignments.append(snapshot)
            self._write_assignment(course_dir, assignment)
            assignment_folder = safe_name(assignment.get("name"), f"assignment-{aid}")
            for file_id in self._extract_file_ids_from_html(assignment.get("description")):
                assignment_file_ids[file_id] = assignment_folder
            for attachment in assignment.get("attachments") or []:
                if attachment.get("id"):
                    assignment_file_ids[int(attachment["id"])] = assignment_folder

        file_state = dict(old_files)
        processed_ids: set[str] = set()

        # 1. Download every file visible in the Canvas course Files area, preserving folders.
        try:
            folder_paths = self._folder_paths(course_id)
            for info in self.client.list_course_files(course_id):
                if not info.get("id"):
                    continue
                file_id = str(info["id"])
                folder_path = folder_paths.get(str(info.get("folder_id")), Path())
                filename = safe_name(info.get("display_name") or info.get("filename"), f"file-{file_id}")
                destination = course_dir / "Course Files" / folder_path / filename
                self._download_one(info, destination, old_files, file_state, downloaded_files, skipped_files)
                processed_ids.add(file_id)
        except (CanvasAPIError, OSError, KeyError, ValueError) as exc:
            errors.append(f"Course Files: {exc}")

        # 2. Download files directly attached to assignments or linked in assignment descriptions.
        for file_id, assignment_folder in assignment_file_ids.items():
            if str(file_id) in processed_ids:
                continue
            try:
                info = self.client.get_file(file_id)
                filename = safe_name(info.get("display_name") or info.get("filename"), f"file-{file_id}")
                destination = course_dir / "Assignments" / assignment_folder / "Attachments" / filename
                self._download_one(info, destination, old_files, file_state, downloaded_files, skipped_files)
                processed_ids.add(str(file_id))
            except (CanvasAPIError, OSError, KeyError, ValueError) as exc:
                errors.append(f"Assignment file {file_id}: {exc}")

        # 3. Download module file items not already present in Course Files.
        for file_id, module_name in self._collect_module_file_ids(course_id, modules):
            if str(file_id) in processed_ids:
                continue
            try:
                info = self.client.get_file(file_id)
                filename = safe_name(info.get("display_name") or info.get("filename"), f"file-{file_id}")
                destination = course_dir / "Modules" / safe_name(module_name) / filename
                self._download_one(info, destination, old_files, file_state, downloaded_files, skipped_files)
                processed_ids.add(str(file_id))
            except (CanvasAPIError, OSError, KeyError, ValueError) as exc:
                errors.append(f"Module file {file_id}: {exc}")

        readme = course_dir / "README.md"
        readme.write_text(
            f"# {course.get('name', course_name)}\n\n"
            f"Canvas course ID: {course_id}\n\n"
            f"Last synchronized: {utc_now()}\n\n"
            f"Modules found: {len(modules)}\n\n"
            f"Assignments found: {len(assignments)}\n\n"
            f"Canvas files tracked: {len(file_state)}\n",
            encoding="utf-8",
        )

        synced_at = utc_now()
        previous.setdefault("courses", {})[course_id] = {
            "course": {"id": course.get("id"), "name": course.get("name"), "course_code": course.get("course_code")},
            "assignments": assignment_state,
            "files": file_state,
            "last_sync": synced_at,
        }
        previous["last_sync"] = synced_at
        self.store.write("sync_state", previous)

        summary = {
            "course": course.get("name") or course_name,
            "synced_at": synced_at,
            "new_assignments": new_assignments,
            "updated_assignments": updated_assignments,
            "downloaded_files": downloaded_files,
            "skipped_files": skipped_files,
            "errors": errors,
        }
        self.store.write("last_summary", summary)
        return summary

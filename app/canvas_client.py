from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urljoin

import requests


class CanvasAPIError(RuntimeError):
    pass


@dataclass
class CanvasClient:
    base_url: str
    token: str
    timeout: int = 20

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(method, self._url(path), timeout=self.timeout, **kwargs)
        except requests.RequestException as exc:
            raise CanvasAPIError(f"Network error while contacting Canvas: {exc}") from exc

        if response.status_code == 401:
            raise CanvasAPIError("Canvas rejected the access token.")
        if response.status_code == 403:
            raise CanvasAPIError("Canvas denied access to this resource.")
        if response.status_code == 404:
            raise CanvasAPIError("Canvas resource was not found.")
        if response.status_code >= 400:
            detail = response.text[:300].strip()
            raise CanvasAPIError(f"Canvas returned HTTP {response.status_code}: {detail}")
        return response

    def get_json(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params).json()

    def paginate(self, path: str, params: dict | None = None) -> Iterable[dict]:
        url = self._url(path)
        next_params = {"per_page": 100, **(params or {})}
        while url:
            try:
                response = self.session.get(url, params=next_params, timeout=self.timeout)
            except requests.RequestException as exc:
                raise CanvasAPIError(f"Network error while contacting Canvas: {exc}") from exc
            if response.status_code >= 400:
                self._request("GET", path, params=next_params)
            payload = response.json()
            if not isinstance(payload, list):
                raise CanvasAPIError("Canvas returned an unexpected response format.")
            yield from payload
            url = response.links.get("next", {}).get("url")
            next_params = None

    def list_courses(self) -> list[dict]:
        return list(self.paginate("api/v1/courses", {"enrollment_state": "active"}))

    def list_modules(self, course_id: int | str) -> list[dict]:
        return list(self.paginate(f"api/v1/courses/{course_id}/modules", {"include[]": "items"}))

    def list_module_items(self, course_id: int | str, module_id: int | str) -> list[dict]:
        return list(self.paginate(f"api/v1/courses/{course_id}/modules/{module_id}/items"))

    def list_assignments(self, course_id: int | str) -> list[dict]:
        return list(self.paginate(
            f"api/v1/courses/{course_id}/assignments",
            {"include[]": ["description", "attachments"]},
        ))

    def list_course_files(self, course_id: int | str) -> list[dict]:
        """List every file the current user can access in a course."""
        return list(self.paginate(f"api/v1/courses/{course_id}/files"))

    def list_folders(self, course_id: int | str) -> list[dict]:
        """List course folders so local downloads can preserve Canvas hierarchy."""
        return list(self.paginate(f"api/v1/courses/{course_id}/folders"))

    def get_file(self, file_id: int | str) -> dict:
        return self.get_json(f"api/v1/files/{file_id}")

    def download_file(self, file_info: dict, destination) -> None:
        url = file_info.get("url")
        if not url:
            raise CanvasAPIError(f"File {file_info.get('id')} has no download URL.")
        try:
            with self.session.get(url, timeout=60, stream=True) as response:
                response.raise_for_status()
                with open(destination, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
        except (requests.RequestException, OSError) as exc:
            raise CanvasAPIError(f"Could not download {file_info.get('display_name', 'file')}: {exc}") from exc

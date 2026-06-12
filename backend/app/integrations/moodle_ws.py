from __future__ import annotations

import httpx


class MoodleWSError(Exception):
    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class MoodleWSClient:
    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    async def get_enrolled_users(self, course_id: int) -> list[dict]:
        params = {
            "wstoken": self._token,
            "wsfunction": "core_enrol_get_enrolled_users",
            "moodlewsrestformat": "json",
            "courseid": course_id,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(f"{self._base_url}/webservice/rest/server.php", params=params)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise MoodleWSError(f"Moodle HTTP error: {exc.response.status_code}", status_code=502) from exc
            except httpx.RequestError as exc:
                raise MoodleWSError(f"Moodle connection error: {exc}", status_code=502) from exc

            data = resp.json()

            # Moodle returns {"exception": ..., "message": ...} on errors
            if isinstance(data, dict) and "exception" in data:
                raise MoodleWSError(data.get("message", "Moodle WS error"), status_code=502)

            if not isinstance(data, list):
                raise MoodleWSError("Unexpected Moodle WS response format", status_code=502)

            return data

import asyncio
from collections.abc import Iterable
from typing import Any

import httpx

from app.core.config import Settings


class BangumiAPIError(RuntimeError):
    pass


class BangumiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BangumiClient":
        headers = {
            "User-Agent": self.settings.bangumi_user_agent,
            "Accept": "application/json",
        }
        if self.settings.bangumi_token:
            headers["Authorization"] = f"Bearer {self.settings.bangumi_token}"

        self._client = httpx.AsyncClient(
            base_url=self.settings.bangumi_base_url,
            timeout=self.settings.bangumi_timeout_seconds,
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()

    async def _get(self, path: str, params: Iterable[tuple[str, str]]) -> Any:
        if self._client is None:
            raise RuntimeError("BangumiClient must be used as an async context manager.")

        response = await self._client.get(path, params=list(params))
        if response.status_code >= 400:
            raise BangumiAPIError(
                f"Bangumi API request failed: {response.status_code} {response.text[:300]}"
            )
        return response.json()

    @staticmethod
    def _extract_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]

        if isinstance(payload, dict):
            for key in ("data", "items", "results", "list"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]

        return []

    def build_season_browse_params(
        self,
        *,
        year: int,
        month: int,
        limit: int,
        offset: int,
    ) -> list[tuple[str, str]]:
        """
        Align to the already-validated Bangumi spike path:
        GET /v0/subjects
        type=2
        year=...
        month=...
        sort=rank
        limit / offset
        """
        return [
            ("type", "2"),
            ("year", str(year)),
            ("month", str(month)),
            ("sort", "rank"),
            ("limit", str(limit)),
            ("offset", str(offset)),
        ]

    async def fetch_season_subjects(
        self,
        *,
        year: int,
        month: int,
        page_limit: int,
        per_page: int,
    ) -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []

        for page_idx in range(page_limit):
            offset = page_idx * per_page
            params = self.build_season_browse_params(
                year=year,
                month=month,
                limit=per_page,
                offset=offset,
            )
            payload = await self._get("/v0/subjects", params=params)
            items = self._extract_items(payload)
            if not items:
                break

            all_items.extend(items)

            if len(items) < per_page:
                break

            if self.settings.bangumi_request_pause_seconds > 0:
                await asyncio.sleep(self.settings.bangumi_request_pause_seconds)

        return all_items

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp

from .exceptions import InvalidAuth, RotarexConnectionError, RotarexError
from .models import RotarexTank

DEFAULT_BASE_URL = "https://waveapi.rotarex.com"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
# The token endpoint answers 400 (invalid_grant) or 401 for wrong credentials
AUTH_ERROR_STATUSES = (400, 401)
# Renew the token slightly before it expires to avoid races with the server
TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)


class RotarexApi:
    """Client for the Rotarex DIMES SRG API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._password = password
        self._access_token: str | None = None
        self._expires_at: datetime | None = None

    async def login(self) -> None:
        """Authenticate with the stored credentials and store the access token.

        Raises InvalidAuth when the credentials are rejected and
        RotarexConnectionError when the API cannot be reached or fails.
        """
        payload = {
            "grant_type": "password",
            "username": self._email,
            "password": hashlib.sha256(self._password.encode("utf-8")).hexdigest(),
        }
        try:
            async with self._session.post(
                f"{self._base_url}/token", data=payload, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status in AUTH_ERROR_STATUSES:
                    raise InvalidAuth(f"Login rejected with status {resp.status}")
                resp.raise_for_status()
                token_data = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RotarexConnectionError(f"Error during login: {err}") from err

        try:
            self._access_token = token_data["access_token"]
            expires_in = int(token_data["expires_in"])
        except (KeyError, TypeError, ValueError) as err:
            raise RotarexError("Unexpected token response") from err
        self._expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

    async def fetch_tanks(self) -> list[RotarexTank]:
        """Fetch all tanks of the account, logging in when needed."""
        if self._token_expired():
            await self.login()

        raw = await self._request_tanks()
        if raw is None:
            # The token was revoked server side, log in again once
            await self.login()
            raw = await self._request_tanks()
            if raw is None:
                raise InvalidAuth("Access token rejected after a new login")

        return [RotarexTank.from_dict(tank) for tank in raw if "Guid" in tank]

    def _token_expired(self) -> bool:
        if self._access_token is None or self._expires_at is None:
            return True
        return datetime.now(UTC) >= self._expires_at - TOKEN_EXPIRY_MARGIN

    async def _request_tanks(self) -> list[dict[str, Any]] | None:
        """Request the raw tank list, returning None when the token is rejected."""
        try:
            async with self._session.get(
                f"{self._base_url}/api/Tanks",
                headers={"Authorization": f"Bearer {self._access_token}"},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    return None
                resp.raise_for_status()
                tanks: list[dict[str, Any]] = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RotarexConnectionError(f"Error fetching tanks: {err}") from err
        return tanks

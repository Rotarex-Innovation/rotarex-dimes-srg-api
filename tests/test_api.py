"""Tests for the Rotarex API client."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import datetime

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from rotarex_dimes_srg_api import (
    DEFAULT_BASE_URL,
    InvalidAuth,
    RotarexApi,
    RotarexConnectionError,
    RotarexError,
)

TOKEN_URL = f"{DEFAULT_BASE_URL}/token"
TANKS_URL = f"{DEFAULT_BASE_URL}/api/Tanks"
TOKEN = {"access_token": "token", "expires_in": 3600}
TANKS = [
    {
        "Guid": "tank-1",
        "Name": "Tank 1",
        "SynchDatas": [
            {"SynchDate": "2024-01-01T12:00:00Z", "Level": 75.5, "Battery": 85.0},
            {"SynchDate": "2024-01-02T12:00:00Z", "Level": 70.0, "Battery": 80.0},
            {"SynchDate": "not-a-date", "Level": 1.0, "Battery": 1.0},
        ],
    },
    {"Guid": "tank-2", "Name": None, "SynchDatas": None},
    {"Name": "Entry without guid"},
]


@pytest.fixture
def mock_http() -> Iterator[aioresponses]:
    with aioresponses() as mocked:
        yield mocked


@pytest.fixture
async def api() -> AsyncIterator[RotarexApi]:
    async with aiohttp.ClientSession() as session:
        yield RotarexApi(session, "user@example.com", "secret")


async def test_fetch_tanks(mock_http: aioresponses, api: RotarexApi) -> None:
    mock_http.post(TOKEN_URL, payload=TOKEN)
    mock_http.get(TANKS_URL, payload=TANKS)

    tanks = await api.fetch_tanks()

    assert [tank.guid for tank in tanks] == ["tank-1", "tank-2"]
    latest = tanks[0].latest_sync
    assert latest is not None
    assert latest.level == 70.0
    assert latest.synch_date == datetime(2024, 1, 2, 12, 0)
    assert tanks[1].name is None
    assert tanks[1].synch_datas == []
    assert tanks[1].latest_sync is None


async def test_token_is_reused(mock_http: aioresponses, api: RotarexApi) -> None:
    mock_http.post(TOKEN_URL, payload=TOKEN)
    mock_http.get(TANKS_URL, payload=TANKS, repeat=True)

    await api.fetch_tanks()
    await api.fetch_tanks()

    assert len(mock_http.requests[("POST", URL(TOKEN_URL))]) == 1


@pytest.mark.parametrize("status", [400, 401])
async def test_login_invalid_auth(
    mock_http: aioresponses, api: RotarexApi, status: int
) -> None:
    mock_http.post(TOKEN_URL, status=status)

    with pytest.raises(InvalidAuth):
        await api.login()


@pytest.mark.parametrize("status", [500, 503])
async def test_login_server_error_is_not_auth_error(
    mock_http: aioresponses, api: RotarexApi, status: int
) -> None:
    mock_http.post(TOKEN_URL, status=status)

    with pytest.raises(RotarexConnectionError):
        await api.login()


@pytest.mark.parametrize("exception", [aiohttp.ClientError(), TimeoutError()])
async def test_login_connection_error(
    mock_http: aioresponses, api: RotarexApi, exception: Exception
) -> None:
    mock_http.post(TOKEN_URL, exception=exception)

    with pytest.raises(RotarexConnectionError):
        await api.login()


async def test_login_unexpected_response(
    mock_http: aioresponses, api: RotarexApi
) -> None:
    mock_http.post(TOKEN_URL, payload={"unexpected": True})

    with pytest.raises(RotarexError):
        await api.login()


async def test_fetch_tanks_relogin_on_401(
    mock_http: aioresponses, api: RotarexApi
) -> None:
    mock_http.post(TOKEN_URL, payload=TOKEN, repeat=True)
    mock_http.get(TANKS_URL, status=401)
    mock_http.get(TANKS_URL, payload=TANKS)

    tanks = await api.fetch_tanks()

    assert len(tanks) == 2


async def test_fetch_tanks_401_after_relogin(
    mock_http: aioresponses, api: RotarexApi
) -> None:
    mock_http.post(TOKEN_URL, payload=TOKEN, repeat=True)
    mock_http.get(TANKS_URL, status=401, repeat=True)

    with pytest.raises(InvalidAuth):
        await api.fetch_tanks()


@pytest.mark.parametrize("kwargs", [{"status": 500}, {"exception": TimeoutError()}])
async def test_fetch_tanks_connection_error(
    mock_http: aioresponses, api: RotarexApi, kwargs: dict
) -> None:
    mock_http.post(TOKEN_URL, payload=TOKEN)
    mock_http.get(TANKS_URL, **kwargs)

    with pytest.raises(RotarexConnectionError):
        await api.fetch_tanks()


async def test_custom_base_url(mock_http: aioresponses) -> None:
    mock_http.post("https://example.com/token", payload=TOKEN)
    mock_http.get("https://example.com/api/Tanks", payload=TANKS)

    async with aiohttp.ClientSession() as session:
        api = RotarexApi(
            session, "user@example.com", "secret", base_url="https://example.com/"
        )
        tanks = await api.fetch_tanks()

    assert len(tanks) == 2

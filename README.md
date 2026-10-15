# Rotarex DIMES SRG API

Async Python client for the Rotarex DIMES SRG cloud API, used to read the level and battery of DIMES SRG tank monitoring devices. It is the library behind the Home Assistant `rotarex` integration.

## Installation

```bash
pip install rotarex-dimes-srg-api
```

## Usage

```python
import asyncio

import aiohttp

from rotarex_dimes_srg_api import InvalidAuth, RotarexApi, RotarexConnectionError


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        api = RotarexApi(session, "your_email@example.com", "your_password")
        try:
            tanks = await api.fetch_tanks()
        except InvalidAuth:
            print("Wrong email or password")
            return
        except RotarexConnectionError:
            print("Rotarex API unreachable")
            return

        for tank in tanks:
            sync = tank.latest_sync
            if sync is not None:
                print(tank.name, sync.level, sync.battery, sync.synch_date)


asyncio.run(main())
```

`fetch_tanks()` logs in when needed and renews the access token automatically. Call `login()` yourself to only check the credentials.

### Errors

| Exception | Raised when |
| --- | --- |
| `InvalidAuth` | The credentials are rejected |
| `RotarexConnectionError` | The API can't be reached, times out or returns a server error |
| `RotarexError` | Base class of the above, also raised for unexpected responses |

### Server

The client talks to `DEFAULT_BASE_URL` by default. Pass `base_url=` to `RotarexApi` to use another server.

A runnable script is available in [`examples/fetch_tanks.py`](examples/fetch_tanks.py). It reads the credentials from the `ROTAREX_EMAIL` and `ROTAREX_PASSWORD` environment variables.

## Development

```bash
pip install -e ".[test]"
ruff check src tests examples
mypy src
pytest
```

Releases are published to PyPI by GitHub Actions when a GitHub release is created.

## License

MIT, see [LICENSE](LICENSE).

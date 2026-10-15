"""Print the tanks of a Rotarex DIMES SRG account.

Usage:
    ROTAREX_EMAIL=you@example.com ROTAREX_PASSWORD=... python examples/fetch_tanks.py

Set ROTAREX_BASE_URL to use another server than the default one.
"""

import asyncio
import os

import aiohttp

from rotarex_dimes_srg_api import DEFAULT_BASE_URL, RotarexApi


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        api = RotarexApi(
            session,
            os.environ["ROTAREX_EMAIL"],
            os.environ["ROTAREX_PASSWORD"],
            base_url=os.environ.get("ROTAREX_BASE_URL", DEFAULT_BASE_URL),
        )
        for tank in await api.fetch_tanks():
            print(tank.guid, tank.name, tank.latest_sync)


if __name__ == "__main__":
    asyncio.run(main())

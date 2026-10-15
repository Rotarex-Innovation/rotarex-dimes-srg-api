from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from operator import attrgetter
from typing import Any


def _parse_synch_date(value: str | None) -> datetime | None:
    """Parse a SynchDate value into a naive datetime.

    The API reports the local time of the device but labels it as UTC, so the
    offset is dropped instead of being trusted.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except ValueError:
        return None


@dataclass(frozen=True, kw_only=True)
class RotarexSyncData:
    """Represent a synchronization data entry."""

    synch_date: datetime | None
    level: float | None
    battery: float | None


@dataclass(frozen=True, kw_only=True)
class RotarexTank:
    """Represent a Rotarex tank."""

    guid: str
    name: str | None
    synch_datas: list[RotarexSyncData]

    @cached_property
    def latest_sync(self) -> RotarexSyncData | None:
        """Return the most recent synchronization with a valid date."""
        return max(
            (sync for sync in self.synch_datas if sync.synch_date is not None),
            key=attrgetter("synch_date"),
            default=None,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RotarexTank:
        """Create a RotarexTank from API dictionary data."""
        synch_datas = [
            RotarexSyncData(
                synch_date=_parse_synch_date(sync.get("SynchDate")),
                level=sync.get("Level"),
                battery=sync.get("Battery"),
            )
            for sync in data["SynchDatas"] or []
        ]
        return cls(
            guid=data["Guid"],
            name=data.get("Name"),
            synch_datas=synch_datas,
        )

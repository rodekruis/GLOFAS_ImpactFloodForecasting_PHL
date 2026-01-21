from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass(frozen=True)
class BasinConfig:
    basin_id: str
    country_iso3: Optional[str]
    hydrobasins_level: int
    hydrobasins_id: int
    raw: Dict[str, Any]

    def validate(self) -> List[str]:
        issues: List[str] = []
        if self.hydrobasins_level <= 0:
            issues.append("hydrobasins_level must be > 0")
        if self.hydrobasins_id <= 0:
            issues.append("hydrobasins_id must be > 0")
        return issues


def load_basin_config(path: Union[str, Path]) -> BasinConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Basin config YAML not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Basin config YAML must parse to a dictionary")

    basin_id = str(data.get("basin_id", "")).strip()
    if not basin_id:
        raise ValueError("basin_id is required in basin config")

    hlev = data.get("hydrobasins_level")
    hid = data.get("hydrobasins_id")
    if hlev is None or hid is None:
        raise ValueError("hydrobasins_level and hydrobasins_id are required in basin config")

    return BasinConfig(
        basin_id=basin_id,
        country_iso3=data.get("country_iso3"),
        hydrobasins_level=int(hlev),
        hydrobasins_id=int(hid),
        raw=data,
    )

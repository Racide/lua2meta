from pathlib import Path
from typing import NamedTuple

__all__ = [
    "DepotKeys",
    "Manifest",
    "DepotInfo",
    "DepotInfos",
    "DepotManifests",
    "InputContent",
    "AppInfo",
]

type DepotKeys = dict[int, str]


class Manifest(NamedTuple):
    gid: int
    content: bytes


class DepotInfo(NamedTuple):
    gid: int
    size: int
    dlc_app_id: int | None


type DepotInfos = dict[int, DepotInfo]
type DepotManifests = dict[int, Manifest]


class InputContent(NamedTuple):
    lua_src: str
    manifests: DepotManifests


class AppInfo(NamedTuple):
    appid: int
    name: str
    install_dir: Path
    build_id: int

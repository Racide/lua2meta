import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import cast

__all__ = ["args"]

_parser = argparse.ArgumentParser("lua2meta")

_parser.add_argument(
    "lua",
    metavar="PATH",
    help="Path to the lua file",
    type=Path,
)

_parser.add_argument(
    "--depots",
    nargs="+",
    metavar="DEPOT-ID",
    help="Filter to the given depot ids. All depots in the lua file are processed if not set",
    type=int,
)

_parser.add_argument(
    "-o",
    "--out-dir",
    metavar="PATH",
    help="Path to the directory where .manifest and .acf files will be written to",
    default=".",
    type=Path,
)

_parser.add_argument(
    "--acf-dir",
    metavar="PATH",
    help="Override the directory where the .acf file will be written to",
    type=Path,
)


_parser.add_argument(
    "-f",
    "--offline",
    help="Do not fetch from network. No .acf will be generated",
    action="store_true",
)

_parser.add_argument(
    "-u",
    "--update",
    help="Prefer cdn manifests over bundled, in case of gid mismatch",
    action="store_true",
)

_parser.add_argument(
    "-a",
    "--api-url",
    metavar="TEMPLATE",
    help='API endpoint from which manifest request codes are obtained. Python format string with "appid", "manifestid", "depotid"',
)

_parser.add_argument(
    "-d",
    "--download-dir",
    metavar="PATH",
    help="Use DepotDownloaderMod to download the depots to the specified directory",
    type=Path,
)

_parser.add_argument(
    "-D",
    "--dry-download",
    help="Print a CLI command instead of running the downloader",
    action="store_true",
)

_parser.add_argument(
    "--downloader",
    metavar="PATH",
    help="DepotDownloaderMod executable",
    default="DepotDownloaderMod.exe",
    type=Path,
)

_parser.add_argument(
    "--downloader-args",
    metavar="ARGS",
    help="Additional arguments to pass to the downloader, as a single string",
)


@dataclass
class Args:
    lua: Path
    depots: list[int]
    out_dir: Path
    acf_dir: Path
    offline: bool
    update: bool
    api_url: str
    download_dir: Path
    dry_download: bool
    downloader: Path
    downloader_args: str


args = cast(Args, _parser.parse_args())

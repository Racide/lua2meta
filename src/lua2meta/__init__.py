import errno
import os
import re
import shlex
import subprocess
import sys
import zipfile
from pathlib import Path
from subprocess import CalledProcessError

# from lua2meta.lua.writer import ACFWriter
from steam.client import SteamClient
from steam.client.cdn import CDNClient

from lua2meta import lua_parser
from lua2meta.acf import write_acf
from lua2meta.args import args
from lua2meta.network import fetch_manifest, fetch_metadata
from lua2meta.types import DepotInfos, DepotKeys, DepotManifests, InputContent, Manifest


def load_input_content(path: Path) -> InputContent:
    if str(path) == "-":
        return InputContent(sys.stdin.read(), {})
    if not path.suffix == ".zip":
        return InputContent(path.read_text(), {})

    with zipfile.ZipFile(path) as zip:
        namelist = zip.namelist()
    zip = zipfile.Path(path)
    lua_path: zipfile.Path | None = None
    manifests: DepotManifests = {}
    for child in (zip / path for path in namelist):
        if child.is_file() and child.suffix == ".lua":
            if lua_path:
                print(f'Additional "{lua_path.name}" skipped')
                continue
            lua_path = child
            print(f'Found "{lua_path.name}"')
        if child.is_file() and child.suffix == ".manifest":
            if not (
                match := re.fullmatch(r"(?P<depot_id>\d+)_(?P<gid>\d+)", child.stem)
            ):
                # binary vdf parsing is reportedly broken in steam module,
                # which is probably abandoned, can only automate on filenames
                print(f'Unrecognized manifest filename "{child.name}"')
                continue
            manifests[int(match.group("depot_id"))] = Manifest(
                int(match.group("gid")), child.read_bytes()
            )
    if not lua_path:
        raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), "*.lua")
    return InputContent(lua_path.read_text(), manifests)


def fetch_manifests(
    cdn_client: CDNClient,
    appid: int,
    manifest_gids: DepotInfos,
) -> DepotManifests:
    manifests: DepotManifests = {}

    for depot, depot_info in manifest_gids.items():
        try:
            manifest = fetch_manifest(cdn_client, appid, depot, depot_info.gid)
        except Exception:
            print(f"Failed to fetch manifest {depot_info.gid} for depot {depot}")
            continue
        manifests[depot] = manifest
    return manifests


def write_manifests(manifests: DepotManifests):
    for depot, (gid, content) in manifests.items():
        (args.out_dir / f"{depot}_{gid}.manifest").write_bytes(content)


def write_keylist(depot_keys: DepotKeys):
    s = "\n".join(f"{depot};{key}" for depot, key in depot_keys.items())
    (args.out_dir / "keys.txt").write_text(s)


def download(appid: int, manifests: DepotManifests, download_dir: Path):
    download_dir = args.download_dir / download_dir
    download_dir.mkdir(exist_ok=True)

    argv: list[str] = [""] * 11
    argv[0] = str(args.downloader)
    argv[1] = "-app"
    argv[2] = str(appid)
    argv[3] = "-depotkeys"
    argv[4] = str(args.out_dir / "keys.txt")
    argv[5] = "-depot"
    argv[6] = "DEPOT PLACEHOLDER"
    argv[7] = "-manifestfile"
    argv[8] = "MANIFESTFILE PLACEHOLDER"
    argv[9] = "-dir"
    argv[10] = str(download_dir)
    if args.downloader_args:
        argv += shlex.split(args.downloader_args)

    for depot, (gid, _) in manifests.items():
        argv[6] = str(depot)
        argv[8] = str(args.out_dir / f"{depot}_{gid}.manifest")
        print(*(f'"{arg}"' if " " in arg else arg for arg in argv), "\n\\/\n")
        if not args.dry_download:
            subprocess.run(argv, check=True)


def main():
    if not args.out_dir.is_dir():
        print(OSError(errno.ENOENT, os.strerror(errno.ENOENT), str(args.out_dir)))
        return 1
    if args.acf_dir is None:
        args.acf_dir = args.out_dir
    if not args.acf_dir.is_dir():
        print(OSError(errno.ENOENT, os.strerror(errno.ENOENT), str(args.out_dir)))
        return 1
    if args.download_dir is None:
        args.download_dir = args.out_dir
    if not args.download_dir.is_dir():
        print(OSError(errno.ENOENT, os.strerror(errno.ENOENT), str(args.out_dir)))
        return 1

    if args.api_url:
        try:
            args.api_url.format(appid=0, depotid=1, manifestid=2)
        except KeyError as ex:
            print(
                f"Invalid api endpoint template, used unknown placeholder: {ex.args[0]}"
            )
            return 1
        except ValueError:
            print('Invalid api endpoint template, try "--help" for more information')
            return 1

    try:
        lua_src, manifests = load_input_content(args.lua)
    except Exception as ex:
        print("Attempting to open lua source file resulted in the following error:")
        print(ex)
        return 2

    try:
        appid, depot_keys = lua_parser.parse(lua_src)
    except Exception as ex:
        print("Attempting to parse lua source file resulted in the following error:")
        print(ex)
        return 2

    if args.depots:
        depot_keys: DepotKeys = {
            depot: depot_keys[depot] for depot in args.depots if depot in depot_keys
        }
    manifests = {
        depot: manifests[depot] for depot in manifests.keys() & depot_keys.keys()
    }

    if not args.offline:
        client = SteamClient()
        client.anonymous_login()
        print("Logged in anonymously")

        try:
            app_info, depot_infos = fetch_metadata(client, appid)
        except Exception:
            print("Failed fetch metadata from Steam")
            return 3

        depot_infos = {
            depot: depot_infos[depot]
            for depot in depot_infos.keys() & depot_keys.keys()
        }

        if args.api_url:
            remote_manifests = (
                depot_keys.keys() - manifests.keys()
            ) & depot_infos.keys()

            if args.update:
                upgradable_manifests = {
                    depot
                    for depot in manifests.keys() & depot_infos.keys()
                    if manifests[depot].gid != depot_infos[depot]
                }
                for depot in upgradable_manifests:
                    print(f"Outdated manifest for depot {depot}")
                remote_manifests |= upgradable_manifests

            cdn_client = CDNClient(client)
            fetched_manifests = fetch_manifests(
                cdn_client,
                appid,
                {depot: depot_infos[depot] for depot in remote_manifests},
            )
            manifests |= fetched_manifests

            for depot in remote_manifests - fetched_manifests.keys():
                print(f"Failed to download manifest file for depot {depot}")

    if lost_manifests := depot_keys.keys() - manifests.keys():
        print("Failed to download necessary manifests for the following depots:")
        print(", ".join(map(str, lost_manifests)))
        return 3

    if not args.offline:
        try:
            write_acf(app_info, depot_infos)  # pyright: ignore[reportPossiblyUnboundVariable]
        except Exception:
            print(f"Failed to write .acf file to {args.acf_dir}")
            return 4

    try:
        write_keylist(depot_keys)
        write_manifests(manifests)
    except Exception:
        print(f"Failed to write output to {args.out_dir.absolute()}")
        return 4

    try:
        download(
            appid,
            manifests,
            Path(str(appid)) if args.offline else app_info.install_dir,  # pyright: ignore[reportPossiblyUnboundVariable]
        )
    except CalledProcessError as ex:
        print(f"\nDownloader terminated with a non-zero error {ex.returncode}")
        return 5
    except Exception:
        print(f"Failed to download in {args.download_dir.absolute()}")

    return 0


if __name__ == "__main__":
    main()

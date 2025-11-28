import errno
import os
import re
import shlex
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from subprocess import CalledProcessError

from steam.client import SteamClient
from steam.client.cdn import CDNClient

from lua2meta import lua_parser
from lua2meta import vdf
from lua2meta.args import args
from lua2meta.network import fetch_manifest, fetch_metadata
from lua2meta.types import DepotInfos, DepotKeys, DepotManifests, InputContent, Manifest
from lua2meta.utils import dict_copyorder, dict_intersect


def load_input_content(path: Path) -> InputContent:
    if str(path) == "-":
        return InputContent(sys.stdin.read(), {})
    if not path.suffix == ".zip":
        return InputContent(path.read_text(), {})

    with zipfile.ZipFile(path) as zip_file:
        zip = zipfile.Path(zip_file)
        lua_path: zipfile.Path | None = None
        manifests: DepotManifests = {}
        for child in (zip / path for path in zip_file.namelist()):
            if child.is_file() and child.suffix == ".lua":
                if lua_path:
                    print(f'Additional "{lua_path.name}" skipped')
                    continue
                lua_path = child
                print(f'Found "{lua_path.name}"')
            if child.is_file() and child.suffix == ".manifest":
                if not (match := re.fullmatch(r"(?P<depot_id>\d+)_(?P<gid>\d+)", child.stem)):
                    # binary vdf parsing is reportedly broken in steam module,
                    # which is probably abandoned, can only automate on filenames
                    print(f'Unrecognized manifest filename "{child.name}"')
                    continue
                manifests[int(match.group("depot_id"))] = Manifest(int(match.group("gid")), child.read_bytes())
        if not lua_path:
            raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), "*.lua")
        return InputContent(lua_path.read_text(), manifests)


def fetch_manifests(
    cdn_client: CDNClient,
    appid: int,
    manifest_infos: DepotInfos,
) -> DepotManifests:
    manifests: DepotManifests = {}

    for depot, depot_info in manifest_infos.items():
        try:
            manifest = fetch_manifest(cdn_client, appid, depot, depot_info.gid)
        except Exception as ex:
            print(f"Failed to fetch manifest {depot_info.gid} for depot {depot}:")
            print(ex)
            continue
        manifests[depot] = manifest
    return manifests


def write_manifests(manifests: DepotManifests):
    for depot, (gid, content) in manifests.items():
        (args.out_dir / f"{depot}_{gid}.manifest").write_bytes(content)


def write_keylist(appid: int, depot_keys: DepotKeys):
    s = "\n".join(f"{depot};{key}" for depot, key in depot_keys.items())
    (args.out_dir / f"{appid}_keys.txt").write_text(s)


def update_config(depot_keys: DepotKeys):
    backup_config = args.config.with_suffix(".bak.vdf")
    try:
        shutil.copyfile(args.config, backup_config)
    except Exception:
        print(f"Failed to create backup at {backup_config}, abort:")
        raise
    try:
        vdf.write_config(depot_keys)
    except Exception:
        print(f"Failed to update config .vdf file at {args.config},")
        print(f"backup available at {backup_config}:")
        raise


def download(appid: int, manifests: DepotManifests, download_dir_name: Path):
    download_dir = args.download_dir / download_dir_name

    argv: list[str] = [""] * 12
    argv[0] = str(args.downloader)
    argv[1] = "-app"
    argv[2] = str(appid)
    argv[3] = "-depot"
    argv[4] = "DEPOT PLACEHOLDER"
    argv[5] = "-validate"
    argv[6] = "-depotkeys"
    argv[7] = str(args.out_dir / f"{appid}_keys.txt")
    argv[8] = "-manifestfile"
    argv[9] = "MANIFESTFILE PLACEHOLDER"
    argv[10] = "-dir"
    argv[11] = str(download_dir)
    if args.downloader_args:
        argv += shlex.split(args.downloader_args)

    for depot, (gid, _) in manifests.items():
        argv[4] = str(depot)
        argv[9] = str(args.out_dir / f"{depot}_{gid}.manifest")
        print(*(f'"{arg}"' if " " in arg else arg for arg in argv))
        if not args.dry_download:
            download_dir.mkdir(exist_ok=True)
            print("\\/\n")
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
    if args.config and not args.config.is_file():
        print(OSError(errno.ENOENT, os.strerror(errno.ENOENT), str(args.config)))
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
            print(f"Invalid api endpoint template, used unknown placeholder: {ex.args[0]}")
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
        depot_keys: DepotKeys = {depot: depot_keys[depot] for depot in args.depots if depot in depot_keys}
    manifests = dict_intersect(manifests, depot_keys)

    if not args.offline:
        client = SteamClient()
        client.anonymous_login()
        print("Logged in anonymously")

        try:
            app_info, depot_infos = fetch_metadata(client, appid)
        except Exception:
            print("Failed fetch metadata from Steam")
            return 3

        for depot in depot_keys.keys() - depot_infos.keys():
            print(f"Unknown depot {depot} will be skipped")
        depot_keys = dict_intersect(depot_keys, depot_infos)
        manifests = dict_intersect(manifests, depot_infos)

        if args.api_url:
            remote_manifest_gids = depot_keys.keys() - manifests.keys()

            if args.update:
                upgradable_manifest_gids = {depot for depot in manifests.keys() if manifests[depot].gid != depot_infos[depot].gid}
                for depot in upgradable_manifest_gids:
                    print(f"Outdated manifest for depot {depot}")
                remote_manifest_gids |= upgradable_manifest_gids

            cdn_client = CDNClient(client)
            fetched_manifests = fetch_manifests(
                cdn_client,
                appid,
                dict_intersect(depot_infos, remote_manifest_gids),
            )
            for depot in remote_manifest_gids - fetched_manifests.keys():
                print(f"Failed to download manifest file for depot {depot}")
            manifests |= fetched_manifests  # breaks ordering

        depot_infos = dict_intersect(depot_infos, manifests)
        manifests = dict_copyorder(manifests, depot_infos)

    if lost_manifests := depot_keys.keys() - manifests.keys():
        print("Missing necessary manifests for the following depots:")
        print(", ".join(map(str, lost_manifests)))
        return 3

    try:
        write_keylist(appid, depot_keys)
        write_manifests(manifests)
    except Exception as ex:
        print(f"Failed to write output to {args.out_dir.absolute()}:")
        print(ex)
        return 4

    if not args.offline:
        try:
            vdf.write_acf(app_info, depot_infos)  # pyright: ignore[reportPossiblyUnboundVariable]
        except Exception as ex:
            print(f"Failed to write .acf file to {args.acf_dir}:")
            print(ex)
            return 4
        if args.config:
            try:
                update_config(depot_keys)
            except Exception as ex:
                print(ex)
                print("Try updating the config .vdf file manually")

    try:
        download(
            appid,
            manifests,
            Path(str(appid)) if args.offline else app_info.install_dir,  # pyright: ignore[reportPossiblyUnboundVariable]
        )
    except CalledProcessError as ex:
        print(f"\nDownloader terminated with a non-zero status {ex.returncode}")
        return 6
    except Exception as ex:
        print(f"Failed to download in {args.download_dir.absolute()}:")
        print(ex)

    return 0


if __name__ == "__main__":
    main()

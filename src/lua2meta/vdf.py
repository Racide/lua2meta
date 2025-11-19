from typing import cast
import vdf
from vdf import VDFDict

from lua2meta.args import args
from lua2meta.types import AppInfo, DepotInfo, DepotInfos, DepotKeys

__all__ = ["write_acf", "write_config"]


def write_acf(app_info: AppInfo, depot_infos: DepotInfos):
    def installed_depot(depot_info: DepotInfo):
        value = {"manifest": depot_info.gid, "size": depot_info.size}
        if depot_info.dlc_app_id is not None:
            value["dlcappid"] = depot_info.dlc_app_id
        return value

    acf_contents = {
        "AppState": {
            "appid": app_info.appid,
            "Universe": "1",
            "name": app_info.name,
            "StateFlags": "4",
            "installdir": str(app_info.install_dir),
            "buildid": app_info.build_id,
            "InstalledDepots": {depot: installed_depot(depot_info) for depot, depot_info in depot_infos.items()},
        }
    }
    (args.acf_dir / f"appmanifest_{app_info.appid}.acf").write_text(vdf.dumps(acf_contents, pretty=True))


def write_config(depot_keys: DepotKeys):
    with args.config.open(mode="r+") as config_file:
        config = cast(VDFDict, vdf.load(config_file, mapper=VDFDict))
        t = config["InstallConfigStore"]["Software"]["valve"]["Steam"]
        # deduplicate depots
        t["depots"] = t["depots"] | {str(depot): {"DecryptionKey": key} for depot, key in depot_keys.items()}
        config_file.seek(0)
        vdf.dump(config, config_file, pretty=True)
        config_file.truncate()

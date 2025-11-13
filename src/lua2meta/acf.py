import vdf

from lua2meta.args import args
from lua2meta.types import AppInfo, DepotInfo, DepotInfos


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

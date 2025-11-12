import errno
import io
import os
from pathlib import Path
import zipfile

import requests
import requests.adapters
from requests.adapters import HTTPAdapter
from steam.client import SteamClient
from steam.client.cdn import CDNClient, ContentServer
from urlpath import URL

from lua2meta.args import args
from lua2meta.types import AppInfo, DepotInfo, DepotInfos, Manifest

__all__ = ["fetch_manifest"]


def initialize_mrc_session():
    # A respectful strategy for a mysterious endpoint
    retry_strategy = requests.adapters.Retry(
        total=5,  # total retry attempts
        # connect=5,  # retry on connection errors
        # read=5,  # retry on read errors
        # status=5,  # retry on bad status codes
        backoff_factor=2,  # exponential backoff
        status_forcelist=[429, 500, 502, 503, 504],  # transient failures
        allowed_methods=["GET"],
        # respect_retry_after_header=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


mrc_session = initialize_mrc_session()


def fetch_metadata(client: SteamClient, appid: int) -> tuple[AppInfo, DepotInfos]:
    product_info = client.get_product_info((appid,), auto_access_tokens=False)
    if product_info is None:
        raise KeyError("apps", "No response from steam api")
    app = product_info["apps"][appid]
    depot_infos: DepotInfos = {}
    for id, depot in app["depots"].items():
        try:
            dlc_app_id = int(depot["dlcappid"])
        except Exception:
            dlc_app_id = None
        try:
            depot_infos[int(id)] = DepotInfo(
                int(depot["manifests"]["public"]["gid"]),
                int(depot["manifests"]["public"]["size"]),
                dlc_app_id,
            )
        except Exception:
            continue
    return (
        AppInfo(
            appid,
            app["common"]["name"],
            Path(app["config"]["installdir"]),
            int(app["depots"]["branches"]["public"]["buildid"]),
        ),
        depot_infos,
    )


def fetch_manifest_request_code(appid: int, depot: int, gid: int) -> str:
    url = args.api_url.format(appid=appid, depotid=depot, manifestid=gid)
    print(f"Fetching request code from: {url}")
    response = mrc_session.get(url, timeout=10)
    assert response.status_code == 200
    return response.text


def decompress_manifest(manifest: bytes):
    with zipfile.ZipFile(io.BytesIO(manifest)) as zip_file:
        zip = zipfile.Path(zip_file)
        for child in (zip / path for path in zip_file.namelist()):
            if child.is_file():
                return child.read_bytes()
    raise OSError(errno.ENOENT, os.strerror(errno.ENOENT), "file")


def fetch_manifest(
    cdn_client: CDNClient,
    appid: int,
    depot: int,
    gid: int,
) -> Manifest:
    server: ContentServer = cdn_client.get_content_server()
    server_url = URL("").with_components(
        hostname=server.host,
        port=server.port,
        scheme="https" if server.https else "http",
    )
    try:
        code = fetch_manifest_request_code(appid, depot, gid)
    except Exception:
        print("Failed to retrieve manifest request code")
        raise

    url: URL = server_url / "depot" / depot / "manifest" / gid / 5 / code

    print(f"Download manifest from {url}")
    response = url.get()
    assert response.status_code == 200
    manifest = response.content
    try:
        manifest = decompress_manifest(manifest)
        print(f"Manifest {gid} decompressed")
    except Exception:
        print(f"Manifest {gid} likely uncompressed")
    return Manifest(gid, manifest)

# lua2meta

This tool retrieves metadata files associated with a .lua file and processes for archival use.

```txt
usage: lua2meta [-h] [--depots DEPOT-ID [DEPOT-ID ...]] [-o PATH] [--acf-dir PATH] [-f] [-u] [-a TEMPLATE] [-d PATH] [-D] [--downloader PATH] [--downloader-args ARGS] PATH

positional arguments:
  PATH                  Path to the .lua file or .zip with lua and .manifest s

options:
  -h, --help            show this help message and exit
  --depots DEPOT-ID [DEPOT-ID ...]
                        Filter to the given depot ids. All depots in the lua file are processed if not set
  -o, --out-dir PATH    Path to the directory where .manifest and .acf files will be written to
  --acf-dir PATH        Override the directory where the .acf file will be written to
  -f, --offline         Do not fetch from network. No .acf will be generated
  -u, --update          Prefer cdn manifests over bundled, in case of gid mismatch
  -a, --api-url TEMPLATE
                        API endpoint from which manifest request codes are obtained. Python format string with "appid", "manifestid", "depotid"
  -d, --download-dir PATH
                        Use DepotDownloaderMod to download the depots to the specified directory
  -D, --dry-download    Print a CLI command instead of running the downloader
  --downloader PATH     DepotDownloaderMod executable
  --downloader-args ARGS
                        Additional arguments to pass to the downloader, as a single string
```

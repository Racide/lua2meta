# lua2meta

This tool retrieves metadata files associated with a .lua file and processes for archival use.

```txt
usage: lua2meta [-h] [--depots DEPOT-ID [DEPOT-ID ...]] [-o PATH] [--acf-dir PATH] [-f] [-u] [-a TEMPLATE] [-c PATH] [-d PATH] [-D] [--downloader PATH]
                [--downloader-args ARGS]
                PATH

positional arguments:
  PATH                  path to the .lua file or .zip with lua and .manifest s

options:
  -h, --help            show this help message and exit
  --depots DEPOT-ID [DEPOT-ID ...]
                        filter to the given depot ids. All depots in the lua file are processed if not set
  -o, --out-dir PATH    path to the directory where .manifest and .acf files will be written to
  --acf-dir PATH        override the directory where the .acf file will be written to
  -f, --offline         do not fetch from network. No .acf will be generated
  -u, --update          prefer cdn manifests over bundled, in case of gid mismatch
  -a, --api-url TEMPLATE
                        API endpoint from which manifest request codes are obtained. Python format string with "appid", "manifestid", "depotid"
  -c, --config PATH     path to the config .vdf file where depot keys will be added
  -d, --download-dir PATH
                        use DepotDownloaderMod to download the depots to the specified directory
  -D, --dry-download    print a CLI command instead of running the downloader
  --downloader PATH     DepotDownloaderMod executable
  --downloader-args ARGS
                        additional arguments to pass to the downloader, as a single string
```

Deodexer
========

Deodexer is a simple tool that uses [vdexExtractor](https://github.com/anestisb/vdexExtractor) to deodex Android 8.0+ ROMs.


Usage
-----

If you have the `vdexExtractor` and `zipalign` tools already installed or otherwise available, just run the `deodex.py` script against your extracted ROM directory.

```sh
./deodex.py /path/to/extracted/ROM
```

It will recursively find any `.jar` and `.apk` file in the directory and attempt to deodex and zipalign them. If the file is successfully deodexed, its corresponding `.art`, `.oat`, `.odex`, or `.vdex` files will be deleted. The script will deodex any many files as possible, deferring failure until the end and performs operations atomically so nothing is changed if an operation fails for a file. Deodexer is idempotent, so it can be run as many times as desired against the same directory.

If you don't have the required tools installed, there's a prebuilt docker image with deodexer and all the dependencies included. To use it, simply run:

```sh
docker run --rm -it \
    -v /path/to/extracted/ROM:/sysroot \
    chenxiaolong/deodexer:1.1
```

The docker image, by default, runs Deodexer against the directory mounted at `/sysroot` inside the container. The permissions of any files created in the bind mounted volume should match the permissions of the directory itself.


Compiling from Source
---------------------

To build the docker image from source, simply run:

```sh
docker build -t deodexer .
```


License
-------

Deodexer is licensed under GPLv3+ (see the LICENSE file). Third party libraries and programs are used under their respective licenses. Copies of these licenses are in the `licenses/` directory of this repository. Patches and other source code modifications to third party software are under the same license as the original software.

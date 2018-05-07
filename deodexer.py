#!/usr/bin/env python3

# Copyright (C) 2018  Andrew Gunnerson <andrewgunnerson@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import errno
import glob
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile


programs = None


class DeodexException(Exception):
    pass


class RenamableTempFile(object):
    def __init__(self, *args, **kwargs):
        kwargs['delete'] = False
        self.file = tempfile.NamedTemporaryFile(*args, **kwargs)
        self.needs_unlink = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.file.close()
        if self.needs_unlink:
            os.unlink(self.file.name)

    def rename_and_disown(self, path):
        os.rename(self.file.name, path)
        self.needs_unlink = False


def is_deodexed(path):
    with zipfile.ZipFile(path) as z:
        try:
            z.getinfo('classes.dex')
            return True
        except KeyError:
            return False


def delete_file_and_empty_parents(path):
    os.unlink(path)
    for p in pathlib.Path(path).parents:
        try:
            os.rmdir(p)
        except OSError as e:
            if e.errno == errno.ENOTEMPTY or e.errno == errno.ENOENT:
                break


def find_optimized_files(path):
    # Framework odex/vdex files are in:
    # * <base dir>/<arch>/boot-<stem>.{oat,vdex} for jars in the boot
    #   class path
    # * <base dir>/boot.oat for jars in the boot class path
    # * <base dir>/oat/<arch>/<stem>.{odex,vdex} for other jars
    #
    # APK odex/vdex files are in:
    # * <base dir>/oat/<arch>/<stem>.{odex,vdex}

    file_path = pathlib.Path(path)
    files = glob.glob(str(file_path.parent / 'oat' / '*' /
            glob.escape(file_path.stem)) + '.*')

    if file_path.suffix == '.jar':
        files.extend(glob.glob(str(file_path.parent / '*' /
                ('boot-' + glob.escape(file_path.stem))) + '.*'))

    known_extensions = ['.art', '.oat', '.odex', '.vdex']
    files_by_type = {}

    for f in files:
        extension = pathlib.Path(f).suffix
        if extension in known_extensions:
            files_by_type.setdefault(extension[1:], []).append(f)

    return files_by_type


def deodex_vdex(vdex, temp_dir):
    subprocess.run([
        programs['vdexExtractor'],
        '-i', vdex,
        '-o', temp_dir,
        '-v', '2',
    ], check=True)


def zipalign(path):
    prog = programs['zipalign']
    result = subprocess.run([prog, '-c', '4', path])
    if result.returncode != 0:
        output_path = path + '.zipaligned'
        subprocess.run([prog, '4', path, output_path], check=True)
        os.rename(output_path, path)


def add_dex_files_to_zip(zip_path, dex_dir, prefix):
    file_path = pathlib.Path(zip_path)

    with RenamableTempFile(dir=str(file_path.parent),
                           prefix=str(file_path.name) + '.') as t:
        with open(zip_path, 'rb') as f:
            shutil.copyfileobj(f, t.file)

        t.file.seek(0)

        with zipfile.ZipFile(t.file, 'a') as z:
            for p in os.scandir(dex_dir):
                if not p.name.startswith(prefix):
                    raise DeodexException(
                            'Found unknown file in dex dir: ' + p.name)

                z.write(pathlib.Path(dex_dir) / p.name,
                        arcname=p.name[len(prefix):])

        t.rename_and_disown(zip_path)

    zipalign(zip_path)


def deodex_file(sysroot, path):
    optimized_files = find_optimized_files(path)

    if not is_deodexed(path) and optimized_files:
        if 'vdex' not in optimized_files:
            raise DeodexException('No vdex files found for: ' + path)

        with tempfile.TemporaryDirectory() as temp_dir:
            used_vdex = None
            fail_info = None

            for vdex in optimized_files['vdex']:
                try:
                    deodex_vdex(vdex, temp_dir)
                    used_vdex = vdex
                    fail_info = None
                    break
                except Exception as e:
                    fail_info = (vdex, e)

            if fail_info:
                raise DeodexException('Failed to extract vdex: ' + fail_info[0]) \
                        from fail_info[1]

            # Atomically update zip file
            prefix = pathlib.Path(used_vdex).stem + '.apk_'
            try:
                add_dex_files_to_zip(path, temp_dir, prefix)
            except:
                subprocess.run(['ls', temp_dir])
                raise

    for t in optimized_files:
        for f in optimized_files[t]:
            delete_file_and_empty_parents(f)


def deodex_system(sysroot):
    failed = []

    for root, _, files in os.walk(sysroot):
        for f in files:
            full_path = str(pathlib.Path(root).joinpath(f))

            if f.endswith('.apk') or f.endswith('.jar'):
                print('Processing: ' + full_path)
                try:
                    deodex_file(sysroot, full_path)
                except DeodexException as e:
                    traceback.print_exc()
                    failed.append(full_path)
            elif f == 'boot.art' or f == 'boot.oat' or f == 'boot.vdex':
                delete_file_and_empty_parents(full_path)

    if failed:
        print('Failed to deodex:', file=sys.stderr)
        for f in failed:
            print('- ' + f, file=sys.stderr)
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description='''\
            Simple tool to deodex Android 8.0+ ROMs
        ''',
        epilog='''\
            This tool supports deodexing Android 8.0+ ROMs that use vdex files
            to store the optimized dex code. After successful deodexing, any
            related '.art', '.oat', '.odex', and '.vdex' files will be deleted.
            Any file that is deodexed will also be zipaligned, though
            already-deodexed files are left alone.
        ''',
    )
    parser.add_argument('--vdexextractor', default='vdexExtractor',
                        help='Path to vdexExtractor binary')
    parser.add_argument('--zipalign', default='zipalign',
                        help='Path to zipalign binary')
    parser.add_argument('sysroot',
                        help='System/vendor directory to deodex')

    args = parser.parse_args()

    global programs
    programs = {
        'vdexExtractor': args.vdexextractor,
        'zipalign': args.zipalign,
    }

    for prog in programs:
        if not shutil.which(programs[prog]):
            raise DeodexException('%s executable not found' % prog)

    if not deodex_system(args.sysroot):
        exit(1)


if __name__ == '__main__':
    main()

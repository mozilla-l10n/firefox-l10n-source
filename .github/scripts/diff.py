# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Compare messages in localization files between two paths
"""

from __future__ import annotations

from argparse import ArgumentParser
from os import walk
from os.path import commonpath, exists, join, relpath
from sys import exit

from moz.l10n.resource import UnsupportedResource, l10n_equal, parse_resource


def diff_tree(a_root: str, b_root: str, ignore: set[str]) -> int:
    common_root = commonpath((a_root, b_root))
    diff_count = 0
    b_seen: set[str] = set()
    for dirpath, dirnames, filenames in walk(a_root):
        dirnames[:] = [dn for dn in dirnames if not dn.startswith((".", "_"))]
        for fn in filenames:
            if not fn.startswith((".", "_")):
                a_path = join(dirpath, fn)
                rel_path = relpath(a_path, a_root)
                if rel_path in ignore:
                    continue
                b_path = join(b_root, rel_path)
                if not exists(b_path):
                    print(f"Missing file: {relpath(b_path, common_root)}")
                    diff_count += 1
                elif not l10n_equal_paths(a_path, b_path):
                    print(f"Files at {rel_path} differ")
                    diff_count += 1
                b_seen.add(b_path)
    for dirpath, dirnames, filenames in walk(b_root):
        dirnames[:] = [dn for dn in dirnames if not dn.startswith((".", "_"))]
        for fn in filenames:
            if not fn.startswith((".", "_")):
                b_path = join(dirpath, fn)
                rel_path = relpath(b_path, b_root)
                if rel_path not in ignore and b_path not in b_seen:
                    a_path = join(a_root, rel_path)
                    print(f"Missing file: {relpath(a_path, common_root)}")
                    diff_count += 1
    return diff_count


def l10n_equal_paths(a_path: str, b_path: str) -> bool:
    with open(a_path, "rb") as a_file:
        a_bytes = a_file.read()
    with open(b_path, "rb") as b_file:
        b_bytes = b_file.read()
    if a_bytes == b_bytes:
        return True

    try:
        a_res = parse_resource(a_path, a_bytes)
    except UnsupportedResource:
        a_res = None
    except Exception as error:
        print(f"Parse error at {a_path}: {error}")
        return False
    try:
        b_res = parse_resource(b_path, b_bytes)
    except Exception as error:
        if isinstance(error, UnsupportedResource) and a_res is None:
            return True
        else:
            print(f"Parse error at {b_path}: {error}")
            return False
    if a_res is None:
        print(f"Parse error at {a_path}")
        return False

    return l10n_equal(a_res, b_res)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs=2, help="Root directories for the comparison")
    parser.add_argument("--ignore", nargs="*", help="Relative paths to ignore")
    args = parser.parse_args()

    ignore = set(args.ignore) if args.ignore else set()
    if diff_tree(args.path[0], args.path[1], ignore):
        exit(1)

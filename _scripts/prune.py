# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Prune localization files after updates from Firefox branches.

Expects to find `_data/[branch].json` for each branch,
and removes any other JSON data files in `_data/`.
Removes any files and messages not used by any branch.

Writes a commit message summary as `.prune_msg`.
"""

import json
from argparse import ArgumentParser
from os import getcwd, remove, scandir
from os.path import join, relpath, splitext
from sys import exit
from moz.l10n.paths import L10nDiscoverPaths
from moz.l10n.resource import parse_resource, serialize_resource
from moz.l10n.resource.data import Entry


def prune_file(path: str, msg_refs: set[str]):
    with open(path, "+rb") as file:
        resource = parse_resource(path, file.read())
        drop_count = 0
        for section in resource.sections:
            next = [
                entry
                for entry in section.entries
                if not isinstance(entry, Entry)
                or ".".join(section.id + entry.id) in msg_refs
            ]
            diff = len(section.entries) - len(next)
            if diff > 0:
                drop_count += diff
                section.entries = next
        resource.sections = [
            section for section in resource.sections if section.entries
        ]
        if drop_count:
            print(f"drop {drop_count} from {path}")
            file.seek(0)
            for line in serialize_resource(resource):
                file.write(line.encode("utf-8"))
            file.truncate()
    return drop_count


def prune(branches: list[str]):
    cwd = getcwd()

    removed_data = []
    removed_files = 0
    removed_messages = 0
    refs: dict[str, set[str]] = {}
    expected = set(branches)
    for entry in scandir("_data"):
        branch, ext = splitext(entry.name)
        if entry.is_file() and ext == ".json":
            if branch in branches:
                expected.remove(branch)
                with open(entry.path, "r") as file:
                    data: dict[str, list[str]] = json.load(file)
                for path, keys in data.items():
                    if path in refs:
                        refs[path].update(keys)
                    else:
                        refs[path] = set(keys)
            else:
                print(f"remove {relpath(entry.path, cwd)}")
                remove(entry.path)
                removed_data.append(branch)
    if not refs:
        exit(f"No data found for: {branches}")
    if expected:
        exit(f"Incomplete data! Not found: {expected}")

    for ref_path in L10nDiscoverPaths(cwd, ref_root=cwd).ref_paths:
        path = relpath(ref_path, cwd)
        if path not in refs:
            print(f"remove {path}")
            remove(path)
            removed_files += 1
        elif refs[path]:
            removed_messages += prune_file(path, refs[path])
    return removed_data, removed_files, removed_messages


def write_commit_msg(data: list[str], files: int, messages: int):
    summary = []
    for branch in data:
        summary.append(f"{branch} data")
    if files:
        summary.append(f"{files} file" if files == 1 else f"{files} files")
    if messages:
        summary.append(
            f"{messages} message" if messages == 1 else f"{messages} messages"
        )
    with open(".prune_msg", "w") as file:
        file.write(f"Removed: {', '.join(summary)}" if summary else "no changes")


if __name__ == "__main__":
    prog = "python -m _scripts.prune"
    parser = ArgumentParser(prog=prog, description=__doc__)
    args = parser.parse_args()

    config_file = join("_configs", "config.json")
    with open(config_file) as f:
        cfg_automation = json.load(f)

    removed = prune(cfg_automation["branches"])
    write_commit_msg(*removed)

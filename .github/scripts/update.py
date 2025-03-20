# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Update the localization source files from a Firefox branch, adding new files and
messages. For updates from the "{HEAD}" branch, also update changed messages.

Writes a summary of the branch's localized files and message keys as
`_data/[branch].json`, and a commit message summary as `.update_msg`.
"""

import json
import tomllib
from argparse import ArgumentParser
from filecmp import cmp
from os import makedirs
from os.path import abspath, dirname, exists, join, relpath
from re import sub
from shutil import copy
from sys import exit
from typing import TypedDict

import tomli_w
from moz.l10n.paths import L10nConfigPaths
from moz.l10n.resource import (
    UnsupportedResource,
    add_entries,
    parse_resource,
    serialize_resource,
)
from moz.l10n.model import Entry


class AutomationConfig(TypedDict):
    branches: list[str]
    head: str
    paths: list[str]


def add_config(fx_root: str, fx_cfg_path: str, done: set[str], source_dirs: set[str]):
    parts = fx_cfg_path.split("/")
    if (
        "{" in fx_cfg_path
        or len(parts) < 3
        or parts[-2] != "locales"
        or parts[-1] != "l10n.toml"
    ):
        exit(f"Unsupported config path: {fx_cfg_path}")

    cfg_path = join("_configs", f"{'-'.join(parts[:-2])}.toml")
    if cfg_path not in done:
        done.add(cfg_path)
        with open(join(fx_root, fx_cfg_path), "rb") as file:
            cfg = tomllib.load(file)
        cfg["basepath"] = ".."
        for path in cfg["paths"]:
            ref_path = path["reference"]
            if "/en-US/" in ref_path:
                source_dirs.add(ref_path[: ref_path.find("/en-US/")])

            # Remove placeholders like `{l}` from l10n paths
            path["reference"] = sub(r"{\s*\S+\s*}", "", path["l10n"])
        if "includes" in cfg:
            for incl in cfg["includes"]:
                incl["path"] = add_config(fx_root, incl["path"], done, source_dirs)

        makedirs(dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "wb") as file:
            tomli_w.dump(cfg, file)
    return cfg_path


def update(
    cfg_automation: AutomationConfig,
    branch: str,
    fx_root: str,
    config_files: list[str],
):
    if branch not in cfg_automation["branches"]:
        exit(f"Unknown branch: {branch}")
    is_head = branch == cfg_automation["head"]
    if not exists(fx_root):
        exit(f"Firefox root not found: {fx_root}")
    print(f"source: {branch} at {fx_root}")
    fx_root = abspath(fx_root)

    fixed_config_paths: set[str] = set()
    source_dirs: set[str] = set()
    source_files: set[str] = set()
    for cfg_name in config_files:
        cfg_path = join(fx_root, cfg_name)
        if not exists(cfg_path):
            exit(f"Config file not found: {cfg_path}")
        paths = L10nConfigPaths(cfg_path)
        source_files.update(fx_path for fx_path, _ in paths.all())
        if branch == cfg_automation["head"]:
            add_config(fx_root, cfg_name, fixed_config_paths, source_dirs)

    messages: dict[str, list[str]] = {}
    new_files = 0
    updated_files = 0
    for fx_path in source_files:
        rel_path = relpath(fx_path, fx_root).replace("/locales/en-US", "")
        makedirs(dirname(rel_path), exist_ok=True)

        try:
            fx_res = parse_resource(fx_path)
        except UnsupportedResource:
            messages[rel_path] = []
            if not exists(rel_path):
                print(f"create {rel_path}")
                copy(fx_path, rel_path)
                new_files += 1
            elif branch == cfg_automation["head"] and not cmp(fx_path, rel_path):
                print(f"update {rel_path}")
                copy(fx_path, rel_path)
                updated_files += 1
            else:
                # print(f"skip {rel_path}")
                pass
            continue

        messages[rel_path] = [
            ".".join(section.id + entry.id)
            for section in fx_res.sections
            for entry in section.entries
            if isinstance(entry, Entry)
        ]

        if not exists(rel_path):
            print(f"create {rel_path}")
            with open(rel_path, "+wb") as file:
                for line in serialize_resource(fx_res):
                    file.write(line.encode("utf-8"))
            new_files += 1
        elif cmp(fx_path, rel_path):
            # print(f"equal {rel_path}")
            pass
        else:
            with open(rel_path, "+rb") as file:
                res = parse_resource(rel_path, file.read())
                if add_entries(res, fx_res, use_source_entries=is_head):
                    print(f"update {rel_path}")
                    file.seek(0)
                    for line in serialize_resource(res):
                        file.write(line.encode("utf-8"))
                    file.truncate()
                    updated_files += 1
                else:
                    # print(f"unchanged {rel_path}")
                    pass

    data_path = join("_data", f"{branch}.json")
    makedirs(dirname(data_path), exist_ok=True)
    with open(data_path, "w") as file:
        json.dump(messages, file, indent=2, sort_keys=True)

    return new_files, updated_files, sorted(list(source_dirs))


def write_commit_msg(args, new_files: int, updated_files: int):
    new_str = f"{new_files} new" if new_files else ""
    update_str = f"{updated_files} updated" if updated_files else ""
    summary = (
        f"{new_str} and {update_str}"
        if new_str and update_str
        else new_str or update_str or "no changes"
    )
    count = updated_files or new_files
    summary += " files" if count > 1 else " file" if count == 1 else ""
    head = f"{args.branch} ({args.commit})" if args.commit else args.branch
    with open(".update_msg", "w") as file:
        file.write(f"{head}: {summary}")


if __name__ == "__main__":
    config_file = join(".github", "update-config.json")
    with open(config_file) as f:
        cfg_automation = json.load(f)

    prog = "python .github/scripts/update.py"
    parser = ArgumentParser(
        prog=prog,
        description=__doc__.format(HEAD=cfg_automation["head"]),
        epilog=f"""Example: {prog} --branch release --firefox ../firefox
        --configs browser/locales/l10n.toml mobile/android/locales/l10n.toml""",
    )
    parser.add_argument(
        "--branch",
        required=True,
        help='The branch identifier, e.g. "master", "beta", or "release".',
    )
    parser.add_argument("--commit", help="A commit id for the branch.")
    parser.add_argument(
        "--firefox", required=True, help="Path to the root of the Firefox source tree."
    )
    parser.add_argument(
        "--configs",
        metavar="C",
        nargs="+",
        required=True,
        help="Relative paths from the Firefox root to the l10n.toml files.",
    )
    args = parser.parse_args()

    new_files, updated_files, source_dirs = update(
        cfg_automation, args.branch, args.firefox, args.configs
    )

    if cfg_automation["paths"] != source_dirs and args.branch == cfg_automation["head"]:
        # Write back updated configuration
        cfg_automation["paths"] = source_dirs
        with open(config_file, "w") as file:
            json.dump(cfg_automation, file, indent=2, sort_keys=True)

    write_commit_msg(args, new_files, updated_files)

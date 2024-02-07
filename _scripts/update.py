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
import tomli_w
import tomllib
from argparse import ArgumentParser
from filecmp import cmp
from os import makedirs
from os.path import abspath, dirname, exists, join, relpath
from pathlib import Path
from re import sub
from shutil import copy
from sys import exit
from compare_locales.merge import merge_channels
from compare_locales.parser import Entity, getParser
from compare_locales.paths import ProjectFiles, TOMLParser
from typing import TypedDict


class AutomationConfig(TypedDict):
    branches: list[str]
    head: str
    paths: list[str]


def add_config(fx_root: str, fx_cfg_path: str, done: set[str], paths: set[str]):
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
            # Most reference paths end with `/en-US/**``, but in case of
            # components `en-US` might be in the middle of the path
            # (e.g. `browser/locales/en-US/pdfviewer/**`).
            ref_parts = [
                part
                for part in path["reference"].split("/")
                if part not in ("**", "en-US")
            ]
            paths.add("/".join(ref_parts))

            # Remove placeholders like `{l}` from l10n paths
            path["reference"] = sub(r"{\s*\S+\s*}", "", path["l10n"])
        if "includes" in cfg:
            for incl in cfg["includes"]:
                incl["path"] = add_config(fx_root, incl["path"], done, paths)

        makedirs(dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "wb") as file:
            tomli_w.dump(cfg, file)
    return cfg_path


def update_str(
    cfg_automation: AutomationConfig,
    branch: str,
    fx_root: str,
    config_files: list[str],
    paths: list[str],
):
    if branch not in cfg_automation["branches"]:
        exit(f"Unknown branch: {branch}")
    if not exists(fx_root):
        exit(f"Firefox root not found: {fx_root}")
    print(f"source: {branch} at {fx_root}")

    configs = []
    fixed_configs = set()
    all_paths: set[str] = set()
    for cfg_name in config_files:
        cfg_path = join(fx_root, cfg_name)
        if not exists(cfg_path):
            exit(f"Config file not found: {cfg_path}")
        configs.append(TOMLParser().parse(cfg_path))
        if branch == cfg_automation["head"]:
            add_config(fx_root, cfg_name, fixed_configs, all_paths)

    # Remove paths that are included in other paths, taking advantage of
    # the alphabetical order.
    for new_path in sorted(list(all_paths)):
        if not paths:
            paths.append(new_path)
        else:
            add_path = True
            for stored_path in paths[:]:
                if Path(stored_path) in Path(new_path).parents:
                    add_path = False
            if add_path:
                paths.append(new_path)

    messages = {}
    new_files = 0
    updated_files = 0
    for fx_path, *_ in ProjectFiles(None, configs):
        rel_path = relpath(fx_path, abspath(fx_root)).replace("/locales/en-US", "")
        makedirs(dirname(rel_path), exist_ok=True)

        try:
            fx_parser = getParser(fx_path)
        except UserWarning:  # No parser found
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

        fx_parser.readFile(fx_path)
        fx_res = [entity for entity in fx_parser.walk()]
        messages[rel_path] = [
            entity.key for entity in fx_res if isinstance(entity, Entity)
        ]

        if not exists(rel_path):
            print(f"create {rel_path}")
            copy(fx_path, rel_path)
            new_files += 1
        elif cmp(fx_path, rel_path):
            # print(f"equal {rel_path}")
            pass
        else:
            with open(rel_path, "+rb") as file:
                l10n_data = file.read()
                merge_data = merge_channels(
                    rel_path,
                    (
                        [fx_res, l10n_data]
                        if branch == cfg_automation["head"]
                        else [l10n_data, fx_res]
                    ),
                )
                if merge_data == l10n_data:
                    # print(f"unchanged {rel_path}")
                    pass
                else:
                    print(f"update {rel_path}")
                    file.seek(0)
                    file.write(merge_data)
                    file.truncate()
                    updated_files += 1

    data_path = join("_data", f"{branch}.json")
    makedirs(dirname(data_path), exist_ok=True)
    with open(data_path, "w") as file:
        json.dump(messages, file, indent=2)

    return new_files, updated_files


def write_commit_msg(args, new_path_msg: str, new_files: int, updated_files: int):
    new_str = f"{new_files} new" if new_files else ""
    update_str = f"{updated_files} updated" if updated_files else ""
    summary = (
        f"{new_str} and {update_str}"
        if new_str and update_str
        else new_str or update_str or "no changes"
    )
    count = updated_files or new_files
    summary += " files" if count > 1 else " file" if count == 1 else ""
    if new_path_msg:
        summary += new_path_msg
    head = f"{args.branch} ({args.commit})" if args.commit else args.branch
    with open(".update_msg", "w") as file:
        file.write(f"{head}: {summary}")


if __name__ == "__main__":
    config_file = join("_configs", "config.json")
    with open(config_file) as f:
        cfg_automation = json.load(f)

    prog = "python -m _scripts.update"
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

    paths: list[str] = list()
    update = update_str(cfg_automation, args.branch, args.firefox, args.configs, paths)

    new_path_msg: str = ""
    if cfg_automation["paths"] != paths and args.branch == cfg_automation["head"]:
        removed = list(set(cfg_automation["paths"]) - set(paths))
        added = list(set(paths) - set(cfg_automation["paths"]))
        new_path_msg = "\nUpdated paths for sparse checkout: \n"
        new_path_msg += (
            f"- {len(removed)} removed ({', '.join(removed)})" if removed else ""
        )
        new_path_msg += f"- {len(added)} added ({','.join(added)})" if added else ""

        # Write back updated configuration
        cfg_automation["paths"] = paths
        with open(config_file, "w") as f:
            f.write(json.dumps(cfg_automation, indent=2, sort_keys=True))

    write_commit_msg(args, new_path_msg, *update)

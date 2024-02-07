# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Update the configuration file in `_configs/config.json`, adding all paths
available in the specified config files.
"""

import json
import tomllib
from argparse import ArgumentParser
from os.path import exists, join
from sys import exit
from typing import TypedDict


class AutomationConfig(TypedDict):
    branches: list[str]
    head: str
    paths: list[str]


def add_config(cfg_path: str, paths: list[str], done: set[str]):
    if cfg_path not in done:
        done.add(cfg_path)
        with open(cfg_path, "rb") as file:
            cfg = tomllib.load(file)

        for path in cfg["paths"]:
            if not path["reference"].endswith("**"):
                continue
            paths.add(path["reference"].replace("**", "locales"))

        if "includes" in cfg:
            for incl in cfg["includes"]:
                add_config(incl["path"], paths, done)


def read_paths(paths: list[str], config_files: list[str]):
    read_configs = set()
    for cfg_path in config_files:
        if not exists(cfg_path):
            exit(f"Config file not found: {cfg_path}")
        add_config(cfg_path, paths, read_configs)


if __name__ == "__main__":
    config_file = join("_configs", "config.json")
    with open(config_file) as f:
        cfg_automation = json.load(f)

    prog = "python -m _scripts.read_paths"
    parser = ArgumentParser(
        prog=prog,
        description=__doc__,
        epilog=f"""Example: {prog}
        --configs browser/locales/l10n.toml mobile/android/locales/l10n.toml""",
    )
    parser.add_argument(
        "--configs",
        metavar="C",
        nargs="+",
        required=True,
        help="Relative paths from the Firefox root to the l10n.toml files.",
    )
    args = parser.parse_args()

    paths: set[str] = set()
    read_paths(paths, args.configs)

    cfg_automation["paths"] = sorted(list(paths))
    with open(config_file, "w") as f:
        f.write(json.dumps(cfg_automation, indent=2, sort_keys=True))

import json
import tomli_w
import tomllib
from filecmp import cmp
from os import makedirs
from os.path import abspath, dirname, exists, join, relpath
from re import match, sub
from shutil import copy
from sys import argv, exit
from compare_locales.merge import merge_channels
from compare_locales.parser import Entity, getParser
from compare_locales.paths import ProjectFiles, TOMLParser

HEAD = "master"


def add_config(fx_root: str, fx_cfg_path: str, done: set[str]):
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
            path["reference"] = sub(r"{\s*\S+\s*}", "", path["l10n"])
        if "includes" in cfg:
            for incl in cfg["includes"]:
                incl["path"] = add_config(fx_root, incl["path"], done)

        makedirs(dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "wb") as file:
            tomli_w.dump(cfg, file)
    return cfg_path


def update(branch: str, fx_root: str, config_files: list[str]):
    if branch not in [HEAD, "beta", "release"] and not match("esr[0-9]+", branch):
        exit(f"Unknown branch: {branch}")
    if not exists(fx_root):
        exit(f"Firefox root not found: {fx_root}")
    print(f"updating from {branch}...")

    configs = []
    fixed_configs = set()
    for cfg_name in config_files:
        cfg_path = join(fx_root, cfg_name)
        if not exists(cfg_path):
            exit(f"Config file not found: {cfg_path}")
        configs.append(TOMLParser().parse(cfg_path))
        if branch == HEAD:
            add_config(fx_root, cfg_name, fixed_configs)

    messages = {}
    changes = {"new": 0, "update": 0}
    for fx_path, *_ in ProjectFiles(None, configs):
        rel_path = relpath(fx_path, fx_root).replace("/locales/en-US", "")
        makedirs(dirname(rel_path), exist_ok=True)

        try:
            fx_parser = getParser(fx_path)
        except UserWarning:  # No parser found
            messages[rel_path] = []
            if not exists(rel_path):
                print(f"  create {rel_path}")
                copy(fx_path, rel_path)
                changes["new"] += 1
            elif branch == HEAD and not cmp(fx_path, rel_path):
                print(f"  update {rel_path}")
                copy(fx_path, rel_path)
                changes["update"] += 1
            else:
                # print(f"  skip {rel_path}")
                pass
            continue

        fx_parser.readFile(fx_path)
        fx_res = [entity for entity in fx_parser.walk()]
        messages[rel_path] = [
            entity.key for entity in fx_res if isinstance(entity, Entity)
        ]

        if not exists(rel_path):
            print(f"  create {rel_path}")
            copy(fx_path, rel_path)
            changes["new"] += 1
        elif cmp(fx_path, rel_path):
            # print(f"  equal {rel_path}")
            pass
        else:
            with open(rel_path, "+rb") as file:
                l10n_data = file.read()
                merge_data = merge_channels(
                    rel_path,
                    [fx_res, l10n_data] if branch == HEAD else [l10n_data, fx_res],
                )
                if merge_data == l10n_data:
                    # print(f"  unchanged {rel_path}")
                    pass
                else:
                    print(f"  update {rel_path}")
                    file.seek(0)
                    file.write(merge_data)
                    file.truncate()
                    changes["update"] += 1

    data_path = join("_data", f"{branch}.json")
    makedirs(dirname(data_path), exist_ok=True)
    with open(data_path, "w") as file:
        json.dump(messages, file, indent=2)

    return changes


if __name__ == "__main__":
    branch = argv[-1]
    changes = update(
        branch,
        fx_root=abspath("../firefox"),
        config_files=[
            "browser/locales/l10n.toml",
            "mobile/android/locales/l10n.toml",
        ],
    )
    new = f"{changes['new']} new" if changes["new"] else ""
    update = f"{changes['update']} updated" if changes["update"] else ""
    summary = f"{new} and {update}" if new and update else new or update or "no changes"
    count = changes["update"] or changes["new"]
    summary += " files" if count > 1 else " file" if count == 1 else ""
    with open(".update_msg", "w") as file:
        file.write(f"Update from {branch}: {summary}")

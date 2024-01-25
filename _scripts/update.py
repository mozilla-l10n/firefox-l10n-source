from filecmp import cmp
from json import dump
from os import makedirs
from os.path import abspath, dirname, exists, join, relpath
from re import match
from shutil import copy
from sys import argv, exit
from compare_locales.merge import merge_channels
from compare_locales.parser import getParser
from compare_locales.paths import ProjectFiles, TOMLParser

HEAD = "master"


def update(branch: str, fx_root: str, l10n_root: str, config_files: list[str]):
    if branch not in [HEAD, "beta", "release"] and not match("esr[0-9]+", branch):
        exit(f"Unknown branch: {branch}")
    if not exists(fx_root):
        exit(f"Firefox root not found: {fx_root}")
    if not exists(l10n_root):
        exit(f"L10n root not found: {l10n_root}")
    configs = []
    for cfg_name in config_files:
        cfg_path = join(fx_root, cfg_name)
        if not exists(cfg_path):
            exit(f"Config file not found: {cfg_path}")
        configs.append(TOMLParser().parse(cfg_path))

    print(f"updating from {branch}...")
    messages = {}
    for fx_path, *_ in ProjectFiles(None, configs):
        rel_path = relpath(fx_path, fx_root).replace("/locales/en-US", "")
        try:
            fx_parser = getParser(fx_path)
        except UserWarning:
            # print(f"  skip {rel_path}")
            continue
        fx_parser.readFile(fx_path)
        messages[rel_path] = [
            entity.key for entity in fx_parser.walk(only_localizable=True)
        ]

        l10n_path = join(l10n_root, rel_path)
        makedirs(dirname(l10n_path), exist_ok=True)
        if not exists(l10n_path):
            print(f"  create {rel_path}")
            copy(fx_path, l10n_path)
        elif cmp(fx_path, l10n_path):
            # print(f"  equal {rel_path}")
            continue
        else:
            with open(l10n_path, "+rb") as file:
                l10n_data = file.read()
                fx_gen = fx_parser.walk()
                merge_data = merge_channels(
                    rel_path,
                    [fx_gen, l10n_data] if branch == HEAD else [l10n_data, fx_gen],
                )
                if merge_data == l10n_data:
                    # print(f"  unchanged {rel_path}")
                    continue
                else:
                    print(f"  update {rel_path}")
                    file.seek(0)
                    file.write(merge_data)
                    file.truncate()

    data_path = join(l10n_root, "_data", f"{branch}.json")
    makedirs(dirname(data_path), exist_ok=True)
    with open(data_path, "w") as file:
        dump(messages, file, indent=2)
    print(f"done: {len(messages)} files, {sum(len(x) for x in messages)} messages")


if __name__ == "__main__":
    update(
        branch=argv[-1],
        fx_root=abspath("../firefox"),
        l10n_root=abspath("."),
        config_files=[
            "browser/locales/l10n.toml",
            "mobile/android/locales/l10n.toml",
        ],
    )

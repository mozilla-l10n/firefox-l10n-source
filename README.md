# Firefox Localization: Source

This repository contains the source locale messages for Firefox.
They are extracted from the active branches (Nightly, Beta, Release, ESRs)
by a scheduled [GitHub action](./.github/workflows/update.yml),
which produces pull requests that are reviewed by the L10n team before merging.

From here, messages are exposed to translators in [Pontoon](https://pontoon.mozilla.org/).

Note that unless otherwise specified,
files in this repository have been processed from their Source Code Form,
and therefore following our [license](./LICENSE) (MPL-2.0)
do not necessarily carry a Source Code Form License Notice.
The Source Code Form for each such file is available from
[mozilla/mozilla-firefox/firefox](https://github.com/mozilla-firefox/firefox).

## Adding a New Version

Before adding a new version, make sure to merge pending update pull requests
(it will avoid the need to rebase existing PRs). Then:

1. Create a local branch.
2. Add the new version to the update configuration in `.github/update-config.json`.
Note that ESR versions should be ordered by the most recent to the least recent
(e.g. `esr140` before `esr128`). The name of the version needs to match the
branch name on [mozilla/mozilla-firefox/firefox](https://github.com/mozilla-firefox/firefox).
5. Open a pull request.
6. Once the pull request is merged, run the update automation. This will generate
the corresponding data storage file in `_data`.

## Removing a Supported Version

Before removing a supported version from the repository, make sure to merge
pending update pull requests and pause sync in Pontoon. Then:

1. Create a local branch.
2. Remove the corresponding data storage file in `_data` (e.g. `_data/esr128.json`).
3. Remove the version from the update configuration in `.github/update-config.json`.
4. In a virtual environment with the [requirements](.github/scripts/requirements.txt)
installed, run the Python script `.github/scripts/prune.py`. This will remove
the content and provide a report.
5. Open a pull request.
6. Once the pull request is merged, run the update automation.

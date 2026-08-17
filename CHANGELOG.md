# Changelog

This project is a modified version of [mekhq-blog](https://github.com/AaronGullickson/mekhq-blog)
by Aaron Gullickson, licensed under the GNU General Public License v3.0. The
GPL asks that modifications be stated plainly, so this file records what was
changed here and when. Everything before v0.3 is the original project.

## v0.4.0-beta -- 2026-08-13 (`bundled-release` branch)

A pre-baked Windows release that needs nothing installed.

- `bundle/launcher.py`, frozen into `MekHQ-Website.exe`, finds MekHQ, runs
  the campaign parser, builds the site, and serves it with a browser open on
  it. Answers are remembered in `campaign.ini`.
- `bundle/build_release.py` assembles a folder carrying its own Ruby, gems
  and Python, and zips it. Around 72 MB.
- Paths inside the release are kept short enough to survive Windows' 260
  character limit wherever the zip is unpacked, and the launcher checks its
  own path at startup rather than letting the build fail obscurely.
- Generated campaign pages and portraits are no longer kept in the
  repository, and the release ships the template's sample content instead of
  a real campaign.

## v0.3 -- 2026-08-12

Brought back to life on current tooling. The project dated from 2021 and
neither half still ran.

### Ruby and Jekyll

- Jekyll 3.8.6 cannot run on Ruby 3.x; moved to Jekyll 4.3+.
- Added `webrick`, dropped from the Ruby standard library in 3.0, and
  updated `wdm` and `tzinfo`.
- Silenced the bundled Bootstrap 4 SCSS deprecation warnings under Dart
  Sass, so real build errors stay visible.
- `_config.yml` now excludes the toolchain files from the built site.

### Campaign parser

- Reads both save layouts: personnel under `humanResources`, forces as
  `formations`/`subFormations`, alongside the older 0.4x element names.
- Follows MekHQ's Mech to Mek renames across roles and skill types, and
  handles `isCountUp`, the Heroic and Legendary skill tiers, and the
  expanded role, status and scenario enums. Unknown values degrade to a
  readable label instead of raising.
- Resolves ranks the way MekHQ does, following `--MW`/`--TECH` column
  redirects across the now nine-column rank tables. Without this, every
  tech, driver, doctor and administrator came out with no rank at all.
- Quotes front matter values, so a mission called `Operation: Rope Burn` no
  longer produces invalid YAML.
- Resolves paths against the script's own directory, and accepts the save
  name and MekHQ path as command line arguments.
- Role filter pages updated to the new role names, which would otherwise
  render empty.
- Added `requirements.txt`.

### Known gaps

- Mission and scenario output has never been built from a real MekHQ save
  with contracts in it. MekHQ's bundled sample campaign has none.
- There are no automated tests.

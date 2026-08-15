# Pre-baked release

An experiment: ship a zip that needs nothing installed. The person who
downloads it double-clicks an exe and ends up looking at their campaign in a
browser, with no Ruby, no Jekyll, no Python, and no command line.

This directory holds the two pieces that make that zip. It is build
scaffolding — none of it ends up in the release itself.

| File | What it is |
| --- | --- |
| `launcher.py` | the program the user actually runs, frozen into `MekHQ-Website.exe` |
| `build_release.py` | assembles the release folder and zips it |

## Building it

Run from a machine with the normal development setup working, since the
release is assembled out of that setup:

```bash
python bundle/build_release.py
```

It needs Ruby with its MSYS2 toolchain (the winget `RubyWithDevKit` package)
and `pip install pyinstaller`. Output lands in `bundle/dist/`, which is
gitignored. `--skip-zip` stops before the slow part while testing.

## What ends up in the zip

```
MekHQ-Website/
├── MekHQ-Website.exe     the launcher, with Python inside it
├── README-FIRST.txt      instructions for someone who has never seen this
├── campaign.ini          written on first run, remembers their answers
├── runtime/ruby/         a copy of Ruby, minus the compiler toolchain
├── gems/                 Jekyll and its gems
└── site/                 this repository
```

The folder is named as briefly as it can be, and the gems sit beside the site
rather than under it. Both are about the path limit below, not tidiness.

## How it works

**Ruby travels.** RubyInstaller's `ruby.exe` finds its standard library
relative to its own location rather than a fixed path, so copying the install
folder somewhere else and running it works. What gets left behind is
`msys64/`, the compiler toolchain, which is the bulk of the install and is
only needed to build native gems.

**Gems are built here, not there.** Because the toolchain is left out, the
release cannot compile anything. `build_release.py` therefore installs the
gems with the development Ruby, into `gems/`, and the copied Ruby just loads
the results. They are built against the same version and ABI, so this is only
a question of where the files sit. The launcher sets `BUNDLE_PATH` to that
folder at run time, so no path is recorded anywhere and the release can be
unzipped wherever.

**Windows gives up at 260 characters.** This is the sharpest constraint on
the whole idea, because a release is a deep tree living wherever someone drops
it. Three things buy room: the folder is called `MekHQ-Website` rather than
the 48-character release name, the gems moved out of `site/vendor/bundle`,
and the gem trees are pruned of test suites, docs and vendored Java sources
that no run time loads. Longest path inside the release went from 161
characters to 140, and the unzip location gets 106 characters to play with
instead of about 50. The launcher measures its own path at startup and says
so plainly rather than letting Jekyll fail with `Invalid argument`.

Pruning is scoped to the gem trees, and `verify()` checks the site still has
its pages afterwards. Both exist because the first version of the prune ran
over the whole release and deleted every markdown file in it, producing a
release that started up, read the campaign, reported success, and served a
website with no TO&E, no fiction and no mission history.

**The exe is a front end, not a rewrite.** `launcher.py` is frozen with
PyInstaller and does four things: work out where MekHQ is, run
`process_campaign.py`, run `jekyll build`, then `jekyll serve` and open a
browser. It runs the campaign script with `runpy` from disk rather than
importing a copy baked into the exe, so `site/process_campaign.py` stays
readable and editable in the release — someone can still change which
personnel get loaded, exactly as the README describes.

Because that script is read at run time, PyInstaller cannot see what it
imports, so `launcher.py` imports the same modules itself — that block near
the top is what puts `html` and `dateutil` in the exe. Anything else the
campaign script starts importing has to be added there too, or the release
breaks while the development setup carries on working. This is the sharpest
edge in the whole arrangement, because nothing fails until someone runs the
release.

**Nothing is asked twice.** The first run scans the usual places for a folder
holding `MekHQ.jar` and a `campaigns/` directory, offers a numbered list of
saves, and writes both answers to `campaign.ini`.

## What this costs

| | Size |
| --- | --- |
| `runtime/ruby/` | 76 MB |
| `gems/` | 47 MB |
| `site/` | 8 MB |
| `MekHQ-Website.exe` | 9 MB |
| **Unzipped total** | **131 MB** |
| **The zip people download** | **72 MB** |

Most of that is a Ruby install carried along to run one program. Dropping
`msys64/` takes the Ruby copy from 1.2 GB to 76 MB, and it is the single
thing that makes this size plausible at all.

## What was tested

The published zip is extracted somewhere unrelated and run with `PATH` cut
down to `C:\Windows\system32;C:\Windows`, and `GEM_HOME`, `GEM_PATH`,
`RUBYOPT`, `RUBYLIB`, `BUNDLE_PATH` and `BUNDLE_GEMFILE` cleared — as close
to a machine with no Ruby and no Python as can be arranged without a second
machine. From a cold start, with no `campaign.ini`, it finds MekHQ by itself
in 0.3 seconds, reads the save, writes 94 personnel and 15 forces, compiles
the stylesheet and builds 94 pages.

Test the zip, not the folder it was built from. Both bugs worth having found
here — the path limit and the over-eager prune — were invisible in the build
folder and obvious the moment the artifact was unpacked and used. Check that
pages have content in them too, not just that they return 200: a site with
every page empty answers just as cheerfully as a working one.

That is not the same as testing on a clean Windows install, which is the
honest next step: this machine still has the Visual C++ runtimes and other
odds and ends that a fresh one might not.

## Still open

- **Only tested on Windows.** The same approach would work for macOS and
  Linux, but each needs its own Ruby copy and its own build run — there is no
  cross-building here.
- **Unsigned.** Windows SmartScreen warns about an unrecognised publisher,
  and some antivirus products treat PyInstaller output as suspicious on
  principle. Signing is not free: since 2023 the keys must live on certified
  hardware, which puts a certificate somewhere around 120 US dollars a year
  at the cheapest (Azure Trusted Signing) and several hundred for the
  ordinary kind. Worse, only the expensive tier clears SmartScreen straight
  away — the cheaper certificates build reputation over time, so a small
  project sits behind the warning regardless. MekHQ itself ships unsigned, so
  the audience already knows the dance. Publishing the zip's SHA-256 with
  each release costs nothing and is the honest version of the same promise.
  SignPath Foundation signs open-source projects free, which is worth
  applying for if this ever goes public.
- **Updating means re-downloading.** There is no update mechanism, so a fix
  to the campaign parser means shipping the whole zip again.
- **The gem set is frozen at build time.** Whatever `bundle install` resolved
  on build day is what ships, which is good for reproducibility and bad for
  security fixes.

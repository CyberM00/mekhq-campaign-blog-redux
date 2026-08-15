#!/usr/bin/env python3
"""Assemble the pre-baked Windows release.

Produces a folder (and matching zip) that carries its own Ruby, its own gems,
and a launcher exe with Python inside it, so the person opening it needs
nothing installed. Run this from a machine that already has a working
development setup:

    python bundle/build_release.py

Optional arguments:
    --ruby PATH     the Ruby install to copy from (default C:/Ruby33-x64)
    --version TEXT  version stamped into the folder and zip name
    --skip-zip      leave the folder unzipped, for quicker test runs
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'dist')

# Copied into the release as the site itself. Everything else in the repo is
# either development scaffolding or output that gets regenerated.
SITE_SKIP = {'.git', '.github', '.bundle', '.jekyll-cache', '.jekyll-metadata',
             '.sass-cache', '_site', 'bundle', 'vendor', 'Gemfile.lock',
             '__pycache__'}

# Dropped from the copied Ruby. msys64 is the compiler toolchain, only needed
# to build native gems, which this machine has already done. The rest is
# documentation and development headers.
RUBY_SKIP_TOP = {'msys64', 'include', 'packages', 'share'}
RUBY_SKIP_NAMES = {'unins000.exe', 'unins000.dat', 'pkgconfig'}
RUBY_SKIP_SUFFIX = ('.dll.a', '.pdb')

# Pruned from the gem trees afterwards. None of it is loaded at run time, and
# it holds the longest paths in the release: a gem's bundled Java test suite
# runs 60 characters deeper than anything that actually does something.
# Windows refuses to handle paths past 260 characters, and Explorer's own
# unzip is one of the things that gives up, so this is about the release
# unpacking at all rather than about saving space.
PRUNE_DIRS = {'test', 'tests', 'spec', 'specs', 'doc', 'docs', 'examples',
              'benchmark', 'benchmarks', 'fixtures'}
PRUNE_SUFFIX = ('.java', '.md', '.rdoc')


def run(command, cwd=None, env=None):
    print('  $ ' + ' '.join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, env=env)
    if result.returncode != 0:
        sys.exit('Failed: ' + ' '.join(command))


def copy_site(target):
    print('Copying the site...', flush=True)
    os.makedirs(target, exist_ok=True)
    for entry in os.listdir(REPO):
        if entry in SITE_SKIP:
            continue
        source = os.path.join(REPO, entry)
        destination = os.path.join(target, entry)
        if os.path.isdir(source):
            shutil.copytree(source, destination,
                            ignore=shutil.ignore_patterns(*SITE_SKIP))
        else:
            shutil.copy2(source, destination)


def install_gems(site, gems, ruby_bin):
    """Install the gems into their own folder beside the site.

    They used to live in site/vendor/bundle, which cost 14 characters of path
    on every gem file for no benefit. The launcher points BUNDLE_PATH here at
    run time, so no relative path is recorded anywhere and the release can
    still be unzipped wherever.

    This uses the development Ruby rather than the copied one, because a few
    gems (bigdecimal among them) build native extensions and so need the
    MSYS2 toolchain that gets left out of the release. The extensions are
    built against the same Ruby version and ABI that ships here, so the
    copied Ruby loads them happily.
    """
    print('Installing gems into the release...', flush=True)
    env = dict(os.environ)
    env['PATH'] = ruby_bin + os.pathsep + env.get('PATH', '')
    for leaky in ('GEM_HOME', 'GEM_PATH', 'RUBYOPT'):
        env.pop(leaky, None)
    env['BUNDLE_PATH'] = gems
    ruby = os.path.join(ruby_bin, 'ruby.exe')
    run([ruby, '-S', 'bundle', 'install'], cwd=site, env=env)


def prune(*roots):
    """Delete what no run time loads, to keep paths short.

    Only ever point this at the gem trees. The site is made of exactly the
    kinds of files this deletes — the pages are markdown, and _posts is
    someone's fiction — so pruning it removes the website.
    """
    print('Pruning paths...', flush=True)
    removed = 0
    for target in roots:
        removed += prune_tree(target)
    print('  removed {} files and folders'.format(removed), flush=True)


def prune_tree(target):
    removed = 0
    for root, dirs, files in os.walk(target, topdown=True):
        for name in list(dirs):
            if name.lower() in PRUNE_DIRS:
                shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                dirs.remove(name)
                removed += 1
        for name in files:
            if name.endswith(PRUNE_SUFFIX):
                try:
                    os.remove(os.path.join(root, name))
                    removed += 1
                except OSError:
                    pass
    return removed


def write_notices(target, ruby_bin, gems):
    """List what the release redistributes, and under which licence.

    Read out of the installed gemspecs rather than kept by hand, so it
    describes the gems that actually shipped.
    """
    print('Listing third-party licences...', flush=True)
    script = (
        "Dir.glob(ARGV[0] + '/**/specifications/*.gemspec')"
        ".map { |f| Gem::Specification.load(f) }.compact"
        ".sort_by { |s| s.name.downcase }.uniq { |s| [s.name, s.version] }"
        ".each { |s| puts [s.name, s.version, "
        "(s.licenses.empty? ? 'see gem' : s.licenses.join(', ')), "
        "s.homepage].join(\"\\t\") }"
    )
    # Dir.glob wants forward slashes, so hand Ruby a path it can use rather
    # than making it undo Windows separators
    result = subprocess.run([os.path.join(ruby_bin, 'ruby.exe'), '-e', script,
                             gems.replace('\\', '/')],
                            capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit('Could not read the gem licences:\n' + result.stderr)
    rows = [line.split('\t') for line in result.stdout.splitlines()
            if line.count('\t') == 3]
    if not rows:
        sys.exit('No gems found under {} — the notices file would ship '
                 'empty.'.format(gems))

    lines = [
        'THIRD-PARTY NOTICES',
        '===================',
        '',
        'This release redistributes the software below. Each remains under',
        'its own licence, held by its own authors. The full licence text for',
        'each component ships inside its own folder in this release.',
        '',
        'The website generator itself is licensed under the GNU General',
        'Public License v3.0 and is a modified version of mekhq-blog by',
        'Aaron Gullickson (https://github.com/AaronGullickson/mekhq-blog).',
        'See LICENSE and CHANGELOG.md in the site folder.',
        '',
        'RUNTIMES',
        '',
        '  Ruby            Ruby licence / BSD-2-Clause   https://www.ruby-lang.org/',
        '  Python          PSF licence                   https://www.python.org/',
        '                  (inside MekHQ-Website.exe, via PyInstaller, GPL',
        '                   with a linking exception for frozen programs)',
        '  Dart Sass       MIT                           https://sass-lang.com/',
        '                  (ships inside the sass-embedded gem)',
        '',
        'FRONT END',
        '',
        '  Bootstrap 4     MIT                           https://getbootstrap.com/',
        '',
        'RUBY GEMS ({} of them)'.format(len(rows)),
        '',
    ]
    for name, version, licence, homepage in rows:
        lines.append('  {:<28} {:<10} {:<22} {}'.format(
            name, version, licence, homepage))
    lines += [
        '',
        'BATTLETECH',
        '',
        '  MechWarrior, BattleMech, `Mech and AeroTech are registered',
        '  trademarks of The Topps Company, Inc. Catalyst Game Labs and the',
        '  Catalyst Game Labs logo are trademarks of InMediaRes Productions,',
        '  LLC. MechWarrior Copyright Microsoft Corporation.',
        '',
        '  This is an unofficial fan project, not endorsed by or affiliated',
        '  with Microsoft, Topps, or Catalyst Game Labs, provided free of',
        '  charge under Microsoft\'s Game Content Usage Rules',
        '  <https://www.xbox.com/en-US/developers/rules>.',
        '',
        '  Portraits and campaign data are read from your own MekHQ install',
        '  when you run this program. MegaMek data is licensed CC BY-NC-SA',
        '  4.0 <https://creativecommons.org/licenses/by-nc-sa/4.0/> and is',
        '  not redistributed here.',
        '',
    ]
    with open(os.path.join(target, 'THIRD-PARTY-NOTICES.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write('\n'.join(lines))
    print('  {} gems listed'.format(len(rows)), flush=True)


def verify(target):
    """Check the release still has the pieces a working site needs.

    Written after a pruning pass quietly deleted every markdown page in the
    site, which left a release that started up, read the campaign, built
    without complaint, and served a website with no TO&E, no fiction and no
    mission history in it.
    """
    print('Checking the release...', flush=True)
    required = [
        'MekHQ-Website.exe',
        'site/index.html', 'site/toe.md', 'site/fiction.md',
        'site/missions.md', 'site/_config.yml', 'site/process_campaign.py',
        'site/css/site.scss', 'site/_layouts/bio.html',
        'site/LICENSE', 'site/CHANGELOG.md', 'THIRD-PARTY-NOTICES.txt',
        'site/_includes/header.html', 'site/campaign/_posts',
        'site/personnel-roles/mechwarriors.md',
        'runtime/ruby/bin/ruby.exe',
    ]
    missing = [item for item in required
               if not os.path.exists(os.path.join(target, item))]
    gem_dirs = os.path.join(target, 'gems', 'ruby')
    if not os.path.isdir(gem_dirs):
        missing.append('gems/ruby')
    if missing:
        sys.exit('The release is missing:\n  ' + '\n  '.join(missing))
    print('  all present', flush=True)


def longest_path(target):
    worst = ('', 0)
    for root, _, files in os.walk(target):
        for name in files:
            full = os.path.relpath(os.path.join(root, name), target)
            if len(full) > worst[1]:
                worst = (full, len(full))
    return worst


def copy_ruby(source, target):
    print('Copying Ruby (this takes a minute)...', flush=True)

    def ignore(directory, names):
        skipped = set()
        for name in names:
            full = os.path.join(directory, name)
            relative = os.path.relpath(full, source).replace('\\', '/')
            if relative in RUBY_SKIP_TOP or name in RUBY_SKIP_NAMES:
                skipped.add(name)
            elif name.endswith(RUBY_SKIP_SUFFIX):
                skipped.add(name)
            elif relative.endswith(('gems/3.3.0/cache', 'gems/3.3.0/doc')):
                skipped.add(name)
        return skipped

    shutil.copytree(source, target, ignore=ignore)


def build_exe(target):
    print('Building the launcher exe...', flush=True)
    work = os.path.join(OUT, 'build')
    run([sys.executable, '-m', 'PyInstaller',
         '--onefile',
         '--name', 'MekHQ-Website',
         '--distpath', target,
         '--workpath', work,
         '--specpath', work,
         '--console',
         os.path.join(HERE, 'launcher.py')])


def write_readme(target, version):
    text = """MekHQ Campaign Website {version}
===========================================================

Turns a MekHQ campaign save into a website you can browse and publish.
Nothing to install: Ruby, Jekyll and Python are already inside this folder.

HOW TO USE IT

  1. Save your campaign in MekHQ.
  2. Double-click MekHQ-Website.exe.
  3. The first run asks where MekHQ is, and which campaign to read. It
     remembers your answers in campaign.ini.
  4. A browser opens at http://127.0.0.1:4000/ with your campaign in it.

Leave the black window open while you browse. Closing it stops the site.
After playing more, run it again to refresh.

PUTTING IT ON THE INTERNET

The site is plain files, so any web host will serve it. Run:

    MekHQ-Website.exe --build-only

then upload everything inside site\\_site to your host. Free options that
work well are Netlify, GitHub Pages and Cloudflare Pages.

MAKING IT YOURS

  site\\_config.yml            unit name, description, banner on or off
  site\\css\\site.scss          colours and fonts, at the bottom of the file
  site\\assets\\images          banner_image.png and unit_logo.png
  site\\campaign\\_posts        fiction, as markdown files

Everything under site\\campaign is rewritten every run, apart from _posts,
so put your own writing there and leave the rest to the program.

OTHER OPTIONS

    MekHQ-Website.exe --help          list every option
    MekHQ-Website.exe --serve-only    browse without re-reading MekHQ
    MekHQ-Website.exe --port 4001     use a different port

Delete campaign.ini to be asked about the MekHQ folder and save again.

ONE THING TO WATCH

Keep this folder somewhere with a short path, like C:\\MekHQ-Website or your
Desktop. Windows cannot start programs whose path runs past 260 characters,
and the site builder sits deep inside this folder. It will tell you plainly
if the folder is too deep, rather than failing in a confusing way.
""".format(version=version)
    with open(os.path.join(target, 'README-FIRST.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write(text)


def make_zip(folder, inside_name, name):
    archive = os.path.join(OUT, name + '.zip')
    print('Zipping (this takes a few minutes)...', flush=True)
    if os.path.exists(archive):
        os.remove(archive)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED,
                         compresslevel=6) as zipped:
        for root, _, files in os.walk(folder):
            for filename in files:
                full = os.path.join(root, filename)
                inside = os.path.join(inside_name,
                                      os.path.relpath(full, folder))
                zipped.write(full, inside)
    return archive


def folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for filename in files:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                pass
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ruby', default='C:/Ruby33-x64')
    parser.add_argument('--version', default='v0.3')
    parser.add_argument('--skip-zip', action='store_true')
    args = parser.parse_args()

    if not os.path.isfile(os.path.join(args.ruby, 'bin', 'ruby.exe')):
        sys.exit('No ruby.exe under {}. Pass --ruby with the right '
                 'path.'.format(args.ruby))

    # The folder people unzip is named as briefly as it can be: every
    # character here is one they cannot spend on where they keep it. The zip
    # itself keeps the long descriptive name, since that only has to be
    # unique in a downloads folder.
    folder = 'MekHQ-Website'
    zip_name = 'mekhq-campaign-blog-redux-{}-windows'.format(args.version)
    target = os.path.join(OUT, folder)
    if os.path.exists(target):
        print('Clearing the previous build...', flush=True)
        shutil.rmtree(target)
    os.makedirs(target)

    site = os.path.join(target, 'site')
    ruby = os.path.join(target, 'runtime', 'ruby')
    gems = os.path.join(target, 'gems')

    copy_site(site)
    copy_ruby(args.ruby, ruby)
    install_gems(site, gems, os.path.join(args.ruby, 'bin'))
    prune(gems, ruby)
    build_exe(target)
    write_readme(target, args.version)
    write_notices(target, os.path.join(ruby, 'bin'), gems)
    verify(target)

    deepest, depth = longest_path(target)
    print('\nRelease folder: {} ({:.0f} MB)'.format(
        target, folder_size(target) / 1e6))
    print('Longest path inside it: {} characters'.format(depth))
    print('  {}'.format(deepest))
    print('Leaves {} characters for wherever someone unzips it.'.format(
        260 - depth - len(folder) - 1))
    if not args.skip_zip:
        archive = make_zip(target, folder, zip_name)
        print('Zip: {} ({:.0f} MB)'.format(archive,
                                           os.path.getsize(archive) / 1e6))


if __name__ == '__main__':
    main()

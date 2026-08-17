#!/usr/bin/env python3
"""Front end for the pre-baked release of this site.

The release ships its own Ruby and its own copy of this repository, so the
person running it does not need Ruby, Jekyll, or Python installed. This
launcher is what the bundled MekHQ-Website.exe runs:

    1. work out where MekHQ is and which save to read
    2. run process_campaign.py against that save
    3. build the site with the bundled Jekyll
    4. rewrite its links so the folder works on its own
    5. open it in a browser

There is no web server in that list. Jekyll writes links from the root of a
site, which only a server can answer; rewriting them to ordinary relative
paths means the built folder opens by double-clicking index.html, today and
in five years, with nothing running. --serve is still there for anyone
editing the site who wants it rebuilt as they go.

--share packs the whole site into one file to send someone, and --publish
packages it for a web host. Run with --help for the rest.
"""

import argparse
import configparser
import glob
import os
import runpy
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile

# process_campaign.py is read from disk at run time, so the exe builder cannot
# see what it imports and would leave those modules out. Importing them here
# is what puts them in the exe. Keep this list in step with that script.
import datetime  # noqa: F401
import gzip  # noqa: F401
import html  # noqa: F401
import re  # noqa: F401
import shutil  # noqa: F401
import xml.etree.ElementTree  # noqa: F401
from dateutil import relativedelta  # noqa: F401
import share  # noqa: F401
from PIL import Image  # noqa: F401

CONFIG_NAME = 'campaign.ini'

# Places a MekHQ install is likely to be sitting, checked in order. Each is
# scanned a couple of levels deep, since people usually unzip MekHQ into a
# folder of its own inside one of these.
SEARCH_ROOTS = [
    os.path.expanduser('~/Desktop'),
    os.path.expanduser('~/Documents'),
    os.path.expanduser('~/Downloads'),
    os.path.expanduser('~'),
    'C:/Program Files',
    'C:/Program Files (x86)',
    'C:/Games',
    'C:/',
]

# Skipped while scanning: big, slow, and never where MekHQ lives.
SCAN_SKIP = {'Windows', 'AppData', 'node_modules', 'OneDriveTemp',
             'ProgramData', 'System Volume Information', 'Recovery',
             'PerfLogs', 'MSOCache'}


def base_dir():
    """The directory holding the exe (or this script, when run from source)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE = base_dir()
SITE = os.path.join(BASE, 'site')
GEMS = os.path.join(BASE, 'gems')
RUBY_BIN = os.path.join(BASE, 'runtime', 'ruby', 'bin')


def say(message):
    print(message, flush=True)


def pause():
    """Hold the window open so a double-clicking user can read what happened."""
    try:
        if sys.stdin and sys.stdin.isatty():
            input('\nPress Enter to close this window.')
    except EOFError:
        pass


def fail(message):
    print('\n' + message, flush=True)
    pause()
    sys.exit(1)


# ----------------------------------------------------------------------------
# Finding MekHQ and the campaign save
# ----------------------------------------------------------------------------

def looks_like_mekhq(path):
    """A MekHQ directory has the jar and a campaigns folder next to it."""
    return (os.path.isfile(os.path.join(path, 'MekHQ.jar')) and
            os.path.isdir(os.path.join(path, 'campaigns')))


def scan_for_mekhq(max_depth=4):
    """Look a few levels down each likely root for a MekHQ install.

    Depth matters because people nest: a folder for BattleTech things, a
    folder for MekHQ, then the versioned folder the zip unpacked as. It stays
    bounded so this cannot turn into a scan of the whole drive.
    """
    for root in SEARCH_ROOTS:
        if not os.path.isdir(root):
            continue
        found = scan_below(root, max_depth)
        if found:
            return os.path.normpath(found)
    return None


def scan_below(root, depth):
    if looks_like_mekhq(root):
        return root
    if depth <= 0:
        return None
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return None
    for entry in entries:
        # nothing worth finding lives in these, and they are enormous
        if entry.startswith(('.', '$')) or entry in SCAN_SKIP:
            continue
        candidate = os.path.join(root, entry)
        if not os.path.isdir(candidate) or os.path.islink(candidate):
            continue
        found = scan_below(candidate, depth - 1)
        if found:
            return found
    return None


def prompt_for_mekhq():
    say('\nI could not find MekHQ automatically.')
    say('Open the folder holding MekHQ.jar and paste its path here.')
    while True:
        answer = input('MekHQ folder: ').strip().strip('"')
        if not answer:
            fail('No MekHQ folder given, so there is nothing to read.')
        if looks_like_mekhq(answer):
            return os.path.abspath(answer)
        say('That folder has no MekHQ.jar and campaigns folder in it. '
            'Try again, or close this window.')


def find_saves(mekhq_path):
    saves = glob.glob(os.path.join(mekhq_path, 'campaigns', '*.cpnx')) + \
            glob.glob(os.path.join(mekhq_path, 'campaigns', '*.cpnx.gz'))
    return sorted(saves, key=os.path.getmtime, reverse=True)


def choose_save(saves, remembered):
    """Pick a save: the remembered one if it is still there, else ask."""
    names = [os.path.basename(s) for s in saves]
    if remembered in names:
        return remembered
    if len(saves) == 1:
        return names[0]
    say('\nWhich campaign should the website show?')
    for index, name in enumerate(names, start=1):
        stamp = time.strftime('%Y-%m-%d %H:%M',
                              time.localtime(os.path.getmtime(saves[index - 1])))
        say('  {}. {}  (saved {})'.format(index, name, stamp))
    while True:
        answer = input('Number [1]: ').strip() or '1'
        if answer.isdigit() and 1 <= int(answer) <= len(names):
            return names[int(answer) - 1]
        say('Enter a number between 1 and {}.'.format(len(names)))


# ----------------------------------------------------------------------------
# Settings file, so the questions above are only asked once
# ----------------------------------------------------------------------------

def load_config():
    parser = configparser.ConfigParser()
    parser.read(os.path.join(BASE, CONFIG_NAME), encoding='utf-8')
    if not parser.has_section('campaign'):
        parser.add_section('campaign')
    return parser


def save_config(parser):
    with open(os.path.join(BASE, CONFIG_NAME), 'w', encoding='utf-8') as handle:
        handle.write('# Remembered settings. Delete this file to be asked '
                     'again, or edit it by hand.\n')
        parser.write(handle)


def resolve_campaign():
    config = load_config()
    mekhq_path = config.get('campaign', 'mekhq_path', fallback='').strip()
    campaign_file = config.get('campaign', 'campaign_file', fallback='').strip()

    if not mekhq_path or not looks_like_mekhq(mekhq_path):
        say('Looking for your MekHQ install...')
        mekhq_path = scan_for_mekhq() or prompt_for_mekhq()
        say('Found MekHQ: {}'.format(mekhq_path))

    saves = find_saves(mekhq_path)
    if not saves:
        fail('No campaign saves in {}.\nStart a campaign in MekHQ and save it '
             'first, then run this again.'.format(
                 os.path.join(mekhq_path, 'campaigns')))

    campaign_file = choose_save(saves, campaign_file)

    config.set('campaign', 'mekhq_path', mekhq_path)
    config.set('campaign', 'campaign_file', campaign_file)
    save_config(config)
    return mekhq_path, campaign_file


# ----------------------------------------------------------------------------
# The three things this launcher actually does
# ----------------------------------------------------------------------------

def run_parser(mekhq_path, campaign_file):
    say('\nReading {}...'.format(campaign_file))
    script = os.path.join(SITE, 'process_campaign.py')
    if not os.path.isfile(script):
        fail('Missing {}. The release is incomplete.'.format(script))
    argv = sys.argv
    cwd = os.getcwd()
    try:
        sys.argv = [script, campaign_file, mekhq_path]
        runpy.run_path(script, run_name='__main__')
    except SystemExit as stop:
        if stop.code:
            fail('Reading the campaign failed.')
    except Exception as problem:
        fail('Reading the campaign failed: {}\n\nIf this is a campaign the '
             'website has never seen before, the save may use something this '
             'script does not handle yet.'.format(problem))
    finally:
        sys.argv = argv
        os.chdir(cwd)


def ruby_env():
    """Point Ruby and Bundler at the copies inside this release."""
    env = dict(os.environ)
    env['PATH'] = RUBY_BIN + os.pathsep + env.get('PATH', '')
    env['BUNDLE_GEMFILE'] = os.path.join(SITE, 'Gemfile')
    # a Ruby installed on the user's own machine must not leak into this
    for leaky in ('GEM_HOME', 'GEM_PATH', 'RUBYOPT', 'RUBYLIB'):
        env.pop(leaky, None)
    # the gems sit beside the site rather than under it, which keeps every
    # gem file 14 characters further from the Windows path limit
    env['BUNDLE_PATH'] = GEMS
    return env


def run_jekyll(arguments):
    ruby = os.path.join(RUBY_BIN, 'ruby.exe')
    if not os.path.isfile(ruby):
        fail('Missing the bundled Ruby at {}.\nThe release is '
             'incomplete.'.format(ruby))
    command = [ruby, '-S', 'bundle', 'exec', 'jekyll'] + arguments
    return subprocess.run(command, cwd=SITE, env=ruby_env()).returncode


# Windows refuses to start a program whose path passes 260 characters, and
# the error it gives when that happens says nothing useful, so the check
# happens here instead. The deepest thing that has to run is the Dart binary
# behind the stylesheet compiler, 89 characters below this folder; the build
# prints the true figure so this stays honest.
MAX_BASE_LENGTH = 165


def check_path_length():
    if len(BASE) <= MAX_BASE_LENGTH:
        return
    fail('This folder is too deep inside other folders for Windows to run '
         'the site builder:\n\n    {}\n\nThat path is {} characters long, '
         'and Windows gives up somewhere past 260 once the program files '
         'inside are counted.\n\nMove this folder somewhere shorter, like '
         'C:\\MekHQ-Website or your Desktop, and run it '
         'again.'.format(BASE, len(BASE)))


# ----------------------------------------------------------------------------
# Making the built site work by double-clicking it
# ----------------------------------------------------------------------------

# Jekyll writes links from the root of a web server: /css/site.css, and
# /forces/mek-company with no file extension. Opened from a folder rather than
# served, every one of those is broken -- which is the only reason this program
# ever needed to run a web server. Rewriting them to ordinary relative paths
# turns the output into something anyone can open by double-clicking, forever,
# with no program running.
LINK_PATTERN = re.compile(r'((?:href|src)=")/([^"]*)"')
CSS_URL_PATTERN = re.compile(r'url\((["\']?)/([^)"\']*)\1\)')


def resolve_target(site, path):
    """Point a server-style path at a file that exists on disk."""
    path = path.split('#')[0].split('?')[0]
    if not path:
        return 'index.html'
    full = os.path.join(site, path.replace('/', os.sep))
    if os.path.isdir(full):
        return path.rstrip('/') + '/index.html'
    if not os.path.splitext(path)[1] and os.path.isfile(full + '.html'):
        return path + '.html'
    return path


def make_portable(site):
    """Rewrite absolute links so the folder works from the file system."""
    changed = 0
    for root, _, files in os.walk(site):
        for name in files:
            if not name.endswith(('.html', '.css')):
                continue
            full = os.path.join(root, name)
            depth = os.path.relpath(root, site).replace('\\', '/')
            up = '' if depth == '.' else '../' * len(depth.split('/'))

            def to_relative(match, up=up):
                target = resolve_target(site, match.group(2))
                anchor = match.group(2).partition('#')[2]
                return '{}{}{}"'.format(match.group(1), up + target,
                                        '#' + anchor if anchor else '')

            try:
                with open(full, encoding='utf-8') as handle:
                    original = handle.read()
            except (OSError, UnicodeDecodeError):
                continue
            text = LINK_PATTERN.sub(to_relative, original)
            text = CSS_URL_PATTERN.sub(
                lambda m, up=up: 'url({}{}{})'.format(
                    m.group(1), up + resolve_target(site, m.group(2)),
                    m.group(1)), text)
            # the stylesheet reaches up twice for images that sit one level
            # up; harmless on a server, which clamps at the root, but it
            # escapes the folder entirely when opened as a file
            if name.endswith('.css'):
                text = text.replace('../../assets/', '../assets/')
            if text != original:
                with open(full, 'w', encoding='utf-8') as handle:
                    handle.write(text)
                changed += 1
    return changed


def build_site():
    say('\nBuilding the website...')
    if run_jekyll(['build']) != 0:
        fail('The site build failed. The messages above say why.')
    pages = make_portable(os.path.join(SITE, '_site'))
    say('Built {} pages.'.format(pages))
    say('  {}'.format(os.path.join(SITE, '_site')))


def site_title():
    """The unit's name, used to name the file people get sent."""
    try:
        with open(os.path.join(SITE, '_config.yml'), encoding='utf-8') as f:
            for line in f:
                if line.startswith('title:'):
                    return line.split(':', 1)[1].strip().strip('\'"')
    except OSError:
        pass
    return 'Campaign'


def open_locally():
    page = os.path.join(SITE, '_site', 'index.html')
    if not os.path.isfile(page):
        fail('Nothing has been built yet, so there is nothing to open.')
    say('\nOpening your campaign...')
    webbrowser.open('file:///' + page.replace('\\', '/'))
    say('\nThe website is an ordinary folder of files. Open index.html any')
    say('time you like - this program only needs running again when your')
    say('campaign has moved on.')


def publish_site():
    """Zip the site for a host, and point at the easiest one.

    Deliberately no accounts, tokens or logins here. Netlify Drop takes a
    dropped zip and gives back a public address without so much as an email,
    which is the shortest path from a campaign save to a link you can hand
    your group.
    """
    source = os.path.join(SITE, '_site')
    if not os.path.isdir(source):
        fail('Nothing has been built yet, so there is nothing to publish.')
    name = re.sub(r'[^\w\- ]', '', site_title()).strip() or 'Campaign'
    archive = os.path.join(BASE, name + ' website.zip')
    say('\nPackaging the site for a web host...')
    if os.path.exists(archive):
        os.remove(archive)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for root, _, files in os.walk(source):
            for filename in files:
                full = os.path.join(root, filename)
                zipped.write(full, os.path.relpath(full, source))
    say('Made {} ({:.1f} MB)'.format(archive, os.path.getsize(archive) / 1e6))
    say('')
    say('To put it online, free, with no account:')
    say('  1. Go to https://app.netlify.com/drop')
    say('  2. Drag that zip onto the page')
    say('  3. You get a public address to share')
    say('')
    say('GitHub Pages and Cloudflare Pages work the same way if you would')
    say('rather use those; upload the contents of the zip as the site.')
    if not os.environ.get('MEKHQ_WEBSITE_NO_BROWSER'):
        webbrowser.open('https://app.netlify.com/drop')
    return archive


def export_share_file():
    """Fold the whole site into one file that can be sent to someone."""
    import share
    name = re.sub(r'[^\w\- ]', '', site_title()).strip() or 'Campaign'
    output = os.path.join(BASE, name + '.html')
    say('\nPacking the whole site into one file...')
    size = share.build(os.path.join(SITE, '_site'), site_title(), output)
    say('\nMade {} ({:.1f} MB)'.format(output, size / 1e6))
    say('\nSend that one file to anyone - email, chat, a USB stick. They')
    say('double-click it and the whole campaign opens in their browser.')
    say('Nothing for them to install, and no internet needed.')
    return output


def serve_site(port, open_browser):
    url = 'http://127.0.0.1:{}/'.format(port)
    say('\nStarting the preview server at {}'.format(url))
    say('Leave this window open while you browse. Press Ctrl+C to stop.\n')
    if open_browser:
        threading.Timer(4.0, lambda: webbrowser.open(url)).start()
    try:
        run_jekyll(['serve', '--host', '127.0.0.1', '--port', str(port),
                    '--skip-initial-build'])
    except KeyboardInterrupt:
        say('\nServer stopped.')


# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Build and preview a MekHQ campaign website.')
    parser.add_argument('--share', action='store_true',
                        help='also pack the site into a single file you can '
                             'send to someone')
    parser.add_argument('--publish', action='store_true',
                        help='package the site for putting online, and show '
                             'you where to drop it')
    parser.add_argument('--build-only', action='store_true',
                        help='build and stop, without opening a browser')
    parser.add_argument('--serve', action='store_true',
                        help='also run a local web server, which rebuilds as '
                             'you edit the site')
    parser.add_argument('--open-only', action='store_true',
                        help='open what was built last without reading MekHQ '
                             'again')
    parser.add_argument('--port', type=int, default=4000,
                        help='port for the --serve web server (default 4000)')
    parser.add_argument('--no-browser', action='store_true',
                        help='do not open a browser window')
    args = parser.parse_args()

    say('MekHQ Campaign Website')
    say('=' * 60)
    check_path_length()

    if not args.open_only:
        mekhq_path, campaign_file = resolve_campaign()
        run_parser(mekhq_path, campaign_file)
        build_site()

    if args.share:
        export_share_file()

    if args.publish:
        publish_site()

    if args.build_only:
        pause()
        return

    if args.serve:
        serve_site(args.port, not args.no_browser)
        return

    if not args.no_browser:
        open_locally()
    pause()


if __name__ == '__main__':
    main()

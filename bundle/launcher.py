#!/usr/bin/env python3
"""Front end for the pre-baked release of this site.

The release ships its own Ruby and its own copy of this repository, so the
person running it does not need Ruby, Jekyll, or Python installed. This
launcher is what the bundled MekHQ-Website.exe runs:

    1. work out where MekHQ is and which save to read
    2. run process_campaign.py against that save
    3. build the site with the bundled Jekyll
    4. serve it and open a browser

Run it with --help to see the individual steps as flags.
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


def build_site():
    say('\nBuilding the website...')
    if run_jekyll(['build']) != 0:
        fail('The site build failed. The messages above say why.')
    say('Built: {}'.format(os.path.join(SITE, '_site')))


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
    parser.add_argument('--build-only', action='store_true',
                        help='write the site to site/_site and exit, for '
                             'uploading to a web host')
    parser.add_argument('--serve-only', action='store_true',
                        help='skip reading MekHQ, just serve what was built')
    parser.add_argument('--port', type=int, default=4000,
                        help='port for the preview server (default 4000)')
    parser.add_argument('--no-browser', action='store_true',
                        help='do not open a browser window')
    args = parser.parse_args()

    say('MekHQ Campaign Website')
    say('=' * 60)
    check_path_length()

    if not args.serve_only:
        mekhq_path, campaign_file = resolve_campaign()
        run_parser(mekhq_path, campaign_file)
        build_site()

    if args.build_only:
        say('\nUpload the contents of site/_site to any web host to publish.')
        pause()
        return

    serve_site(args.port, not args.no_browser)


if __name__ == '__main__':
    main()

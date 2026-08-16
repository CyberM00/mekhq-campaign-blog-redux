#!/usr/bin/env python3
"""Fold a built site into one HTML file that opens by double-clicking it.

A folder of pages is awkward to hand to someone: they have to unzip it, find
index.html, and keep the rest of the files next to it. This packs the whole
site — every page, the stylesheet, every portrait — into a single file that
works offline, over email, or from a chat message, with no server and nothing
to install on their end.

Pages become sections of one document, keyed by their original path, and
links between them become fragment links that a small script switches
between. Images are embedded as data URIs.
"""

import base64
import json
import mimetypes
import os
import re
import urllib.parse

MAIN_PATTERN = re.compile(r'<main\b[^>]*>(.*?)</main>', re.S)
TITLE_PATTERN = re.compile(r'<title>(.*?)</title>', re.S)
LINK_PATTERN = re.compile(r'(href|src)="([^"]+)"')
CSS_URL_PATTERN = re.compile(r'url\((["\']?)([^)"\']+)\1\)')

# pages that exist for machines rather than people
SKIP_PAGES = {'404.html'}


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


# MekHQ portraits are 200 KB PNGs, which is generous for something shown at
# 200 pixels wide. Left alone they make a 27 MB file, past what most mail and
# chat services accept; shrunk to what the page actually displays, the same
# campaign fits in a few MB and still looks right.
PORTRAIT_WIDTH = 300
ARTWORK_WIDTH = 1400


def data_uri(path, max_width=ARTWORK_WIDTH):
    raw = None
    kind = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    try:
        from PIL import Image
        import io
        with Image.open(path) as picture:
            if picture.width > max_width:
                height = round(picture.height * max_width / picture.width)
                picture = picture.resize((max_width, height),
                                         Image.LANCZOS)
            buffer = io.BytesIO()
            if picture.mode in ('RGBA', 'LA', 'P'):
                # MekHQ portraits are cut out against transparency, which
                # matters wherever they sit on the camouflage background, so
                # they stay PNG. Reducing them to a palette keeps that and
                # still takes 194 KB down to under 30.
                picture.convert('RGBA').quantize(
                    colors=128, method=Image.FASTOCTREE).save(
                        buffer, format='PNG', optimize=True)
                kind = 'image/png'
            else:
                picture.convert('RGB').save(buffer, format='JPEG',
                                            quality=82, optimize=True)
                kind = 'image/jpeg'
            raw = buffer.getvalue()
    except Exception:
        # without Pillow, or for anything it cannot read, ship the original
        raw = None
    if raw is None:
        with open(path, 'rb') as handle:
            raw = handle.read()
    return 'data:{};base64,{}'.format(
        kind, base64.b64encode(raw).decode('ascii'))


def page_id(relative):
    """A stable fragment name for a page, from its path in the site."""
    return urllib.parse.quote(relative.replace('\\', '/'))


def collect_pages(site):
    pages = []
    for root, _, files in os.walk(site):
        for name in sorted(files):
            if not name.endswith('.html') or name in SKIP_PAGES:
                continue
            full = os.path.join(root, name)
            relative = os.path.relpath(full, site).replace('\\', '/')
            pages.append((relative, full))
    # index first, so it is what opens
    pages.sort(key=lambda item: (item[0] != 'index.html', item[0]))
    return pages


def inline_css(site, cache):
    """The stylesheet, with its images embedded."""
    css_path = os.path.join(site, 'css', 'site.css')
    if not os.path.isfile(css_path):
        return ''
    css = read(css_path)

    def swap(match):
        target = match.group(2)
        if target.startswith(('data:', 'http:', 'https:', '//')):
            return match.group(0)
        resolved = os.path.normpath(
            os.path.join(os.path.dirname(css_path), target.split('?')[0]))
        if os.path.isfile(resolved):
            return 'url({})'.format(data_uri(resolved))
        return match.group(0)

    return CSS_URL_PATTERN.sub(swap, css)


def embed(path, cache):
    """Number each distinct image, so one file holds one copy of each.

    Portraits repeat across the roster pages, the role pages and their own
    bios. Written out inline every time, a campaign of 94 people came to
    100 MB; carried once each and handed out by the script below, the same
    site is a twentieth of that.
    """
    if path not in cache:
        cache[path] = len(cache)
    return cache[path]


def image_bank(cache):
    uris = [''] * len(cache)
    for path, index in cache.items():
        width = (PORTRAIT_WIDTH if 'portraits' in path.replace(os.sep, '/')
                 else ARTWORK_WIDTH)
        uris[index] = data_uri(path, width)
    return uris


def rewrite_body(html, page_dir, site, ids, cache):
    """Point links at other sections, and pull images into the file."""
    def swap(match):
        attribute, target = match.group(1), match.group(2)
        if target.startswith(('http:', 'https:', 'mailto:', 'data:', '#')):
            return match.group(0)
        path, _, anchor = target.partition('#')
        if not path:
            return match.group(0)
        resolved = os.path.normpath(os.path.join(page_dir,
                                                 urllib.parse.unquote(path)))
        relative = os.path.relpath(resolved, site).replace('\\', '/')
        if attribute == 'src':
            if os.path.isfile(resolved):
                return 'data-image="{}"'.format(embed(resolved, cache))
            return match.group(0)
        if relative in ids:
            return 'href="#{}"'.format(page_id(relative))
        return match.group(0)

    return LINK_PATTERN.sub(swap, html)


VIEWER_SCRIPT = """
(function () {
  var images = window.MEKHQ_IMAGES || [];
  var waiting = document.querySelectorAll('img[data-image]');
  for (var n = 0; n < waiting.length; n++) {
    waiting[n].src = images[waiting[n].getAttribute('data-image')] || '';
  }
  var pages = document.querySelectorAll('.mekhq-page');
  function show(id) {
    var found = false;
    for (var i = 0; i < pages.length; i++) {
      var match = pages[i].id === id;
      pages[i].style.display = match ? 'block' : 'none';
      found = found || match;
    }
    if (!found && pages.length) {
      pages[0].style.display = 'block';
    }
    window.scrollTo(0, 0);
  }
  function current() {
    return decodeURIComponent(window.location.hash.replace(/^#/, ''));
  }
  window.addEventListener('hashchange', function () { show(current()); });
  show(current() || (pages.length ? pages[0].id : ''));
})();
"""


def build(site, title, output):
    """Write the whole site to one file. Returns its size in bytes."""
    pages = collect_pages(site)
    ids = {relative for relative, _ in pages}
    cache = {}
    css = inline_css(site, cache)

    sections = []
    for relative, full in pages:
        html = read(full)
        body = MAIN_PATTERN.search(html)
        if not body:
            continue
        page_title = TITLE_PATTERN.search(html)
        sections.append(
            '<div class="mekhq-page" id="{}" style="display:none">\n'
            '<!-- {} -->\n{}\n</div>'.format(
                page_id(relative),
                page_title.group(1).strip() if page_title else relative,
                rewrite_body(body.group(1), os.path.dirname(full), site,
                             ids, cache)))

    # The drop-down in the navigation bar is a Bootstrap component and needs
    # its JavaScript, which normally comes from the footer. Only <main> and
    # <nav> are carried across, so it has to be brought in on purpose or the
    # Personnel menu will not open for whoever receives this.
    scripts = []
    for name in ('jquery.slim.min.js', 'popper.min.js', 'bootstrap.min.js'):
        script_path = os.path.join(site, 'assets', 'js', name)
        if os.path.isfile(script_path):
            scripts.append('<script>{}</script>'.format(read(script_path)))

    # the navigation from the front page, pointed at the sections
    nav = ''
    index = os.path.join(site, 'index.html')
    if os.path.isfile(index):
        found = re.search(r'<nav\b.*?</nav>', read(index), re.S)
        if found:
            nav = rewrite_body(found.group(0), site, site, ids, cache)

    document = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{css}
/* the pages are stacked in one file and shown one at a time */
.mekhq-page {{ display: none; }}
body {{ padding-top: 56px; }}
</style>
</head>
<body>
{nav}
{sections}
{scripts}
<script>window.MEKHQ_IMAGES = {images};</script>
<script>{script}</script>
</body>
</html>
""".format(title=title, css=css, nav=nav,
           sections='\n'.join(sections), script=VIEWER_SCRIPT,
           images=json.dumps(image_bank(cache)),
           scripts='\n'.join(scripts))

    with open(output, 'w', encoding='utf-8') as handle:
        handle.write(document)
    return os.path.getsize(output)

#!/usr/bin/env python3
"""Verify a static site folder and compare it to a previous index.html.

Usage:
  check_site.py SITE_DIR [--overlay UPDATE_SITE_DIR] [--html INDEX] [--baseline OLD_INDEX]

  SITE_DIR   the published folder (pure-sky-creations)
  --overlay  an update folder not merged yet; its files count as present
  --html     the index.html to check (default: SITE_DIR/index.html)
  --baseline the previous index.html; splits orphans and broken anchors into
             "caused by this update" and "already there"

Exit code 1 if anything would break the deployed site: a missing asset, a
wrong-case path, or a broken anchor this update introduced. Orphans and
pre-existing anchor problems are reported but never fail the check.

Paths are compared case-sensitively on purpose. Windows finds `Photo.JPG` when
the HTML says `photo.jpg`, but Netlify serves from Linux and returns a 404.
"""
import argparse
import os
import re
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")

# Quote characters, whitespace and brackets end a path; backticks catch JS templates.
ASSET_RE = re.compile(r"""(assets/[^"'`)\s\\<>]+)""")
LOCAL_RE = re.compile(r"""(?:src|href)=["']([^"'#][^"']*)["']""")
ID_RE = re.compile(r"""\bid=["']([^"']+)""")
ANCHOR_RE = re.compile(r"""href=["']#([^"']+)""")
NON_LOCAL = ("http:", "https:", "mailto:", "tel:", "about:", "data:", "//", "assets/")


def clean(ref):
    """Strip ?v=2 style cache-busters and #fragments, then decode %20 etc."""
    return urllib.parse.unquote(ref.split("?")[0].split("#")[0])


def read_refs(path):
    with open(path, encoding="utf-8") as f:
        html = f.read()
    refs = {clean(m) for m in ASSET_RE.findall(html)}
    refs |= {clean(m) for m in LOCAL_RE.findall(html) if not m.startswith(NON_LOCAL)}
    return html, refs


def list_files(root):
    if not root or not os.path.isdir(root):
        return set()
    return {
        os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
        for d, _, files in os.walk(root)
        for f in files
    }


def show(label, items):
    items = sorted(items)
    print(f"{label}: {len(items)}")
    for item in items:
        print(f"  {item}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("--overlay")
    ap.add_argument("--html")
    ap.add_argument("--baseline")
    a = ap.parse_args()

    html, refs = read_refs(a.html or os.path.join(a.site, "index.html"))
    site_files = list_files(a.site)
    overlay_files = list_files(a.overlay)
    present = site_files | overlay_files
    lower = {p.lower(): p for p in present}

    missing = {r for r in refs if r not in present and r.lower() not in lower}
    wrong_case = {f"{r} (on disk: {lower[r.lower()]})" for r in refs
                  if r not in present and r.lower() in lower}

    old_refs, old_ids, old_broken = set(), set(), set()
    if a.baseline:
        old_html, old_refs = read_refs(a.baseline)
        old_ids = set(ID_RE.findall(old_html))
        old_broken = set(ANCHOR_RE.findall(old_html)) - old_ids

    ids = set(ID_RE.findall(html))
    broken = set(ANCHOR_RE.findall(html)) - ids
    new_broken = broken - old_broken

    assets = {p for p in present if p.startswith("assets/")}
    orphans = assets - refs
    newly_orphaned = orphans & old_refs
    already_orphaned = orphans - newly_orphaned
    # Only meaningful before the merge: files the update ships but never uses.
    unused_new = {p for p in overlay_files if p.startswith("assets/")} - refs

    print(f"asset and local references: {len(refs)}")
    show("MISSING (fails)", missing)
    show("WRONG CASE, 404s on Netlify (fails)", wrong_case)
    show("BROKEN ANCHORS from this update (fails)", new_broken)
    show("broken anchors already there", broken & old_broken)
    if a.baseline:
        show("sections removed by this update", old_ids - ids)
    show("NEWLY ORPHANED, superseded by this update", newly_orphaned)
    show("already orphaned, leave alone", already_orphaned)
    if a.overlay:
        show("update assets the new page never uses", unused_new)

    failed = missing or wrong_case or new_broken
    print("RESULT:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

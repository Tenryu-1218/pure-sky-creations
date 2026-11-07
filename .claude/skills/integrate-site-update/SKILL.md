---
name: integrate-site-update
description: Merge a dated website update folder (update-YYYY-MM-DD/pure-sky-creations/) into the published pure-sky-creations/ folder, verify it, clean up, and push to GitHub so Netlify redeploys. Use whenever the user mentions a new update folder, says to integrate, merge, apply or ship a website update, or asks to get the new version of the Pure Sky Creations site live, even if they don't say "skill" or name the folder exactly.
---

# Integrate a site update

Update folders are exports from the design tool. They hold a complete new `index.html` plus only the assets that are new, so the merge is an overlay onto the existing site, not a folder swap. Replacing `pure-sky-creations/` with the update would delete about 190 assets the page still needs.

## Repo layout

- `pure-sky-creations/` is the only folder Netlify publishes (`netlify.toml`, no build command). Pushing to `main` triggers the deploy.
- `uploads/` holds the user's original photos, which have no exact copy in the site. It isn't published, so leave it alone and don't put updates there.

## 1. Preflight

Use the folder the user named. Otherwise use the newest `update-*` folder, and if several are waiting, ask whether to apply them in date order.

```bash
git status -sb      # expect main, not behind origin, only the update folder untracked
git fetch origin
```

Stop and ask if there are unrelated uncommitted changes, because they could end up in the deploy. Run `git pull --ff-only` if `main` is behind.

Expect `update-*/pure-sky-creations/index.html`. If the layout differs (loose files, a zip, renamed folders, an update to `image-slot.js`), work out the equivalent mapping and tell the user what you assumed.

## 2. Check before merging

Save the current page as a baseline in the scratchpad, then run the checker against the update while it is still separate. A failure here costs nothing, since nothing has moved yet.

```bash
git show HEAD:pure-sky-creations/index.html > "$SCRATCH/baseline.html"
U=update-YYYY-MM-DD/pure-sky-creations
python -I .claude/skills/integrate-site-update/scripts/check_site.py pure-sky-creations \
  --overlay "$U" --html "$U/index.html" --baseline "$SCRATCH/baseline.html"
```

If it reports FAIL, don't push a broken page:
- **Missing asset:** look for it in git history. Copy it into the site only if it is clearly the same file. Otherwise ask the user.
- **Wrong case:** tell the user which path differs. Windows hides this, but it 404s on Netlify.
- **Broken anchor:** usually a nav link to a removed section. Ask the user, because the fix changes their page.

Known false positives: `artist`, `engineer` and `warrior` are mode tabs handled by JavaScript (`data-mode-go`), so they always show as broken anchors with no matching `id`.

## 3. Merge

Move every file from the update into `pure-sky-creations/` at the same relative path, overwriting. Confirm the update folder has no files left, then remove it.

```bash
( cd "$U" && find . -type f | sed 's|^\./||' ) | while read -r f; do
  mkdir -p "pure-sky-creations/$(dirname "$f")"
  mv -f "$U/$f" "pure-sky-creations/$f"
done
```

## 4. Delete what the update replaced

Run `git rm` on the files listed under **NEWLY ORPHANED**. The new page stopped using them, and they stay recoverable from git history. Name them in the final report, because a removed photo may be worth a second look.

Leave the **already orphaned** files. They predate this update, and the user may be keeping them on purpose, so mention them only if the list has grown or they ask.

Assets referenced with a cache-buster such as `foo.jpg?v=2` are still in use. The checker handles this, but a plain `grep` for the filename can mislead.

## 5. Verify the merged site

Re-run the checker without `--overlay`, keeping `--baseline`. It should say PASS with zero newly orphaned files.

Then serve the folder and render it, since a passing file check doesn't prove the page works:

```bash
python -m http.server 8931 --directory pure-sky-creations   # run in the background
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars \
  --user-data-dir="<scratchpad, Windows path>\chrome" --window-size=1400,2600 --virtual-time-budget=8000 \
  --screenshot="<scratchpad, Windows path>\site.png" "http://localhost:8931/index.html#artist"
```

Read the screenshot and confirm the page is styled and images load. Also use `--dump-dom` to confirm the headings and items added by this update's diff are present. Check `#warrior` and `#engineer` too if the diff touches those panels. Stop the server afterwards.

## 6. Commit and push

Stage by explicit path so stray files stay out of the deploy, and summarize real content changes from the diff of `index.html`, such as pieces added, sold or reorganized.

```bash
git add pure-sky-creations
git status --short    # read this: only site files, no update folder
git commit            # e.g. "Update site for 2026-11-07: reorganize jewelry and shodo, add new pieces"
git push origin main
```

Asking for this workflow is the request to push to `main`, so no second confirmation is needed once the checks pass. If the push is rejected, pull with `--rebase` and re-run the check. Never force-push: `main` is the live site.

## 7. Report

Confirm `git rev-parse HEAD` matches `origin/main`, then tell the user:
- the commit hash and a short summary of what changed on the site
- files added and files deleted
- anything visitors will notice being gone, such as removed sections or pieces
- how far verification went

The Netlify deploy doesn't report back to GitHub commit statuses, so a successful push only shows that Netlify was given the new version. Say so, and ask the user to check the Netlify dashboard or live site unless you have actually confirmed the deploy.

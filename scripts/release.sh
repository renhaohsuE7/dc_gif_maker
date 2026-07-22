#!/usr/bin/env bash
# Create a GitHub Release for an existing, already-pushed tag.
#
# Idempotent (skips if the release exists) and secret-safe: the token comes
# from $GITHUB_TOKEN / $GH_TOKEN, or falls back to the local git credential
# store — it is kept in a shell variable and never printed or logged.
#
# Runs inside the dcmaker image (which bundles `gh`). See README "發佈 Release".
#
#   scripts/release.sh v0.2.0                 # create, auto-generated notes
#   scripts/release.sh v0.2.0 --draft         # stage without publishing
#   scripts/release.sh v0.2.0 --latest=false  # don't mark as "Latest"
#   scripts/release.sh v0.2.0 --notes-file CHANGELOG.md   # custom body
#
# Any extra args are passed straight through to `gh release create`.
set -euo pipefail

tag="${1:-}"
if [[ -z "$tag" ]]; then
    echo "usage: release.sh <tag> [gh release create flags...]" >&2
    exit 2
fi
shift

# --- repo slug: $DCM_RELEASE_REPO wins; else derive from the origin remote ----
repo="${DCM_RELEASE_REPO:-}"
if [[ -z "$repo" ]]; then
    git config --global --add safe.directory "$(pwd)" 2>/dev/null || true
    url="$(git config --get remote.origin.url 2>/dev/null || true)"
    repo="$(sed -E 's#^(git@github\.com:|https://github\.com/)##; s#\.git$##' <<<"$url")"
fi
if [[ "$repo" != */* ]]; then
    echo "cannot determine repo; set DCM_RELEASE_REPO=owner/name" >&2
    exit 2
fi

# --- token: env first, else git credential store (kept in-var, never echoed) --
token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$token" ]]; then
    token="$(printf 'protocol=https\nhost=github.com\n\n' \
               | git credential fill 2>/dev/null \
               | sed -n 's/^password=//p' || true)"
fi
if [[ -z "$token" ]]; then
    echo "no token found. Export a PAT with 'Contents: read and write' (or the" >&2
    echo "classic 'repo' scope), then re-run:" >&2
    echo "  export GITHUB_TOKEN=github_pat_xxx" >&2
    exit 3
fi
export GH_TOKEN="$token"

# --- idempotent: skip if the release already exists --------------------------
if gh release view "$tag" -R "$repo" >/dev/null 2>&1; then
    echo "release $tag already exists on $repo — nothing to do"
    gh release view "$tag" -R "$repo" --json url -q '"  " + .url'
    exit 0
fi

echo "creating release $tag on $repo ..."
# --verify-tag: refuse to invent a tag; we only release tags already pushed.
# --generate-notes: build the changelog from merged PRs / commits since last tag.
gh release create "$tag" -R "$repo" --verify-tag --generate-notes "$@"
gh release view "$tag" -R "$repo" --json url -q '"created: " + .url'

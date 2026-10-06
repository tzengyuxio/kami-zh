#!/usr/bin/env bash
# Assemble the browser version (web/) into web/dist/.
#
#   tools/web.sh          # build web/dist/
#   tools/web.sh serve    # build, then serve it at http://localhost:8000/
#
# Needs game/KAMI (the original) to build the patch, like tools/release.sh;
# the translation is built from scratch in a temporary copy. web/dist/ holds
# only the page, the script and kami-zh.kzp -- no game data -- so it can be
# published as is (e.g. to GitHub Pages).
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d -t kami-web)
trap 'command rm -rf "$work"' EXIT

mkdir -p "$work/repo/game"
cp -R "$root/tools" "$root/translation" "$work/repo/"
cp -R "$root/game/KAMI" "$work/repo/game/"
(cd "$work/repo" && SKIP_OPENING=0 python3 tools/install.py >/dev/null)

dist=$root/web/dist
command rm -rf "$dist"
mkdir -p "$dist"
python3 "$root/tools/mkpatch.py" "$root/game/KAMI" "$work/repo/build/KAMI" "$dist/kami-zh.kzp"
cp "$root/web/index.html" "$root/web/app.js" "$dist/"
echo "$dist 已就緒"

if [ "${1:-}" = serve ]; then
  cd "$dist" && python3 -m http.server 8000
fi

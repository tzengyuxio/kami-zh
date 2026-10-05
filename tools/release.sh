#!/usr/bin/env bash
# Build the release patcher zips into patcher/dist/.
#
#   tools/release.sh v1.0.0
#
# Needs game/KAMI (the original) and Go. The translation is built from
# scratch in a temporary copy -- opening kept, no gameplay tweaks -- so
# build/KAMI is left alone.
set -euo pipefail

version=${1:?usage: tools/release.sh VERSION}
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d -t kami-release)
trap 'command rm -rf "$work"' EXIT

mkdir -p "$work/repo/game"
cp -R "$root/tools" "$root/translation" "$work/repo/"
cp -R "$root/game/KAMI" "$work/repo/game/"
(cd "$work/repo" && SKIP_OPENING=0 python3 tools/install.py >/dev/null)
python3 "$root/tools/mkpatch.py" "$root/game/KAMI" "$work/repo/build/KAMI" "$root/patcher/kami-zh.kzp"

dist=$root/patcher/dist
command rm -rf "$dist"
mkdir -p "$dist"

package() {   # package NAME BINARY
  local dir=$work/$1
  mkdir -p "$dir"
  cp "$2" "$dir/"
  # CRLF + BOM so Notepad on old Windows reads the UTF-8 text
  { printf '\xef\xbb\xbf'; sed "s/@VERSION@/$version/; s/\$/\r/" "$root/patcher/README.txt"; } > "$dir/README.txt"
  sed 's/$/\r/' "$root/patcher/kami-zh.conf" > "$dir/kami-zh.conf"
  (cd "$work" && zip -qrX "$dist/$1.zip" "$1")
}

cd "$root/patcher"
GOOS=windows GOARCH=amd64 go build -trimpath -ldflags=-s -o "$work/win/kami-zh-patch.exe" .
package "kami-zh-patch-$version-windows" "$work/win/kami-zh-patch.exe"

GOOS=darwin GOARCH=arm64 go build -trimpath -ldflags=-s -o "$work/arm64" .
GOOS=darwin GOARCH=amd64 go build -trimpath -ldflags=-s -o "$work/amd64" .
mkdir -p "$work/mac"
lipo -create -output "$work/mac/kami-zh-patch" "$work/arm64" "$work/amd64"
package "kami-zh-patch-$version-macos" "$work/mac/kami-zh-patch"

ls -l "$dist"

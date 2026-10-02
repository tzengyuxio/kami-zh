#!/usr/bin/env bash
# Copy the original game into build/ and apply every translation TSV.
#
#   tools/build.sh
#
# game/ stays pristine; everything lands in build/.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
py="$root/.venv/bin/python"
cd "$root"

mkdir -p build/KAMI
cp game/KAMI/* build/KAMI/

# KAMI.COM chains FMDRV -> OPEN.EXE -> MAIN.EXE. Point the OPEN slot at
# MAIN.EXE so testing skips the two-minute opening; MAIN.EXE cannot be run
# on its own because KAMI.COM is what installs the INT 65h handler it needs.
if [ "${SKIP_OPENING:-1}" = "1" ]; then
  "$py" - <<'PY'
d = bytearray(open('build/KAMI/KAMI.COM', 'rb').read())
i = d.find(b'OPEN.EXE\x00')
d[i:i + 8] = b'MAIN.EXE'
open('build/KAMI/KAMI.COM', 'wb').write(bytes(d))
PY
fi

apply() {  # apply <tsv> <target-file> [xor]
  local tsv=$1 target=$2 xor=${3:-0}
  local tmp; tmp=$(mktemp -t kami-patch)
  cp "build/KAMI/$target" "$tmp"
  "$py" tools/patch.py apply --tsv "$tsv" --target "$tmp" \
      --out "build/KAMI/$target" --xor "$xor"
  rm "$tmp"
}

apply translation/trial_main_ui.tsv   MAIN.EXE
apply translation/trial_startmenu.tsv MAIN.EXE
apply translation/trial_event.tsv     EVENT.DAT 0x77

for f in MAIN.EXE EVENT.DAT; do
  a=$(stat -f%z "game/KAMI/$f"); b=$(stat -f%z "build/KAMI/$f")
  [ "$a" = "$b" ] || { echo "$f 大小改變了: $a -> $b" >&2; exit 1; }
done
echo "build/ 已就緒，檔案大小與原版一致"

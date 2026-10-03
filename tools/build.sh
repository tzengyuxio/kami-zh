#!/usr/bin/env bash
# Copy the original game into build/ and apply every translation TSV.
#
#   tools/build.sh
#
# game/ stays pristine; everything lands in build/.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# The patch path is pure stdlib, so any python3 will do; .venv is only needed
# for the graphics tools (pillow). Prefer it when present.
if [ -x "$root/.venv/bin/python" ]; then
  py="$root/.venv/bin/python"
elif command -v python3 > /dev/null; then
  py=python3
else
  echo "找不到 python3" >&2
  exit 1
fi
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

# In-place string patches: these must fit the slot they overwrite.
apply() {  # apply <tsv> <target-file>
  local tsv=$1 target=$2
  local tmp; tmp=$(mktemp -t kami-patch)
  cp "build/KAMI/$target" "$tmp"
  "$py" tools/patch.py apply --tsv "$tsv" --target "$tmp" --out "build/KAMI/$target"
  rm "$tmp"
}

apply translation/main_ui.tsv         MAIN.EXE
apply translation/trial_startmenu.tsv MAIN.EXE

# Name tables: fixed-stride records, 14 bytes of name each.
"$py" tools/tables.py game/KAMI/SDATA.CIM --table SDATA.CIM \
    --glossary translation/glossary.tsv --out build/KAMI/SDATA.CIM

# monster names (RPDATA.CIM, same fixed-width records)
"$py" tools/tables.py game/KAMI/RPDATA.CIM --table RPDATA.CIM \
    --glossary translation/glossary.tsv --out build/KAMI/RPDATA.CIM

# Story text: EVENT.DAT is rebuilt from scratch, so translations may be any
# length. The block offsets this moves live in MAIN.EXE, which is why the
# already-patched MAIN.EXE goes in and comes back out.
"$py" tools/event.py --event game/KAMI/EVENT.DAT --main build/KAMI/MAIN.EXE \
    apply --tsv translation/event.tsv \
    --out-event build/KAMI/EVENT.DAT --out-main build/KAMI/MAIN.EXE

# MAIN.EXE is patched in place and must keep its size; EVENT.DAT may not.
a=$(stat -f%z game/KAMI/MAIN.EXE); b=$(stat -f%z build/KAMI/MAIN.EXE)
[ "$a" = "$b" ] || { echo "MAIN.EXE 大小改變了: $a -> $b" >&2; exit 1; }
echo "build/ 已就緒 (MAIN.EXE $b bytes, EVENT.DAT $(stat -f%z build/KAMI/EVENT.DAT) bytes)"
